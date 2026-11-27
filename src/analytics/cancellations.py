"""Análise separada de cancelamentos, negativos sem prefixo C e registros atípicos."""

from decimal import Decimal
from typing import Any

import pandas as pd

from src.analytics.orders import sum_decimal_by_key
from src.config import REQUIRED_COLUMNS
from src.data.cleaning import (
    CATEGORY_ACCOUNTING_ADJUSTMENT,
    CATEGORY_AMBIGUOUS_OR_INVALID,
    CATEGORY_CANCELLATION,
    CATEGORY_NEGATIVE_QTY_NO_C,
    CATEGORY_NON_POSITIVE_PRICE,
)


def analyze_cancellations_and_anomalies(
    df_classified: pd.DataFrame,
    df_sales_v2: pd.DataFrame,
) -> dict[str, Any]:
    """Analisa cancelamentos (prefixo C) e demais categorias não-venda separadamente."""
    df_canc_raw = df_classified.loc[
        df_classified["categoria_registro"] == CATEGORY_CANCELLATION
    ].copy()
    dup_canc = df_canc_raw.duplicated(subset=REQUIRED_COLUMNS, keep="first")
    df_canc_dedup = df_canc_raw.loc[~dup_canc].copy()

    df_neg_no_c = df_classified.loc[
        df_classified["categoria_registro"] == CATEGORY_NEGATIVE_QTY_NO_C
    ].copy()
    df_non_pos_price = df_classified.loc[
        df_classified["categoria_registro"] == CATEGORY_NON_POSITIVE_PRICE
    ].copy()
    df_adj_a = df_classified.loc[
        df_classified["categoria_registro"] == CATEGORY_ACCOUNTING_ADJUSTMENT
    ].copy()
    df_ambiguous = df_classified.loc[
        df_classified["categoria_registro"] == CATEGORY_AMBIGUOUS_OR_INVALID
    ].copy()

    vendas_v2_dec = sum(df_sales_v2["valor_linha_decimal"], Decimal("0"))
    canc_raw_dec = sum(df_canc_raw["valor_linha_decimal"], Decimal("0"))
    canc_dedup_dec = sum(df_canc_dedup["valor_linha_decimal"], Decimal("0"))

    pct_canc_raw = (
        float((abs(canc_raw_dec) / vendas_v2_dec) * Decimal("100"))
        if vendas_v2_dec > 0
        else 0.0
    )
    pct_canc_dedup = (
        float((abs(canc_dedup_dec) / vendas_v2_dec) * Decimal("100"))
        if vendas_v2_dec > 0
        else 0.0
    )

    saldo_observado_raw = vendas_v2_dec + canc_raw_dec
    saldo_observado_dedup = vendas_v2_dec + canc_dedup_dec

    # Distribuição de cancelamentos por produto (usando cancelamentos deduplicados)
    if not df_canc_dedup.empty:
        prod_desc = (
            df_canc_dedup.dropna(subset=["description"])
            .groupby(["stock_code", "description"])
            .agg(ocorrencias=("invoice_no", "count"))
            .reset_index()
            .sort_values(
                by=["stock_code", "ocorrencias", "description"],
                ascending=[True, False, True],
            )
        )
        desc_map: dict[str, str] = {}
        for code, desc in zip(prod_desc["stock_code"], prod_desc["description"]):
            if code not in desc_map:
                desc_map[code] = desc

        canc_by_product = (
            df_canc_dedup.groupby("stock_code")
            .agg(
                linhas_cancelamento=("invoice_no", "count"),
                notas_distintas=("invoice_no", "nunique"),
                unidades_canceladas=("quantity", "sum"),
                valor_cancelamento=("valor_linha", "sum"),
                codigo_operacional=("is_non_merchandise_code", "max"),
            )
            .reset_index()
        )
        dec_prod = sum_decimal_by_key(
            df_canc_dedup["stock_code"], df_canc_dedup["valor_linha_decimal"]
        )
        canc_by_product["valor_cancelamento_decimal"] = [
            dec_prod[c] for c in canc_by_product["stock_code"]
        ]
        canc_by_product["descricao_principal"] = [
            desc_map.get(c, "SEM DESCRIÇÃO") for c in canc_by_product["stock_code"]
        ]
        canc_by_product["valor_absoluto_cancelamento"] = canc_by_product[
            "valor_cancelamento"
        ].abs()
        canc_by_product = (
            canc_by_product.sort_values(
                by=["valor_absoluto_cancelamento", "stock_code"],
                ascending=[False, True],
            )
            .reset_index(drop=True)
        )
    else:
        canc_by_product = pd.DataFrame(
            {
                "stock_code": pd.Series(dtype="object"),
                "descricao_principal": pd.Series(dtype="object"),
                "linhas_cancelamento": pd.Series(dtype="int64"),
                "notas_distintas": pd.Series(dtype="int64"),
                "unidades_canceladas": pd.Series(dtype="int64"),
                "valor_cancelamento": pd.Series(dtype="float64"),
                "valor_cancelamento_decimal": pd.Series(dtype="object"),
                "valor_absoluto_cancelamento": pd.Series(dtype="float64"),
                "codigo_operacional": pd.Series(dtype="bool"),
            }
        )

    # Distribuição de cancelamentos por país integrada com vendas positivas V2
    sales_country = (
        df_sales_v2.groupby("country")
        .agg(
            pedidos_venda=("invoice_no", "nunique"),
            vendas_positivas=("valor_linha", "sum"),
        )
        .reset_index()
    )
    sales_country_dec = sum_decimal_by_key(
        df_sales_v2["country"], df_sales_v2["valor_linha_decimal"]
    )

    if not df_canc_dedup.empty:
        canc_country = (
            df_canc_dedup.groupby("country")
            .agg(
                linhas_cancelamento=("invoice_no", "count"),
                notas_cancelamento_distintas=("invoice_no", "nunique"),
                unidades_canceladas=("quantity", "sum"),
                valor_cancelamento=("valor_linha", "sum"),
            )
            .reset_index()
        )
        canc_country_dec = sum_decimal_by_key(
            df_canc_dedup["country"], df_canc_dedup["valor_linha_decimal"]
        )
    else:
        canc_country = pd.DataFrame(
            {
                "country": pd.Series(dtype="object"),
                "linhas_cancelamento": pd.Series(dtype="int64"),
                "notas_cancelamento_distintas": pd.Series(dtype="int64"),
                "unidades_canceladas": pd.Series(dtype="int64"),
                "valor_cancelamento": pd.Series(dtype="float64"),
            }
        )
        canc_country_dec = {}

    country_combined = sales_country.merge(canc_country, on="country", how="outer")
    country_combined["pedidos_venda"] = [
        0 if pd.isna(v) else int(v) for v in country_combined["pedidos_venda"]
    ]
    country_combined["vendas_positivas"] = [
        0.0 if pd.isna(v) else float(v) for v in country_combined["vendas_positivas"]
    ]
    country_combined["linhas_cancelamento"] = [
        0 if pd.isna(v) else int(v) for v in country_combined["linhas_cancelamento"]
    ]
    country_combined["notas_cancelamento_distintas"] = [
        0 if pd.isna(v) else int(v)
        for v in country_combined["notas_cancelamento_distintas"]
    ]
    country_combined["unidades_canceladas"] = [
        0 if pd.isna(v) else int(v) for v in country_combined["unidades_canceladas"]
    ]
    country_combined["valor_cancelamento"] = [
        0.0 if pd.isna(v) else float(v) for v in country_combined["valor_cancelamento"]
    ]

    vendas_dec_col: list[Decimal] = []
    canc_dec_col: list[Decimal] = []
    saldo_dec_col: list[Decimal] = []
    pct_sobre_vendas_col: list[float | None] = []
    for pais in country_combined["country"]:
        v_dec = sales_country_dec.get(pais, Decimal("0"))
        c_dec = canc_country_dec.get(pais, Decimal("0"))
        vendas_dec_col.append(v_dec)
        canc_dec_col.append(c_dec)
        saldo_dec_col.append(v_dec + c_dec)
        if v_dec > 0:
            pct_sobre_vendas_col.append(
                round(float((abs(c_dec) / v_dec) * Decimal("100")), 2)
            )
        else:
            pct_sobre_vendas_col.append(None)

    country_combined["vendas_positivas_decimal"] = vendas_dec_col
    country_combined["valor_cancelamento_decimal"] = canc_dec_col
    country_combined["saldo_monetario_observado_decimal"] = saldo_dec_col
    country_combined["saldo_monetario_observado"] = [
        float(val) for val in saldo_dec_col
    ]
    country_combined["participacao_cancelamento_sobre_vendas_pct"] = pct_sobre_vendas_col
    country_combined["valor_absoluto_cancelamento"] = country_combined[
        "valor_cancelamento"
    ].abs()
    country_combined = (
        country_combined.sort_values(
            by=["valor_absoluto_cancelamento", "country"], ascending=[False, True]
        )
        .reset_index(drop=True)
    )

    summary = {
        "linhas_cancelamento_brutas": int(len(df_canc_raw)),
        "duplicatas_exatas_em_cancelamentos": int(dup_canc.sum()),
        "linhas_cancelamento_deduplicadas": int(len(df_canc_dedup)),
        "notas_cancelamento_distintas": int(df_canc_raw["invoice_no"].nunique()),
        "unidades_canceladas_brutas": int(df_canc_raw["quantity"].sum()),
        "unidades_canceladas_deduplicadas": int(df_canc_dedup["quantity"].sum()),
        "cancelamentos_com_cliente": int(df_canc_dedup["customer_id"].notna().sum()),
        "cancelamentos_sem_cliente": int(df_canc_dedup["customer_id"].isna().sum()),
        "vendas_positivas_v2_decimal": vendas_v2_dec,
        "valor_cancelamentos_brutos_decimal": canc_raw_dec,
        "valor_cancelamentos_deduplicados_decimal": canc_dedup_dec,
        "participacao_cancelamentos_brutos_sobre_vendas_v2_pct": round(pct_canc_raw, 4),
        "participacao_cancelamentos_dedup_sobre_vendas_v2_pct": round(pct_canc_dedup, 4),
        "saldo_monetario_observado_bruto_decimal": saldo_observado_raw,
        "saldo_monetario_observado_dedup_decimal": saldo_observado_dedup,
        "linhas_negativas_sem_c": int(len(df_neg_no_c)),
        "unidades_negativas_sem_c": int(df_neg_no_c["quantity"].sum())
        if not df_neg_no_c.empty
        else 0,
        "valor_negativas_sem_c_decimal": sum(
            df_neg_no_c["valor_linha_decimal"], Decimal("0")
        ),
        "linhas_preco_nao_positivo": int(len(df_non_pos_price)),
        "linhas_preco_nao_positivo_com_cliente": int(
            df_non_pos_price["customer_id"].notna().sum()
        )
        if not df_non_pos_price.empty
        else 0,
        "linhas_ajuste_prefixo_a": int(len(df_adj_a)),
        "valor_liquido_ajustes_prefixo_a_decimal": sum(
            df_adj_a["valor_linha_decimal"], Decimal("0")
        ),
        "detalhes_ajustes_prefixo_a": [
            {
                "invoice_no": inv,
                "stock_code": stk,
                "description": desc,
                "quantity": int(qty),
                "valor_decimal": str(val_dec),
            }
            for inv, stk, desc, qty, val_dec in zip(
                df_adj_a["invoice_no"],
                df_adj_a["stock_code"],
                df_adj_a["description"],
                df_adj_a["quantity"],
                df_adj_a["valor_linha_decimal"],
            )
        ],
        "linhas_ambiguas_ou_inconsistentes": int(len(df_ambiguous)),
    }

    return {
        "resumo": summary,
        "cancelamentos_por_produto": canc_by_product,
        "cancelamentos_por_pais": country_combined,
    }
