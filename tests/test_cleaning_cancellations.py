"""Testes de triagem mutuamente exclusiva, deduplicação e análise de cancelamentos."""

from datetime import datetime
from decimal import Decimal

import pandas as pd
import pytest

from src.analytics.cancellations import analyze_cancellations_and_anomalies
from src.data.cleaning import (
    CATEGORY_ACCOUNTING_ADJUSTMENT,
    CATEGORY_AMBIGUOUS_OR_INVALID,
    CATEGORY_CANCELLATION,
    CATEGORY_NEGATIVE_QTY_NO_C,
    CATEGORY_NON_POSITIVE_PRICE,
    CATEGORY_VALID_SALE_RAW,
    build_clean_datasets,
)
from src.data.validation import (
    audit_raw_data_quality,
    parse_customer_id,
    parse_exact_integer,
)


def test_clean_datasets_mutually_exclusive_triage_and_v1_comparison(synthetic_raw_df):
    result = build_clean_datasets(synthetic_raw_df)
    resumo = result["resumo_limpeza"]

    assert resumo["linhas_brutas"] == 18
    assert resumo["contagem_triagem"] == {
        CATEGORY_VALID_SALE_RAW: 11,
        CATEGORY_CANCELLATION: 2,
        CATEGORY_ACCOUNTING_ADJUSTMENT: 2,
        CATEGORY_NEGATIVE_QTY_NO_C: 1,
        CATEGORY_NON_POSITIVE_PRICE: 1,
        CATEGORY_AMBIGUOUS_OR_INVALID: 1,
    }
    assert sum(resumo["contagem_triagem"].values()) == 18

    # Deduplicação remove exatamente 1 linha (500001 / 20002 / qty=5 / £ 50,00)
    assert resumo["duplicatas_exatas_removidas_em_vendas"] == 1
    assert resumo["valor_duplicatas_removidas_decimal"] == Decimal("50.00")
    assert resumo["linhas_mantidas_v2"] == 10

    # V1 (apenas Quantity > 0 e UnitPrice > 0) inclui A563185 (+£100) e C500014 (+£10)
    assert resumo["linhas_mantidas_v1_equivalente"] == 12
    assert resumo["diferenca_linhas_v1_vs_v2"] == 2

    # Confere faturamento exato em Decimal com 3 casas preservadas
    rev_v2 = sum(result["df_sales_v2"]["valor_linha_decimal"], Decimal("0"))
    rev_v1 = sum(result["df_sales_v1"]["valor_linha_decimal"], Decimal("0"))
    assert rev_v2 == Decimal("1850.003")
    assert rev_v1 == Decimal("1960.003")


def test_cancellations_analysis_separates_categories_and_computes_balance(synthetic_raw_df):
    cleaned = build_clean_datasets(synthetic_raw_df)
    canc_data = analyze_cancellations_and_anomalies(
        df_classified=cleaned["df_classified"],
        df_sales_v2=cleaned["df_sales_v2"],
    )
    resumo = canc_data["resumo"]

    assert resumo["linhas_cancelamento_brutas"] == 2
    assert resumo["notas_cancelamento_distintas"] == 2
    assert resumo["unidades_canceladas_brutas"] == -3
    assert resumo["valor_cancelamentos_deduplicados_decimal"] == Decimal("-50.00")
    assert resumo["linhas_negativas_sem_c"] == 1
    assert resumo["valor_negativas_sem_c_decimal"] == Decimal("0.00")
    assert resumo["linhas_preco_nao_positivo"] == 1
    assert resumo["linhas_ajuste_prefixo_a"] == 2
    assert resumo["valor_liquido_ajustes_prefixo_a_decimal"] == Decimal("0.00")
    assert resumo["linhas_ambiguas_ou_inconsistentes"] == 1

    # Saldo monetário observado = 1850.003 + (-50.00) = 1800.003
    assert resumo["saldo_monetario_observado_dedup_decimal"] == Decimal("1800.003")
    expected_pct = (50.0 / 1850.003) * 100.0
    assert resumo["participacao_cancelamentos_dedup_sobre_vendas_v2_pct"] == pytest.approx(
        expected_pct, rel=1e-3
    )

    # Verifica tabela por país (France tem £40 vendas e -£10 cancelamentos = 25%)
    by_country = canc_data["cancelamentos_por_pais"]
    france_row = by_country.loc[by_country["country"] == "France"].iloc[0]
    assert france_row["vendas_positivas_decimal"] == Decimal("40.00")
    assert france_row["valor_cancelamento_decimal"] == Decimal("-10.00")
    assert france_row["saldo_monetario_observado_decimal"] == Decimal("30.00")
    assert france_row["participacao_cancelamento_sobre_vendas_pct"] == pytest.approx(25.0)


def test_fractional_and_non_finite_quantities_and_prices_are_rejected_without_truncation():
    rows = [
        # Venda válida inteira de referência
        (700001, "10001", "PRODUTO OK", 2, datetime(2011, 10, 1, 10, 0), 10.00, 101.0, "United Kingdom"),
        # Quantidade positiva fracionada: NÃO pode ser truncada para 1
        (700002, "10001", "PRODUTO FRAC", 1.5, datetime(2011, 10, 1, 10, 5), 10.00, 101.0, "United Kingdom"),
        # Quantidade negativa fracionada
        ("C700003", "10001", "CANC FRAC", -1.5, datetime(2011, 10, 1, 10, 6), 10.00, 101.0, "United Kingdom"),
        # Quantidade infinita
        (700004, "10001", "PRODUTO INF", float("inf"), datetime(2011, 10, 1, 10, 7), 10.00, 101.0, "United Kingdom"),
        # Preço unitário infinito
        (700005, "10001", "PRECO INF", 2, datetime(2011, 10, 1, 10, 8), float("inf"), 101.0, "United Kingdom"),
        # Preço unitário -inf
        (700006, "10001", "PRECO NINF", 2, datetime(2011, 10, 1, 10, 9), float("-inf"), 101.0, "United Kingdom"),
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "InvoiceNo", "StockCode", "Description", "Quantity",
            "InvoiceDate", "UnitPrice", "CustomerID", "Country",
        ],
    )

    audit = audit_raw_data_quality(df)
    assert audit["quantidades_fracionadas_ou_nao_finitas"] == 3
    assert audit["precos_nao_finitos"] == 2

    cleaned = build_clean_datasets(df)
    resumo = cleaned["resumo_limpeza"]
    assert resumo["linhas_mantidas_v2"] == 1
    assert resumo["linhas_mantidas_v1_equivalente"] == 1
    assert resumo["contagem_triagem"][CATEGORY_VALID_SALE_RAW] == 1
    assert resumo["contagem_triagem"][CATEGORY_AMBIGUOUS_OR_INVALID] == 5
    assert resumo["quantidades_fracionadas_ou_nao_finitas"] == 3
    assert resumo["precos_nao_finitos"] == 2

    # Receita e quantidade permanecem 100% consistentes apenas com o registro válido (2 x 10.00 = 20.00)
    assert int(cleaned["df_sales_v2"]["quantity"].sum()) == 2
    assert sum(cleaned["df_sales_v2"]["valor_linha_decimal"], Decimal("0")) == Decimal("20.00")


def test_parse_customer_id_distinguishes_valid_missing_and_invalid():
    # Válidos
    assert parse_customer_id(123) == ("123", "valido")
    assert parse_customer_id(123.0) == ("123", "valido")
    assert parse_customer_id("123") == ("123", "valido")
    assert parse_customer_id(" 123.00 ") == ("123", "valido")

    # Ausentes
    assert parse_customer_id(None) == (None, "ausente")
    assert parse_customer_id(float("nan")) == (None, "ausente")
    assert parse_customer_id("") == (None, "ausente")
    assert parse_customer_id("   ") == (None, "ausente")

    # Inválidos (nunca truncados para 123 nem aceitos)
    assert parse_customer_id(123.5) == (None, "invalido")
    assert parse_customer_id("123.5") == (None, "invalido")
    assert parse_customer_id(float("inf")) == (None, "invalido")
    assert parse_customer_id(float("-inf")) == (None, "invalido")
    assert parse_customer_id("inf") == (None, "invalido")
    assert parse_customer_id(0) == (None, "invalido")
    assert parse_customer_id(-123) == (None, "invalido")
    assert parse_customer_id("-123") == (None, "invalido")
    assert parse_customer_id("ABC") == (None, "invalido")
    assert parse_customer_id("12.3.4") == (None, "invalido")
    assert parse_customer_id(True) == (None, "invalido")


def test_invalid_customer_id_never_merges_with_valid_customer_and_separates_from_missing():
    rows = [
        # Cliente válido 123
        (710001, "10001", "ITEM A", 2, datetime(2011, 10, 1, 10, 0), 25.00, 123.0, "United Kingdom"),
        # Cliente ausente (venda guest válida, mantida na base geral)
        (710002, "10001", "ITEM A", 1, datetime(2011, 10, 2, 10, 0), 25.00, None, "United Kingdom"),
        # CustomerID fracionado 123.5: NÃO pode ser truncado para 123!
        (710003, "10001", "ITEM A", 4, datetime(2011, 10, 3, 10, 0), 25.00, 123.5, "United Kingdom"),
        # CustomerID infinito
        (710004, "10001", "ITEM A", 1, datetime(2011, 10, 4, 10, 0), 25.00, float("inf"), "United Kingdom"),
        # CustomerID malformado
        (710005, "10001", "ITEM A", 1, datetime(2011, 10, 5, 10, 0), 25.00, "CLI-XYZ", "United Kingdom"),
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "InvoiceNo", "StockCode", "Description", "Quantity",
            "InvoiceDate", "UnitPrice", "CustomerID", "Country",
        ],
    )

    audit = audit_raw_data_quality(df)
    assert audit["customer_ids_ausentes"] == 1
    assert audit["customer_ids_invalidos"] == 3

    cleaned = build_clean_datasets(df)
    resumo = cleaned["resumo_limpeza"]
    assert resumo["customer_ids_ausentes"] == 1
    assert resumo["customer_ids_invalidos"] == 3
    assert resumo["linhas_mantidas_v2"] == 2  # apenas 710001 (válido) e 710002 (ausente)
    assert resumo["contagem_triagem"][CATEGORY_AMBIGUOUS_OR_INVALID] == 3

    df_v2 = cleaned["df_sales_v2"]
    assert list(df_v2["invoice_no"]) == ["710001", "710002"]
    # Garante que cliente 123 manteve somente seu pedido de £ 50,00 (sem absorver 710003 de £ 100,00)
    c123_rows = df_v2.loc[df_v2["customer_id"] == "123"]
    assert len(c123_rows) == 1
    assert sum(c123_rows["valor_linha_decimal"], Decimal("0")) == Decimal("50.00")


def test_large_integers_above_2_pow_53_preserve_exact_precision_in_quantity_and_customer_id():
    big_id_1 = 2**53 + 1  # 9007199254740993 (perderia +1 se passasse por float64)
    big_id_2 = 2**53 + 3  # 9007199254740995 (colidiria ou perderia precisão em float64)
    big_qty = 2**53 + 1   # 9007199254740993

    # Verifica parsing unitário exato via int, Decimal e string
    assert parse_exact_integer(big_qty) == (big_qty, True)
    assert parse_exact_integer(str(big_qty)) == (big_qty, True)
    assert parse_exact_integer(f"{big_qty}.00") == (big_qty, True)
    assert parse_exact_integer(Decimal(big_qty)) == (big_qty, True)
    assert parse_exact_integer(f"{big_qty}.5") == (None, False)

    assert parse_customer_id(big_id_1) == (str(big_id_1), "valido")
    assert parse_customer_id(str(big_id_1)) == (str(big_id_1), "valido")
    assert parse_customer_id(f"{big_id_1}.0") == (str(big_id_1), "valido")
    assert parse_customer_id(Decimal(big_id_1)) == (str(big_id_1), "valido")
    assert parse_customer_id(big_id_2) == (str(big_id_2), "valido")
    assert parse_customer_id(big_id_1) != parse_customer_id(big_id_2)

    # Testa coluna mista contendo inteiro > 2**53 e fracionado 1.5 na mesma coluna Quantity
    rows = [
        (720001, "10001", "ITEM A", big_qty, datetime(2011, 10, 1, 10, 0), Decimal("1.00"), big_id_1, "United Kingdom"),
        (720002, "10001", "ITEM A", str(big_qty), datetime(2011, 10, 2, 10, 0), "2.00", str(big_id_2), "United Kingdom"),
        (720003, "10001", "ITEM FRAC", 1.5, datetime(2011, 10, 3, 10, 0), 10.00, big_id_1, "United Kingdom"),
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "InvoiceNo", "StockCode", "Description", "Quantity",
            "InvoiceDate", "UnitPrice", "CustomerID", "Country",
        ],
    )

    audit = audit_raw_data_quality(df)
    assert audit["quantidades_fracionadas_ou_nao_finitas"] == 1
    assert audit["customer_ids_invalidos"] == 0

    cleaned = build_clean_datasets(df)
    df_v2 = cleaned["df_sales_v2"]
    assert len(df_v2) == 2

    # Nenhum dos valores > 2**53 pode ser arredondado para 9007199254740992
    assert list(df_v2["quantity"]) == [big_qty, big_qty]
    assert list(df_v2["customer_id"]) == [str(big_id_1), str(big_id_2)]
    assert list(df_v2["valor_linha_decimal"]) == [
        Decimal(big_qty) * Decimal("1.00"),
        Decimal(big_qty) * Decimal("2.00"),
    ]
    assert sum(df_v2["valor_linha_decimal"], Decimal("0")) == Decimal(big_qty) * Decimal("3.00")


def test_cancellations_empty_input_emits_no_future_warning():
    import warnings

    rows = [
        (730001, "10001", "ITEM A", 2, datetime(2011, 10, 1, 10, 0), 10.00, 101, "Brazil"),
        (730002, "10002", "ITEM B", 3, datetime(2011, 10, 2, 10, 0), 15.00, 102, "Canada"),
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "InvoiceNo", "StockCode", "Description", "Quantity",
            "InvoiceDate", "UnitPrice", "CustomerID", "Country",
        ],
    )
    cleaned = build_clean_datasets(df)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", FutureWarning)
        canc_data = analyze_cancellations_and_anomalies(
            df_classified=cleaned["df_classified"],
            df_sales_v2=cleaned["df_sales_v2"],
        )

    future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert future_warnings == [], f"FutureWarning inesperado emitido: {[str(w.message) for w in future_warnings]}"
    assert canc_data["resumo"]["linhas_cancelamento_brutas"] == 0
    assert list(canc_data["cancelamentos_por_pais"]["linhas_cancelamento"]) == [0, 0]
