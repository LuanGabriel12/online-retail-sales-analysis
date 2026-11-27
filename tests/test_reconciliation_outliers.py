"""Testes de reconciliação matemática, outliers e análise de sensibilidade."""

from datetime import date, datetime
from decimal import Decimal

import pandas as pd

from src.analytics.commercial import (
    analyze_countries,
    build_monthly_evolution,
    build_product_ranking,
)
from src.analytics.customers import build_customers_rfm_table
from src.analytics.orders import build_orders_table
from src.analytics.outliers import (
    investigate_primary_outliers,
    run_sensitivity_analysis,
)
from src.analytics.segmentation import (
    apply_rfm_segmentation,
    summarize_rfm_segments,
)
from src.data.cleaning import build_clean_datasets
from src.reporting.reconciliation import run_reconciliation


def test_reconciliation_passes_all_checks_on_valid_data(synthetic_raw_df):
    cleaned = build_clean_datasets(synthetic_raw_df)
    orders, _ = build_orders_table(cleaned["df_sales_v2"])
    customers, ident_summary = build_customers_rfm_table(
        cleaned["df_sales_v2"], orders, reference_date=date(2011, 12, 10)
    )
    df_rfm = apply_rfm_segmentation(customers)
    segments = summarize_rfm_segments(df_rfm)
    countries, country_notes = analyze_countries(cleaned["df_sales_v2"], orders)
    products = build_product_ranking(cleaned["df_sales_v2"])
    monthly = build_monthly_evolution(cleaned["df_sales_v2"], orders)

    rec = run_reconciliation(
        resumo_limpeza=cleaned["resumo_limpeza"],
        df_sales_v2=cleaned["df_sales_v2"],
        df_orders_v2=orders,
        df_customers_rfm=df_rfm,
        df_segments_summary=segments,
        df_products=products,
        df_countries=countries,
        df_monthly=monthly,
        identification_summary=ident_summary,
        country_notes=country_notes,
    )

    assert rec["todas_aprovadas"] is True
    assert rec["total_checagens"] == 18
    assert rec["reprovadas"] == 0
    assert rec["auditoria_monetaria"]["faturamento_exato_decimal"] == "1850.003"
    assert rec["auditoria_monetaria"]["faturamento_exibicao_2_casas"] == "1850.00"


def test_reconciliation_detects_revenue_divergence(synthetic_raw_df):
    cleaned = build_clean_datasets(synthetic_raw_df)
    orders, _ = build_orders_table(cleaned["df_sales_v2"])
    customers, ident_summary = build_customers_rfm_table(
        cleaned["df_sales_v2"], orders, reference_date=date(2011, 12, 10)
    )
    df_rfm = apply_rfm_segmentation(customers)
    segments = summarize_rfm_segments(df_rfm)
    countries, country_notes = analyze_countries(cleaned["df_sales_v2"], orders)
    products = build_product_ranking(cleaned["df_sales_v2"])
    monthly = build_monthly_evolution(cleaned["df_sales_v2"], orders)

    # Adultera deliberadamente o faturamento de um produto para testar detecção
    products_corrupted = products.copy()
    products_corrupted.loc[0, "faturamento_total_decimal"] = (
        products_corrupted.loc[0, "faturamento_total_decimal"] + Decimal("1.00")
    )

    rec = run_reconciliation(
        resumo_limpeza=cleaned["resumo_limpeza"],
        df_sales_v2=cleaned["df_sales_v2"],
        df_orders_v2=orders,
        df_customers_rfm=df_rfm,
        df_segments_summary=segments,
        df_products=products_corrupted,
        df_countries=countries,
        df_monthly=monthly,
        identification_summary=ident_summary,
        country_notes=country_notes,
    )

    assert rec["todas_aprovadas"] is False
    rec04 = [c for c in rec["checagens"] if c["codigo"] == "REC-04"][0]
    assert rec04["aprovado"] is False


def test_outliers_investigation_and_sensitivity_scenarios():
    rows = [
        (581483, 23843, "PAPER CRAFT , LITTLE BIRDIE", 80995, datetime(2011, 12, 9, 9, 15), 2.08, 16446.0, "United Kingdom"),
        ("C581484", 23843, "PAPER CRAFT , LITTLE BIRDIE", -80995, datetime(2011, 12, 9, 9, 27), 2.08, 16446.0, "United Kingdom"),
        (553573, 22980, "PANTRY SCRUBBING BRUSH", 2, datetime(2011, 5, 18, 9, 52), 1.45, 16446.0, "United Kingdom"),
        (541431, 23166, "MEDIUM CERAMIC TOP STORAGE JAR", 74215, datetime(2011, 1, 18, 10, 1), 1.04, 12346.0, "United Kingdom"),
        ("C541433", 23166, "MEDIUM CERAMIC TOP STORAGE JAR", -74215, datetime(2011, 1, 18, 10, 17), 1.04, 12346.0, "United Kingdom"),
        (550001, 84077, "WORLD WAR 2 GLIDERS", 100, datetime(2011, 6, 1, 11, 0), 0.50, 14646.0, "Netherlands"),
        (550001, "POST", "POSTAGE", 1, datetime(2011, 6, 1, 11, 0), 15.00, 14646.0, "Netherlands"),
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "InvoiceNo", "StockCode", "Description", "Quantity",
            "InvoiceDate", "UnitPrice", "CustomerID", "Country",
        ],
    )
    cleaned = build_clean_datasets(df)

    outliers = investigate_primary_outliers(cleaned["df_classified"], cleaned["df_sales_v2"])
    p1 = outliers["outlier_principal_23843"]
    assert p1["encontrado"] is True
    assert p1["quantity"] == 80995
    assert p1["valor_decimal"] == Decimal("168469.60")
    assert p1["participacao_volume_produto_pct"] == 100.0
    assert p1["outros_pedidos_mesmo_cliente"] == 1
    assert p1["receita_outros_pedidos_cliente_decimal"] == Decimal("2.90")
    assert len(p1["cancelamentos_potencialmente_relacionados"]) == 1
    assert p1["cancelamentos_potencialmente_relacionados"][0]["invoice_no_cancelamento"] == "C581484"
    assert p1["cancelamentos_potencialmente_relacionados"][0]["diferenca_minutos"] == 12.0

    sens_df, impact = run_sensitivity_analysis(
        df_sales_v2=cleaned["df_sales_v2"],
        df_sales_v1=cleaned["df_sales_v1"],
        df_valid_raw=cleaned["df_valid_raw"],
    )
    assert len(sens_df) == 6
    assert impact["valor_codigos_operacionais_na_base_v2_decimal"] == Decimal("15.00")

    sem_dois = sens_df.loc[
        sens_df["cenario"] == "5. Sem Dois Maiores Outliers (581483 e 541431)"
    ].iloc[0]
    assert sem_dois["faturamento_total_decimal"] == Decimal("67.90")
    assert "84077" in sem_dois["produto_lider_unidades"]
