"""Investigação de registros atípicos e análise de sensibilidade metodológica."""

from decimal import Decimal
from typing import Any

import pandas as pd

from src.analytics.commercial import build_product_ranking
from src.analytics.orders import build_orders_table
from src.config import (
    PRIMARY_OUTLIER_INVOICE,
    PRIMARY_OUTLIER_STOCK_CODE,
    SECONDARY_OUTLIER_INVOICE,
    SECONDARY_OUTLIER_STOCK_CODE,
)
from src.data.cleaning import CATEGORY_CANCELLATION


def _inspect_single_outlier(
    df_classified: pd.DataFrame,
    df_sales_v2: pd.DataFrame,
    invoice_no: str,
    stock_code: str,
) -> dict[str, Any]:
    """Inspeciona um registro de venda atípico e eventuais cancelamentos compatíveis."""
    sale_rows = df_sales_v2.loc[
        (df_sales_v2["invoice_no"] == invoice_no)
        & (df_sales_v2["stock_code"] == stock_code)
    ].copy()

    if sale_rows.empty:
        return {
            "encontrado": False,
            "invoice_no": invoice_no,
            "stock_code": stock_code,
        }

    row = sale_rows.iloc[0]
    qty = int(row["quantity"])
    price = float(row["unit_price"])
    val_dec: Decimal = row["valor_linha_decimal"]
    cid = row["customer_id"]
    dt = row["invoice_date"]
    desc = row["description"]

    # Participação no volume total do produto na base principal V2
    product_all_v2 = df_sales_v2.loc[df_sales_v2["stock_code"] == stock_code]
    total_product_units = int(product_all_v2["quantity"].sum())
    total_product_orders = int(product_all_v2["invoice_no"].nunique())
    share_product_units_pct = (
        round((qty / total_product_units) * 100, 2) if total_product_units > 0 else 0.0
    )

    # Busca notas de cancelamento potencialmente relacionadas sem afirmar vínculo comprovado
    canc_rows = df_classified.loc[
        (df_classified["categoria_registro"] == CATEGORY_CANCELLATION)
        & (df_classified["stock_code"] == stock_code)
        & (df_classified["quantity"] == -qty)
    ].copy()
    if cid is not None:
        canc_rows = canc_rows.loc[canc_rows["customer_id"] == cid]

    potential_cancellations: list[dict[str, Any]] = []
    for c_inv, c_qty, c_price, c_val, c_dt in zip(
        canc_rows["invoice_no"],
        canc_rows["quantity"],
        canc_rows["unit_price"],
        canc_rows["valor_linha_decimal"],
        canc_rows["invoice_date"],
    ):
        diff_min = round((c_dt - dt).total_seconds() / 60.0, 2)
        potential_cancellations.append(
            {
                "invoice_no_cancelamento": c_inv,
                "quantity": int(c_qty),
                "unit_price": float(c_price),
                "valor_decimal": str(c_val),
                "invoice_date": str(c_dt),
                "diferenca_minutos": diff_min,
            }
        )

    # Outros pedidos positivos do mesmo cliente para contextualização
    other_customer_orders = 0
    other_customer_rev_dec = Decimal("0")
    if cid is not None:
        other_sub = df_sales_v2.loc[
            (df_sales_v2["customer_id"] == cid)
            & (df_sales_v2["invoice_no"] != invoice_no)
        ]
        other_customer_orders = int(other_sub["invoice_no"].nunique())
        other_customer_rev_dec = sum(other_sub["valor_linha_decimal"], Decimal("0"))

    return {
        "encontrado": True,
        "invoice_no": invoice_no,
        "stock_code": stock_code,
        "description": desc,
        "customer_id": cid,
        "country": row["country"],
        "invoice_date": str(dt),
        "quantity": qty,
        "unit_price": price,
        "valor_decimal": val_dec,
        "participacao_volume_produto_pct": share_product_units_pct,
        "pedidos_totais_produto_v2": total_product_orders,
        "outros_pedidos_mesmo_cliente": other_customer_orders,
        "receita_outros_pedidos_cliente_decimal": other_customer_rev_dec,
        "cancelamentos_potencialmente_relacionados": potential_cancellations,
        "nota_metodologica": (
            "A base da UCI não possui chave estrangeira vinculando notas de "
            "cancelamento ao pedido original; a correspondência por produto, "
            "cliente, quantidade oposta e proximidade temporal constitui forte "
            "indício operacional, mas não prova documental definitiva."
        ),
    }


def investigate_primary_outliers(
    df_classified: pd.DataFrame,
    df_sales_v2: pd.DataFrame,
) -> dict[str, Any]:
    """Investiga os dois maiores pedidos atípicos identificados na auditoria."""
    outlier_primary = _inspect_single_outlier(
        df_classified,
        df_sales_v2,
        invoice_no=PRIMARY_OUTLIER_INVOICE,
        stock_code=PRIMARY_OUTLIER_STOCK_CODE,
    )
    outlier_secondary = _inspect_single_outlier(
        df_classified,
        df_sales_v2,
        invoice_no=SECONDARY_OUTLIER_INVOICE,
        stock_code=SECONDARY_OUTLIER_STOCK_CODE,
    )
    return {
        "outlier_principal_23843": outlier_primary,
        "outlier_secundario_23166": outlier_secondary,
    }


def _evaluate_scenario(
    nome_cenario: str,
    descricao_regra: str,
    df_scenario: pd.DataFrame,
    base_rev_dec: Decimal,
    base_orders: int,
    base_units: int,
) -> dict[str, Any]:
    """Calcula os mesmos KPIs e líderes de ranking para um cenário de sensibilidade."""
    orders_df, _ = build_orders_table(df_scenario)
    products_df = build_product_ranking(df_scenario)

    rev_dec = sum(df_scenario["valor_linha_decimal"], Decimal("0"))
    n_rows = int(len(df_scenario))
    n_orders = int(len(orders_df))
    n_units = int(df_scenario["quantity"].sum())
    n_customers = int(df_scenario["customer_id"].nunique(dropna=True))
    ticket_medio = float(rev_dec) / n_orders if n_orders > 0 else 0.0

    # Líder de produto por unidades vendidas
    top_prod_units = products_df.sort_values(
        by=["unidades_vendidas", "stock_code"], ascending=[False, True]
    ).iloc[0]

    # Líder de cliente por faturamento
    df_ident = df_scenario.dropna(subset=["customer_id"])
    if not df_ident.empty:
        top_cust = (
            df_ident.groupby("customer_id")
            .agg(faturamento=("valor_linha", "sum"))
            .reset_index()
            .sort_values(by=["faturamento", "customer_id"], ascending=[False, True])
            .iloc[0]
        )
        top_cust_id = str(top_cust["customer_id"])
        top_cust_rev = float(top_cust["faturamento"])
    else:
        top_cust_id = "N/A"
        top_cust_rev = 0.0

    # País com maior ticket médio
    country_ticket = (
        orders_df.groupby("country")
        .agg(
            pedidos=("invoice_no", "nunique"),
            faturamento=("faturamento_pedido", "sum"),
        )
        .reset_index()
    )
    country_ticket["ticket_medio"] = (
        country_ticket["faturamento"] / country_ticket["pedidos"]
    )
    top_country_ticket = country_ticket.sort_values(
        by=["ticket_medio", "country"], ascending=[False, True]
    ).iloc[0]

    delta_rev_dec = rev_dec - base_rev_dec
    delta_rev_pct = (
        round(float((delta_rev_dec / base_rev_dec) * Decimal("100")), 4)
        if base_rev_dec > 0
        else 0.0
    )

    return {
        "cenario": nome_cenario,
        "regra_aplicada": descricao_regra,
        "linhas_transacao": n_rows,
        "pedidos_distintos": n_orders,
        "delta_pedidos_vs_base": n_orders - base_orders,
        "clientes_identificados": n_customers,
        "unidades_vendidas": n_units,
        "delta_unidades_vs_base": n_units - base_units,
        "faturamento_total_decimal": rev_dec,
        "faturamento_total": float(rev_dec),
        "delta_faturamento_decimal": delta_rev_dec,
        "delta_faturamento_pct": delta_rev_pct,
        "ticket_medio": round(ticket_medio, 2),
        "produto_lider_unidades": f"{top_prod_units['stock_code']} - {top_prod_units['descricao_principal']}",
        "produto_lider_unidades_qtd": int(top_prod_units["unidades_vendidas"]),
        "cliente_lider_faturamento": top_cust_id,
        "cliente_lider_faturamento_valor": round(top_cust_rev, 2),
        "pais_maior_ticket_medio": f"{top_country_ticket['country']} ({int(top_country_ticket['pedidos'])} pedidos)",
        "pais_maior_ticket_medio_valor": round(float(top_country_ticket["ticket_medio"]), 2),
    }


def run_sensitivity_analysis(
    df_sales_v2: pd.DataFrame,
    df_sales_v1: pd.DataFrame,
    df_valid_raw: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Compara a base principal V2 frente a cenários metodológicos alternativos."""
    base_rev_dec = sum(df_sales_v2["valor_linha_decimal"], Decimal("0"))
    base_orders = int(df_sales_v2["invoice_no"].nunique())
    base_units = int(df_sales_v2["quantity"].sum())

    # Prepara recortes derivados preservando integralmente df_sales_v2
    df_sem_outlier_principal = df_sales_v2.loc[
        df_sales_v2["invoice_no"] != PRIMARY_OUTLIER_INVOICE
    ].copy()
    df_sem_dois_outliers = df_sales_v2.loc[
        ~df_sales_v2["invoice_no"].isin(
            [PRIMARY_OUTLIER_INVOICE, SECONDARY_OUTLIER_INVOICE]
        )
    ].copy()
    df_apenas_mercadorias = df_sales_v2.loc[
        ~df_sales_v2["is_non_merchandise_code"]
    ].copy()

    cenarios_def = [
        (
            "1. Base Principal V2",
            "Vendas positivas padrão sem prefixo A e sem duplicatas exatas",
            df_sales_v2,
        ),
        (
            "2. Reprodução da Regra V1",
            "Quantity > 0 e UnitPrice > 0 sem duplicatas exatas (regra original V1)",
            df_sales_v1,
        ),
        (
            "3. Sem Remoção de Duplicatas Exatas",
            "Mantém as linhas exatamente repetidas na base positiva padrão",
            df_valid_raw,
        ),
        (
            "4. Sem Outlier Principal (581483)",
            "Exclui o pedido 581483 (23843 - PAPER CRAFT , LITTLE BIRDIE, 80.995 un.)",
            df_sem_outlier_principal,
        ),
        (
            "5. Sem Dois Maiores Outliers (581483 e 541431)",
            "Exclui os pedidos 581483 (80.995 un.) e 541431 (74.215 un.)",
            df_sem_dois_outliers,
        ),
        (
            "6. Apenas Mercadorias (sem códigos operacionais)",
            "Exclui códigos não-mercadoria (DOT, POST, M, AMAZONFEE, C2, BANK CHARGES, etc.)",
            df_apenas_mercadorias,
        ),
    ]

    resultados: list[dict[str, Any]] = []
    for nome, regra, frame in cenarios_def:
        if not frame.empty:
            resultados.append(
                _evaluate_scenario(
                    nome_cenario=nome,
                    descricao_regra=regra,
                    df_scenario=frame,
                    base_rev_dec=base_rev_dec,
                    base_orders=base_orders,
                    base_units=base_units,
                )
            )

    df_sensitivity = pd.DataFrame(resultados)

    # Impacto específico nos rankings de clientes e produtos ao retirar os outliers
    ranking_impact = {
        "linhas_codigos_operacionais_na_base_v2": int(
            df_sales_v2["is_non_merchandise_code"].sum()
        ),
        "valor_codigos_operacionais_na_base_v2_decimal": sum(
            df_sales_v2.loc[
                df_sales_v2["is_non_merchandise_code"], "valor_linha_decimal"
            ],
            Decimal("0"),
        ),
    }

    return df_sensitivity, ranking_impact
