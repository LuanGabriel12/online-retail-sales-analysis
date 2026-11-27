"""Orquestração ponta a ponta do pipeline Online Retail Customer Analytics V2."""

import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.analytics.cancellations import analyze_cancellations_and_anomalies
from src.analytics.commercial import (
    analyze_countries,
    build_customer_ranking,
    build_executive_kpis,
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
    analyze_recurrence_and_concentration,
    apply_rfm_segmentation,
    summarize_rfm_segments,
)
from src.config import DEFAULT_REPORTS_DIR, RFM_REFERENCE_DATE
from src.data.cleaning import build_clean_datasets
from src.data.loader import load_raw_dataset
from src.data.validation import audit_raw_data_quality
from src.reporting.exports import export_csv_reports, export_markdown_reports
from src.reporting.reconciliation import run_reconciliation


def run_customer_analytics_pipeline(
    data_path: Path | None = None,
    reports_dir: Path | None = None,
    reference_date: date = RFM_REFERENCE_DATE,
    inspect_precision: bool = True,
) -> dict[str, Any]:
    """Executa todas as etapas analíticas, valida reconciliação e exporta relatórios."""
    start_time = time.perf_counter()
    output_dir = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR

    # 1. Carga e inspeção da fonte original (sem modificar o arquivo bruto)
    df_raw, metadata = load_raw_dataset(
        file_path=data_path,
        inspect_precision=inspect_precision,
    )

    # 2. Auditoria de qualidade dos dados brutos
    quality_audit = audit_raw_data_quality(df_raw)

    # 3. Triagem mutuamente exclusiva, padronização e construção das bases V2 e V1
    cleaned = build_clean_datasets(df_raw)
    df_classified = cleaned["df_classified"]
    df_valid_raw = cleaned["df_valid_raw"]
    df_sales_v2 = cleaned["df_sales_v2"]
    df_sales_v1 = cleaned["df_sales_v1"]
    resumo_limpeza = cleaned["resumo_limpeza"]

    # 4. Construção da base de pedidos (com validação prévia de conflitos)
    df_orders_v2, order_consistency = build_orders_table(df_sales_v2)

    # 5. Construção da base de clientes e cálculo descritivo de RFM
    df_customers, identification_summary = build_customers_rfm_table(
        df_sales=df_sales_v2,
        df_orders=df_orders_v2,
        reference_date=reference_date,
    )

    # 6. Segmentação RFM por regras transparentes e resumo por segmento
    df_customers_rfm = apply_rfm_segmentation(df_customers)
    df_segments_summary = summarize_rfm_segments(df_customers_rfm)

    # 7. Inteligência comercial, geográfica, produtos, clientes e série mensal
    df_countries, country_notes = analyze_countries(df_sales_v2, df_orders_v2)
    df_products = build_product_ranking(df_sales_v2)
    total_rev_v2_dec = sum(df_sales_v2["valor_linha_decimal"], Decimal("0"))
    df_customer_ranking = build_customer_ranking(
        df_rfm=df_customers_rfm,
        total_overall_revenue_decimal=total_rev_v2_dec,
    )
    df_monthly = build_monthly_evolution(df_sales_v2, df_orders_v2)

    # 8. Recorrência observada e concentração comercial
    recurrence_summary = analyze_recurrence_and_concentration(
        df_rfm=df_customers_rfm,
        df_products=df_products,
        df_countries=df_countries,
        total_overall_revenue_decimal=total_rev_v2_dec,
    )

    # 9. Cancelamentos, negativos sem C e registros não comerciais
    cancellations_data = analyze_cancellations_and_anomalies(
        df_classified=df_classified,
        df_sales_v2=df_sales_v2,
    )

    # 10. Investigação de outliers e análise de sensibilidade metodológica
    outliers_info = investigate_primary_outliers(
        df_classified=df_classified,
        df_sales_v2=df_sales_v2,
    )
    df_sensitivity, ranking_impact = run_sensitivity_analysis(
        df_sales_v2=df_sales_v2,
        df_sales_v1=df_sales_v1,
        df_valid_raw=df_valid_raw,
    )

    # 11. KPIs executivos consolidados
    kpis_df = build_executive_kpis(
        df_sales_v2=df_sales_v2,
        df_orders_v2=df_orders_v2,
        df_rfm=df_customers_rfm,
        identification_summary=identification_summary,
        recurrence_summary=recurrence_summary,
        cancellations_summary=cancellations_data["resumo"],
        df_sales_v1=df_sales_v1,
    )

    # 12. Reconciliação matemática independente
    reconciliation = run_reconciliation(
        resumo_limpeza=resumo_limpeza,
        df_sales_v2=df_sales_v2,
        df_orders_v2=df_orders_v2,
        df_customers_rfm=df_customers_rfm,
        df_segments_summary=df_segments_summary,
        df_products=df_products,
        df_countries=df_countries,
        df_monthly=df_monthly,
        identification_summary=identification_summary,
        country_notes=country_notes,
    )

    # 13. Exportação de CSVs, amostras e relatórios Markdown
    exported_csvs = export_csv_reports(
        reports_dir=output_dir,
        kpis_df=kpis_df,
        df_customers_rfm=df_customers_rfm,
        df_segments_summary=df_segments_summary,
        df_countries=df_countries,
        df_products=df_products,
        df_customer_ranking=df_customer_ranking,
        df_monthly=df_monthly,
        cancellations_by_country=cancellations_data["cancelamentos_por_pais"],
        df_sensitivity=df_sensitivity,
    )
    exported_mds = export_markdown_reports(
        reports_dir=output_dir,
        metadata=metadata,
        quality_audit=quality_audit,
        resumo_limpeza=resumo_limpeza,
        order_consistency=order_consistency,
        reconciliation=reconciliation,
        df_sales_v2=df_sales_v2,
        df_orders_v2=df_orders_v2,
        df_sales_v1=df_sales_v1,
        df_segments_summary=df_segments_summary,
        df_countries=df_countries,
        df_products=df_products,
        df_customer_ranking=df_customer_ranking,
        df_monthly=df_monthly,
        identification_summary=identification_summary,
        recurrence_summary=recurrence_summary,
        cancellations_data=cancellations_data,
        country_notes=country_notes,
        outliers_info=outliers_info,
        df_sensitivity=df_sensitivity,
        ranking_impact=ranking_impact,
    )

    elapsed_seconds = round(time.perf_counter() - start_time, 2)

    return {
        "elapsed_seconds": elapsed_seconds,
        "metadata": metadata,
        "quality_audit": quality_audit,
        "resumo_limpeza": resumo_limpeza,
        "order_consistency": order_consistency,
        "identification_summary": identification_summary,
        "recurrence_summary": recurrence_summary,
        "cancellations_data": cancellations_data,
        "country_notes": country_notes,
        "outliers_info": outliers_info,
        "ranking_impact": ranking_impact,
        "reconciliation": reconciliation,
        "dataframes": {
            "df_sales_v2": df_sales_v2,
            "df_sales_v1": df_sales_v1,
            "df_orders_v2": df_orders_v2,
            "df_customers_rfm": df_customers_rfm,
            "df_segments_summary": df_segments_summary,
            "df_countries": df_countries,
            "df_products": df_products,
            "df_customer_ranking": df_customer_ranking,
            "df_monthly": df_monthly,
            "df_sensitivity": df_sensitivity,
            "kpis_df": kpis_df,
        },
        "exported_csvs": exported_csvs,
        "exported_mds": exported_mds,
    }
