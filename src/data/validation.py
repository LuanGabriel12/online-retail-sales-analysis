"""Validação estrutural e diagnóstico completo de qualidade dos dados."""

from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

from src.config import DATASET_METADATA, REQUIRED_COLUMNS


def validate_required_schema(df_raw: pd.DataFrame) -> None:
    """Valida a presença de todas as colunas obrigatórias no dataset bruto."""
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df_raw.columns]
    if missing_cols:
        raise ValueError(
            f"Colunas obrigatórias ausentes no dataset: {missing_cols}"
        )


def parse_exact_decimal(value) -> tuple[Decimal | None, bool]:
    """Converte valor numérico finito para Decimal exato sem passagem intermediária por float."""
    if isinstance(value, bool) or value is None:
        return None, False

    if isinstance(value, Decimal):
        return (value, True) if value.is_finite() else (None, False)

    if isinstance(value, int):
        return Decimal(value), True

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None, False
        try:
            dec_val = Decimal(cleaned)
        except InvalidOperation:
            return None, False
        return (dec_val, True) if dec_val.is_finite() else (None, False)

    if pd.isna(value):
        return None, False

    try:
        dec_val = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None, False
    return (dec_val, True) if dec_val.is_finite() else (None, False)


def parse_exact_integer(value) -> tuple[int | None, bool]:
    """Converte valor numérico finito exatamente inteiro para int sem perda acima de 2**53."""
    if isinstance(value, bool) or value is None:
        return None, False

    if isinstance(value, int):
        return value, True

    dec_val, is_valid_dec = parse_exact_decimal(value)
    if not is_valid_dec or dec_val is None:
        return None, False

    sign, digits, exponent = dec_val.as_tuple()
    if not isinstance(exponent, int):
        return None, False

    if exponent >= 0:
        # Evita expansão desproporcional de expoentes científicos extremos
        if exponent > 18:
            return None, False
        digits_str = "".join(str(d) for d in digits) + ("0" * exponent)
        parsed = int(digits_str) if digits_str else 0
        return (-parsed if sign else parsed), True

    frac_len = -exponent
    if len(digits) <= frac_len:
        if all(d == 0 for d in digits):
            return 0, True
        return None, False

    if any(d != 0 for d in digits[-frac_len:]):
        return None, False

    int_digits = digits[:-frac_len]
    parsed = int("".join(str(d) for d in int_digits)) if int_digits else 0
    return (-parsed if sign else parsed), True


def is_finite_number(value) -> bool:
    """Verifica se o valor é numérico finito (exclui NaN, inf, -inf e booleanos)."""
    _dec, ok = parse_exact_decimal(value)
    return ok


def is_finite_integer(value) -> bool:
    """Verifica se o valor é numérico finito e exatamente inteiro sem conversão para float."""
    _val, ok = parse_exact_integer(value)
    return ok


def parse_customer_id(value) -> tuple[str | None, str]:
    """Valida e padroniza CustomerID distinguindo 'valido', 'ausente' e 'invalido'.

    Regras explícitas (usando int e Decimal, sem truncamento nem perda acima de 2**53):
    - `None`, `NaN` ou texto vazio/espaços -> `(None, 'ausente')`.
    - Inteiro positivo finito (incluindo int > 2**53, Decimal inteiro, float `.0` exato
      ou texto `'17850'`/`'17850.0'`) -> `('<digitos>', 'valido')`.
    - Fracionados (`123.5`, `'123.5'`), infinitos (`inf`, `-inf`), zero/negativos,
      notação científica textual (`'1e5'`), booleanos ou textos malformados (`'ABC'`,
      `'12.3.4'`) -> `(None, 'invalido')`, sem jamais truncar o identificador.
    """
    if isinstance(value, bool):
        return None, "invalido"

    if value is None:
        return None, "ausente"

    if isinstance(value, int):
        if value > 0:
            return str(value), "valido"
        return None, "invalido"

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None, "ausente"
        if cleaned.isdigit():
            parsed_int = int(cleaned)
            if parsed_int > 0:
                return str(parsed_int), "valido"
            return None, "invalido"
        parts = cleaned.split(".")
        if (
            len(parts) == 2
            and parts[0].isdigit()
            and parts[1].isdigit()
            and set(parts[1]) == {"0"}
        ):
            parsed_int = int(parts[0])
            if parsed_int > 0:
                return str(parsed_int), "valido"
        return None, "invalido"

    if isinstance(value, Decimal):
        if value.is_nan():
            return None, "ausente"
        parsed_int, ok = parse_exact_integer(value)
        if ok and parsed_int is not None and parsed_int > 0:
            return str(parsed_int), "valido"
        return None, "invalido"

    if pd.isna(value):
        return None, "ausente"

    parsed_int, ok = parse_exact_integer(value)
    if ok and parsed_int is not None and parsed_int > 0:
        return str(parsed_int), "valido"
    return None, "invalido"


def _normalize_id_series(series: pd.Series) -> pd.Series:
    """Converte identificadores para texto limpo sem transformar nulos em 'nan'."""
    values: list[str | None] = []
    for item in series:
        if pd.isna(item):
            values.append(None)
        else:
            cleaned = str(item).strip()
            values.append(cleaned if cleaned else None)
    return pd.Series(values, index=series.index, dtype="object")


def _count_unit_prices_above_2dp(
    parsed_prices: list[tuple[Decimal | None, bool]],
    raw_prices: pd.Series,
) -> dict[str, int]:
    """Identifica preços unitários finitos com precisão superior a duas casas decimais."""
    gt_2dp: dict[str, int] = {}
    for (dec_val, ok), raw_val in zip(parsed_prices, raw_prices):
        if not ok or dec_val is None:
            continue
        normalized = dec_val.normalize()
        exponent = normalized.as_tuple().exponent
        decimals = -exponent if isinstance(exponent, int) and exponent < 0 else 0
        if decimals > 2:
            key = str(raw_val).strip()
            gt_2dp[key] = gt_2dp.get(key, 0) + 1
    return gt_2dp


def audit_raw_data_quality(df_raw: pd.DataFrame) -> dict[str, Any]:
    """Executa auditoria completa das 8 colunas, tipos, duplicatas e conflitos."""
    validate_required_schema(df_raw)

    total_rows = int(len(df_raw))
    total_cols = int(len(df_raw.columns))

    dtypes_map = {col: str(df_raw[col].dtype) for col in df_raw.columns}

    # Valores ausentes por coluna
    missing_summary: list[dict[str, Any]] = []
    for col in REQUIRED_COLUMNS:
        n_missing = int(df_raw[col].isna().sum())
        pct_missing = round((n_missing / total_rows) * 100, 4) if total_rows > 0 else 0.0
        missing_summary.append(
            {
                "coluna": col,
                "ausentes": n_missing,
                "percentual": pct_missing,
            }
        )

    # Duplicatas exatas na base bruta
    exact_duplicates_extra = int(df_raw.duplicated().sum())
    exact_duplicates_involved = int(df_raw.duplicated(keep=False).sum())

    # Datas
    invoice_dates = pd.to_datetime(df_raw["InvoiceDate"], errors="coerce")
    invalid_dates = int(invoice_dates.isna().sum())
    min_date = invoice_dates.min()
    max_date = invoice_dates.max()
    expected_start = DATASET_METADATA["periodo_esperado_inicio"]
    expected_end = DATASET_METADATA["periodo_esperado_fim"]
    dates_outside_expected = int(
        ((invoice_dates < expected_start) | (invoice_dates > expected_end)).sum()
    )

    # Padrões de InvoiceNo
    inv_norm = _normalize_id_series(df_raw["InvoiceNo"])
    inv_upper = inv_norm.astype(str).str.upper()
    inv_missing = int(inv_norm.isna().sum())
    starts_with_c = inv_norm.notna() & inv_upper.str.startswith("C")
    starts_with_a = inv_norm.notna() & inv_upper.str.startswith("A")
    all_digits = inv_norm.notna() & inv_norm.astype(str).str.isdigit()
    other_invoice_pattern = inv_norm.notna() & ~(starts_with_c | starts_with_a | all_digits)

    # Padrões de StockCode e Description
    stk_norm = _normalize_id_series(df_raw["StockCode"])
    stk_upper = stk_norm.astype(str).str.upper()
    distinct_stock_raw = int(stk_norm.nunique(dropna=True))
    distinct_stock_upper = int(stk_upper[stk_norm.notna()].nunique())

    # Produtos com múltiplas descrições (na base bruta)
    temp_prod = pd.DataFrame(
        {
            "stock_upper": stk_upper,
            "stock_valid": stk_norm.notna(),
            "desc_clean": df_raw["Description"].astype("object"),
        }
    )
    temp_prod = temp_prod[temp_prod["stock_valid"]].copy()
    cleaned_descs: list[str | None] = []
    for item in temp_prod["desc_clean"]:
        if pd.isna(item):
            cleaned_descs.append(None)
        else:
            cleaned_descs.append(str(item).strip())
    temp_prod["desc_stripped"] = cleaned_descs

    desc_per_stock = (
        temp_prod.dropna(subset=["desc_stripped"])
        .groupby("stock_upper")["desc_stripped"]
        .nunique()
    )
    products_multiple_descriptions = int((desc_per_stock > 1).sum())

    # Integridade exata de Quantity, UnitPrice e CustomerID (sem conversão para float)
    parsed_qty = [parse_exact_integer(q) for q in df_raw["Quantity"]]
    parsed_price = [parse_exact_decimal(p) for p in df_raw["UnitPrice"]]

    qty_fractional_or_invalid = sum(1 for _val, ok in parsed_qty if not ok)
    price_non_finite = sum(1 for _val, ok in parsed_price if not ok)

    parsed_cids = [parse_customer_id(v) for v in df_raw["CustomerID"]]
    cid_parsed_series = pd.Series(
        [item[0] for item in parsed_cids], index=df_raw.index, dtype="object"
    )
    cid_status_series = pd.Series(
        [item[1] for item in parsed_cids], index=df_raw.index, dtype="object"
    )
    cid_ausentes = int((cid_status_series == "ausente").sum())
    cid_invalidos = int((cid_status_series == "invalido").sum())

    # Sinais de Quantity e UnitPrice (apenas sobre valores exatos válidos)
    qty_positive = sum(1 for q, ok in parsed_qty if ok and q is not None and q > 0)
    qty_zero = sum(1 for q, ok in parsed_qty if ok and q == 0)
    qty_negative = sum(1 for q, ok in parsed_qty if ok and q is not None and q < 0)
    qty_negative_without_c = sum(
        1
        for is_c, (q, ok) in zip(starts_with_c, parsed_qty)
        if (not is_c) and ok and q is not None and q < 0
    )

    zero_dec = Decimal("0")
    price_positive = sum(
        1 for p, ok in parsed_price if ok and p is not None and p > zero_dec
    )
    price_zero = sum(
        1 for p, ok in parsed_price if ok and p is not None and p == zero_dec
    )
    price_negative = sum(
        1 for p, ok in parsed_price if ok and p is not None and p < zero_dec
    )

    # Precisão de UnitPrice (> 2 casas decimais)
    unit_price_gt_2dp = _count_unit_prices_above_2dp(parsed_price, df_raw["UnitPrice"])

    # Consistência por pedido (InvoiceNo) na base bruta
    temp_inv = pd.DataFrame(
        {
            "invoice_no": inv_upper,
            "invoice_valid": inv_norm.notna(),
            "customer_id": cid_parsed_series,
            "country": df_raw["Country"],
            "invoice_date": invoice_dates,
            "stock_code": stk_upper,
        }
    )
    temp_inv = temp_inv[temp_inv["invoice_valid"]].copy()

    inv_group = temp_inv.groupby("invoice_no").agg(
        linhas=("stock_code", "count"),
        produtos_distintos=("stock_code", "nunique"),
        clientes_nao_nulos=("customer_id", "nunique"),
        paises_distintos=("country", "nunique"),
        datas_distintas=("invoice_date", "nunique"),
    )
    orders_with_multiple_items = int((inv_group["linhas"] > 1).sum())
    orders_with_multiple_products = int((inv_group["produtos_distintos"] > 1).sum())
    orders_conflicting_customer = int((inv_group["clientes_nao_nulos"] > 1).sum())
    orders_conflicting_country = int((inv_group["paises_distintos"] > 1).sum())
    orders_multiple_timestamps = int((inv_group["datas_distintas"] > 1).sum())

    # Verifica também mistura de cliente preenchido e nulo no mesmo InvoiceNo
    has_null_cust = (
        temp_inv.assign(is_null=temp_inv["customer_id"].isna())
        .groupby("invoice_no")["is_null"]
        .nunique()
    )
    orders_mixed_null_customer = int((has_null_cust > 1).sum())

    # Clientes em múltiplos países (apenas sobre CustomerID válidos)
    temp_cust_country = pd.DataFrame(
        {"customer_id": cid_parsed_series, "country": df_raw["Country"]}
    ).dropna(subset=["customer_id"])
    if not temp_cust_country.empty:
        cust_country_nunique = temp_cust_country.groupby("customer_id")[
            "country"
        ].nunique()
        customers_multiple_countries = int((cust_country_nunique > 1).sum())
    else:
        customers_multiple_countries = 0

    return {
        "total_linhas_brutas": total_rows,
        "total_colunas": total_cols,
        "tipos_colunas": dtypes_map,
        "valores_ausentes": missing_summary,
        "duplicatas_exatas_excedentes": exact_duplicates_extra,
        "linhas_envolvidas_duplicatas_exatas": exact_duplicates_involved,
        "datas_invalidas": invalid_dates,
        "data_minima": str(min_date) if pd.notna(min_date) else None,
        "data_maxima": str(max_date) if pd.notna(max_date) else None,
        "datas_fora_periodo_esperado": dates_outside_expected,
        "invoice_no_ausentes": inv_missing,
        "linhas_invoice_numerico": int(all_digits.sum()),
        "pedidos_distintos_numerico": int(inv_upper[all_digits].nunique()),
        "linhas_invoice_prefixo_c": int(starts_with_c.sum()),
        "notas_cancelamento_distintas": int(inv_upper[starts_with_c].nunique()),
        "linhas_invoice_prefixo_a": int(starts_with_a.sum()),
        "notas_ajuste_prefixo_a_distintas": int(inv_upper[starts_with_a].nunique()),
        "linhas_invoice_outro_padrao": int(other_invoice_pattern.sum()),
        "stock_code_distintos_bruto": distinct_stock_raw,
        "stock_code_distintos_maiusculo": distinct_stock_upper,
        "variacoes_caixa_stock_code": distinct_stock_raw - distinct_stock_upper,
        "produtos_multiplas_descricoes": products_multiple_descriptions,
        "quantidade_positiva": qty_positive,
        "quantidade_zero": qty_zero,
        "quantidade_negativa": qty_negative,
        "quantidade_negativa_sem_prefixo_c": qty_negative_without_c,
        "quantidades_fracionadas_ou_nao_finitas": qty_fractional_or_invalid,
        "preco_positivo": price_positive,
        "preco_zero": price_zero,
        "preco_negativo": price_negative,
        "precos_nao_finitos": price_non_finite,
        "customer_ids_ausentes": cid_ausentes,
        "customer_ids_invalidos": cid_invalidos,
        "unit_price_acima_2_casas": unit_price_gt_2dp,
        "pedidos_com_multiplas_linhas": orders_with_multiple_items,
        "pedidos_com_multiplos_produtos": orders_with_multiple_products,
        "pedidos_conflito_cliente": orders_conflicting_customer,
        "pedidos_mistura_cliente_nulo": orders_mixed_null_customer,
        "pedidos_conflito_pais": orders_conflicting_country,
        "pedidos_multiplos_timestamps": orders_multiple_timestamps,
        "clientes_multiplos_paises": customers_multiple_countries,
    }


def validate_order_level_consistency(df_sales: pd.DataFrame) -> dict[str, Any]:
    """Valida consistência de cliente, país e data por pedido antes de consolidar."""
    grouped = df_sales.groupby("invoice_no").agg(
        clientes_nao_nulos=("customer_id", "nunique"),
        paises_distintos=("country", "nunique"),
        datas_distintas=("invoice_date", "nunique"),
        data_min=("invoice_date", "min"),
        data_max=("invoice_date", "max"),
    )

    mixed_null_cust = (
        df_sales.assign(is_null=df_sales["customer_id"].isna())
        .groupby("invoice_no")["is_null"]
        .nunique()
    )

    conflicting_customer_ids = list(
        grouped[grouped["clientes_nao_nulos"] > 1].index
    )
    mixed_null_customer_ids = list(mixed_null_cust[mixed_null_cust > 1].index)
    conflicting_country_ids = list(grouped[grouped["paises_distintos"] > 1].index)

    multi_date = grouped[grouped["datas_distintas"] > 1].copy()
    max_time_diff_seconds = 0.0
    same_calendar_day_count = 0
    if not multi_date.empty:
        diffs = (multi_date["data_max"] - multi_date["data_min"]).dt.total_seconds()
        max_time_diff_seconds = float(diffs.max())
        same_calendar_day_count = int(
            (
                multi_date["data_min"].dt.normalize()
                == multi_date["data_max"].dt.normalize()
            ).sum()
        )

    return {
        "total_pedidos_verificados": int(len(grouped)),
        "pedidos_conflito_cliente": len(conflicting_customer_ids),
        "ids_conflito_cliente": conflicting_customer_ids,
        "pedidos_mistura_cliente_nulo": len(mixed_null_customer_ids),
        "ids_mistura_cliente_nulo": mixed_null_customer_ids,
        "pedidos_conflito_pais": len(conflicting_country_ids),
        "ids_conflito_pais": conflicting_country_ids,
        "pedidos_multiplos_timestamps": int(len(multi_date)),
        "pedidos_multiplos_timestamps_mesmo_dia": same_calendar_day_count,
        "diferenca_maxima_segundos_mesmo_pedido": max_time_diff_seconds,
    }
