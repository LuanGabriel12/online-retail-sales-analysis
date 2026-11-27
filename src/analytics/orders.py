"""Construção da base analítica em nível de pedido (uma linha por InvoiceNo)."""

from decimal import Decimal
from typing import Any

import pandas as pd

from src.data.validation import validate_order_level_consistency


def sum_decimal_by_key(keys: pd.Series, values: pd.Series) -> dict[Any, Decimal]:
    """Soma valores Decimal agrupados por chave de forma exata e determinística."""
    totals: dict[Any, Decimal] = {}
    for key, val in zip(keys, values):
        if key in totals:
            totals[key] = totals[key] + val
        else:
            totals[key] = val
    return totals


def build_orders_table(df_sales: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Consolida transações válidas em nível de pedido após validar conflitos."""
    if df_sales.empty:
        raise ValueError("Não é possível construir a base de pedidos com DataFrame vazio.")

    consistency = validate_order_level_consistency(df_sales)

    if consistency["pedidos_conflito_cliente"] > 0:
        raise ValueError(
            "Conflito de cliente no mesmo InvoiceNo detectado para os pedidos: "
            f"{consistency['ids_conflito_cliente'][:10]}"
        )
    if consistency["pedidos_mistura_cliente_nulo"] > 0:
        raise ValueError(
            "Mistura de cliente identificado e nulo no mesmo InvoiceNo detectada: "
            f"{consistency['ids_mistura_cliente_nulo'][:10]}"
        )
    if consistency["pedidos_conflito_pais"] > 0:
        raise ValueError(
            "Conflito de país no mesmo InvoiceNo detectado para os pedidos: "
            f"{consistency['ids_conflito_pais'][:10]}"
        )

    # Como a consistência de customer_id e country foi verificada acima (0 conflitos),
    # usar 'first' para ambos é seguro e determinístico. Para invoice_date, usamos 'min'
    # (horário de abertura do pedido) e preservamos a contagem de timestamps distintos.
    orders = (
        df_sales.groupby("invoice_no")
        .agg(
            customer_id=("customer_id", "first"),
            country=("country", "first"),
            data_pedido=("invoice_date", "min"),
            data_pedido_fim=("invoice_date", "max"),
            timestamps_distintos=("invoice_date", "nunique"),
            faturamento_pedido=("valor_linha", "sum"),
            quantidade_unidades=("quantity", "sum"),
            produtos_distintos=("stock_code", "nunique"),
            linhas_transacao=("stock_code", "count"),
        )
        .reset_index()
        .sort_values(by=["data_pedido", "invoice_no"], ascending=[True, True])
        .reset_index(drop=True)
    )

    decimal_totals = sum_decimal_by_key(
        df_sales["invoice_no"], df_sales["valor_linha_decimal"]
    )
    orders["faturamento_pedido_decimal"] = [
        decimal_totals[inv] for inv in orders["invoice_no"]
    ]
    orders["ano_mes"] = orders["data_pedido"].dt.strftime("%Y-%m")
    orders["cliente_identificado"] = orders["customer_id"].notna()

    return orders, consistency
