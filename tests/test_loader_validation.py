"""Testes de carregamento, hash SHA-256, esquema e auditoria de qualidade."""

from pathlib import Path

import pandas as pd
import pytest

from src.data.loader import calculate_sha256, load_raw_dataset, resolve_data_path
from src.data.validation import audit_raw_data_quality, validate_required_schema


def test_load_raw_dataset_xlsx_and_precision_inspection(synthetic_raw_df, tmp_path: Path):
    xlsx_path = tmp_path / "sample_online_retail.xlsx"
    synthetic_raw_df.to_excel(xlsx_path, index=False, engine="openpyxl")

    df_loaded, metadata = load_raw_dataset(file_path=xlsx_path, inspect_precision=True)

    assert len(df_loaded) == 18
    assert metadata["file_name"] == "sample_online_retail.xlsx"
    assert metadata["sha256"] == calculate_sha256(xlsx_path)
    assert metadata["excel_data_rows"] == 18
    assert metadata["unit_price_gt_2dp_rows"] == 1
    assert "0.001" in metadata["unit_price_gt_2dp_values"]
    assert metadata["non_integer_customer_ids"] == 0


def test_load_raw_dataset_invalid_format_raises(tmp_path: Path):
    txt_path = tmp_path / "dados.txt"
    txt_path.write_text("invalido", encoding="utf-8")

    with pytest.raises(ValueError, match="Formato de arquivo não suportado"):
        load_raw_dataset(file_path=txt_path)


def test_resolve_data_path_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        resolve_data_path(tmp_path / "inexistente.xlsx")


def test_validate_required_schema_missing_column_raises(synthetic_raw_df):
    df_broken = synthetic_raw_df.drop(columns=["CustomerID"])
    with pytest.raises(ValueError, match="Colunas obrigatórias ausentes"):
        validate_required_schema(df_broken)


def test_audit_raw_data_quality_detects_missing_duplicates_and_conflicts(synthetic_raw_df):
    audit = audit_raw_data_quality(synthetic_raw_df)

    assert audit["total_linhas_brutas"] == 18
    assert audit["total_colunas"] == 8
    assert audit["duplicatas_exatas_excedentes"] == 1
    assert audit["linhas_envolvidas_duplicatas_exatas"] == 2
    assert audit["linhas_invoice_prefixo_c"] == 3
    assert audit["linhas_invoice_prefixo_a"] == 2
    assert audit["quantidade_negativa_sem_prefixo_c"] == 1
    assert audit["preco_zero"] == 2
    assert audit["preco_negativo"] == 1
    assert audit["unit_price_acima_2_casas"] == {"0.001": 1}
    # StockCode 20001 ('LAMPADA RETRO' e 'damaged') e 20002 ('CANECA AZUL' e 'CANECA AZUL V2')
    assert audit["produtos_multiplas_descricoes"] == 2
    assert audit["pedidos_multiplos_timestamps"] == 1  # InvoiceNo 500001
    assert audit["clientes_multiplos_paises"] == 1  # Customer 102 (FR + DE)

    missing_by_col = {m["coluna"]: m["ausentes"] for m in audit["valores_ausentes"]}
    assert missing_by_col["Description"] == 1
    assert missing_by_col["CustomerID"] == 4
