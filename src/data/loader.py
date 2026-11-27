"""Carga do dataset Online Retail, verificação de SHA-256 e inspeção de precisão."""

import hashlib
from pathlib import Path
from typing import Any

import openpyxl
import pandas as pd

from src.config import ALT_DATA_PATH, DATASET_METADATA, DEFAULT_DATA_PATH
from src.data.validation import parse_customer_id, parse_exact_decimal


def resolve_data_path(custom_path: Path | None = None) -> Path:
    """Resolve o caminho do arquivo de dados sem modificar o arquivo bruto."""
    if custom_path is not None:
        resolved = Path(custom_path)
        if not resolved.exists():
            raise FileNotFoundError(
                f"Arquivo de dados não encontrado no caminho informado: {resolved}"
            )
        return resolved

    if DEFAULT_DATA_PATH.exists():
        return DEFAULT_DATA_PATH
    if ALT_DATA_PATH.exists():
        return ALT_DATA_PATH

    raise FileNotFoundError(
        "Arquivo 'Online Retail.xlsx' não encontrado. "
        f"Locais verificados: '{DEFAULT_DATA_PATH}' e '{ALT_DATA_PATH}'. "
        "Consulte data/README.md para instruções oficiais de obtenção na UCI."
    )


def calculate_sha256(file_path: Path) -> str:
    """Calcula o hash SHA-256 de um arquivo em blocos para evitar alto uso de memória."""
    hasher = hashlib.sha256()
    with Path(file_path).open("rb") as arquivo:
        while True:
            bloco = arquivo.read(1024 * 1024)
            if not bloco:
                break
            hasher.update(bloco)
    return hasher.hexdigest()


def inspect_excel_workbook_metadata(
    file_path: Path,
    inspect_precision: bool = True,
) -> dict[str, Any]:
    """Inspeciona metadados do arquivo Excel e precisão decimal original de UnitPrice."""
    path = Path(file_path)
    sha256_hash = calculate_sha256(path)
    size_bytes = path.stat().st_size

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet_names = list(workbook.sheetnames)
    sheet_name = sheet_names[0]
    worksheet = workbook[sheet_name]

    headers: list[Any] = []
    excel_row_count = 0
    invoice_types: dict[str, int] = {}
    stock_types: dict[str, int] = {}
    unit_price_more_than_2dp: dict[str, int] = {}
    non_integer_customer_ids = 0

    if inspect_precision:
        for idx, row in enumerate(worksheet.iter_rows(values_only=True)):
            if idx == 0:
                headers = list(row)
                continue
            excel_row_count += 1
            if len(row) < 8:
                continue
            inv, stk, _desc, _qty, _dt, up, cid, _country = row[:8]

            t_inv = type(inv).__name__
            invoice_types[t_inv] = invoice_types.get(t_inv, 0) + 1

            t_stk = type(stk).__name__
            stock_types[t_stk] = stock_types.get(t_stk, 0) + 1

            if up is not None:
                dec_up, up_ok = parse_exact_decimal(up)
                if up_ok and dec_up is not None:
                    exponent = dec_up.as_tuple().exponent
                    decimals = -exponent if isinstance(exponent, int) and exponent < 0 else 0
                    if decimals > 2:
                        key = str(up)
                        unit_price_more_than_2dp[key] = (
                            unit_price_more_than_2dp.get(key, 0) + 1
                        )

            if cid is not None:
                _cid_norm, cid_status = parse_customer_id(cid)
                if cid_status == "invalido":
                    non_integer_customer_ids += 1
    else:
        for row in worksheet.iter_rows(min_row=1, max_row=1, values_only=True):
            headers = list(row)

    workbook.close()

    return {
        "file_path": str(path),
        "file_name": path.name,
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "sha256": sha256_hash,
        "sha256_matches_official": sha256_hash == DATASET_METADATA["sha256_esperado"],
        "sheet_names": sheet_names,
        "active_sheet": sheet_name,
        "headers": headers,
        "excel_data_rows": excel_row_count,
        "invoice_no_python_types": invoice_types,
        "stock_code_python_types": stock_types,
        "unit_price_gt_2dp_values": unit_price_more_than_2dp,
        "unit_price_gt_2dp_rows": sum(unit_price_more_than_2dp.values()),
        "non_integer_customer_ids": non_integer_customer_ids,
    }


def load_raw_dataset(
    file_path: Path | None = None,
    inspect_precision: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Carrega o arquivo Excel ou CSV bruto e retorna DataFrame + metadados."""
    path = resolve_data_path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".xlsx":
        metadata = inspect_excel_workbook_metadata(
            path, inspect_precision=inspect_precision
        )
        df_raw = pd.read_excel(path, engine="openpyxl")
    elif suffix == ".csv":
        sha256_hash = calculate_sha256(path)
        size_bytes = path.stat().st_size
        # Leitura explícita com dtype=str evita inferência automática para float64
        # (ex.: Quantity > 2**53 com 1.5 na mesma coluna, ou CustomerID grande com nulos).
        df_raw = pd.read_csv(
            path,
            dtype=str,
            keep_default_na=True,
        )
        if "InvoiceDate" in df_raw.columns:
            df_raw["InvoiceDate"] = pd.to_datetime(
                df_raw["InvoiceDate"], errors="coerce"
            )
        metadata = {
            "file_path": str(path),
            "file_name": path.name,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "sha256": sha256_hash,
            "sha256_matches_official": sha256_hash
            == DATASET_METADATA["sha256_esperado"],
            "sheet_names": [],
            "active_sheet": "csv",
            "headers": list(df_raw.columns),
            "excel_data_rows": len(df_raw),
            "invoice_no_python_types": {},
            "stock_code_python_types": {},
            "unit_price_gt_2dp_values": {},
            "unit_price_gt_2dp_rows": 0,
            "non_integer_customer_ids": 0,
        }
    else:
        raise ValueError(
            f"Formato de arquivo não suportado: '{suffix}'. Utilize '.xlsx' ou '.csv'."
        )

    if df_raw.empty:
        raise ValueError(f"O arquivo carregado está vazio: {path}")

    return df_raw, metadata
