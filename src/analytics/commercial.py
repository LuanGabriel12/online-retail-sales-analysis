"""Análises comerciais, geográficas, de produtos, clientes e evolução mensal."""

from decimal import Decimal
from typing import Any

import pandas as pd

from src.analytics.orders import sum_decimal_by_key
from src.config import COUNTRY_SAMPLE_THRESHOLDS, INCOMPLETE_YEAR_MONTHS


def _classify_country_sample_size(pedidos: int) -> str:
    """Classifica o porte amostral de pedidos do país para contextualizar comparações."""
    if pedidos <= COUNTRY_SAMPLE_THRESHOLDS["amostra_muito_baixa_max_pedidos"]:
        return "Amostra muito baixa (< 10 pedidos)"
    if pedidos <= COUNTRY_SAMPLE_THRESHOLDS["amostra_moderada_max_pedidos"]:
        return "Amostra moderada (10 a 49 pedidos)"
    return "Amostra robusta (>= 50 pedidos)"


def analyze_countries(
    df_sales: pd.DataFrame,
    df_orders: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Calcula desempenho comercial, ticket médio e recorrência contextualizada por país."""
    total_rev_dec = sum(df_orders["faturamento_pedido_decimal"], Decimal("0"))
    global_ticket = (
        float(total_rev_dec) / len(df_orders) if len(df_orders) > 0 else 0.0
    )

    country_agg = (
        df_orders.groupby("country")
        .agg(
            pedidos_distintos=("invoice_no", "nunique"),
            clientes_identificados=("customer_id", "nunique"),
            unidades_vendidas=("quantidade_unidades", "sum"),
            faturamento_total=("faturamento_pedido", "sum"),
            pedidos_identificados=("cliente_identificado", "sum"),
        )
        .reset_index()
    )

    dec_by_country = sum_decimal_by_key(
        df_orders["country"], df_orders["faturamento_pedido_decimal"]
    )
    country_agg["faturamento_total_decimal"] = [
        dec_by_country[c] for c in country_agg["country"]
    ]
    country_agg["participacao_faturamento_pct"] = [
        float((val / total_rev_dec) * Decimal("100")) if total_rev_dec > 0 else 0.0
        for val in country_agg["faturamento_total_decimal"]
    ]
    country_agg["ticket_medio"] = (
        country_agg["faturamento_total"] / country_agg["pedidos_distintos"]
    )

    # Recorrência dentro de cada país (clientes com >= 2 pedidos no respectivo país)
    orders_ident = df_orders.dropna(subset=["customer_id"]).copy()
    if not orders_ident.empty:
        cust_country_orders = (
            orders_ident.groupby(["country", "customer_id"])
            .agg(pedidos_no_pais=("invoice_no", "nunique"))
            .reset_index()
        )
        cust_country_orders["recorrente_no_pais"] = (
            cust_country_orders["pedidos_no_pais"] >= 2
        )
        rec_by_country = (
            cust_country_orders.groupby("country")
            .agg(clientes_recorrentes_no_pais=("recorrente_no_pais", "sum"))
            .reset_index()
        )
        country_agg = country_agg.merge(rec_by_country, on="country", how="left")
        country_agg["clientes_recorrentes_no_pais"] = [
            0 if pd.isna(v) else int(v)
            for v in country_agg["clientes_recorrentes_no_pais"]
        ]
    else:
        country_agg["clientes_recorrentes_no_pais"] = 0

    min_cust_rec = COUNTRY_SAMPLE_THRESHOLDS["min_clientes_recorrencia_interpretavel"]
    taxas_rec: list[float | None] = []
    rec_interpretavel: list[bool] = []
    classif_amostra: list[str] = []
    alerta_ticket_baixa_amostra: list[bool] = []

    for pedidos, clientes, recorrentes, ticket in zip(
        country_agg["pedidos_distintos"],
        country_agg["clientes_identificados"],
        country_agg["clientes_recorrentes_no_pais"],
        country_agg["ticket_medio"],
    ):
        classif_amostra.append(_classify_country_sample_size(int(pedidos)))
        is_interpretable = int(clientes) >= min_cust_rec
        rec_interpretavel.append(is_interpretable)
        if int(clientes) > 0:
            taxas_rec.append(round((int(recorrentes) / int(clientes)) * 100, 2))
        else:
            taxas_rec.append(None)

        alerta_ticket_baixa_amostra.append(
            bool(
                float(ticket) > global_ticket
                and int(pedidos)
                <= COUNTRY_SAMPLE_THRESHOLDS["amostra_muito_baixa_max_pedidos"]
            )
        )

    country_agg["taxa_recorrencia_pais_pct"] = taxas_rec
    country_agg["recorrencia_interpretavel"] = rec_interpretavel
    country_agg["classificacao_amostra"] = classif_amostra
    country_agg["alerta_ticket_elevado_baixa_amostra"] = alerta_ticket_baixa_amostra

    country_agg = (
        country_agg.sort_values(
            by=["faturamento_total", "country"], ascending=[False, True]
        )
        .reset_index(drop=True)
    )

    # Verifica clientes presentes em múltiplos países para evitar soma indevida
    total_distinct_customers = int(df_sales["customer_id"].nunique(dropna=True))
    sum_customers_across_countries = int(country_agg["clientes_identificados"].sum())

    low_sample_high_ticket = country_agg.loc[
        country_agg["alerta_ticket_elevado_baixa_amostra"]
    ].sort_values(by="ticket_medio", ascending=False)

    country_notes = {
        "total_paises": int(len(country_agg)),
        "clientes_distintos_globais": total_distinct_customers,
        "soma_clientes_por_pais": sum_customers_across_countries,
        "diferenca_clientes_multiplos_paises": sum_customers_across_countries
        - total_distinct_customers,
        "paises_ticket_alto_baixa_amostra": list(low_sample_high_ticket["country"]),
    }

    return country_agg, country_notes


def build_product_ranking(df_sales: pd.DataFrame) -> pd.DataFrame:
    """Consolida ranking de produtos por StockCode padronizado sem perder receitas."""
    total_rev_dec = sum(df_sales["valor_linha_decimal"], Decimal("0"))
    total_units = int(df_sales["quantity"].sum())

    # Descrição principal por StockCode: mais frequente não nula, desempate alfabético
    desc_counts = (
        df_sales.dropna(subset=["description"])
        .groupby(["stock_code", "description"])
        .agg(ocorrencias=("invoice_no", "count"))
        .reset_index()
        .sort_values(
            by=["stock_code", "ocorrencias", "description"],
            ascending=[True, False, True],
        )
    )
    primary_desc_map: dict[str, str] = {}
    for code, desc in zip(desc_counts["stock_code"], desc_counts["description"]):
        if code not in primary_desc_map:
            primary_desc_map[code] = desc

    products = (
        df_sales.groupby("stock_code")
        .agg(
            unidades_vendidas=("quantity", "sum"),
            faturamento_total=("valor_linha", "sum"),
            pedidos_distintos=("invoice_no", "nunique"),
            clientes_identificados=("customer_id", "nunique"),
            linhas_transacao=("invoice_no", "count"),
            qtd_descricoes_distintas=("description", "nunique"),
            codigo_operacional=("is_non_merchandise_code", "max"),
        )
        .reset_index()
    )

    dec_by_product = sum_decimal_by_key(
        df_sales["stock_code"], df_sales["valor_linha_decimal"]
    )
    products["faturamento_total_decimal"] = [
        dec_by_product[code] for code in products["stock_code"]
    ]
    products["descricao_principal"] = [
        primary_desc_map.get(code, "SEM DESCRIÇÃO") for code in products["stock_code"]
    ]
    products["participacao_faturamento_pct"] = [
        float((val / total_rev_dec) * Decimal("100")) if total_rev_dec > 0 else 0.0
        for val in products["faturamento_total_decimal"]
    ]
    products["participacao_unidades_pct"] = (
        products["unidades_vendidas"] / total_units * 100 if total_units > 0 else 0.0
    )
    products["preco_medio_ponderado"] = (
        products["faturamento_total"] / products["unidades_vendidas"]
    )

    products = (
        products.sort_values(
            by=["faturamento_total", "unidades_vendidas", "stock_code"],
            ascending=[False, False, True],
        )
        .reset_index(drop=True)
    )
    products["ranking_faturamento"] = list(range(1, len(products) + 1))

    return products


def build_customer_ranking(
    df_rfm: pd.DataFrame,
    total_overall_revenue_decimal: Decimal,
) -> pd.DataFrame:
    """Constrói ranking de clientes por faturamento acumulado com participação acumulada."""
    total_ident_dec = sum(df_rfm["faturamento_acumulado_decimal"], Decimal("0"))
    ranking = (
        df_rfm.sort_values(
            by=["valor_monetario", "customer_id"], ascending=[False, True]
        )
        .reset_index(drop=True)
        .copy()
    )

    ranking["ranking_faturamento"] = list(range(1, len(ranking) + 1))

    part_ident: list[float] = []
    part_total: list[float] = []
    acum_ident: list[float] = []
    running_dec = Decimal("0")

    for val in ranking["faturamento_acumulado_decimal"]:
        running_dec += val
        p_ident = (
            float((val / total_ident_dec) * Decimal("100"))
            if total_ident_dec > 0
            else 0.0
        )
        p_total = (
            float((val / total_overall_revenue_decimal) * Decimal("100"))
            if total_overall_revenue_decimal > 0
            else 0.0
        )
        p_acum = (
            float((running_dec / total_ident_dec) * Decimal("100"))
            if total_ident_dec > 0
            else 0.0
        )
        part_ident.append(round(p_ident, 4))
        part_total.append(round(p_total, 4))
        acum_ident.append(round(p_acum, 4))

    ranking["participacao_receita_identificada_pct"] = part_ident
    ranking["participacao_receita_total_pct"] = part_total
    ranking["participacao_acumulada_identificada_pct"] = acum_ident

    return ranking


def build_monthly_evolution(
    df_sales: pd.DataFrame,
    df_orders: pd.DataFrame,
) -> pd.DataFrame:
    """Consolida evolução mensal de vendas, pedidos e ticket médio com alerta de mês incompleto."""
    monthly = (
        df_orders.groupby("ano_mes")
        .agg(
            pedidos_distintos=("invoice_no", "nunique"),
            clientes_identificados=("customer_id", "nunique"),
            unidades_vendidas=("quantidade_unidades", "sum"),
            linhas_transacao=("linhas_transacao", "sum"),
            faturamento_total=("faturamento_pedido", "sum"),
            data_inicial_mes=("data_pedido", "min"),
            data_final_mes=("data_pedido", "max"),
        )
        .reset_index()
        .sort_values(by="ano_mes", ascending=True)
        .reset_index(drop=True)
    )

    dec_by_month = sum_decimal_by_key(
        df_sales["ano_mes"], df_sales["valor_linha_decimal"]
    )
    monthly["faturamento_total_decimal"] = [
        dec_by_month[ym] for ym in monthly["ano_mes"]
    ]
    monthly["ticket_medio"] = (
        monthly["faturamento_total"] / monthly["pedidos_distintos"]
    )
    monthly["dias_calendario_cobertos"] = (
        (
            monthly["data_final_mes"].dt.normalize()
            - monthly["data_inicial_mes"].dt.normalize()
        ).dt.days
        + 1
    ).astype(int)
    monthly["periodo_incompleto"] = monthly["ano_mes"].isin(INCOMPLETE_YEAR_MONTHS)

    return monthly


def build_executive_kpis(
    df_sales_v2: pd.DataFrame,
    df_orders_v2: pd.DataFrame,
    df_rfm: pd.DataFrame,
    identification_summary: dict[str, Any],
    recurrence_summary: dict[str, Any],
    cancellations_summary: dict[str, Any],
    df_sales_v1: pd.DataFrame,
) -> pd.DataFrame:
    """Monta tabela consolidada de KPIs executivos da V2 com comparação à V1."""
    rev_v2_dec = sum(df_sales_v2["valor_linha_decimal"], Decimal("0"))
    orders_v2 = int(len(df_orders_v2))
    units_v2 = int(df_sales_v2["quantity"].sum())
    ticket_v2 = float(rev_v2_dec) / orders_v2 if orders_v2 > 0 else 0.0

    rev_v1_dec = sum(df_sales_v1["valor_linha_decimal"], Decimal("0"))
    orders_v1 = int(df_sales_v1["invoice_no"].nunique())
    ticket_v1 = float(rev_v1_dec) / orders_v1 if orders_v1 > 0 else 0.0

    ref_date_str = str(identification_summary["data_referencia_rfm"])

    rows = [
        ("faturamento_vendas_positivas_v2_gbp", f"{rev_v2_dec:.3f}", "GBP", "Base principal V2 (vendas positivas padrão sem ajustes A e sem duplicatas exatas)"),
        ("faturamento_vendas_positivas_v1_gbp", f"{rev_v1_dec:.3f}", "GBP", "Reprodução da regra V1 (Quantity > 0 e UnitPrice > 0 sem duplicatas exatas)"),
        ("pedidos_validos_v2", str(orders_v2), "pedidos", "Quantidade de InvoiceNo distintos na base V2"),
        ("pedidos_validos_v1", str(orders_v1), "pedidos", "Quantidade de InvoiceNo distintos na reprodução V1"),
        ("ticket_medio_geral_v2_gbp", f"{ticket_v2:.2f}", "GBP", "Faturamento total V2 / pedidos distintos V2"),
        ("ticket_medio_geral_v1_gbp", f"{ticket_v1:.2f}", "GBP", "Faturamento total V1 / pedidos distintos V1"),
        ("unidades_vendidas_v2", str(units_v2), "unidades", "Soma de Quantity nas transações válidas V2"),
        ("linhas_transacao_v2", str(len(df_sales_v2)), "linhas", "Granularidade transacional após triagem e deduplicação"),
        ("clientes_identificados_v2", str(len(df_rfm)), "clientes", "Clientes com CustomerID preenchido na base V2"),
        ("faturamento_clientes_identificados_gbp", f"{identification_summary['faturamento_identificado_decimal']:.3f}", "GBP", "Receita atribuível a clientes identificados"),
        ("faturamento_sem_identificacao_gbp", f"{identification_summary['faturamento_nao_identificado_decimal']:.3f}", "GBP", "Receita válida sem CustomerID (mantida nas visões gerais)"),
        ("participacao_faturamento_sem_cliente_pct", f"{identification_summary['percentual_faturamento_nao_identificado']:.2f}", "%", "Percentual da receita V2 sem CustomerID"),
        ("taxa_recorrencia_observada_pct", f"{recurrence_summary['taxa_recorrencia_observada_pct']:.2f}", "%", "Clientes com 2 ou mais pedidos distintos no período"),
        ("clientes_compra_unica", str(recurrence_summary["clientes_compra_unica"]), "clientes", "Clientes identificados com exatamente 1 pedido"),
        ("clientes_recorrentes", str(recurrence_summary["clientes_recorrentes"]), "clientes", "Clientes identificados com 2 ou mais pedidos"),
        ("concentracao_top10_clientes_identificados_pct", f"{recurrence_summary['concentracao_clientes']['top_10']['participacao_receita_identificada_pct']:.2f}", "%", "Participação dos 10 maiores clientes sobre a receita identificada"),
        ("concentracao_top50_clientes_identificados_pct", f"{recurrence_summary['concentracao_clientes']['top_50']['participacao_receita_identificada_pct']:.2f}", "%", "Participação dos 50 maiores clientes sobre a receita identificada"),
        ("recencia_media_dias", f"{df_rfm['recencia_dias'].mean():.2f}", "dias", f"Média de dias até data de referência RFM ({ref_date_str})"),
        ("recencia_mediana_dias", f"{df_rfm['recencia_dias'].median():.2f}", "dias", f"Mediana de dias até data de referência RFM ({ref_date_str})"),
        ("frequencia_media_pedidos", f"{df_rfm['frequencia'].mean():.2f}", "pedidos", "Média de pedidos distintos por cliente identificado"),
        ("valor_monetario_medio_cliente_gbp", f"{df_rfm['valor_monetario'].mean():.2f}", "GBP", "Média acumulada por cliente identificado"),
        ("valor_monetario_mediano_cliente_gbp", f"{df_rfm['valor_monetario'].median():.2f}", "GBP", "Mediana acumulada por cliente (evidencia assimetria)"),
        ("notas_cancelamento_distintas", str(cancellations_summary["notas_cancelamento_distintas"]), "notas", "InvoiceNo distintos iniciados pela letra C"),
        ("valor_cancelamentos_deduplicados_gbp", f"{cancellations_summary['valor_cancelamentos_deduplicados_decimal']:.3f}", "GBP", "Valor monetário das notas de cancelamento sem duplicatas exatas"),
        ("participacao_cancelamentos_sobre_vendas_v2_pct", f"{cancellations_summary['participacao_cancelamentos_dedup_sobre_vendas_v2_pct']:.2f}", "%", "abs(cancelamentos deduplicados) / vendas positivas V2"),
        ("saldo_monetario_observado_dedup_gbp", f"{cancellations_summary['saldo_monetario_observado_dedup_decimal']:.3f}", "GBP", "Vendas positivas V2 + cancelamentos deduplicados (não é receita líquida contábil)"),
    ]

    return pd.DataFrame(rows, columns=["indicador", "valor", "unidade", "observacao"])
