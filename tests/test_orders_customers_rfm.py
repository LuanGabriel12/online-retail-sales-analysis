"""Testes da base de pedidos, conflitos de pedido e base de clientes/RFM."""

from datetime import date, datetime
from decimal import Decimal

import pandas as pd
import pytest

from src.analytics.customers import build_customers_rfm_table
from src.analytics.orders import build_orders_table
from src.data.cleaning import build_clean_datasets


def test_build_orders_table_consolidates_multi_item_and_multi_timestamp_order(synthetic_raw_df):
    cleaned = build_clean_datasets(synthetic_raw_df)
    orders, consistency = build_orders_table(cleaned["df_sales_v2"])

    assert len(orders) == 9
    assert consistency["pedidos_conflito_cliente"] == 0
    assert consistency["pedidos_conflito_pais"] == 0
    assert consistency["pedidos_multiplos_timestamps"] == 1
    assert consistency["diferenca_maxima_segundos_mesmo_pedido"] == 60.0

    # Pedido 500001 tem 2 itens distintos (20001 e 20002), 15 un., £ 250,00 e min timestamp 10:00
    ped_500001 = orders.loc[orders["invoice_no"] == "500001"].iloc[0]
    assert ped_500001["produtos_distintos"] == 2
    assert ped_500001["quantidade_unidades"] == 15
    assert ped_500001["faturamento_pedido_decimal"] == Decimal("250.00")
    assert ped_500001["data_pedido"] == pd.Timestamp("2011-10-01 10:00:00")
    assert ped_500001["timestamps_distintos"] == 2


def test_build_orders_table_raises_on_conflicting_customer():
    df_conflict = pd.DataFrame(
        [
            (600001, "10001", "ITEM A", 1, datetime(2011, 10, 1, 10, 0), 10.0, 101.0, "United Kingdom"),
            (600001, "10002", "ITEM B", 1, datetime(2011, 10, 1, 10, 0), 15.0, 999.0, "United Kingdom"),
        ],
        columns=[
            "InvoiceNo", "StockCode", "Description", "Quantity",
            "InvoiceDate", "UnitPrice", "CustomerID", "Country",
        ],
    )
    cleaned = build_clean_datasets(df_conflict)
    with pytest.raises(ValueError, match="Conflito de cliente"):
        build_orders_table(cleaned["df_sales_v2"])


def test_build_orders_table_raises_on_mixed_null_customer():
    df_conflict = pd.DataFrame(
        [
            (600002, "10001", "ITEM A", 1, datetime(2011, 10, 1, 10, 0), 10.0, 101.0, "United Kingdom"),
            (600002, "10002", "ITEM B", 1, datetime(2011, 10, 1, 10, 0), 15.0, None, "United Kingdom"),
        ],
        columns=[
            "InvoiceNo", "StockCode", "Description", "Quantity",
            "InvoiceDate", "UnitPrice", "CustomerID", "Country",
        ],
    )
    cleaned = build_clean_datasets(df_conflict)
    with pytest.raises(ValueError, match="Mistura de cliente identificado e nulo"):
        build_orders_table(cleaned["df_sales_v2"])


def test_build_orders_table_raises_on_conflicting_country():
    df_conflict = pd.DataFrame(
        [
            (600003, "10001", "ITEM A", 1, datetime(2011, 10, 1, 10, 0), 10.0, 101.0, "United Kingdom"),
            (600003, "10002", "ITEM B", 1, datetime(2011, 10, 1, 10, 0), 15.0, 101.0, "France"),
        ],
        columns=[
            "InvoiceNo", "StockCode", "Description", "Quantity",
            "InvoiceDate", "UnitPrice", "CustomerID", "Country",
        ],
    )
    cleaned = build_clean_datasets(df_conflict)
    with pytest.raises(ValueError, match="Conflito de país"):
        build_orders_table(cleaned["df_sales_v2"])


def test_build_customers_rfm_table_fixed_reference_date_and_unidentified_gap(synthetic_raw_df):
    cleaned = build_clean_datasets(synthetic_raw_df)
    orders, _ = build_orders_table(cleaned["df_sales_v2"])
    customers, ident_summary = build_customers_rfm_table(
        df_sales=cleaned["df_sales_v2"],
        df_orders=orders,
        reference_date=date(2011, 12, 10),
    )

    # Gap entre faturamento total e identificado
    assert ident_summary["faturamento_total_decimal"] == Decimal("1850.003")
    assert ident_summary["faturamento_identificado_decimal"] == Decimal("1750.003")
    assert ident_summary["faturamento_nao_identificado_decimal"] == Decimal("100.00")
    assert ident_summary["pedidos_com_cliente"] == 8
    assert ident_summary["pedidos_sem_cliente"] == 1
    assert ident_summary["clientes_em_multiplos_paises"] == 1
    assert ident_summary["ids_clientes_multiplos_paises"] == ["102"]

    assert len(customers) == 3

    c101 = customers.loc[customers["customer_id"] == "101"].iloc[0]
    assert c101["frequencia"] == 5
    assert c101["faturamento_acumulado_decimal"] == Decimal("1650.00")
    assert c101["ticket_medio"] == pytest.approx(330.0)
    assert c101["recencia_dias"] == 9  # 2011-12-10 - 2011-12-01
    assert c101["produtos_distintos"] == 2

    c102 = customers.loc[customers["customer_id"] == "102"].iloc[0]
    assert c102["frequencia"] == 2
    assert c102["faturamento_acumulado_decimal"] == Decimal("100.00")
    assert c102["paises_distintos"] == 2
    assert c102["pais_principal"] == "Germany"  # empate em 1 pedido, desempate por receita (£60 > £40)
    assert c102["recencia_dias"] == 5  # 2011-12-10 - 2011-12-05

    c103 = customers.loc[customers["customer_id"] == "103"].iloc[0]
    assert c103["frequencia"] == 1
    assert c103["faturamento_acumulado_decimal"] == Decimal("0.003")
    assert c103["recencia_dias"] == 223  # 2011-12-10 - 2011-05-01


def test_build_customers_rfm_table_rejects_reference_date_before_last_purchase(synthetic_raw_df):
    cleaned = build_clean_datasets(synthetic_raw_df)
    orders, _ = build_orders_table(cleaned["df_sales_v2"])
    with pytest.raises(ValueError, match="não pode ser anterior"):
        build_customers_rfm_table(
            df_sales=cleaned["df_sales_v2"],
            df_orders=orders,
            reference_date=date(2011, 11, 1),
        )
