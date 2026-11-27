"""Segmentação RFM baseada em regras transparentes, recorrência e concentração."""

from decimal import Decimal
from typing import Any

import pandas as pd

from src.analytics.orders import sum_decimal_by_key
from src.config import RFM_SEGMENT_ORDER, RFM_THRESHOLDS, to_decimal


def classify_rfm_segment(
    recencia_dias: int,
    frequencia: int,
    valor_monetario: Decimal | float,
    thresholds: dict[str, Any] | None = None,
) -> str:
    """Classifica um cliente em exatamente um segmento RFM por ordem de prioridade.

    Ordem de prioridade (mutuamente exclusiva e coletivamente exaustiva):
    1. Alto valor e recorrentes: frequencia >= 5, valor_monetario >= £ 1.500 e recencia <= 90 dias
    2. Recorrentes recentes: frequencia >= 2 e recencia <= 90 dias
    3. Compra única recente: frequencia == 1 e recencia <= 90 dias
    4. Recorrentes há mais tempo sem compras: frequencia >= 2 e recencia > 90 dias
    5. Compra única há mais tempo sem compras: frequencia == 1 e recencia > 90 dias
    """
    cfg = thresholds if thresholds is not None else RFM_THRESHOLDS
    if frequencia < 1:
        raise ValueError(f"Frequência inválida para segmentação RFM: {frequencia}")
    if recencia_dias < 0:
        raise ValueError(f"Recência negativa inválida para segmentação RFM: {recencia_dias}")

    valor_dec = to_decimal(valor_monetario)
    recencia_max = int(cfg["recencia_recente_max_dias"])
    freq_rec_min = int(cfg["frequencia_recorrente_min_pedidos"])
    freq_hv_min = int(cfg["frequencia_alto_valor_min_pedidos"])
    valor_hv_min = to_decimal(cfg["valor_monetario_alto_valor_min_gbp"])

    if (
        frequencia >= freq_hv_min
        and valor_dec >= valor_hv_min
        and recencia_dias <= recencia_max
    ):
        return "Alto valor e recorrentes"

    if frequencia >= freq_rec_min and recencia_dias <= recencia_max:
        return "Recorrentes recentes"

    if frequencia == 1 and recencia_dias <= recencia_max:
        return "Compra única recente"

    if frequencia >= freq_rec_min and recencia_dias > recencia_max:
        return "Recorrentes há mais tempo sem compras"

    return "Compra única há mais tempo sem compras"


def apply_rfm_segmentation(
    df_customers: pd.DataFrame,
    thresholds: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Aplica a segmentação RFM a todos os clientes elegíveis e verifica unicidade."""
    if df_customers.empty:
        raise ValueError("A base de clientes não pode estar vazia para segmentação.")

    if df_customers["customer_id"].duplicated().any():
        raise ValueError("Há CustomerID duplicado na base de clientes antes da segmentação.")

    df_rfm = df_customers.copy()
    segmentos: list[str] = []
    for rec, freq, mon in zip(
        df_rfm["recencia_dias"],
        df_rfm["frequencia"],
        df_rfm["faturamento_acumulado_decimal"],
    ):
        segmentos.append(
            classify_rfm_segment(
                recencia_dias=int(rec),
                frequencia=int(freq),
                valor_monetario=mon,
                thresholds=thresholds,
            )
        )

    df_rfm["segmento_rfm"] = segmentos

    # Garantia explícita: todos os segmentos pertencem ao conjunto oficial e sem nulos
    if df_rfm["segmento_rfm"].isna().any():
        raise ValueError("Existem clientes sem segmento RFM atribuído.")
    if not df_rfm["segmento_rfm"].isin(RFM_SEGMENT_ORDER).all():
        raise ValueError("Foram encontrados rótulos de segmento fora do padrão oficial.")

    return df_rfm


def summarize_rfm_segments(df_rfm: pd.DataFrame) -> pd.DataFrame:
    """Consolida métricas comerciais e comportamentais por segmento RFM."""
    total_clientes = int(len(df_rfm))
    total_receita_dec = sum(df_rfm["faturamento_acumulado_decimal"], Decimal("0"))
    dec_por_segmento = sum_decimal_by_key(
        df_rfm["segmento_rfm"], df_rfm["faturamento_acumulado_decimal"]
    )

    grouped = (
        df_rfm.groupby("segmento_rfm")
        .agg(
            qtd_clientes=("customer_id", "count"),
            faturamento_total=("valor_monetario", "sum"),
            pedidos_totais=("frequencia", "sum"),
            unidades_totais=("quantidade_unidades", "sum"),
            valor_monetario_medio_cliente=("valor_monetario", "mean"),
            valor_monetario_mediano_cliente=("valor_monetario", "median"),
            frequencia_media=("frequencia", "mean"),
            frequencia_mediana=("frequencia", "median"),
            recencia_media_dias=("recencia_dias", "mean"),
            recencia_mediana_dias=("recencia_dias", "median"),
        )
        .reset_index()
    )

    # Ordena de acordo com a prioridade oficial de segmentos (mantendo apenas os existentes ou todos)
    order_map = {seg: idx for idx, seg in enumerate(RFM_SEGMENT_ORDER)}
    grouped["ordem_prioridade"] = [order_map[seg] for seg in grouped["segmento_rfm"]]
    grouped = grouped.sort_values(by="ordem_prioridade").reset_index(drop=True)

    grouped["faturamento_total_decimal"] = [
        dec_por_segmento[seg] for seg in grouped["segmento_rfm"]
    ]
    grouped["participacao_clientes_pct"] = (
        grouped["qtd_clientes"] / total_clientes * 100
        if total_clientes > 0
        else 0.0
    )
    grouped["participacao_faturamento_pct"] = [
        float((val / total_receita_dec) * Decimal("100"))
        if total_receita_dec > 0
        else 0.0
        for val in grouped["faturamento_total_decimal"]
    ]
    # Ticket médio correto do segmento = faturamento total do segmento / total de pedidos do segmento
    grouped["ticket_medio_segmento"] = (
        grouped["faturamento_total"] / grouped["pedidos_totais"]
    )

    return grouped


def _classify_frequency_bucket(freq: int) -> str:
    """Agrupa frequência de pedidos em faixas comerciais legíveis."""
    if freq == 1:
        return "1 pedido"
    if freq == 2:
        return "2 pedidos"
    if 3 <= freq <= 4:
        return "3 a 4 pedidos"
    if 5 <= freq <= 9:
        return "5 a 9 pedidos"
    return "10 ou mais pedidos"


def analyze_recurrence_and_concentration(
    df_rfm: pd.DataFrame,
    df_products: pd.DataFrame,
    df_countries: pd.DataFrame,
    total_overall_revenue_decimal: Decimal,
) -> dict[str, Any]:
    """Calcula recorrência observada no período, faixas de frequência e concentração."""
    total_customers = int(len(df_rfm))
    single_order_df = df_rfm.loc[df_rfm["frequencia"] == 1]
    repeat_order_df = df_rfm.loc[df_rfm["frequencia"] >= 2]

    single_count = int(len(single_order_df))
    repeat_count = int(len(repeat_order_df))
    recurrence_rate_pct = (
        round((repeat_count / total_customers) * 100, 2) if total_customers > 0 else 0.0
    )

    # Contexto de janela de observação: clientes cuja primeira compra ocorreu nos últimos 90 dias
    recent_first_purchase = df_rfm.loc[df_rfm["dias_desde_primeira_compra"] <= 90]
    recent_first_single = recent_first_purchase.loc[
        recent_first_purchase["frequencia"] == 1
    ]

    # Distribuição por faixas de frequência
    bucket_order = [
        "1 pedido",
        "2 pedidos",
        "3 a 4 pedidos",
        "5 a 9 pedidos",
        "10 ou mais pedidos",
    ]
    df_freq = df_rfm.copy()
    df_freq["faixa_frequencia"] = [
        _classify_frequency_bucket(int(f)) for f in df_freq["frequencia"]
    ]
    total_ident_rev_dec = sum(df_rfm["faturamento_acumulado_decimal"], Decimal("0"))
    dec_by_bucket = sum_decimal_by_key(
        df_freq["faixa_frequencia"], df_freq["faturamento_acumulado_decimal"]
    )

    freq_rows: list[dict[str, Any]] = []
    for bucket in bucket_order:
        sub = df_freq.loc[df_freq["faixa_frequencia"] == bucket]
        cnt = int(len(sub))
        rev_dec = dec_by_bucket.get(bucket, Decimal("0"))
        freq_rows.append(
            {
                "faixa_frequencia": bucket,
                "qtd_clientes": cnt,
                "participacao_clientes_pct": round((cnt / total_customers) * 100, 2)
                if total_customers > 0
                else 0.0,
                "faturamento_decimal": rev_dec,
                "participacao_faturamento_identificado_pct": round(
                    float((rev_dec / total_ident_rev_dec) * Decimal("100")), 2
                )
                if total_ident_rev_dec > 0
                else 0.0,
            }
        )

    # Concentração em clientes (Top 10, Top 50, Top 100)
    rfm_sorted = df_rfm.sort_values(
        by=["valor_monetario", "customer_id"], ascending=[False, True]
    ).reset_index(drop=True)

    customer_concentration: dict[str, dict[str, Any]] = {}
    for top_n in (10, 50, 100):
        slice_df = rfm_sorted.head(top_n)
        rev_dec = sum(slice_df["faturamento_acumulado_decimal"], Decimal("0"))
        customer_concentration[f"top_{top_n}"] = {
            "qtd_clientes": int(len(slice_df)),
            "faturamento_decimal": rev_dec,
            "participacao_receita_identificada_pct": round(
                float((rev_dec / total_ident_rev_dec) * Decimal("100")), 2
            )
            if total_ident_rev_dec > 0
            else 0.0,
            "participacao_receita_total_pct": round(
                float((rev_dec / total_overall_revenue_decimal) * Decimal("100")), 2
            )
            if total_overall_revenue_decimal > 0
            else 0.0,
        }

    # Concentração em produtos (Top 10 por faturamento e Top 10 por unidades)
    prod_by_rev = df_products.sort_values(
        by=["faturamento_total", "stock_code"], ascending=[False, True]
    ).reset_index(drop=True)
    top10_prod_rev_dec = sum(
        prod_by_rev.head(10)["faturamento_total_decimal"], Decimal("0")
    )
    top10_prod_rev_pct = (
        round(
            float((top10_prod_rev_dec / total_overall_revenue_decimal) * Decimal("100")),
            2,
        )
        if total_overall_revenue_decimal > 0
        else 0.0
    )

    # Concentração geográfica (Top 1 e Top 5 países por faturamento)
    countries_by_rev = df_countries.sort_values(
        by=["faturamento_total", "country"], ascending=[False, True]
    ).reset_index(drop=True)
    top1_country = countries_by_rev.head(1)
    top5_countries = countries_by_rev.head(5)
    top1_rev_dec = sum(top1_country["faturamento_total_decimal"], Decimal("0"))
    top5_rev_dec = sum(top5_countries["faturamento_total_decimal"], Decimal("0"))

    return {
        "total_clientes_identificados": total_customers,
        "clientes_compra_unica": single_count,
        "participacao_compra_unica_pct": round((single_count / total_customers) * 100, 2)
        if total_customers > 0
        else 0.0,
        "clientes_recorrentes": repeat_count,
        "taxa_recorrencia_observada_pct": recurrence_rate_pct,
        "faturamento_compra_unica_decimal": sum(
            single_order_df["faturamento_acumulado_decimal"], Decimal("0")
        ),
        "faturamento_recorrentes_decimal": sum(
            repeat_order_df["faturamento_acumulado_decimal"], Decimal("0")
        ),
        "clientes_primeira_compra_ultimos_90_dias": int(len(recent_first_purchase)),
        "clientes_compra_unica_primeira_compra_ultimos_90_dias": int(
            len(recent_first_single)
        ),
        "distribuicao_frequencia": freq_rows,
        "concentracao_clientes": customer_concentration,
        "concentracao_top10_produtos_faturamento_decimal": top10_prod_rev_dec,
        "concentracao_top10_produtos_faturamento_pct": top10_prod_rev_pct,
        "pais_lider_faturamento": str(top1_country.iloc[0]["country"])
        if not top1_country.empty
        else None,
        "pais_lider_faturamento_decimal": top1_rev_dec,
        "pais_lider_faturamento_pct": round(
            float((top1_rev_dec / total_overall_revenue_decimal) * Decimal("100")), 2
        )
        if total_overall_revenue_decimal > 0
        else 0.0,
        "top5_paises_faturamento_decimal": top5_rev_dec,
        "top5_paises_faturamento_pct": round(
            float((top5_rev_dec / total_overall_revenue_decimal) * Decimal("100")), 2
        )
        if total_overall_revenue_decimal > 0
        else 0.0,
    }
