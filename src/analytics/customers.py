"""Construção da base analítica de clientes e cálculo descritivo de RFM."""

from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from src.analytics.orders import sum_decimal_by_key
from src.config import RFM_REFERENCE_DATE


def _resolve_primary_country_per_customer(df_orders_identified: pd.DataFrame) -> dict[str, str]:
    """Determina o país principal de cada cliente por maior número de pedidos (desempate por receita)."""
    country_stats = (
        df_orders_identified.groupby(["customer_id", "country"])
        .agg(
            pedidos=("invoice_no", "nunique"),
            faturamento=("faturamento_pedido", "sum"),
        )
        .reset_index()
        .sort_values(
            by=["customer_id", "pedidos", "faturamento", "country"],
            ascending=[True, False, False, True],
        )
    )

    primary_country: dict[str, str] = {}
    for cid, country in zip(country_stats["customer_id"], country_stats["country"]):
        if cid not in primary_country:
            primary_country[cid] = country
    return primary_country


def build_customers_rfm_table(
    df_sales: pd.DataFrame,
    df_orders: pd.DataFrame,
    reference_date: date = RFM_REFERENCE_DATE,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Gera base de clientes identificados com métricas comerciais e RFM reprodutível."""
    if df_sales.empty or df_orders.empty:
        raise ValueError("As bases transacional e de pedidos não podem estar vazias.")

    max_observed_date = df_orders["data_pedido"].max().date()
    if reference_date < max_observed_date:
        raise ValueError(
            f"A data de referência RFM ({reference_date}) não pode ser anterior "
            f"à última compra observada ({max_observed_date})."
        )

    # Quantifica explicitamente a diferença entre total geral e clientes identificados
    mask_sales_ident = df_sales["customer_id"].notna()
    df_sales_ident = df_sales.loc[mask_sales_ident].copy()
    df_sales_unident = df_sales.loc[~mask_sales_ident].copy()

    mask_orders_ident = df_orders["customer_id"].notna()
    df_orders_ident = df_orders.loc[mask_orders_ident].copy()
    df_orders_unident = df_orders.loc[~mask_orders_ident].copy()

    total_rev_dec = sum(df_sales["valor_linha_decimal"], Decimal("0"))
    ident_rev_dec = sum(df_sales_ident["valor_linha_decimal"], Decimal("0"))
    unident_rev_dec = sum(df_sales_unident["valor_linha_decimal"], Decimal("0"))

    pct_ident = (
        float((ident_rev_dec / total_rev_dec) * Decimal("100"))
        if total_rev_dec > 0
        else 0.0
    )
    pct_unident = (
        float((unident_rev_dec / total_rev_dec) * Decimal("100"))
        if total_rev_dec > 0
        else 0.0
    )

    identification_summary = {
        "data_referencia_rfm": str(reference_date),
        "ultima_compra_observada_base": str(df_orders["data_pedido"].max()),
        "linhas_com_cliente": int(len(df_sales_ident)),
        "linhas_sem_cliente": int(len(df_sales_unident)),
        "pedidos_com_cliente": int(len(df_orders_ident)),
        "pedidos_sem_cliente": int(len(df_orders_unident)),
        "faturamento_total_decimal": total_rev_dec,
        "faturamento_identificado_decimal": ident_rev_dec,
        "faturamento_nao_identificado_decimal": unident_rev_dec,
        "percentual_faturamento_identificado": round(pct_ident, 4),
        "percentual_faturamento_nao_identificado": round(pct_unident, 4),
    }

    if df_orders_ident.empty:
        raise ValueError("Não há pedidos com CustomerID identificado para construir base de clientes.")

    # Agregação em nível de cliente a partir da base de pedidos identificados
    customers = (
        df_orders_ident.groupby("customer_id")
        .agg(
            faturamento_acumulado=("faturamento_pedido", "sum"),
            pedidos_distintos=("invoice_no", "nunique"),
            quantidade_unidades=("quantidade_unidades", "sum"),
            linhas_transacao=("linhas_transacao", "sum"),
            primeira_compra=("data_pedido", "min"),
            ultima_compra=("data_pedido", "max"),
            paises_distintos=("country", "nunique"),
        )
        .reset_index()
    )

    # Produtos distintos por cliente (calculado na base transacional identificada)
    prod_por_cliente = (
        df_sales_ident.groupby("customer_id")
        .agg(produtos_distintos=("stock_code", "nunique"))
        .reset_index()
    )
    customers = customers.merge(prod_por_cliente, on="customer_id", how="left")

    # Soma exata em Decimal por cliente
    dec_by_cust = sum_decimal_by_key(
        df_orders_ident["customer_id"], df_orders_ident["faturamento_pedido_decimal"]
    )
    customers["faturamento_acumulado_decimal"] = [
        dec_by_cust[cid] for cid in customers["customer_id"]
    ]

    # País principal explícito (sem esconder clientes com múltiplos países)
    primary_country_map = _resolve_primary_country_per_customer(df_orders_ident)
    customers["pais_principal"] = [
        primary_country_map[cid] for cid in customers["customer_id"]
    ]

    # Ticket médio por cliente = faturamento acumulado / pedidos distintos
    customers["ticket_medio"] = (
        customers["faturamento_acumulado"] / customers["pedidos_distintos"]
    )

    # Cálculo reprodutível de Recência (em dias corridos de calendário)
    ref_timestamp = pd.Timestamp(reference_date)
    customers["recencia_dias"] = (
        ref_timestamp - customers["ultima_compra"].dt.normalize()
    ).dt.days.astype(int)

    # Dias desde a primeira compra observada (contexto da janela de observação)
    customers["dias_desde_primeira_compra"] = (
        ref_timestamp - customers["primeira_compra"].dt.normalize()
    ).dt.days.astype(int)
    customers["amplitude_observada_dias"] = (
        customers["ultima_compra"].dt.normalize()
        - customers["primeira_compra"].dt.normalize()
    ).dt.days.astype(int)

    # Colunas RFM explícitas e indicadores de recorrência
    customers["frequencia"] = customers["pedidos_distintos"].astype(int)
    customers["valor_monetario"] = customers["faturamento_acumulado"]
    customers["cliente_recorrente"] = customers["frequencia"] >= 2

    customers = (
        customers.sort_values(
            by=["valor_monetario", "customer_id"], ascending=[False, True]
        )
        .reset_index(drop=True)
    )

    # Identifica clientes presentes em mais de um país
    multi_country_df = customers.loc[customers["paises_distintos"] > 1]
    identification_summary["clientes_identificados_total"] = int(len(customers))
    identification_summary["clientes_em_multiplos_paises"] = int(len(multi_country_df))
    identification_summary["ids_clientes_multiplos_paises"] = list(
        multi_country_df["customer_id"].sort_values()
    )

    return customers, identification_summary
