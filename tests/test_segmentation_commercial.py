"""Testes de segmentação RFM, limites de fronteira, recorrência e comercial."""

from datetime import date
from decimal import Decimal

import pytest

from src.analytics.commercial import (
    analyze_countries,
    build_monthly_evolution,
    build_product_ranking,
)
from src.analytics.customers import build_customers_rfm_table
from src.analytics.orders import build_orders_table
from src.analytics.segmentation import (
    analyze_recurrence_and_concentration,
    apply_rfm_segmentation,
    classify_rfm_segment,
    summarize_rfm_segments,
)
from src.data.cleaning import build_clean_datasets


def test_classify_rfm_segment_exact_boundaries():
    # Fronteira exata para Alto valor e recorrentes: freq=5, mon=1500.00, rec=90
    assert (
        classify_rfm_segment(90, 5, Decimal("1500.00"))
        == "Alto valor e recorrentes"
    )
    # Abaixo do limiar de valor (1499.99) cai para Recorrentes recentes
    assert (
        classify_rfm_segment(90, 5, Decimal("1499.99"))
        == "Recorrentes recentes"
    )
    # Abaixo do limiar de frequência (4) mesmo com alto valor cai para Recorrentes recentes
    assert (
        classify_rfm_segment(10, 4, Decimal("5000.00"))
        == "Recorrentes recentes"
    )
    # Recência 91 com freq >= 5 e alto valor vai para Recorrentes há mais tempo sem compras
    assert (
        classify_rfm_segment(91, 5, Decimal("5000.00"))
        == "Recorrentes há mais tempo sem compras"
    )
    # Compra única recente (rec=90, freq=1)
    assert (
        classify_rfm_segment(90, 1, Decimal("9999.00"))
        == "Compra única recente"
    )
    # Compra única antiga (rec=91, freq=1)
    assert (
        classify_rfm_segment(91, 1, Decimal("50.00"))
        == "Compra única há mais tempo sem compras"
    )

    with pytest.raises(ValueError):
        classify_rfm_segment(10, 0, Decimal("100.00"))
    with pytest.raises(ValueError):
        classify_rfm_segment(-1, 1, Decimal("100.00"))


def test_segmentation_no_overlap_ticket_medio_and_recurrence(synthetic_raw_df):
    cleaned = build_clean_datasets(synthetic_raw_df)
    orders, _ = build_orders_table(cleaned["df_sales_v2"])
    customers, _ = build_customers_rfm_table(
        cleaned["df_sales_v2"], orders, reference_date=date(2011, 12, 10)
    )
    df_rfm = apply_rfm_segmentation(customers)
    segments = summarize_rfm_segments(df_rfm)

    # Cada cliente classificado exatamente uma vez
    assert int(segments["qtd_clientes"].sum()) == len(df_rfm) == 3
    seg_by_cust = dict(zip(df_rfm["customer_id"], df_rfm["segmento_rfm"]))
    assert seg_by_cust == {
        "101": "Alto valor e recorrentes",
        "102": "Recorrentes recentes",
        "103": "Compra única há mais tempo sem compras",
    }

    # Ticket médio por segmento: 1650/5=330, 100/2=50, 0.003/1=0.003
    # Média simples incorreta = (330 + 50 + 0.003)/3 = 126.6677
    # Ticket médio real dos clientes identificados = 1750.003 / 8 = 218.750375
    ticket_real_ident = float(Decimal("1750.003")) / 8.0
    media_simples_errada = float(segments["ticket_medio_segmento"].mean())
    assert ticket_real_ident == pytest.approx(218.750375)
    assert media_simples_errada != pytest.approx(ticket_real_ident)

    # Recorrência e concentração
    countries, country_notes = analyze_countries(cleaned["df_sales_v2"], orders)
    products = build_product_ranking(cleaned["df_sales_v2"])
    recurrence = analyze_recurrence_and_concentration(
        df_rfm=df_rfm,
        df_products=products,
        df_countries=countries,
        total_overall_revenue_decimal=Decimal("1850.003"),
    )

    assert recurrence["clientes_compra_unica"] == 1
    assert recurrence["clientes_recorrentes"] == 2
    assert recurrence["taxa_recorrencia_observada_pct"] == pytest.approx(66.67, abs=0.01)
    assert recurrence["concentracao_clientes"]["top_10"]["faturamento_decimal"] == Decimal("1750.003")

    # Clientes por país somam 4 (UK=2, FR=1, DE=1), mas clientes globais = 3 (C102 em 2 países!)
    assert country_notes["clientes_distintos_globais"] == 3
    assert country_notes["soma_clientes_por_pais"] == 4
    assert country_notes["diferenca_clientes_multiplos_paises"] == 1

    # Evolução mensal sinaliza 2011-12 como período incompleto
    monthly = build_monthly_evolution(cleaned["df_sales_v2"], orders)
    dec_row = monthly.loc[monthly["ano_mes"] == "2011-12"].iloc[0]
    nov_row = monthly.loc[monthly["ano_mes"] == "2011-11"].iloc[0]
    assert bool(dec_row["periodo_incompleto"]) is True
    assert bool(nov_row["periodo_incompleto"]) is False
