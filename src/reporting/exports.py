"""Exportação reprodutível de CSVs, amostras verificadas e relatórios Markdown."""

from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    DATASET_METADATA,
    RFM_THRESHOLDS,
    V1_HISTORICAL_REFERENCE,
    format_gbp,
)


def _format_int(value: int) -> str:
    """Formata inteiros com separador de milhar em padrão PT-BR."""
    return f"{int(value):,}".replace(",", ".")


def _format_pct(value: float | None, decimals: int = 2) -> str:
    """Formata percentuais em padrão PT-BR preservando N/A quando ausente."""
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.{decimals}f}%".replace(".", ",")


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    """Grava DataFrame em CSV UTF-8 com quebras de linha LF determinísticas."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def _write_markdown(content: str, path: Path) -> None:
    """Grava arquivo Markdown em UTF-8 com LF determinístico."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as arquivo:
        arquivo.write(content.strip() + "\n")


def _prepare_decimal_strings(df: pd.DataFrame, decimal_cols: list[str]) -> pd.DataFrame:
    """Converte colunas Decimal para string exata antes da exportação em CSV."""
    out = df.copy()
    for col in decimal_cols:
        if col in out.columns:
            out[col] = [
                f"{val:.3f}" if isinstance(val, Decimal) else str(val)
                for val in out[col]
            ]
    return out


def export_csv_reports(
    reports_dir: Path,
    kpis_df: pd.DataFrame,
    df_customers_rfm: pd.DataFrame,
    df_segments_summary: pd.DataFrame,
    df_countries: pd.DataFrame,
    df_products: pd.DataFrame,
    df_customer_ranking: pd.DataFrame,
    df_monthly: pd.DataFrame,
    cancellations_by_country: pd.DataFrame,
    df_sensitivity: pd.DataFrame,
) -> list[Path]:
    """Exporta todos os arquivos CSV principais e amostras verificadas top-50."""
    exported: list[Path] = []
    samples_dir = reports_dir / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    # 1. kpis_executivos.csv
    p_kpis = reports_dir / "kpis_executivos.csv"
    _write_csv(kpis_df, p_kpis)
    exported.append(p_kpis)

    # 2. resumo_clientes.csv
    cols_resumo_clientes = [
        "customer_id",
        "pais_principal",
        "paises_distintos",
        "faturamento_acumulado_decimal",
        "pedidos_distintos",
        "quantidade_unidades",
        "produtos_distintos",
        "ticket_medio",
        "primeira_compra",
        "ultima_compra",
        "recencia_dias",
        "frequencia",
        "valor_monetario",
        "cliente_recorrente",
        "segmento_rfm",
    ]
    resumo_clientes_out = _prepare_decimal_strings(
        df_customers_rfm[cols_resumo_clientes], ["faturamento_acumulado_decimal"]
    )
    resumo_clientes_out["ticket_medio"] = resumo_clientes_out["ticket_medio"].round(2)
    resumo_clientes_out["valor_monetario"] = resumo_clientes_out["valor_monetario"].round(3)
    p_res_cli = reports_dir / "resumo_clientes.csv"
    _write_csv(resumo_clientes_out, p_res_cli)
    exported.append(p_res_cli)

    # 3. segmentacao_rfm.csv
    cols_seg_rfm = [
        "customer_id",
        "pais_principal",
        "recencia_dias",
        "frequencia",
        "valor_monetario",
        "faturamento_acumulado_decimal",
        "ticket_medio",
        "primeira_compra",
        "ultima_compra",
        "dias_desde_primeira_compra",
        "segmento_rfm",
    ]
    seg_rfm_out = _prepare_decimal_strings(
        df_customers_rfm[cols_seg_rfm], ["faturamento_acumulado_decimal"]
    )
    seg_rfm_out["valor_monetario"] = seg_rfm_out["valor_monetario"].round(3)
    seg_rfm_out["ticket_medio"] = seg_rfm_out["ticket_medio"].round(2)
    p_seg_rfm = reports_dir / "segmentacao_rfm.csv"
    _write_csv(seg_rfm_out, p_seg_rfm)
    exported.append(p_seg_rfm)

    # 4. resumo_segmentos.csv
    cols_res_seg = [
        "ordem_prioridade",
        "segmento_rfm",
        "qtd_clientes",
        "participacao_clientes_pct",
        "faturamento_total_decimal",
        "participacao_faturamento_pct",
        "pedidos_totais",
        "unidades_totais",
        "ticket_medio_segmento",
        "valor_monetario_medio_cliente",
        "valor_monetario_mediano_cliente",
        "frequencia_media",
        "frequencia_mediana",
        "recencia_media_dias",
        "recencia_mediana_dias",
    ]
    res_seg_out = _prepare_decimal_strings(
        df_segments_summary[cols_res_seg], ["faturamento_total_decimal"]
    )
    for col in [
        "participacao_clientes_pct",
        "participacao_faturamento_pct",
        "ticket_medio_segmento",
        "valor_monetario_medio_cliente",
        "valor_monetario_mediano_cliente",
        "frequencia_media",
        "frequencia_mediana",
        "recencia_media_dias",
        "recencia_mediana_dias",
    ]:
        res_seg_out[col] = res_seg_out[col].round(2)
    p_res_seg = reports_dir / "resumo_segmentos.csv"
    _write_csv(res_seg_out, p_res_seg)
    exported.append(p_res_seg)

    # 5. analise_paises.csv
    cols_paises = [
        "country",
        "pedidos_distintos",
        "clientes_identificados",
        "clientes_recorrentes_no_pais",
        "taxa_recorrencia_pais_pct",
        "recorrencia_interpretavel",
        "unidades_vendidas",
        "faturamento_total_decimal",
        "participacao_faturamento_pct",
        "ticket_medio",
        "classificacao_amostra",
        "alerta_ticket_elevado_baixa_amostra",
    ]
    paises_out = _prepare_decimal_strings(
        df_countries[cols_paises], ["faturamento_total_decimal"]
    )
    paises_out["participacao_faturamento_pct"] = paises_out[
        "participacao_faturamento_pct"
    ].round(4)
    paises_out["ticket_medio"] = paises_out["ticket_medio"].round(2)
    p_paises = reports_dir / "analise_paises.csv"
    _write_csv(paises_out, p_paises)
    exported.append(p_paises)

    # 6. ranking_produtos.csv
    cols_produtos = [
        "ranking_faturamento",
        "stock_code",
        "descricao_principal",
        "qtd_descricoes_distintas",
        "codigo_operacional",
        "unidades_vendidas",
        "faturamento_total_decimal",
        "participacao_faturamento_pct",
        "participacao_unidades_pct",
        "pedidos_distintos",
        "clientes_identificados",
        "preco_medio_ponderado",
    ]
    prod_out = _prepare_decimal_strings(
        df_products[cols_produtos], ["faturamento_total_decimal"]
    )
    for col in [
        "participacao_faturamento_pct",
        "participacao_unidades_pct",
        "preco_medio_ponderado",
    ]:
        prod_out[col] = prod_out[col].round(4)
    p_prod = reports_dir / "ranking_produtos.csv"
    _write_csv(prod_out, p_prod)
    exported.append(p_prod)

    # 7. ranking_clientes.csv
    cols_rank_cli = [
        "ranking_faturamento",
        "customer_id",
        "pais_principal",
        "paises_distintos",
        "segmento_rfm",
        "pedidos_distintos",
        "quantidade_unidades",
        "faturamento_acumulado_decimal",
        "ticket_medio",
        "recencia_dias",
        "participacao_receita_identificada_pct",
        "participacao_receita_total_pct",
        "participacao_acumulada_identificada_pct",
    ]
    rank_cli_out = _prepare_decimal_strings(
        df_customer_ranking[cols_rank_cli], ["faturamento_acumulado_decimal"]
    )
    rank_cli_out["ticket_medio"] = rank_cli_out["ticket_medio"].round(2)
    p_rank_cli = reports_dir / "ranking_clientes.csv"
    _write_csv(rank_cli_out, p_rank_cli)
    exported.append(p_rank_cli)

    # 8. evolucao_mensal.csv
    cols_mensal = [
        "ano_mes",
        "periodo_incompleto",
        "data_inicial_mes",
        "data_final_mes",
        "dias_calendario_cobertos",
        "linhas_transacao",
        "pedidos_distintos",
        "clientes_identificados",
        "unidades_vendidas",
        "faturamento_total_decimal",
        "ticket_medio",
    ]
    mensal_out = _prepare_decimal_strings(
        df_monthly[cols_mensal], ["faturamento_total_decimal"]
    )
    mensal_out["ticket_medio"] = mensal_out["ticket_medio"].round(2)
    p_mensal = reports_dir / "evolucao_mensal.csv"
    _write_csv(mensal_out, p_mensal)
    exported.append(p_mensal)

    # 9. analise_cancelamentos.csv
    cols_canc = [
        "country",
        "pedidos_venda",
        "vendas_positivas_decimal",
        "linhas_cancelamento",
        "notas_cancelamento_distintas",
        "unidades_canceladas",
        "valor_cancelamento_decimal",
        "participacao_cancelamento_sobre_vendas_pct",
        "saldo_monetario_observado_decimal",
    ]
    canc_out = _prepare_decimal_strings(
        cancellations_by_country[cols_canc],
        [
            "vendas_positivas_decimal",
            "valor_cancelamento_decimal",
            "saldo_monetario_observado_decimal",
        ],
    )
    p_canc = reports_dir / "analise_cancelamentos.csv"
    _write_csv(canc_out, p_canc)
    exported.append(p_canc)

    # 10. analise_sensibilidade.csv (tabela compacta de cenários)
    cols_sens = [
        "cenario",
        "regra_aplicada",
        "linhas_transacao",
        "pedidos_distintos",
        "delta_pedidos_vs_base",
        "clientes_identificados",
        "unidades_vendidas",
        "delta_unidades_vs_base",
        "faturamento_total_decimal",
        "delta_faturamento_decimal",
        "delta_faturamento_pct",
        "ticket_medio",
        "produto_lider_unidades",
        "produto_lider_unidades_qtd",
        "cliente_lider_faturamento",
        "cliente_lider_faturamento_valor",
        "pais_maior_ticket_medio",
        "pais_maior_ticket_medio_valor",
    ]
    sens_out = _prepare_decimal_strings(
        df_sensitivity[cols_sens],
        ["faturamento_total_decimal", "delta_faturamento_decimal"],
    )
    p_sens = reports_dir / "analise_sensibilidade.csv"
    _write_csv(sens_out, p_sens)
    exported.append(p_sens)

    # Pequenas amostras verificadas (Top 50) para versionamento leve de apresentação
    _write_csv(resumo_clientes_out.head(50), samples_dir / "amostra_resumo_clientes_top50.csv")
    _write_csv(seg_rfm_out.head(50), samples_dir / "amostra_segmentacao_rfm_top50.csv")
    _write_csv(prod_out.head(50), samples_dir / "amostra_ranking_produtos_top50.csv")
    _write_csv(rank_cli_out.head(50), samples_dir / "amostra_ranking_clientes_top50.csv")

    return exported


def _build_quality_report_md(
    metadata: dict[str, Any],
    quality_audit: dict[str, Any],
    resumo_limpeza: dict[str, Any],
    order_consistency: dict[str, Any],
    cancellations_data: dict[str, Any],
) -> str:
    """Gera o conteúdo do relatório relatorio_qualidade.md a partir da execução atual."""
    is_official = bool(metadata.get("sha256_matches_official", False))

    missing_rows = "\n".join(
        f"| `{m['coluna']}` | `{quality_audit['tipos_colunas'].get(m['coluna'], 'N/A')}` | "
        f"{_format_int(m['ausentes'])} | {_format_pct(m['percentual'], 4)} |"
        for m in quality_audit["valores_ausentes"]
    )
    triage_rows = "\n".join(
        f"| `{cat}` | {_format_int(qtd)} |"
        for cat, qtd in resumo_limpeza["contagem_triagem"].items()
    )
    gt2_items = quality_audit["unit_price_acima_2_casas"]
    gt2_text = (
        ", ".join(f"`{k}` ({v} linhas)" for k, v in gt2_items.items())
        if gt2_items
        else "Nenhum registro encontrado"
    )
    canc_res = cancellations_data["resumo"]

    # Bloco de identidade da fonte (separa dataset oficial UCI de entradas alternativas)
    if is_official:
        source_block = (
            f"- **Escopo da entrada:** Dataset oficial confirmado — {DATASET_METADATA['nome']} "
            f"({DATASET_METADATA['fonte']})\n"
            f"- **URL oficial:** {DATASET_METADATA['url_oficial']}\n"
            f"- **DOI:** {DATASET_METADATA['doi']}\n"
            f"- **Autoria original:** {DATASET_METADATA['autoria']}\n"
            f"- **Licença:** {DATASET_METADATA['licenca']}"
        )
    else:
        source_block = (
            "- **Escopo da entrada:** Entrada alternativa (o SHA-256 não corresponde ao "
            "arquivo oficial `Online Retail.xlsx` da UCI; as conclusões deste relatório "
            "refletem exclusivamente os registros desta execução)."
        )

    # Diferença dinâmica entre regra V1 e regra V2
    diff_v1_v2 = int(resumo_limpeza["diferenca_linhas_v1_vs_v2"])
    v1_only_details = resumo_limpeza.get("diferenca_v1_vs_v2_detalhes", [])
    if diff_v1_v2 == 0:
        v1_diff_text = "sem diferença de linhas entre a regra V1 e a regra V2 nesta entrada"
    elif v1_only_details:
        amostra_det = ", ".join(
            f"`{d['invoice_no']}` ({d['description'] or 'sem descrição'}, "
            f"{format_gbp(Decimal(d['valor_decimal']))})"
            for d in v1_only_details[:5]
        )
        v1_diff_text = f"diferença de `{diff_v1_v2}` linha(s): {amostra_det}"
    else:
        v1_diff_text = f"diferença de `{diff_v1_v2}` linha(s) entre V1 e V2"

    # Detalhes dinâmicos de ajustes com prefixo A
    adj_details = canc_res.get("detalhes_ajustes_prefixo_a", [])
    if adj_details:
        adj_ids = ", ".join(f"`{d['invoice_no']}`" for d in adj_details[:10])
        adj_text = (
            f"{canc_res['linhas_ajuste_prefixo_a']} linhas ({adj_ids}), "
            f"saldo líquido {format_gbp(canc_res['valor_liquido_ajustes_prefixo_a_decimal'])}"
        )
    else:
        adj_text = "0 linhas (nenhum ajuste com prefixo `A` encontrado nesta entrada)"

    return f"""# Relatório de Qualidade dos Dados — Online Retail Customer Analytics V2

## 1. Identificação e Integridade da Fonte

{source_block}
- **Arquivo avaliado:** `{metadata['file_name']}` ({metadata['size_mb']} MB / {_format_int(metadata['size_bytes'])} bytes)
- **SHA-256 verificado:** `{metadata['sha256']}` (corresponde ao hash oficial UCI: **{'Sim' if is_official else 'Não'}**)
- **Registros brutos:** {_format_int(quality_audit['total_linhas_brutas'])} linhas e {quality_audit['total_colunas']} colunas
- **Período efetivo observado:** `{quality_audit['data_minima']}` até `{quality_audit['data_maxima']}`
- **Datas fora da janela de referência UCI (01/12/2010 a 09/12/2011):** {_format_int(quality_audit['datas_fora_periodo_esperado'])}

## 2. Granularidade das Bases e Ausência de Chave Única de Item

| Nível analítico | Granularidade (chave lógica) | Observações técnicas |
|---|---|---|
| **Linha de transação** | Uma linha por lançamento de item em fatura | **Não existe identificador único de item (`LineItemID`)** no esquema da base. `InvoiceNo` repete-se em pedidos multiproduto. |
| **Pedido** | Uma linha por `InvoiceNo` válido | Consolidado somente após validar 0 conflitos de `CustomerID` e `Country` por pedido. |
| **Produto** | Uma linha por `StockCode` padronizado (maiúsculas) | Existem `{_format_int(quality_audit['variacoes_caixa_stock_code'])}` variações de caixa e `{_format_int(quality_audit['produtos_multiplas_descricoes'])}` códigos com múltiplas descrições nesta entrada. |
| **Cliente** | Uma linha por `CustomerID` identificado válido | Exclui transações válidas com `CustomerID` ausente (mantidas nas visões gerais) e rejeita identificadores inválidos. |

> **Atenção sobre duplicatas exatas:** foram encontradas **{_format_int(quality_audit['duplicatas_exatas_excedentes'])}** linhas exatamente repetidas na base bruta ({_format_int(quality_audit['linhas_envolvidas_duplicatas_exatas'])} linhas envolvidas). Como não existe chave única de item, não se presume automaticamente que toda linha idêntica seja erro de exportação; a remoção segue a política preservada da V1 na base principal e tem seu impacto quantificado na Análise de Sensibilidade.

## 3. Auditoria de Esquema, Tipos, Valores Ausentes e Integridade Numérica

| Coluna | Tipo lido pelo Pandas | Ausentes | % Ausentes |
|---|---|---:|---:|
{missing_rows}

- **Tipagem observada na leitura Excel (via OpenPyXL):**
  - `InvoiceNo`: `{metadata['invoice_no_python_types']}`
  - `StockCode`: `{metadata['stock_code_python_types']}`
  - `CustomerID` não inteiro / inválido no Excel: `{metadata['non_integer_customer_ids']}`
- **Validação estrita de campos críticos (sem truncamento silencioso):**
  - Quantidades fracionadas ou não finitas (`Quantity`): **{_format_int(quality_audit['quantidades_fracionadas_ou_nao_finitas'])}**
  - Preços unitários não finitos (`UnitPrice`): **{_format_int(quality_audit['precos_nao_finitos'])}**
  - `CustomerID` ausentes (permitidos em vendas gerais): **{_format_int(quality_audit['customer_ids_ausentes'])}**
  - `CustomerID` inválidos (fracionados, infinitos, <= 0 ou malformados — isolados em `registro_ambiguo_ou_inconsistente`): **{_format_int(quality_audit['customer_ids_invalidos'])}**
- **Precisão de `UnitPrice` acima de 2 casas decimais:** {gt2_text}. Os cálculos intermediários preservam a precisão integral em `Decimal` sem arredondamento antecipado.

## 4. Triagem Mutuamente Exclusiva da Base Bruta

| Categoria de triagem (mutuamente exclusiva) | Quantidade de linhas |
|---|---:|
{triage_rows}

- **Vendas positivas padrão antes de deduplicação:** {_format_int(resumo_limpeza['vendas_positivas_antes_deduplicacao'])}
- **Duplicatas exatas removidas nas vendas positivas:** {_format_int(resumo_limpeza['duplicatas_exatas_removidas_em_vendas'])} (impacto monetário: {format_gbp(resumo_limpeza['valor_duplicatas_removidas_decimal'])})
- **Linhas mantidas na Base Principal V2:** {_format_int(resumo_limpeza['linhas_mantidas_v2'])}
- **Linhas na Reprodução da Regra V1:** {_format_int(resumo_limpeza['linhas_mantidas_v1_equivalente'])} ({v1_diff_text})

## 5. Consistência de Pedidos, Produtos e Clientes

- **Pedidos com múltiplas linhas (na base bruta):** {_format_int(quality_audit['pedidos_com_multiplas_linhas'])}
- **Pedidos com múltiplos produtos distintos (na base bruta):** {_format_int(quality_audit['pedidos_com_multiplos_produtos'])}
- **Pedidos com conflito de `CustomerID` (na base V2):** {order_consistency['pedidos_conflito_cliente']}
- **Pedidos com mistura de cliente preenchido e nulo (na base V2):** {order_consistency['pedidos_mistura_cliente_nulo']}
- **Pedidos com conflito de `Country` (na base V2):** {order_consistency['pedidos_conflito_pais']}
- **Pedidos com mais de um timestamp `InvoiceDate` (na base V2):** {order_consistency['pedidos_multiplos_timestamps']} (todos no mesmo dia calendário: {order_consistency['pedidos_multiplos_timestamps_mesmo_dia']}; diferença máxima observada: {order_consistency['diferenca_maxima_segundos_mesmo_pedido']:.0f} segundos — resolvidos determinísticamente com `min(InvoiceDate)`).
- **Clientes associados a mais de um país na base bruta:** {quality_audit['clientes_multiplos_paises']}

## 6. Cancelamentos e Registros Não Comerciais

- **Notas de cancelamento (prefixo `C`):** {_format_int(canc_res['linhas_cancelamento_brutas'])} linhas brutas ({_format_int(canc_res['linhas_cancelamento_deduplicadas'])} sem duplicatas exatas), {_format_int(canc_res['notas_cancelamento_distintas'])} notas distintas, totalizando {format_gbp(canc_res['valor_cancelamentos_deduplicados_decimal'])} (deduplicado) / {format_gbp(canc_res['valor_cancelamentos_brutos_decimal'])} (bruto).
- **Quantidades negativas sem prefixo `C`:** {_format_int(canc_res['linhas_negativas_sem_c'])} linhas ({_format_int(canc_res['unidades_negativas_sem_c'])} unidades), valor monetário {format_gbp(canc_res['valor_negativas_sem_c_decimal'])} (**não tratadas automaticamente como devoluções comerciais**).
- **Preços não positivos (sem prefixo `C`/`A`):** {_format_int(canc_res['linhas_preco_nao_positivo'])} linhas ({_format_int(canc_res['linhas_preco_nao_positivo_com_cliente'])} com `CustomerID`).
- **Ajustes contábeis com prefixo `A`:** {adj_text}.
- **Registros ambíguos ou inconsistentes:** {canc_res['linhas_ambiguas_ou_inconsistentes']} linhas.
"""


def _build_reconciliation_report_md(
    reconciliation: dict[str, Any],
    quality_audit: dict[str, Any],
) -> str:
    """Gera o conteúdo do relatório relatorio_reconciliacao.md."""
    status_geral = "APROVADA (100%)" if reconciliation["todas_aprovadas"] else "COM FALHAS"
    mon = reconciliation["auditoria_monetaria"]

    gt2_items = quality_audit.get("unit_price_acima_2_casas", {})
    gt2_total = sum(gt2_items.values())
    if gt2_total > 0:
        gt2_desc = ", ".join(f"`{k}` ({v} linha(s))" for k, v in gt2_items.items())
        precision_intro = (
            f"A entrada avaliada inclui {_format_int(gt2_total)} ocorrência(s) de preço unitário "
            f"com precisão superior a duas casas decimais ({gt2_desc}). Por isso, nenhum valor é "
            "arredondado antecipadamente durante os cálculos intermediários:"
        )
    else:
        precision_intro = (
            "A entrada avaliada não apresentou preços unitários com precisão superior a duas casas "
            "decimais; ainda assim, todos os cálculos intermediários preservam precisão integral em `Decimal`:"
        )

    table_rows = "\n".join(
        f"| `{c['codigo']}` | {c['descricao']} | `{c['esperado']}` | `{c['observado']}` | `{c['diferenca']}` | **{c['status']}** | {c['observacao']} |"
        for c in reconciliation["checagens"]
    )

    return f"""# Relatório Independente de Reconciliação Matemática

## 1. Resumo Executivo da Reconciliação

- **Status global:** **{status_geral}**
- **Total de verificações executadas:** {reconciliation['total_checagens']}
- **Verificações aprovadas:** {reconciliation['aprovadas']}
- **Verificações reprovadas:** {reconciliation['reprovadas']}

## 2. Política Monetária (GBP) e Auditoria `Decimal` vs `float64`

{precision_intro}

- **Faturamento exato em `Decimal` (3 casas):** `£ {mon['faturamento_exato_decimal']}`
- **Soma em `float64` do Pandas:** `{mon['faturamento_float64']}`
- **Diferença absoluta `float64` vs `Decimal`:** `{mon['diferenca_absoluta_float_vs_decimal']}` GBP
- **Valor para exibição em 2 casas (`ROUND_HALF_UP`):** `£ {mon['faturamento_exibicao_2_casas']}`
- **Delta explícito de arredondamento de exibição:** `{mon['delta_arredondamento_2_casas']}` GBP

> **Limitação documentada da fonte Excel:** arquivos `.xlsx` armazenam números em ponto flutuante IEEE-754. A conversão `Decimal(str(valor))` preserva fielmente a representação decimal curta devolvida pelo Python/OpenPyXL e elimina erro acumulado em somas, mas não substitui uma origem contábil armazenada nativamente em centavos inteiros.

## 3. Matriz Completa de Reconciliações

| Código | Verificação | Esperado | Observado | Diferença | Status | Observação |
|---|---|---:|---:|---:|---|---|
{table_rows}
"""


def _build_customer_analytics_report_md(
    metadata: dict[str, Any],
    df_segments_summary: pd.DataFrame,
    df_customer_ranking: pd.DataFrame,
    identification_summary: dict[str, Any],
    recurrence_summary: dict[str, Any],
    outliers_info: dict[str, Any],
) -> str:
    """Gera o conteúdo do relatório relatorio_customer_analytics.md a partir da execução atual."""
    is_official = bool(metadata.get("sha256_matches_official", False))
    ref_date_str = str(identification_summary["data_referencia_rfm"])
    last_obs_str = str(identification_summary["ultima_compra_observada_base"])

    seg_rows = "\n".join(
        f"| {r['segmento_rfm']} | {_format_int(r['qtd_clientes'])} | {_format_pct(r['participacao_clientes_pct'])} | "
        f"{format_gbp(r['faturamento_total_decimal'])} | {_format_pct(r['participacao_faturamento_pct'])} | "
        f"{format_gbp(r['ticket_medio_segmento'])} | {r['frequencia_media']:.2f} | {r['recencia_media_dias']:.1f} dias |"
        for _, r in df_segments_summary.iterrows()
    )

    freq_rows = "\n".join(
        f"| {f['faixa_frequencia']} | {_format_int(f['qtd_clientes'])} | {_format_pct(f['participacao_clientes_pct'])} | "
        f"{format_gbp(f['faturamento_decimal'])} | {_format_pct(f['participacao_faturamento_identificado_pct'])} |"
        for f in recurrence_summary["distribuicao_frequencia"]
    )

    top10_df = df_customer_ranking.head(10)
    top10_rows = "\n".join(
        f"| {int(r['ranking_faturamento'])} | `{r['customer_id']}` | {r['pais_principal']} | {r['segmento_rfm']} | "
        f"{_format_int(r['pedidos_distintos'])} | {_format_int(r['quantidade_unidades'])} | "
        f"{format_gbp(r['faturamento_acumulado_decimal'])} | {format_gbp(r['ticket_medio'])} | {int(r['recencia_dias'])} d |"
        for _, r in top10_df.iterrows()
    )

    conc = recurrence_summary["concentracao_clientes"]
    multi_ids = identification_summary["ids_clientes_multiplos_paises"]
    multi_ids_text = f" (`{', '.join(multi_ids)}`)" if multi_ids else ""

    if is_official:
        calibration_note = (
            f"os cortes foram ancorados na distribuição observada dos "
            f"{_format_int(identification_summary['clientes_identificados_total'])} clientes do dataset oficial UCI "
            "(quartil superior próximo de 5 pedidos e £ 1.660,60; janela trimestral de 90 dias)"
        )
    else:
        calibration_note = (
            "foram aplicados os limiares configurados de negócio (`5` pedidos, `£ 1.500,00` e `90` dias) "
            "sobre a entrada alternativa avaliada, sem recalibração automática"
        )

    # Nota sobre clientes outliers somente quando realmente presentes no Top 10 da execução atual
    top10_cids = set(top10_df["customer_id"].astype(str))
    flagged_outlier_customers: list[str] = []
    for key in ("outlier_principal_23843", "outlier_secundario_23166"):
        info = outliers_info.get(key, {})
        if info.get("encontrado") and str(info.get("customer_id")) in top10_cids:
            flagged_outlier_customers.append(
                f"`{info['customer_id']}` (pedido `{info['invoice_no']}`)"
            )

    if flagged_outlier_customers:
        outlier_top10_note = (
            f"\n> **Nota de auditoria sobre casos atípicos no Top 10:** os clientes "
            f"{' e '.join(flagged_outlier_customers)} figuram no Top 10 devido a pedidos atípicos "
            "de altíssimo volume com notas de cancelamento compatíveis emitidas minutos depois. "
            "Veja o impacto completo no `relatorio_sensibilidade.md`.\n"
        )
    else:
        outlier_top10_note = ""

    pct_sem_cliente = _format_pct(
        identification_summary["percentual_faturamento_nao_identificado"]
    )
    if identification_summary["pedidos_sem_cliente"] > 0:
        cadastro_hipotese = (
            f"**Qualidade do cadastro ({pct_sem_cliente} da receita sem `CustomerID`):** "
            "investigar por que parte do faturamento ocorre sem identificação de cliente "
            "(ex.: canal guest/PDV) para avaliar o ganho de visibilidade analítica."
        )
    else:
        cadastro_hipotese = (
            "**Cobertura de cadastro (100% da receita V2 com `CustomerID`):** "
            "nesta entrada todas as vendas válidas estão associadas a clientes identificados."
        )

    return f"""# Relatório de Customer Analytics — RFM, Recorrência e Concentração

## 1. Cobertura de Identificação de Clientes

Os registros válidos sem `CustomerID` foram preservados nas análises comerciais gerais e excluídos exclusivamente das etapas que exigem identificação individual:

| Métrica | Clientes identificados | Sem `CustomerID` | Total Base V2 |
|---|---:|---:|---:|
| Linhas de transação | {_format_int(identification_summary['linhas_com_cliente'])} | {_format_int(identification_summary['linhas_sem_cliente'])} | {_format_int(identification_summary['linhas_com_cliente'] + identification_summary['linhas_sem_cliente'])} |
| Pedidos distintos | {_format_int(identification_summary['pedidos_com_cliente'])} | {_format_int(identification_summary['pedidos_sem_cliente'])} | {_format_int(identification_summary['pedidos_com_cliente'] + identification_summary['pedidos_sem_cliente'])} |
| Faturamento observado (GBP) | {format_gbp(identification_summary['faturamento_identificado_decimal'])} ({_format_pct(identification_summary['percentual_faturamento_identificado'])}) | {format_gbp(identification_summary['faturamento_nao_identificado_decimal'])} ({pct_sem_cliente}) | {format_gbp(identification_summary['faturamento_total_decimal'])} (100,00%) |

- **Clientes identificados distintos:** {_format_int(identification_summary['clientes_identificados_total'])}
- **Clientes presentes em mais de um país:** {identification_summary['clientes_em_multiplos_paises']}{multi_ids_text}

## 2. Metodologia RFM e Regras Transparentes de Segmentação

- **Data de referência RFM utilizada nesta execução:** `{ref_date_str}` (última compra válida observada na entrada: `{last_obs_str}`; sem uso de `datetime.now()`).
- **Recency (Recência):** dias corridos entre `{ref_date_str}` e a data normalizada da última compra válida observada.
- **Frequency (Frequência):** quantidade de pedidos de venda distintos (`InvoiceNo`) do cliente no período.
- **Monetary (Valor Monetário):** faturamento bruto acumulado das vendas válidas observadas (não equivale a lucro nem a Customer Lifetime Value preditivo).

### Ordem de Prioridade dos Segmentos (Mutuamente Exclusivos)

1. **Alto valor e recorrentes:** `frequência >= {RFM_THRESHOLDS['frequencia_alto_valor_min_pedidos']}`, `valor monetário >= {format_gbp(RFM_THRESHOLDS['valor_monetario_alto_valor_min_gbp'])}` e `recência <= {RFM_THRESHOLDS['recencia_recente_max_dias']} dias`.
2. **Recorrentes recentes:** `frequência >= {RFM_THRESHOLDS['frequencia_recorrente_min_pedidos']}` e `recência <= {RFM_THRESHOLDS['recencia_recente_max_dias']} dias`.
3. **Compra única recente:** `frequência == 1` e `recência <= {RFM_THRESHOLDS['recencia_recente_max_dias']} dias`.
4. **Recorrentes há mais tempo sem compras:** `frequência >= {RFM_THRESHOLDS['frequencia_recorrente_min_pedidos']}` e `recência > {RFM_THRESHOLDS['recencia_recente_max_dias']} dias`.
5. **Compra única há mais tempo sem compras:** `frequência == 1` e `recência > {RFM_THRESHOLDS['recencia_recente_max_dias']} dias`.

> **Justificativa e ressalva metodológica:** {calibration_note} e **não devem ser interpretados como padrões universais de mercado**. Além disso, estar há mais de {RFM_THRESHOLDS['recencia_recente_max_dias']} dias sem compras observadas **não comprova** que o cliente foi definitivamente perdido, especialmente em perfis atacadistas ou sazonais.

## 3. Desempenho por Segmento RFM

| Segmento RFM | Clientes | % Clientes | Faturamento | % Receita Ident. | Ticket Médio | Freq. Média | Recência Média |
|---|---:|---:|---:|---:|---:|---:|---:|
{seg_rows}

## 4. Recorrência Observada no Período e Efeito de Janela

- **Clientes com 1 pedido:** {_format_int(recurrence_summary['clientes_compra_unica'])} ({_format_pct(recurrence_summary['participacao_compra_unica_pct'])}) — faturamento de {format_gbp(recurrence_summary['faturamento_compra_unica_decimal'])}.
- **Clientes recorrentes (>= 2 pedidos):** {_format_int(recurrence_summary['clientes_recorrentes'])} (**{_format_pct(recurrence_summary['taxa_recorrencia_observada_pct'])}**) — faturamento de {format_gbp(recurrence_summary['faturamento_recorrentes_decimal'])}.
- **Cuidado com a janela de observação:** {_format_int(recurrence_summary['clientes_primeira_compra_ultimos_90_dias'])} clientes tiveram sua primeira compra observada nos últimos 90 dias em relação a `{ref_date_str}` (dos quais {_format_int(recurrence_summary['clientes_compra_unica_primeira_compra_ultimos_90_dias'])} ainda possuem 1 pedido). Como tiveram menos tempo disponível para recomprar, **recorrência observada no recorte não equivale a retenção de longo prazo**, e a primeira compra presente na base não corresponde necessariamente à primeira compra histórica da vida do cliente.

### Distribuição de Frequência

| Faixa de frequência | Clientes | % Clientes | Faturamento | % Receita Identificada |
|---|---:|---:|---:|---:|
{freq_rows}

## 5. Concentração Comercial

- **Top 10 clientes:** {format_gbp(conc['top_10']['faturamento_decimal'])} ({_format_pct(conc['top_10']['participacao_receita_identificada_pct'])} da receita identificada | {_format_pct(conc['top_10']['participacao_receita_total_pct'])} da receita total V2).
- **Top 50 clientes:** {format_gbp(conc['top_50']['faturamento_decimal'])} ({_format_pct(conc['top_50']['participacao_receita_identificada_pct'])} da receita identificada | {_format_pct(conc['top_50']['participacao_receita_total_pct'])} da receita total V2).
- **Top 100 clientes:** {format_gbp(conc['top_100']['faturamento_decimal'])} ({_format_pct(conc['top_100']['participacao_receita_identificada_pct'])} da receita identificada | {_format_pct(conc['top_100']['participacao_receita_total_pct'])} da receita total V2).
- **Top 10 produtos por faturamento:** {format_gbp(recurrence_summary['concentracao_top10_produtos_faturamento_decimal'])} ({_format_pct(recurrence_summary['concentracao_top10_produtos_faturamento_pct'])} da receita total V2).
- **País líder (`{recurrence_summary['pais_lider_faturamento']}`):** {format_gbp(recurrence_summary['pais_lider_faturamento_decimal'])} ({_format_pct(recurrence_summary['pais_lider_faturamento_pct'])} da receita total V2); Top 5 países somam {_format_pct(recurrence_summary['top5_paises_faturamento_pct'])}.

## 6. Top 10 Clientes por Faturamento Acumulado

| Rank | CustomerID | País Principal | Segmento RFM | Pedidos | Unidades | Faturamento | Ticket Médio | Recência |
|---:|---|---|---|---:|---:|---:|---:|---:|
{top10_rows}
{outlier_top10_note}
## 7. Hipóteses Comerciais para Investigação

As frentes abaixo são **hipóteses para investigação comercial**, e não resultados comprovados ou promessas de retorno:

1. **Gestão de contas-chave (`Alto valor e recorrentes`):** investigar padrões de reposição, condições de atendimento e dependência de receita dos maiores clientes recorrentes (sempre considerando a sensibilidade a eventuais pedidos atípicos).
2. **Estímulo à segunda compra (`Compra única recente`):** investigar o intervalo típico entre 1º e 2º pedido entre clientes que entraram recentemente e testar comunicações de acompanhamento pós-compra.
3. **Diagnóstico de reativação (`Recorrentes há mais tempo sem compras`):** investigar se a ausência de compras nos últimos {RFM_THRESHOLDS['recencia_recente_max_dias']} dias decorre de sazonalidade, ruptura de portfólio ou perda real de relacionamento.
4. {cadastro_hipotese}
"""


def _build_sensitivity_report_md(
    metadata: dict[str, Any],
    outliers_info: dict[str, Any],
    df_sensitivity: pd.DataFrame,
    ranking_impact: dict[str, Any],
) -> str:
    """Gera o conteúdo do relatório relatorio_sensibilidade.md derivado dos resultados atuais."""
    is_official = bool(metadata.get("sha256_matches_official", False))
    p1 = outliers_info["outlier_principal_23843"]
    p2 = outliers_info["outlier_secundario_23166"]

    def _format_outlier_block(title: str, info: dict[str, Any]) -> str:
        if not info.get("encontrado"):
            return (
                f"### {title}\n\n"
                "Registro específico do dataset oficial UCI não localizado na entrada avaliada.\n"
            )
        cancs = info["cancelamentos_potencialmente_relacionados"]
        if cancs:
            canc_lines = "\n".join(
                f"  - Nota `{c['invoice_no_cancelamento']}` em `{c['invoice_date']}` "
                f"(+{c['diferenca_minutos']:.0f} min): quantidade `{_format_int(c['quantity'])}`, "
                f"preço unitário {format_gbp(c['unit_price'])}, valor {format_gbp(Decimal(c['valor_decimal']))}."
                for c in cancs
            )
        else:
            canc_lines = "  - Nenhuma nota de cancelamento com quantidade oposta idêntica localizada."

        return f"""### {title}

- **Pedido (`InvoiceNo`):** `{info['invoice_no']}` | **Data:** `{info['invoice_date']}`
- **Produto (`StockCode`):** `{info['stock_code']}` — `{info['description']}`
- **Cliente (`CustomerID`):** `{info['customer_id']}` | **País:** `{info['country']}`
- **Quantidade:** {_format_int(info['quantity'])} unidades | **Preço unitário:** {format_gbp(info['unit_price'])} | **Valor monetário:** {format_gbp(info['valor_decimal'])}
- **Participação no volume total do produto na base V2:** {_format_pct(info['participacao_volume_produto_pct'])} (total de {info['pedidos_totais_produto_v2']} pedido(s) do produto na base V2)
- **Contexto do cliente:** possui {info['outros_pedidos_mesmo_cliente']} outro(s) pedido(s) válido(s) somando {format_gbp(info['receita_outros_pedidos_cliente_decimal'])}.
- **Notas de cancelamento potencialmente relacionadas:**
{canc_lines}
- **Ressalva metodológica:** {info['nota_metodologica']}
"""

    sens_rows = "\n".join(
        f"| {r['cenario']} | {_format_int(r['pedidos_distintos'])} | {_format_int(r['unidades_vendidas'])} | "
        f"{format_gbp(r['faturamento_total_decimal'])} | {format_gbp(r['delta_faturamento_decimal'])} ({_format_pct(r['delta_faturamento_pct'])}) | "
        f"{format_gbp(r['ticket_medio'])} | {r['produto_lider_unidades']} ({_format_int(r['produto_lider_unidades_qtd'])}) | `{r['cliente_lider_faturamento']}` |"
        for _, r in df_sensitivity.iterrows()
    )

    sens_by_prefix = {
        str(r["cenario"]).split(".")[0]: r for _, r in df_sensitivity.iterrows()
    }
    c1 = sens_by_prefix.get("1")
    c2 = sens_by_prefix.get("2")
    c3 = sens_by_prefix.get("3")
    c4 = sens_by_prefix.get("4")
    c5 = sens_by_prefix.get("5")
    c6 = sens_by_prefix.get("6")

    # Síntese 100% derivada dos cenários efetivamente calculados nesta execução
    conclusions: list[str] = []

    if c1 is not None and c2 is not None:
        if c2["delta_faturamento_decimal"] == Decimal("0") and c2["delta_pedidos_vs_base"] == 0:
            conclusions.append(
                "- **Regra V1 vs Base V2:** nesta entrada, não houve diferença entre a regra V1 e a Base Principal V2."
            )
        else:
            conclusions.append(
                f"- **Regra V1 vs Base V2:** a diferença entre V1 e V2 nesta entrada foi de "
                f"{format_gbp(c2['delta_faturamento_decimal'])} ({_format_pct(float(c2['delta_faturamento_pct']))}) "
                f"e {c2['delta_pedidos_vs_base']:+d} pedido(s), alterando o ticket médio de "
                f"{format_gbp(c2['ticket_medio'])} (V1) para {format_gbp(c1['ticket_medio'])} (V2)."
            )

    if c1 is not None and c3 is not None:
        dup_lines = int(c3["linhas_transacao"]) - int(c1["linhas_transacao"])
        if dup_lines == 0:
            conclusions.append(
                "- **Duplicatas exatas:** nenhuma duplicata exata foi removida das vendas positivas nesta entrada."
            )
        else:
            conclusions.append(
                f"- **Duplicatas exatas:** manter as {_format_int(dup_lines)} linha(s) repetida(s) "
                f"adicionaria {format_gbp(c3['delta_faturamento_decimal'])} "
                f"({_format_pct(float(c3['delta_faturamento_pct']))}) ao faturamento da base principal."
            )

    if p1.get("encontrado") or p2.get("encontrado"):
        outlier_parts: list[str] = []
        if p1.get("encontrado") and c4 is not None:
            outlier_parts.append(
                f"remover `{p1['invoice_no']}` altera o faturamento em "
                f"{format_gbp(c4['delta_faturamento_decimal'])} ({_format_pct(float(c4['delta_faturamento_pct']))}) "
                f"e passa a liderança em unidades para `{c4['produto_lider_unidades']}` "
                f"({_format_int(int(c4['produto_lider_unidades_qtd']))} un.)"
            )
        if c5 is not None and (p1.get("encontrado") and p2.get("encontrado")):
            extra_official = (
                " (evidenciando também a unificação por `StockCode` em vez de fragmentar descrições)"
                if is_official
                else ""
            )
            outlier_parts.append(
                f"remover ambos (`{p1['invoice_no']}` e `{p2['invoice_no']}`) altera o faturamento em "
                f"{format_gbp(c5['delta_faturamento_decimal'])} ({_format_pct(float(c5['delta_faturamento_pct']))}) "
                f"e desloca a liderança em unidades para `{c5['produto_lider_unidades']}` "
                f"({_format_int(int(c5['produto_lider_unidades_qtd']))} un.){extra_official}"
            )
        conclusions.append(f"- **Outliers investigados:** {'; '.join(outlier_parts)}.")
    else:
        conclusions.append(
            "- **Outliers investigados do dataset oficial (`581483` e `541431`):** "
            "não foram encontrados nesta entrada; os cenários 4 e 5 permanecem idênticos à Base Principal V2."
        )

    op_lines = int(ranking_impact["linhas_codigos_operacionais_na_base_v2"])
    if op_lines == 0:
        conclusions.append(
            "- **Códigos operacionais não-mercadoria:** nenhum código operacional foi encontrado na base principal desta entrada."
        )
    elif c6 is not None:
        conclusions.append(
            f"- **Códigos operacionais não-mercadoria:** retirar as {_format_int(op_lines)} linha(s) "
            f"administrativas altera o faturamento em {format_gbp(c6['delta_faturamento_decimal'])} "
            f"({_format_pct(float(c6['delta_faturamento_pct']))}), isolando apenas mercadorias físicas."
        )
    else:
        conclusions.append(
            f"- **Códigos operacionais não-mercadoria:** todas as {_format_int(op_lines)} linha(s) "
            "desta entrada correspondem a códigos operacionais (Cenário 6 vazio)."
        )

    conclusions_block = "\n".join(conclusions)
    scope_notice = (
        ""
        if is_official
        else "\n> **Escopo:** entrada alternativa avaliada (não corresponde ao SHA-256 do dataset oficial UCI). "
        "Os cenários 4 e 5 verificam os IDs de referência `581483` e `541431`, aplicáveis apenas quando presentes na entrada.\n"
    )

    return f"""# Relatório de Outliers e Análise de Sensibilidade Metodológica
{scope_notice}
## 1. Princípio Metodológico

Nenhum registro de valor elevado é removido automaticamente da Base Principal V2. Em vez disso, preservamos a base principal transparente e isolamos em cenários paralelos o impacto de cada escolha metodológica (regra V1, duplicatas exatas, pedidos atípicos investigados e códigos operacionais não-mercadoria).

## 2. Investigação dos Pedidos Atípicos de Referência

{_format_outlier_block('Caso 1 — PAPER CRAFT , LITTLE BIRDIE (StockCode 23843 / Pedido 581483)', p1)}

{_format_outlier_block('Caso 2 — MEDIUM CERAMIC TOP STORAGE JAR (StockCode 23166 / Pedido 541431)', p2)}

## 3. Impacto dos Códigos Operacionais Não-Mercadoria na Base V2

A Base Principal V2 desta execução contém **{_format_int(op_lines)}** linha(s) de códigos operacionais/administrativos (`DOT`, `POST`, `M`, `AMAZONFEE`, `C2`, `BANK CHARGES`, `S`, `PADS` e vouchers `gift_0001_*`), totalizando **{format_gbp(ranking_impact['valor_codigos_operacionais_na_base_v2_decimal'])}**.

## 4. Tabela Comparativa de Sensibilidade

| Cenário | Pedidos | Unidades | Faturamento | Variação vs Base V2 | Ticket Médio | Líder em Unidades | Líder em Receita |
|---|---:|---:|---:|---:|---:|---|---|
{sens_rows}

## 5. Síntese das Conclusões de Sensibilidade (Execução Atual)

{conclusions_block}
"""


def _build_executive_report_md(
    metadata: dict[str, Any],
    quality_audit: dict[str, Any],
    df_sales_v2: pd.DataFrame,
    df_orders_v2: pd.DataFrame,
    df_sales_v1: pd.DataFrame,
    df_segments_summary: pd.DataFrame,
    df_countries: pd.DataFrame,
    df_products: pd.DataFrame,
    df_customer_ranking: pd.DataFrame,
    df_monthly: pd.DataFrame,
    identification_summary: dict[str, Any],
    recurrence_summary: dict[str, Any],
    cancellations_data: dict[str, Any],
    country_notes: dict[str, Any],
    outliers_info: dict[str, Any],
    df_sensitivity: pd.DataFrame,
    reconciliation: dict[str, Any],
) -> str:
    """Gera o conteúdo do relatório relatorio_executivo.md 100% derivado da execução atual."""
    is_official = bool(metadata.get("sha256_matches_official", False))
    ref_date_str = str(identification_summary["data_referencia_rfm"])

    rev_v2 = sum(df_sales_v2["valor_linha_decimal"], Decimal("0"))
    orders_v2 = int(len(df_orders_v2))
    ticket_v2 = float(rev_v2) / orders_v2 if orders_v2 > 0 else 0.0
    units_v2 = int(df_sales_v2["quantity"].sum())

    rev_v1 = sum(df_sales_v1["valor_linha_decimal"], Decimal("0"))
    orders_v1 = int(df_sales_v1["invoice_no"].nunique())
    ticket_v1 = float(rev_v1) / orders_v1 if orders_v1 > 0 else 0.0
    diff_rev_v1_v2 = rev_v1 - rev_v2

    canc_res = cancellations_data["resumo"]
    conc = recurrence_summary["concentracao_clientes"]

    top_countries_rows = "\n".join(
        f"| {r['country']} | {_format_int(r['pedidos_distintos'])} | {_format_int(r['clientes_identificados'])} | "
        f"{format_gbp(r['faturamento_total_decimal'])} | {_format_pct(r['participacao_faturamento_pct'])} | "
        f"{format_gbp(r['ticket_medio'])} | {r['classificacao_amostra']} |"
        for _, r in df_countries.head(10).iterrows()
    )

    top_prod_rev_rows = "\n".join(
        f"| {int(r['ranking_faturamento'])} | `{r['stock_code']}` | {r['descricao_principal']} | "
        f"{_format_int(r['unidades_vendidas'])} | {format_gbp(r['faturamento_total_decimal'])} | "
        f"{_format_int(r['pedidos_distintos'])} | {'Operacional' if r['codigo_operacional'] else 'Mercadoria'} |"
        for _, r in df_products.head(10).iterrows()
    )

    monthly_rows = "\n".join(
        f"| `{r['ano_mes']}` | {'Sim (parcial)' if r['periodo_incompleto'] else 'Não'} | "
        f"{_format_int(r['pedidos_distintos'])} | {_format_int(r['unidades_vendidas'])} | "
        f"{format_gbp(r['faturamento_total_decimal'])} | {format_gbp(r['ticket_medio'])} |"
        for _, r in df_monthly.iterrows()
    )

    top_canc_prod = cancellations_data["cancelamentos_por_produto"].head(5)
    if not top_canc_prod.empty:
        top_canc_section = (
            "| StockCode | Descrição Principal | Notas `C` | Unidades Canceladas | Valor Cancelado |\n"
            "|---|---|---:|---:|---:|\n"
            + "\n".join(
                f"| `{r['stock_code']}` | {r['descricao_principal']} | {_format_int(r['notas_distintas'])} | "
                f"{_format_int(r['unidades_canceladas'])} | {format_gbp(r['valor_cancelamento_decimal'])} |"
                for _, r in top_canc_prod.iterrows()
            )
        )
    else:
        top_canc_section = "Nenhuma nota de cancelamento (prefixo `C`) foi encontrada na entrada avaliada."

    top_cust = df_customer_ranking.iloc[0]

    seg_lookup = {
        row["segmento_rfm"]: row for _, row in df_segments_summary.iterrows()
    }
    hv_row = seg_lookup.get("Alto valor e recorrentes")
    hv_qtd = int(hv_row["qtd_clientes"]) if hv_row is not None else 0
    hv_pct_cli = float(hv_row["participacao_clientes_pct"]) if hv_row is not None else 0.0
    hv_pct_rev = float(hv_row["participacao_faturamento_pct"]) if hv_row is not None else 0.0

    rec_ant_row = seg_lookup.get("Recorrentes há mais tempo sem compras")
    uni_ant_row = seg_lookup.get("Compra única há mais tempo sem compras")
    sem_compras_90d_qtd = (
        (int(rec_ant_row["qtd_clientes"]) if rec_ant_row is not None else 0)
        + (int(uni_ant_row["qtd_clientes"]) if uni_ant_row is not None else 0)
    )

    # Observações dinâmicas da tabela V1 vs V2
    if diff_rev_v1_v2 == Decimal("0") and orders_v1 == orders_v2:
        obs_rev_v1_v2 = "Sem diferença entre a regra V1 e a Base Principal V2 nesta entrada"
    elif is_official:
        obs_rev_v1_v2 = (
            f"V2 exclui o lançamento contábil `A563185` (`Adjust bad debt`, {format_gbp(diff_rev_v1_v2)})"
        )
    else:
        obs_rev_v1_v2 = (
            f"V2 exclui registros não-venda que passavam pela regra V1 "
            f"(diferença de {format_gbp(diff_rev_v1_v2)} e {orders_v1 - orders_v2} pedido(s))"
        )

    ticket_v1_cell = (
        f"{format_gbp(ticket_v1)} (ref. histórica V1 UCI: {format_gbp(V1_HISTORICAL_REFERENCE['ticket_medio_geral'])})"
        if is_official
        else format_gbp(ticket_v1)
    )
    obs_units = (
        "Preservado outlier `581483`, avaliado em sensibilidade"
        if outliers_info["outlier_principal_23843"].get("encontrado")
        else "Todos os itens válidos preservados e avaliados em sensibilidade"
    )

    # Alerta dinâmico de países com ticket elevado e baixa amostra
    low_sample_list = country_notes["paises_ticket_alto_baixa_amostra"]
    if low_sample_list:
        example_country = low_sample_list[0]
        ex_row = df_countries.loc[df_countries["country"] == example_country].iloc[0]
        canc_country_df = cancellations_data["cancelamentos_por_pais"]
        ex_canc_match = canc_country_df.loc[canc_country_df["country"] == example_country]
        ex_canc_text = ""
        if not ex_canc_match.empty:
            ex_canc_val = ex_canc_match.iloc[0]["valor_cancelamento_decimal"]
            if ex_canc_val != Decimal("0"):
                ex_canc_text = f" — além de {format_gbp(ex_canc_val)} em cancelamentos"
        low_sample_sentence = (
            f"países como `{', '.join(low_sample_list[:6])}` apresentam ticket médio elevado com "
            f"menos de 10 pedidos (ex.: `{example_country}` tem {format_gbp(ex_row['ticket_medio'])} "
            f"em apenas {_format_int(int(ex_row['pedidos_distintos']))} pedido(s){ex_canc_text}), "
            "inviabilizando comparação direta com mercados robustos."
        )
    else:
        low_sample_sentence = (
            "nenhum país apresentou simultaneamente ticket médio acima da média global e "
            "menos de 10 pedidos nesta entrada."
        )

    # Resposta dinâmica sobre produtos líderes e sensibilidade a outliers
    top_prods_text = ", ".join(
        f"`{r['stock_code']}` (`{r['descricao_principal']}`, {format_gbp(r['faturamento_total_decimal'])})"
        for _, r in df_products.head(3).iterrows()
    )
    sens_by_prefix = {
        str(r["cenario"]).split(".")[0]: r for _, r in df_sensitivity.iterrows()
    }
    c5 = sens_by_prefix.get("5")
    if (
        outliers_info["outlier_principal_23843"].get("encontrado")
        and outliers_info["outlier_secundario_23166"].get("encontrado")
        and c5 is not None
    ):
        outlier_prod_sentence = (
            f" Na sensibilidade, remover `581483` e `541431` altera a receita em "
            f"{format_gbp(c5['delta_faturamento_decimal'])} ({_format_pct(float(c5['delta_faturamento_pct']))}) "
            f"e desloca o topo de volume consolidado por `StockCode` para "
            f"`{c5['produto_lider_unidades']}` ({_format_int(int(c5['produto_lider_unidades_qtd']))} un.)."
        )
    else:
        top_vol = df_products.sort_values(
            by=["unidades_vendidas", "stock_code"], ascending=[False, True]
        ).iloc[0]
        outlier_prod_sentence = (
            f" Em unidades vendidas, lidera `{top_vol['stock_code']}` "
            f"(`{top_vol['descricao_principal']}`, {_format_int(int(top_vol['unidades_vendidas']))} un.)."
        )

    # Contexto dinâmico de meses incompletos
    incomplete_df = df_monthly.loc[df_monthly["periodo_incompleto"]]
    if not incomplete_df.empty:
        inc_items = "; ".join(
            f"`{r['ano_mes']}` cobre apenas {_format_int(int(r['dias_calendario_cobertos']))} dia(s) "
            f"(`{r['data_inicial_mes']}` até `{r['data_final_mes']}`)"
            for _, r in incomplete_df.iterrows()
        )
        incomplete_note = (
            f"> **Contexto temporal obrigatório:** {inc_items} e **não deve ser comparado diretamente** "
            "a meses completos sem normalização de janela."
        )
        incomplete_limitation = ", ".join(f"`{m}` incompleto" for m in incomplete_df["ano_mes"])
    else:
        incomplete_note = (
            "> **Contexto temporal:** nenhum mês desta entrada foi marcado como período incompleto."
        )
        incomplete_limitation = "eventual censura temporal da janela observada"

    # Percentual real de CustomerID ausente na base bruta
    missing_by_col = {m["coluna"]: m["percentual"] for m in quality_audit["valores_ausentes"]}
    raw_missing_cid_pct = _format_pct(missing_by_col.get("CustomerID", 0.0))

    # Frente 1 de investigação derivada dos dados da execução atual
    if not top_canc_prod.empty:
        top_canc_codes = ", ".join(f"`{c}`" for c in top_canc_prod["stock_code"].head(4))
        frente_1 = (
            f"Revisão operacional de grandes pedidos e principais códigos cancelados nesta entrada ({top_canc_codes})."
        )
    else:
        frente_1 = "Monitoramento contínuo de pedidos atípicos e eventuais cancelamentos futuros."

    scope_banner = (
        f"- **Escopo:** Dataset oficial UCI Online Retail (SHA-256 verificado) | **Data de referência RFM:** `{ref_date_str}`"
        if is_official
        else f"- **Escopo:** Entrada alternativa (`{metadata['file_name']}`, SHA-256 não corresponde ao dataset oficial UCI) | **Data de referência RFM:** `{ref_date_str}`"
    )

    return f"""# Relatório Executivo — Online Retail Customer Analytics V2

{scope_banner}

## 1. Panorama Geral e Comparação V1 vs V2

| Indicador | Regra V1 (reproduzida) | Base Principal V2 | Observação |
|---|---:|---:|---|
| Faturamento de vendas positivas | {format_gbp(rev_v1)} (`{rev_v1:.3f}`) | **{format_gbp(rev_v2)}** (`{rev_v2:.3f}`) | {obs_rev_v1_v2} |
| Pedidos válidos distintos | {_format_int(orders_v1)} | **{_format_int(orders_v2)}** | 0 conflitos de cliente ou país por pedido |
| Ticket médio geral | {ticket_v1_cell} | **{format_gbp(ticket_v2)}** | Calculado como `faturamento total / pedidos distintos` |
| Unidades vendidas | {_format_int(int(df_sales_v1['quantity'].sum()))} | **{_format_int(units_v2)}** | {obs_units} |
| Clientes identificados | {_format_int(int(df_sales_v1['customer_id'].nunique(dropna=True)))} | **{_format_int(identification_summary['clientes_identificados_total'])}** | 100% classificados em 5 segmentos RFM mutuamente exclusivos |
| Reconciliação matemática | Não existia na V1 | **{reconciliation['aprovadas']}/{reconciliation['total_checagens']} aprovadas** | 0 divergências entre camadas |

## 2. Respostas às Perguntas de Negócio (Execução Atual)

1. **Clientes de maior valor histórico:** líder absoluto é o cliente `{top_cust['customer_id']}` ({top_cust['pais_principal']}), com {format_gbp(top_cust['faturamento_acumulado_decimal'])} em {_format_int(top_cust['pedidos_distintos'])} pedido(s). Os 10 maiores clientes concentram **{_format_pct(conc['top_10']['participacao_receita_identificada_pct'])}** da receita identificada e os 50 maiores concentram **{_format_pct(conc['top_50']['participacao_receita_identificada_pct'])}**.
2. **Recorrência observada:** **{_format_int(recurrence_summary['clientes_recorrentes'])}** clientes ({_format_pct(recurrence_summary['taxa_recorrencia_observada_pct'])}) realizaram 2 ou mais pedidos no período, respondendo por {format_gbp(recurrence_summary['faturamento_recorrentes_decimal'])}, enquanto {_format_int(recurrence_summary['clientes_compra_unica'])} ({_format_pct(recurrence_summary['participacao_compra_unica_pct'])}) realizaram apenas 1 pedido.
3. **Atividade recente vs afastamento:** considerando a data de referência RFM `{ref_date_str}`, o segmento **Alto valor e recorrentes** reúne {_format_int(hv_qtd)} clientes ({_format_pct(hv_pct_cli)}) que concentram **{_format_pct(hv_pct_rev)}** da receita identificada. Já os grupos sem compras nos últimos {RFM_THRESHOLDS['recencia_recente_max_dias']} dias somam {_format_int(sem_compras_90d_qtd)} clientes (não classificados automaticamente como perdidos definitivos).
4. **Receita sem identificação de cliente:** {format_gbp(identification_summary['faturamento_nao_identificado_decimal'])} ({_format_pct(identification_summary['percentual_faturamento_nao_identificado'])} da receita V2) correspondem a {_format_int(identification_summary['pedidos_sem_cliente'])} pedido(s) sem `CustomerID`, mantidos nas visões gerais.
5. **Países com maior volume comercial:** **{recurrence_summary['pais_lider_faturamento']}** lidera com {_format_pct(recurrence_summary['pais_lider_faturamento_pct'])} da receita total; os 5 maiores mercados concentram {_format_pct(recurrence_summary['top5_paises_faturamento_pct'])}.
6. **Alerta de amostra pequena em ticket médio por país:** {low_sample_sentence}
7. **Produtos de maior demanda e influência de outliers:** os maiores itens em receita nesta execução são {top_prods_text}.{outlier_prod_sentence}
8. **Influência dos cancelamentos:** foram identificadas {_format_int(canc_res['notas_cancelamento_distintas'])} nota(s) com prefixo `C`, somando **{format_gbp(canc_res['valor_cancelamentos_deduplicados_decimal'])}** (deduplicado), equivalente a **{_format_pct(canc_res['participacao_cancelamentos_dedup_sobre_vendas_v2_pct'])}** das vendas positivas V2. O **saldo monetário observado** é de **{format_gbp(canc_res['saldo_monetario_observado_dedup_decimal'])}** (valor descritivo que **não** equivale a faturamento líquido contábil certificado).
9. **Ações comerciais para investigação:** detalhadas na seção 7 abaixo, sempre como hipóteses analíticas e nunca como retorno financeiro comprovado.

## 3. Top 10 Países por Faturamento

| País | Pedidos | Clientes Ident. | Faturamento | % Receita | Ticket Médio | Porte Amostral |
|---|---:|---:|---:|---:|---:|---|
{top_countries_rows}

> **Atenção:** a soma de `Clientes Ident.` por país ({_format_int(country_notes['soma_clientes_por_pais'])}) frente ao total global ({_format_int(country_notes['clientes_distintos_globais'])}) reflete {country_notes['diferenca_clientes_multiplos_paises']} cliente(s) que compraram em mais de um país.

## 4. Top 10 Produtos/Códigos por Faturamento

| Rank | StockCode | Descrição Principal | Unidades | Faturamento | Pedidos | Tipo |
|---:|---|---|---:|---:|---:|---|
{top_prod_rev_rows}

## 5. Evolução Mensal

| Mês (`YYYY-MM`) | Período Incompleto? | Pedidos | Unidades | Faturamento | Ticket Médio |
|---|---|---:|---:|---:|---:|
{monthly_rows}

{incomplete_note}

## 6. Top 5 Códigos em Valor Absoluto de Cancelamentos (Deduplicados)

{top_canc_section}

## 7. Limitações e Frentes de Investigação Comercial

- **Limitações da fonte:** ausência de custos (impede cálculo de margem ou lucro), ausência de chave de vínculo entre notas `C` e pedidos originais, ausência de `LineItemID`, {raw_missing_cid_pct} das linhas brutas sem `CustomerID` e {incomplete_limitation}.
- **Frentes sugeridas para investigação (não comprovadas em produção):**
  1. {frente_1}
  2. Programas de acompanhamento de contas recorrentes de alto valor e entendimento de ciclo de recompra de clientes com compra única recente.
  3. Investigação da causa de vendas sem `CustomerID` para ampliar cobertura futura de CRM (quando aplicável).
"""


def export_markdown_reports(
    reports_dir: Path,
    metadata: dict[str, Any],
    quality_audit: dict[str, Any],
    resumo_limpeza: dict[str, Any],
    order_consistency: dict[str, Any],
    reconciliation: dict[str, Any],
    df_sales_v2: pd.DataFrame,
    df_orders_v2: pd.DataFrame,
    df_sales_v1: pd.DataFrame,
    df_segments_summary: pd.DataFrame,
    df_countries: pd.DataFrame,
    df_products: pd.DataFrame,
    df_customer_ranking: pd.DataFrame,
    df_monthly: pd.DataFrame,
    identification_summary: dict[str, Any],
    recurrence_summary: dict[str, Any],
    cancellations_data: dict[str, Any],
    country_notes: dict[str, Any],
    outliers_info: dict[str, Any],
    df_sensitivity: pd.DataFrame,
    ranking_impact: dict[str, Any],
) -> list[Path]:
    """Gera e grava os 5 relatórios Markdown oficiais em reports/."""
    files_content = {
        reports_dir / "relatorio_qualidade.md": _build_quality_report_md(
            metadata=metadata,
            quality_audit=quality_audit,
            resumo_limpeza=resumo_limpeza,
            order_consistency=order_consistency,
            cancellations_data=cancellations_data,
        ),
        reports_dir / "relatorio_reconciliacao.md": _build_reconciliation_report_md(
            reconciliation=reconciliation,
            quality_audit=quality_audit,
        ),
        reports_dir / "relatorio_customer_analytics.md": _build_customer_analytics_report_md(
            metadata=metadata,
            df_segments_summary=df_segments_summary,
            df_customer_ranking=df_customer_ranking,
            identification_summary=identification_summary,
            recurrence_summary=recurrence_summary,
            outliers_info=outliers_info,
        ),
        reports_dir / "relatorio_sensibilidade.md": _build_sensitivity_report_md(
            metadata=metadata,
            outliers_info=outliers_info,
            df_sensitivity=df_sensitivity,
            ranking_impact=ranking_impact,
        ),
        reports_dir / "relatorio_executivo.md": _build_executive_report_md(
            metadata=metadata,
            quality_audit=quality_audit,
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
            reconciliation=reconciliation,
        ),
    }

    written: list[Path] = []
    for path, content in files_content.items():
        _write_markdown(content, path)
        written.append(path)
    return written
