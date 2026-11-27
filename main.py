"""Ponto de entrada CLI do projeto Online Retail Customer Analytics V2."""

import argparse
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.config import DEFAULT_REPORTS_DIR, RFM_REFERENCE_DATE, format_gbp
from src.pipeline import run_customer_analytics_pipeline


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Interpreta argumentos opcionais de linha de comando."""
    parser = argparse.ArgumentParser(
        description=(
            "Executa o pipeline completo Online Retail Customer Analytics V2 "
            "(qualidade, bases analíticas, RFM, cancelamentos, sensibilidade e reconciliação)."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Caminho opcional para o arquivo Online Retail (.xlsx ou .csv).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORTS_DIR,
        help="Diretório de saída para CSVs e relatórios Markdown (padrão: reports/).",
    )
    parser.add_argument(
        "--reference-date",
        type=str,
        default=str(RFM_REFERENCE_DATE),
        help="Data fixa de referência RFM no formato YYYY-MM-DD (padrão: 2011-12-10).",
    )
    parser.add_argument(
        "--skip-precision-scan",
        action="store_true",
        help="Pula a leitura auxiliar de tipos célula-a-célula no Excel para execução mais rápida.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Coordena a execução do pipeline e imprime resumo executivo no terminal."""
    args = parse_args(argv)
    try:
        ref_date = date.fromisoformat(args.reference_date)
    except ValueError:
        print(
            f"[ERRO] Data de referência inválida: '{args.reference_date}'. Use YYYY-MM-DD.",
            file=sys.stderr,
        )
        return 1

    print("=" * 72)
    print("ONLINE RETAIL CUSTOMER ANALYTICS V2")
    print("=" * 72)
    print(f"Data de referência RFM : {ref_date}")
    print(f"Diretório de saída     : {args.output}")

    try:
        result = run_customer_analytics_pipeline(
            data_path=args.input,
            reports_dir=args.output,
            reference_date=ref_date,
            inspect_precision=not args.skip_precision_scan,
        )
    except Exception as exc:
        print(f"[ERRO] Falha na execução do pipeline: {exc}", file=sys.stderr)
        return 1

    dfs = result["dataframes"]
    rev_v2 = sum(dfs["df_sales_v2"]["valor_linha_decimal"], Decimal("0"))
    orders_v2 = len(dfs["df_orders_v2"])
    ticket_v2 = float(rev_v2) / orders_v2 if orders_v2 > 0 else 0.0
    rec = result["reconciliation"]
    canc = result["cancellations_data"]["resumo"]
    recorr = result["recurrence_summary"]

    print("-" * 72)
    print(f"Arquivo processado     : {result['metadata']['file_name']}")
    print(f"SHA-256                : {result['metadata']['sha256']}")
    print(f"Linhas brutas          : {result['resumo_limpeza']['linhas_brutas']:,}".replace(",", "."))
    print(f"Linhas válidas V2      : {result['resumo_limpeza']['linhas_mantidas_v2']:,}".replace(",", "."))
    print(f"Pedidos válidos V2     : {orders_v2:,}".replace(",", "."))
    print(f"Faturamento V2 (exato) : {format_gbp(rev_v2)} (£ {rev_v2:.3f})")
    print(f"Ticket médio geral V2  : £ {ticket_v2:.2f}")
    print(f"Clientes identificados : {len(dfs['df_customers_rfm']):,}".replace(",", "."))
    print(f"Taxa de recorrência    : {recorr['taxa_recorrencia_observada_pct']:.2f}%")
    print(
        f"Cancelamentos (dedup.) : {canc['notas_cancelamento_distintas']} notas | "
        f"{format_gbp(canc['valor_cancelamentos_deduplicados_decimal'])} "
        f"({canc['participacao_cancelamentos_dedup_sobre_vendas_v2_pct']:.2f}% das vendas V2)"
    )
    print(
        f"Reconciliação          : {rec['aprovadas']}/{rec['total_checagens']} aprovadas "
        f"({'OK' if rec['todas_aprovadas'] else 'FALHA'})"
    )
    print(f"CSVs exportados        : {len(result['exported_csvs'])}")
    print(f"Relatórios Markdown    : {len(result['exported_mds'])}")
    print(f"Tempo total            : {result['elapsed_seconds']:.2f} s")
    print("=" * 72)

    if not rec["todas_aprovadas"]:
        print("[ALERTA] Uma ou mais reconciliações falharam! Verifique relatorio_reconciliacao.md.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
