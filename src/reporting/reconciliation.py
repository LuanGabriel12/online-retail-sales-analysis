"""Reconciliação matemática independente entre todas as camadas analíticas."""

from decimal import Decimal
from typing import Any

import pandas as pd

from src.config import (
    DISPLAY_QUANTIZE,
    RECONCILIATION_TOLERANCE_FLOAT,
    quantize_gbp,
)


def _make_check(
    codigo: str,
    descricao: str,
    esperado: Any,
    observado: Any,
    diferenca: Any,
    aprovado: bool,
    observacao: str = "",
) -> dict[str, Any]:
    """Cria registro padronizado de verificação de reconciliação."""
    return {
        "codigo": codigo,
        "descricao": descricao,
        "esperado": str(esperado),
        "observado": str(observado),
        "diferenca": str(diferenca),
        "status": "APROVADO" if aprovado else "REPROVADO",
        "aprovado": bool(aprovado),
        "observacao": observacao,
    }


def run_reconciliation(
    resumo_limpeza: dict[str, Any],
    df_sales_v2: pd.DataFrame,
    df_orders_v2: pd.DataFrame,
    df_customers_rfm: pd.DataFrame,
    df_segments_summary: pd.DataFrame,
    df_products: pd.DataFrame,
    df_countries: pd.DataFrame,
    df_monthly: pd.DataFrame,
    identification_summary: dict[str, Any],
    country_notes: dict[str, Any],
) -> dict[str, Any]:
    """Executa bateria independente de reconciliações de linhas, receita, pedidos e clientes."""
    checagens: list[dict[str, Any]] = []

    # 1. Reconciliação de linhas brutas vs categorias mutuamente exclusivas da triagem
    linhas_brutas = int(resumo_limpeza["linhas_brutas"])
    soma_triagem = sum(resumo_limpeza["contagem_triagem"].values())
    checagens.append(
        _make_check(
            "REC-01",
            "Linhas brutas vs soma das categorias mutuamente exclusivas de triagem",
            linhas_brutas,
            soma_triagem,
            soma_triagem - linhas_brutas,
            soma_triagem == linhas_brutas,
        )
    )

    # 2. Linhas mantidas + duplicatas removidas + linhas excluídas não-venda == linhas brutas
    soma_destino = (
        int(resumo_limpeza["linhas_mantidas_v2"])
        + int(resumo_limpeza["duplicatas_exatas_removidas_em_vendas"])
        + int(resumo_limpeza["linhas_excluidas_nao_venda"])
    )
    checagens.append(
        _make_check(
            "REC-02",
            "Linhas brutas vs mantidas V2 + duplicatas removidas + excluídas não-venda",
            linhas_brutas,
            soma_destino,
            soma_destino - linhas_brutas,
            soma_destino == linhas_brutas,
        )
    )

    # Totais exatos em Decimal por camada
    rev_trans_dec = sum(df_sales_v2["valor_linha_decimal"], Decimal("0"))
    rev_orders_dec = sum(df_orders_v2["faturamento_pedido_decimal"], Decimal("0"))
    rev_products_dec = sum(df_products["faturamento_total_decimal"], Decimal("0"))
    rev_countries_dec = sum(df_countries["faturamento_total_decimal"], Decimal("0"))
    rev_monthly_dec = sum(df_monthly["faturamento_total_decimal"], Decimal("0"))

    # 3 a 6. Faturamento transacional vs pedidos, produtos, países e mensal
    for code, label, obs_dec in [
        ("REC-03", "Faturamento transacional vs base de pedidos (Decimal)", rev_orders_dec),
        ("REC-04", "Faturamento transacional vs ranking de produtos (Decimal)", rev_products_dec),
        ("REC-05", "Faturamento transacional vs análise por país (Decimal)", rev_countries_dec),
        ("REC-06", "Faturamento transacional vs evolução mensal (Decimal)", rev_monthly_dec),
    ]:
        diff_dec = obs_dec - rev_trans_dec
        checagens.append(
            _make_check(
                code,
                label,
                f"{rev_trans_dec:.3f}",
                f"{obs_dec:.3f}",
                f"{diff_dec:.3f}",
                diff_dec == Decimal("0"),
            )
        )

    # 7. Faturamento identificado + não identificado == transacional total
    rev_ident_dec = identification_summary["faturamento_identificado_decimal"]
    rev_unident_dec = identification_summary["faturamento_nao_identificado_decimal"]
    soma_ident_unident = rev_ident_dec + rev_unident_dec
    diff_ident = soma_ident_unident - rev_trans_dec
    checagens.append(
        _make_check(
            "REC-07",
            "Faturamento transacional vs soma (identificado + sem CustomerID)",
            f"{rev_trans_dec:.3f}",
            f"{soma_ident_unident:.3f}",
            f"{diff_ident:.3f}",
            diff_ident == Decimal("0"),
        )
    )

    # 8. Faturamento identificado na base transacional vs soma da base de clientes
    rev_cust_dec = sum(df_customers_rfm["faturamento_acumulado_decimal"], Decimal("0"))
    diff_cust = rev_cust_dec - rev_ident_dec
    checagens.append(
        _make_check(
            "REC-08",
            "Faturamento de clientes identificados vs soma da base de clientes (Decimal)",
            f"{rev_ident_dec:.3f}",
            f"{rev_cust_dec:.3f}",
            f"{diff_cust:.3f}",
            diff_cust == Decimal("0"),
        )
    )

    # 9. Faturamento por segmento RFM vs total elegível para segmentação
    rev_seg_dec = sum(df_segments_summary["faturamento_total_decimal"], Decimal("0"))
    diff_seg = rev_seg_dec - rev_cust_dec
    checagens.append(
        _make_check(
            "REC-09",
            "Faturamento total dos segmentos RFM vs base elegível de clientes (Decimal)",
            f"{rev_cust_dec:.3f}",
            f"{rev_seg_dec:.3f}",
            f"{diff_seg:.3f}",
            diff_seg == Decimal("0"),
        )
    )

    # 10. Quantidade de clientes por segmento vs elegíveis (unicidade sem sobreposição)
    n_cust_elegiveis = int(len(df_customers_rfm))
    n_cust_distintos = int(df_customers_rfm["customer_id"].nunique())
    n_cust_segmentos = int(df_segments_summary["qtd_clientes"].sum())
    checagens.append(
        _make_check(
            "REC-10",
            "Clientes elegíveis vs soma de clientes nos segmentos (classificação única)",
            n_cust_elegiveis,
            n_cust_segmentos,
            n_cust_segmentos - n_cust_elegiveis,
            (n_cust_segmentos == n_cust_elegiveis) and (n_cust_distintos == n_cust_elegiveis),
        )
    )

    # 11. Pedidos distintos transacional vs base de pedidos
    orders_trans = int(df_sales_v2["invoice_no"].nunique())
    orders_base = int(len(df_orders_v2))
    checagens.append(
        _make_check(
            "REC-11",
            "Pedidos distintos na base transacional vs linhas na base de pedidos",
            orders_trans,
            orders_base,
            orders_base - orders_trans,
            orders_base == orders_trans,
        )
    )

    # 12. Pedidos base de pedidos vs soma por país (válido por 0 conflitos de país por pedido)
    orders_countries = int(df_countries["pedidos_distintos"].sum())
    checagens.append(
        _make_check(
            "REC-12",
            "Total de pedidos vs soma de pedidos por país (sem conflito de país/pedido)",
            orders_base,
            orders_countries,
            orders_countries - orders_base,
            orders_countries == orders_base,
        )
    )

    # 13. Pedidos base de pedidos vs soma mensal
    orders_monthly = int(df_monthly["pedidos_distintos"].sum())
    checagens.append(
        _make_check(
            "REC-13",
            "Total de pedidos vs soma de pedidos por mês",
            orders_base,
            orders_monthly,
            orders_monthly - orders_base,
            orders_monthly == orders_base,
        )
    )

    # 14. Pedidos identificados vs soma de frequência dos clientes e segmentos
    orders_ident = int(identification_summary["pedidos_com_cliente"])
    freq_sum_cust = int(df_customers_rfm["frequencia"].sum())
    freq_sum_seg = int(df_segments_summary["pedidos_totais"].sum())
    checagens.append(
        _make_check(
            "REC-14",
            "Pedidos identificados vs soma da frequência em clientes e segmentos",
            orders_ident,
            freq_sum_cust,
            freq_sum_cust - orders_ident,
            (freq_sum_cust == orders_ident) and (freq_sum_seg == orders_ident),
            observacao=f"Soma pedidos nos segmentos: {freq_sum_seg}",
        )
    )

    # 15. Consistência de unidades entre todas as bases
    units_trans = int(df_sales_v2["quantity"].sum())
    units_orders = int(df_orders_v2["quantidade_unidades"].sum())
    units_products = int(df_products["unidades_vendidas"].sum())
    units_countries = int(df_countries["unidades_vendidas"].sum())
    units_monthly = int(df_monthly["unidades_vendidas"].sum())
    all_units_match = (
        units_trans == units_orders == units_products == units_countries == units_monthly
    )
    checagens.append(
        _make_check(
            "REC-15",
            "Unidades vendidas: transacional vs pedidos, produtos, países e mensal",
            units_trans,
            units_orders,
            units_orders - units_trans,
            all_units_match,
            observacao=(
                f"produtos={units_products}, paises={units_countries}, mensal={units_monthly}"
            ),
        )
    )

    # 16. Consistência do ticket médio global (ponderado, nunca média simples de segmentos)
    ticket_global_formula = float(rev_trans_dec) / orders_base if orders_base > 0 else 0.0
    ticket_orders_mean = float(df_orders_v2["faturamento_pedido"].mean())
    diff_ticket = abs(ticket_global_formula - ticket_orders_mean)
    media_simples_segmentos = float(df_segments_summary["ticket_medio_segmento"].mean())
    checagens.append(
        _make_check(
            "REC-16",
            "Ticket médio global (Faturamento / Pedidos distintos) vs média por pedido",
            f"{ticket_global_formula:.6f}",
            f"{ticket_orders_mean:.6f}",
            f"{diff_ticket:.9f}",
            diff_ticket < 1e-6,
            observacao=(
                f"Média simples incorreta de segmentos seria £ {media_simples_segmentos:.2f} "
                f"(não utilizada)."
            ),
        )
    )

    # 17. Consistência entre soma em Decimal exato e soma em float64 do Pandas
    rev_trans_float = float(df_sales_v2["valor_linha"].sum())
    diff_float_vs_dec = abs(float(rev_trans_dec) - rev_trans_float)
    rev_rounded_2dp = quantize_gbp(rev_trans_dec, DISPLAY_QUANTIZE)
    rounding_delta = rev_rounded_2dp - rev_trans_dec
    checagens.append(
        _make_check(
            "REC-17",
            "Precisão monetária: soma exata Decimal vs float64 do Pandas",
            f"{rev_trans_dec:.3f}",
            f"{rev_trans_float:.6f}",
            f"{diff_float_vs_dec:.12f}",
            diff_float_vs_dec < RECONCILIATION_TOLERANCE_FLOAT,
            observacao=(
                f"Exibição 2 casas (ROUND_HALF_UP): £ {rev_rounded_2dp:.2f} "
                f"(diferença de arredondamento: {rounding_delta:+.3f} GBP)."
            ),
        )
    )

    # 18. Verificação de não aditividade de clientes distintos entre países
    global_cust = int(country_notes["clientes_distintos_globais"])
    sum_country_cust = int(country_notes["soma_clientes_por_pais"])
    expected_overlap = int(country_notes["diferenca_clientes_multiplos_paises"])
    checagens.append(
        _make_check(
            "REC-18",
            "Verificação de sobreposição de clientes distintos entre países",
            global_cust,
            sum_country_cust,
            expected_overlap,
            (sum_country_cust - global_cust) == expected_overlap,
            observacao=(
                f"{expected_overlap} cliente(s) compraram em mais de um país; "
                "contagens distintas por país não devem ser somadas."
            ),
        )
    )

    aprovadas = sum(1 for item in checagens if item["aprovado"])
    reprovadas = len(checagens) - aprovadas

    return {
        "todas_aprovadas": reprovadas == 0,
        "total_checagens": len(checagens),
        "aprovadas": aprovadas,
        "reprovadas": reprovadas,
        "checagens": checagens,
        "auditoria_monetaria": {
            "faturamento_exato_decimal": str(rev_trans_dec),
            "faturamento_float64": repr(rev_trans_float),
            "diferenca_absoluta_float_vs_decimal": f"{diff_float_vs_dec:.12f}",
            "faturamento_exibicao_2_casas": str(rev_rounded_2dp),
            "delta_arredondamento_2_casas": str(rounding_delta),
        },
    }
