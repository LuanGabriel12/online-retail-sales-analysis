"""Classificação mutuamente exclusiva, limpeza e padronização dos dados."""

from decimal import Decimal
from typing import Any

import pandas as pd

from src.config import NON_MERCHANDISE_STOCK_CODES, REQUIRED_COLUMNS
from src.data.validation import (
    parse_customer_id,
    parse_exact_decimal,
    parse_exact_integer,
    validate_required_schema,
)


# Categorias mutuamente exclusivas da triagem inicial (antes de deduplicação)
CATEGORY_VALID_SALE_RAW = "venda_positiva_valida"
CATEGORY_CANCELLATION = "cancelamento_identificado"
CATEGORY_ACCOUNTING_ADJUSTMENT = "ajuste_contabil_prefixo_a"
CATEGORY_NEGATIVE_QTY_NO_C = "quantidade_negativa_sem_prefixo_c"
CATEGORY_NON_POSITIVE_PRICE = "preco_nao_positivo"
CATEGORY_AMBIGUOUS_OR_INVALID = "registro_ambiguo_ou_inconsistente"

ALL_TRIAGE_CATEGORIES = [
    CATEGORY_VALID_SALE_RAW,
    CATEGORY_CANCELLATION,
    CATEGORY_ACCOUNTING_ADJUSTMENT,
    CATEGORY_NEGATIVE_QTY_NO_C,
    CATEGORY_NON_POSITIVE_PRICE,
    CATEGORY_AMBIGUOUS_OR_INVALID,
]

_INT64_MIN = -(2**63)
_INT64_MAX = 2**63 - 1


def _clean_text(value) -> str | None:
    """Remove espaços nas extremidades preservando valores ausentes."""
    if pd.isna(value):
        return None
    cleaned = str(value).strip()
    return cleaned if cleaned else None


def _finalize_exact_int_column(series: pd.Series) -> pd.Series:
    """Mantém int64 quando todos os inteiros cabem em 64 bits; senão preserva int exato."""
    if series.empty:
        return pd.Series(dtype="int64")
    int_values = [int(v) for v in series]
    if all(_INT64_MIN <= v <= _INT64_MAX for v in int_values):
        return pd.Series(int_values, index=series.index, dtype="int64")
    return pd.Series(int_values, index=series.index, dtype="object")


def standardize_raw_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Cria cópia padronizada preservando todas as linhas originais sem perda > 2**53."""
    validate_required_schema(df_raw)
    df = df_raw.copy()

    df["invoice_no"] = [
        _clean_text(v).upper() if _clean_text(v) is not None else None
        for v in df["InvoiceNo"]
    ]
    df["stock_code_original"] = [_clean_text(v) for v in df["StockCode"]]
    df["stock_code"] = [
        v.upper() if v is not None else None for v in df["stock_code_original"]
    ]
    df["description"] = [_clean_text(v) for v in df["Description"]]
    df["invoice_date"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")

    # Parsing exato via int e Decimal (sem pd.to_numeric para não perder precisão > 2**53)
    parsed_qty = [parse_exact_integer(q) for q in df["Quantity"]]
    df["quantity"] = pd.Series(
        [item[0] for item in parsed_qty], index=df.index, dtype="object"
    )
    df["quantity_valida_inteira"] = [item[1] for item in parsed_qty]

    parsed_price = [parse_exact_decimal(p) for p in df["UnitPrice"]]
    df["unit_price_decimal"] = [item[0] for item in parsed_price]
    df["unit_price_finito"] = [item[1] for item in parsed_price]
    df["unit_price"] = [
        float(dec) if dec is not None else float("nan")
        for dec in df["unit_price_decimal"]
    ]

    parsed_cids = [parse_customer_id(v) for v in df["CustomerID"]]
    df["customer_id"] = [item[0] for item in parsed_cids]
    df["customer_id_status"] = [item[1] for item in parsed_cids]
    df["country"] = [_clean_text(v) for v in df["Country"]]

    # Flags estruturais auxiliares
    df["is_non_merchandise_code"] = df["stock_code"].isin(NON_MERCHANDISE_STOCK_CODES)

    # Valor monetário exato em Decimal e espelho float64 para agregações de apoio
    valores_float: list[float] = []
    valores_decimais: list[Decimal] = []
    for qty_int, price_dec in zip(df["quantity"], df["unit_price_decimal"]):
        if qty_int is None or price_dec is None:
            valores_float.append(0.0)
            valores_decimais.append(Decimal("0"))
        else:
            val_dec = Decimal(qty_int) * price_dec
            valores_decimais.append(val_dec)
            valores_float.append(float(val_dec))
    df["valor_linha"] = valores_float
    df["valor_linha_decimal"] = valores_decimais

    # Colunas temporais de apoio
    df["ano_mes"] = df["invoice_date"].dt.strftime("%Y-%m")
    df["data_dia"] = df["invoice_date"].dt.normalize()

    return df


def classify_raw_record(
    invoice_no: str | None,
    stock_code: str | None,
    quantity,
    unit_price,
    invoice_date,
    country: str | None,
    customer_id_status: str = "ausente",
) -> str:
    """Classifica cada linha bruta em exatamente uma categoria mutuamente exclusiva.

    Política estrita de integridade (sem conversão intermediária para float):
    - Quantidades não finitas ou fracionadas (ex.: 1.5, inf, -inf, NaN) são classificadas
      como `registro_ambiguo_ou_inconsistente` e nunca truncadas silenciosamente.
    - Quantidades inteiras acima de 2**53 preservam precisão exata via int/Decimal.
    - Preços unitários não finitos (inf, -inf, NaN) são classificados como
      `registro_ambiguo_ou_inconsistente`.
    - `CustomerID` ausente (`ausente`) é permitido em vendas gerais; já `CustomerID`
      inválido (`invalido`, ex.: 123.5, inf, negativo, zero ou texto malformado) é
      classificado como `registro_ambiguo_ou_inconsistente` e nunca truncado.
    """
    qty_int, qty_ok = parse_exact_integer(quantity)
    price_dec, price_ok = parse_exact_decimal(unit_price)

    if (
        invoice_no is None
        or stock_code is None
        or country is None
        or pd.isna(invoice_date)
        or not qty_ok
        or qty_int is None
        or not price_ok
        or price_dec is None
        or customer_id_status == "invalido"
    ):
        return CATEGORY_AMBIGUOUS_OR_INVALID

    zero_dec = Decimal("0")

    if invoice_no.startswith("C"):
        if qty_int < 0 and price_dec > zero_dec:
            return CATEGORY_CANCELLATION
        return CATEGORY_AMBIGUOUS_OR_INVALID

    if invoice_no.startswith("A"):
        return CATEGORY_ACCOUNTING_ADJUSTMENT

    if not invoice_no.isdigit():
        return CATEGORY_AMBIGUOUS_OR_INVALID

    if qty_int == 0:
        return CATEGORY_AMBIGUOUS_OR_INVALID

    if qty_int < 0:
        return CATEGORY_NEGATIVE_QTY_NO_C

    if price_dec <= zero_dec:
        return CATEGORY_NON_POSITIVE_PRICE

    return CATEGORY_VALID_SALE_RAW


def classify_all_records(df_std: pd.DataFrame) -> pd.DataFrame:
    """Aplica classificação mutuamente exclusiva a todas as linhas padronizadas."""
    df_classified = df_std.copy()
    categorias: list[str] = []
    for inv, stk, qty, price_dec, dt, country, cid_status in zip(
        df_classified["invoice_no"],
        df_classified["stock_code"],
        df_classified["quantity"],
        df_classified["unit_price_decimal"],
        df_classified["invoice_date"],
        df_classified["country"],
        df_classified["customer_id_status"],
    ):
        categorias.append(
            classify_raw_record(inv, stk, qty, price_dec, dt, country, cid_status)
        )
    df_classified["categoria_registro"] = categorias
    return df_classified


def build_clean_datasets(df_raw: pd.DataFrame) -> dict[str, Any]:
    """Executa triagem, deduplicação e gera bases V2, V1 histórica e trilha de auditoria."""
    df_std = standardize_raw_dataframe(df_raw)
    df_classified = classify_all_records(df_std)

    # Recorte de vendas positivas válidas (sem prefixo C/A, qty inteira > 0, price finito > 0, CustomerID não inválido)
    mask_valid_raw = df_classified["categoria_registro"] == CATEGORY_VALID_SALE_RAW
    df_valid_raw = df_classified.loc[mask_valid_raw].copy()
    df_valid_raw["quantity"] = _finalize_exact_int_column(df_valid_raw["quantity"])

    # Identifica duplicatas exatas considerando as 8 colunas originais do dataset
    dup_mask_valid = df_valid_raw.duplicated(subset=REQUIRED_COLUMNS, keep="first")
    df_exact_duplicates_removed = df_valid_raw.loc[dup_mask_valid].copy()
    df_sales_v2 = df_valid_raw.loc[~dup_mask_valid].copy()
    df_sales_v2["quantity"] = _finalize_exact_int_column(df_sales_v2["quantity"])

    # Reprodução fiel da regra da V1 (Quantity > 0 e UnitPrice > 0 + drop_duplicates),
    # protegida contra valores não finitos, fracionados ou CustomerID inválido
    zero_dec = Decimal("0")
    mask_v1_raw = [
        qty_ok
        and price_ok
        and (cid_status != "invalido")
        and (qty_val is not None and qty_val > 0)
        and (price_dec is not None and price_dec > zero_dec)
        for qty_ok, price_ok, cid_status, qty_val, price_dec in zip(
            df_classified["quantity_valida_inteira"],
            df_classified["unit_price_finito"],
            df_classified["customer_id_status"],
            df_classified["quantity"],
            df_classified["unit_price_decimal"],
        )
    ]
    df_v1_raw = df_classified.loc[mask_v1_raw].copy()
    df_sales_v1 = df_v1_raw.drop_duplicates(subset=REQUIRED_COLUMNS, keep="first").copy()
    df_sales_v1["quantity"] = _finalize_exact_int_column(df_sales_v1["quantity"])

    # Contagem mutuamente exclusiva para reconciliação de linhas
    contagem_triagem: dict[str, int] = {}
    for categoria in ALL_TRIAGE_CATEGORIES:
        contagem_triagem[categoria] = int(
            (df_classified["categoria_registro"] == categoria).sum()
        )

    # Contagens explícitas de integridade numérica e de CustomerID
    qty_invalid_count = int((~df_classified["quantity_valida_inteira"]).sum())
    price_non_finite_count = int((~df_classified["unit_price_finito"]).sum())
    cid_missing_count = int((df_classified["customer_id_status"] == "ausente").sum())
    cid_invalid_count = int((df_classified["customer_id_status"] == "invalido").sum())

    # Detalhes dos registros que diferenciam V1 de V2 (ex.: A563185 no dataset oficial)
    v2_keys_index = set(df_sales_v2.index)
    v1_only_df = df_sales_v1.loc[~df_sales_v1.index.isin(v2_keys_index)]
    diferenca_v1_vs_v2_detalhes = [
        {
            "invoice_no": inv,
            "stock_code": stk,
            "description": desc,
            "valor_decimal": str(val_dec),
        }
        for inv, stk, desc, val_dec in zip(
            v1_only_df["invoice_no"],
            v1_only_df["stock_code"],
            v1_only_df["description"],
            v1_only_df["valor_linha_decimal"],
        )
    ]

    resumo_limpeza = {
        "linhas_brutas": int(len(df_classified)),
        "contagem_triagem": contagem_triagem,
        "vendas_positivas_antes_deduplicacao": int(len(df_valid_raw)),
        "duplicatas_exatas_removidas_em_vendas": int(len(df_exact_duplicates_removed)),
        "valor_duplicatas_removidas_decimal": sum(
            df_exact_duplicates_removed["valor_linha_decimal"], Decimal("0")
        ),
        "linhas_mantidas_v2": int(len(df_sales_v2)),
        "linhas_excluidas_nao_venda": int(len(df_classified) - len(df_valid_raw)),
        "linhas_excluidas_total_v2": int(len(df_classified) - len(df_sales_v2)),
        "linhas_mantidas_v1_equivalente": int(len(df_sales_v1)),
        "diferenca_linhas_v1_vs_v2": int(len(df_sales_v1) - len(df_sales_v2)),
        "diferenca_v1_vs_v2_detalhes": diferenca_v1_vs_v2_detalhes,
        "quantidades_fracionadas_ou_nao_finitas": qty_invalid_count,
        "precos_nao_finitos": price_non_finite_count,
        "customer_ids_ausentes": cid_missing_count,
        "customer_ids_invalidos": cid_invalid_count,
    }

    return {
        "df_classified": df_classified,
        "df_valid_raw": df_valid_raw,
        "df_exact_duplicates_removed": df_exact_duplicates_removed,
        "df_sales_v2": df_sales_v2,
        "df_sales_v1": df_sales_v1,
        "resumo_limpeza": resumo_limpeza,
    }
