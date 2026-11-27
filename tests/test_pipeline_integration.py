"""Testes de integração ponta a ponta, idempotência das exportações e importações proibidas."""

import ast
from pathlib import Path

from main import main
from src.config import BASE_DIR


FORBIDDEN_IMPORTS = {
    "numpy",
    "matplotlib",
    "seaborn",
    "polars",
    "pyspark",
    "sklearn",
    "scipy",
    "statsmodels",
    "plotly",
    "streamlit",
    "dash",
}


def test_full_pipeline_cli_end_to_end_and_idempotent_rerun(synthetic_raw_df, tmp_path: Path):
    xlsx_path = tmp_path / "online_retail_test.xlsx"
    out_dir_1 = tmp_path / "reports_run_1"
    out_dir_2 = tmp_path / "reports_run_2"
    synthetic_raw_df.to_excel(xlsx_path, index=False, engine="openpyxl")

    exit_code_1 = main(
        ["--input", str(xlsx_path), "--output", str(out_dir_1), "--reference-date", "2011-12-10"]
    )
    exit_code_2 = main(
        ["--input", str(xlsx_path), "--output", str(out_dir_2), "--reference-date", "2011-12-10"]
    )

    assert exit_code_1 == 0
    assert exit_code_2 == 0

    expected_files = [
        "kpis_executivos.csv",
        "resumo_clientes.csv",
        "segmentacao_rfm.csv",
        "resumo_segmentos.csv",
        "analise_paises.csv",
        "ranking_produtos.csv",
        "ranking_clientes.csv",
        "evolucao_mensal.csv",
        "analise_cancelamentos.csv",
        "analise_sensibilidade.csv",
        "relatorio_qualidade.md",
        "relatorio_reconciliacao.md",
        "relatorio_customer_analytics.md",
        "relatorio_sensibilidade.md",
        "relatorio_executivo.md",
    ]

    for filename in expected_files:
        f1 = out_dir_1 / filename
        f2 = out_dir_2 / filename
        assert f1.exists(), f"Arquivo ausente na execução 1: {filename}"
        assert f2.exists(), f"Arquivo ausente na execução 2: {filename}"
        # Reexecução deve produzir arquivos byte-a-byte idênticos
        assert f1.read_text(encoding="utf-8") == f2.read_text(encoding="utf-8")


def test_cli_rejects_invalid_reference_date(tmp_path: Path):
    exit_code = main(["--reference-date", "data-invalida", "--output", str(tmp_path)])
    assert exit_code == 1


def test_no_forbidden_direct_imports_in_project():
    """Garante ausência de importações diretas proibidas em main.py, src/ e tests/."""
    py_files = [BASE_DIR / "main.py"]
    py_files.extend((BASE_DIR / "src").rglob("*.py"))
    py_files.extend((BASE_DIR / "tests").rglob("*.py"))

    violations: list[str] = []
    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".")[0]
                    if root_mod in FORBIDDEN_IMPORTS:
                        violations.append(f"{py_file}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root_mod = node.module.split(".")[0]
                if root_mod in FORBIDDEN_IMPORTS:
                    violations.append(f"{py_file}: from {node.module} import ...")

    assert violations == [], f"Importações proibidas encontradas: {violations}"


def test_custom_reference_date_propagates_to_all_reports_and_kpis(synthetic_raw_df, tmp_path: Path):
    import pandas as pd

    xlsx_path = tmp_path / "online_retail_refdate.xlsx"
    out_dir = tmp_path / "reports_refdate"
    synthetic_raw_df.to_excel(xlsx_path, index=False, engine="openpyxl")

    exit_code = main(
        ["--input", str(xlsx_path), "--output", str(out_dir), "--reference-date", "2011-12-20"]
    )
    assert exit_code == 0

    # 1. Recência real recalculada para 2011-12-20 (cliente 101 comprou em 2011-12-01 -> 19 dias)
    rfm_df = pd.read_csv(out_dir / "segmentacao_rfm.csv", dtype={"customer_id": str})
    c101_rec = int(rfm_df.loc[rfm_df["customer_id"] == "101", "recencia_dias"].iloc[0])
    assert c101_rec == 19

    # 2. Propagação da data 2011-12-20 em kpis_executivos.csv, relatorio_executivo.md e relatorio_customer_analytics.md
    for filename in [
        "kpis_executivos.csv",
        "relatorio_executivo.md",
        "relatorio_customer_analytics.md",
    ]:
        content = (out_dir / filename).read_text(encoding="utf-8")
        assert "2011-12-20" in content, f"Data 2011-12-20 ausente em {filename}"
        assert "2011-12-10" not in content, f"Data fixa 2011-12-10 vazou em {filename}"


def test_minimal_two_row_synthetic_csv_does_not_leak_official_dataset_conclusions(tmp_path: Path):
    import pandas as pd

    csv_path = tmp_path / "mini_two_rows.csv"
    out_dir = tmp_path / "reports_mini"
    df_mini = pd.DataFrame(
        [
            ("800001", "90001", "CADERNO VERDE", 3, "2011-05-10 10:00:00", 12.00, 501, "Brazil"),
            ("800002", "90002", "CANETA PRETA", 2, "2011-05-12 11:00:00", 5.00, 502, "Canada"),
        ],
        columns=[
            "InvoiceNo", "StockCode", "Description", "Quantity",
            "InvoiceDate", "UnitPrice", "CustomerID", "Country",
        ],
    )
    df_mini.to_csv(csv_path, index=False, encoding="utf-8")

    exit_code = main(
        ["--input", str(csv_path), "--output", str(out_dir), "--reference-date", "2011-06-01"]
    )
    assert exit_code == 0

    exec_md = (out_dir / "relatorio_executivo.md").read_text(encoding="utf-8")
    cust_md = (out_dir / "relatorio_customer_analytics.md").read_text(encoding="utf-8")
    qual_md = (out_dir / "relatorio_qualidade.md").read_text(encoding="utf-8")
    rec_md = (out_dir / "relatorio_reconciliacao.md").read_text(encoding="utf-8")
    sens_md = (out_dir / "relatorio_sensibilidade.md").read_text(encoding="utf-8")

    # Deve refletir os dados reais desta entrada alternativa
    assert "Brazil" in exec_md
    assert "Canada" in exec_md
    assert "90001" in exec_md
    assert "2011-06-01" in exec_md
    assert "Entrada alternativa" in exec_md
    assert "Entrada alternativa" in qual_md

    # Não deve vazar conclusões fixas do dataset oficial inexistentes na entrada de 2 linhas
    for forbidden_exec in [
        "Singapore",
        "Singapura",
        "United Kingdom",
        "A563185",
        "22423",
        "DOTCOM POSTAGE",
        "24,93%",
        "2011-12-10",
        "£ 533,17",
    ]:
        assert forbidden_exec not in exec_md, f"Conclusão fixa '{forbidden_exec}' vazou no relatorio_executivo.md"

    for forbidden_cust in ["16446", "12346", "16,4%", "2011-12-10"]:
        assert forbidden_cust not in cust_md, f"Conclusão fixa '{forbidden_cust}' vazou no relatorio_customer_analytics.md"

    for forbidden_qual in ["A563185", "A563186", "A563187"]:
        assert forbidden_qual not in qual_md, f"Conclusão fixa '{forbidden_qual}' vazou no relatorio_qualidade.md"

    for forbidden_rec in ["PADS", "BANK CHARGES", "4 ocorrências"]:
        assert forbidden_rec not in rec_md, f"Conclusão fixa '{forbidden_rec}' vazou no relatorio_reconciliacao.md"

    for forbidden_sens in ["£ 11.062,06", "£ 24.573,74", "3,61%", "22197"]:
        assert forbidden_sens not in sens_md, f"Conclusão fixa '{forbidden_sens}' vazou no relatorio_sensibilidade.md"


def test_real_csv_ingestion_preserves_large_integers_above_2_pow_53_end_to_end(tmp_path: Path):
    """Testa leitura de CSV real do disco via loader, validação, limpeza e CLI sem perda > 2**53."""
    from decimal import Decimal
    import pandas as pd
    from src.data.cleaning import build_clean_datasets
    from src.data.loader import load_raw_dataset
    from src.data.validation import audit_raw_data_quality

    big_qty_1 = 9007199254740993  # 2**53 + 1
    big_qty_2 = 9007199254740995  # 2**53 + 3
    big_cid = 9007199254740993    # 2**53 + 1

    csv_path = tmp_path / "large_precision_real.csv"
    csv_content = (
        "InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID,Country\n"
        f"740001,10001,ITEM GRANDE 1,{big_qty_1},2011-10-01 10:00:00,1.00,{big_cid},United Kingdom\n"
        f"740002,10001,ITEM GRANDE 2,{big_qty_2},2011-10-02 10:00:00,2.00,,United Kingdom\n"
        f"740003,10001,ITEM FRAC,1.5,2011-10-03 10:00:00,10.00,{big_cid},United Kingdom\n"
        f"740004,10001,ID FRAC,2,2011-10-04 10:00:00,10.00,{big_cid}.5,United Kingdom\n"
    )
    csv_path.write_text(csv_content, encoding="utf-8")

    # 1. Ingestão pelo loader real (sem coerção precoce para float64)
    df_raw, metadata = load_raw_dataset(file_path=csv_path)
    assert metadata["active_sheet"] == "csv"
    assert df_raw["Quantity"].iloc[0] == str(big_qty_1)
    assert df_raw["CustomerID"].iloc[0] == str(big_cid)
    assert pd.isna(df_raw["CustomerID"].iloc[1])

    # 2. Auditoria de qualidade e limpeza preservando exatidão acima de 2**53
    audit = audit_raw_data_quality(df_raw)
    assert audit["quantidades_fracionadas_ou_nao_finitas"] == 1
    assert audit["customer_ids_ausentes"] == 1
    assert audit["customer_ids_invalidos"] == 1

    cleaned = build_clean_datasets(df_raw)
    df_v2 = cleaned["df_sales_v2"]
    assert len(df_v2) == 2
    assert list(df_v2["quantity"]) == [big_qty_1, big_qty_2]
    assert df_v2["customer_id"].iloc[0] == str(big_cid)
    assert pd.isna(df_v2["customer_id"].iloc[1])
    expected_total_dec = (
        Decimal(big_qty_1) * Decimal("1.00") + Decimal(big_qty_2) * Decimal("2.00")
    )
    assert sum(df_v2["valor_linha_decimal"], Decimal("0")) == expected_total_dec

    # 3. Fluxo completo pela CLI sobre o arquivo CSV real
    out_dir = tmp_path / "reports_csv_precision"
    exit_code = main(
        ["--input", str(csv_path), "--output", str(out_dir), "--reference-date", "2011-10-10"]
    )
    assert exit_code == 0

    resumo_cli = pd.read_csv(out_dir / "resumo_clientes.csv", dtype=str)
    assert len(resumo_cli) == 1
    assert resumo_cli["customer_id"].iloc[0] == str(big_cid)
    assert resumo_cli["quantidade_unidades"].iloc[0] == str(big_qty_1)
    assert resumo_cli["faturamento_acumulado_decimal"].iloc[0] == f"{Decimal(big_qty_1):.3f}"
