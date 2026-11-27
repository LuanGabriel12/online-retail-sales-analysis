"""Configurações centrais, metadados da fonte e parâmetros de negócio da V2."""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Diretórios principais do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = BASE_DIR / "Online Retail.xlsx"
ALT_DATA_PATH = BASE_DIR / "data" / "raw" / "Online Retail.xlsx"
DEFAULT_REPORTS_DIR = BASE_DIR / "reports"

# Metadados oficiais do dataset UCI Online Retail
DATASET_METADATA = {
    "nome": "Online Retail",
    "fonte": "UCI Machine Learning Repository",
    "url_oficial": "https://archive.ics.uci.edu/dataset/352/online+retail",
    "doi": "https://doi.org/10.24432/C5BW33",
    "autoria": "Daqing Chen (London South Bank University)",
    "licenca": "CC BY 4.0",
    "moeda": "GBP (£)",
    "planilha_esperada": "Online Retail",
    "registros_esperados_uci": 541909,
    "colunas_esperadas_uci": 8,
    "periodo_esperado_inicio": datetime(2010, 12, 1, 0, 0, 0),
    "periodo_esperado_fim": datetime(2011, 12, 9, 23, 59, 59),
    "sha256_esperado": (
        "43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d"
    ),
}

# Colunas obrigatórias da planilha original
REQUIRED_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]

# Resultados históricos documentados na V1 (referência de auditoria)
V1_HISTORICAL_REFERENCE = {
    "ticket_medio_geral": Decimal("533.17"),
    "maior_ticket_pais": "Singapore",
    "maior_ticket_pais_valor": Decimal("3039.90"),
    "produto_maior_quantidade": "PAPER CRAFT , LITTLE BIRDIE",
    "produto_maior_quantidade_codigo": "23843",
    "produto_maior_quantidade_unidades": 80995,
    "cliente_maior_faturamento": "14646",
    "cliente_maior_faturamento_valor": Decimal("280206.02"),
}

# Data de referência fixa para cálculo reprodutível da Recência RFM
# Corresponde ao dia seguinte à última data observada no dataset (2011-12-09).
RFM_REFERENCE_DATE = date(2011, 12, 10)

# Limiares transparentes de segmentação RFM (autorizados na auditoria da V1)
RFM_THRESHOLDS = {
    "recencia_recente_max_dias": 90,
    "frequencia_recorrente_min_pedidos": 2,
    "frequencia_alto_valor_min_pedidos": 5,
    "valor_monetario_alto_valor_min_gbp": Decimal("1500.00"),
}

# Ordem fixa e prioritária dos segmentos mutuamente exclusivos
RFM_SEGMENT_ORDER = [
    "Alto valor e recorrentes",
    "Recorrentes recentes",
    "Compra única recente",
    "Recorrentes há mais tempo sem compras",
    "Compra única há mais tempo sem compras",
]

# Classificação de porte amostral para países (evitar comparações distorcidas)
COUNTRY_SAMPLE_THRESHOLDS = {
    "amostra_muito_baixa_max_pedidos": 9,
    "amostra_moderada_max_pedidos": 49,
    "min_clientes_recorrencia_interpretavel": 10,
}

# Mês incompleto conhecido no conjunto de dados
INCOMPLETE_YEAR_MONTHS = ["2011-12"]

# Pedidos atípicos investigados na análise de sensibilidade
PRIMARY_OUTLIER_INVOICE = "581483"
PRIMARY_OUTLIER_STOCK_CODE = "23843"
SECONDARY_OUTLIER_INVOICE = "541431"
SECONDARY_OUTLIER_STOCK_CODE = "23166"

# Códigos operacionais ou não-mercadoria identificados na auditoria
NON_MERCHANDISE_STOCK_CODES = [
    "DOT",
    "POST",
    "M",
    "AMAZONFEE",
    "B",
    "C2",
    "BANK CHARGES",
    "S",
    "PADS",
    "CRUK",
    "D",
    "GIFT_0001_10",
    "GIFT_0001_20",
    "GIFT_0001_30",
    "GIFT_0001_40",
    "GIFT_0001_50",
]

# Política monetária em libra esterlina (GBP)
CURRENCY_CODE = "GBP"
CURRENCY_SYMBOL = "£"
DISPLAY_QUANTIZE = Decimal("0.01")
EXACT_QUANTIZE = Decimal("0.001")
RECONCILIATION_TOLERANCE_FLOAT = 0.01


def quantize_gbp(value: Decimal, places: Decimal = DISPLAY_QUANTIZE) -> Decimal:
    """Arredonda um valor Decimal de forma determinística usando ROUND_HALF_UP."""
    return value.quantize(places, rounding=ROUND_HALF_UP)


def to_decimal(value) -> Decimal:
    """Converte número ou texto para Decimal a partir de sua representação textual."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def format_gbp(value, decimals: int = 2) -> str:
    """Formata um valor monetário em GBP para exibição em relatórios Markdown."""
    dec_val = to_decimal(value)
    pattern = Decimal("0.01") if decimals == 2 else Decimal("0.001")
    rounded = quantize_gbp(dec_val, pattern)
    formatted = f"{rounded:,.{decimals}f}"
    # Converte separador para padrão brasileiro (1.234,56) para leitura em PT-BR
    formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{CURRENCY_SYMBOL} {formatted}"
