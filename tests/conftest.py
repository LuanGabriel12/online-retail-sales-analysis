"""Fixtures sintéticas pequenas com resultados verificáveis manualmente."""

from datetime import datetime

import pandas as pd
import pytest


@pytest.fixture
def synthetic_raw_df() -> pd.DataFrame:
    """Base sintética rica com resultados calculáveis à mão.

    Composição manual esperada (18 linhas brutas):
    - Vendas positivas válidas (11 linhas antes de deduplicação; 1 duplicata exata -> 10 linhas V2):
      1. 500001 | C101 (UK) | 2011-10-01 10:00 | 20001 x 10 @ 20.00 = 200.00
      2. 500001 | C101 (UK) | 2011-10-01 10:01 | 20002 x 5  @ 10.00 =  50.00  (2º timestamp +60s no mesmo pedido!)
      3. 500001 | C101 (UK) | 2011-10-01 10:01 | 20002 x 5  @ 10.00 =  50.00  (DUPLICATA EXATA removida!)
      4. 500002 | C101 (UK) | 2011-11-10 09:00 | 20001 x 20 @ 20.00 = 400.00
      5. 500003 | C101 (UK) | 2011-11-15 09:00 | 20001 x 20 @ 20.00 = 400.00
      6. 500004 | C101 (UK) | 2011-11-20 09:00 | 20001 x 20 @ 20.00 = 400.00
      7. 500005 | C101 (UK) | 2011-12-01 09:00 | 20001 x 10 @ 20.00 = 200.00
         -> C101: 5 pedidos, 85 un., £ 1.650,00, última compra 2011-12-01 (recência = 9 dias -> Alto valor e recorrentes)
      8. 500006 | C102 (FR) | 2011-11-25 14:00 | 20002 x 4  @ 10.00 =  40.00
      9. 500007 | C102 (DE) | 2011-12-05 14:00 | 20002 x 6  @ 10.00 =  60.00  (C102 em 2 países: FR e DE!)
         -> C102: 2 pedidos, 10 un., £ 100,00, última compra 2011-12-05 (recência = 5 dias -> Recorrentes recentes)
     10. 500008 | C103 (UK) | 2011-05-01 12:00 | PADS  x 3  @ 0.001 =   0.003 (3 casas decimais + código operacional!)
         -> C103: 1 pedido, 3 un., £ 0,003, última compra 2011-05-01 (recência = 223 dias -> Compra única há mais tempo sem compras)
     11. 500009 | None (UK) | 2011-12-02 15:00 | 20001 x 5  @ 20.00 = 100.00 (sem CustomerID -> mantida na base geral!)
         -> Total V2 deduplicado: 10 linhas, 9 pedidos, 103 unidades, £ 1.850,003
            - Identificado: 8 pedidos, £ 1.750,003 (C101=1650, C102=100, C103=0.003)
            - Não identificado: 1 pedido, £ 100,00

    - Registros não-venda (7 linhas):
     12. C500010 | C101 (UK) | 2011-12-02 | 20001 x -2 @ 20.00 = -40.00 (cancelamento identificado)
     13. C500011 | C102 (FR) | 2011-12-06 | 20002 x -1 @ 10.00 = -10.00 (cancelamento identificado)
     14. A563185 | None (UK) | 2011-08-12 | B     x  1 @ 100.00 = 100.00 (ajuste prefixo A positivo -> entra na V1, sai na V2!)
     15. A563186 | None (UK) | 2011-08-12 | B     x  1 @ -100.00 = -100.00 (ajuste prefixo A negativo)
     16. 500012  | None (UK) | 2011-07-01 | 20001 x -5 @ 0.00  =   0.00 (negativo sem prefixo C)
     17. 500013  | C101 (UK) | 2011-07-02 | 20001 x  2 @ 0.00  =   0.00 (preço não positivo)
     18. C500014 | C101 (UK) | 2011-07-03 | 20001 x  1 @ 10.00 =  10.00 (ambíguo: prefixo C com qty positiva!)
    """
    rows = [
        (500001, 20001, "LAMPADA RETRO", 10, datetime(2011, 10, 1, 10, 0), 20.00, 101.0, "United Kingdom"),
        (500001, "20002", "CANECA AZUL", 5, datetime(2011, 10, 1, 10, 1), 10.00, 101.0, "United Kingdom"),
        (500001, "20002", "CANECA AZUL", 5, datetime(2011, 10, 1, 10, 1), 10.00, 101.0, "United Kingdom"),
        (500002, 20001, "LAMPADA RETRO", 20, datetime(2011, 11, 10, 9, 0), 20.00, 101.0, "United Kingdom"),
        (500003, 20001, "LAMPADA RETRO", 20, datetime(2011, 11, 15, 9, 0), 20.00, 101.0, "United Kingdom"),
        (500004, 20001, "LAMPADA RETRO", 20, datetime(2011, 11, 20, 9, 0), 20.00, 101.0, "United Kingdom"),
        (500005, 20001, "LAMPADA RETRO ", 10, datetime(2011, 12, 1, 9, 0), 20.00, 101.0, "United Kingdom"),
        (500006, "20002", "CANECA AZUL", 4, datetime(2011, 11, 25, 14, 0), 10.00, 102.0, "France"),
        (500007, "20002", "CANECA AZUL V2", 6, datetime(2011, 12, 5, 14, 0), 10.00, 102.0, "Germany"),
        (500008, "PADS", "PADS TO MATCH ALL CUSHIONS", 3, datetime(2011, 5, 1, 12, 0), 0.001, 103.0, "United Kingdom"),
        (500009, 20001, "LAMPADA RETRO", 5, datetime(2011, 12, 2, 15, 0), 20.00, None, "United Kingdom"),
        ("C500010", 20001, "LAMPADA RETRO", -2, datetime(2011, 12, 2, 11, 0), 20.00, 101.0, "United Kingdom"),
        ("C500011", "20002", "CANECA AZUL", -1, datetime(2011, 12, 6, 10, 0), 10.00, 102.0, "France"),
        ("A563185", "B", "Adjust bad debt", 1, datetime(2011, 8, 12, 14, 50), 100.00, None, "United Kingdom"),
        ("A563186", "B", "Adjust bad debt", 1, datetime(2011, 8, 12, 14, 51), -100.00, None, "United Kingdom"),
        (500012, 20001, "damaged", -5, datetime(2011, 7, 1, 10, 0), 0.00, None, "United Kingdom"),
        (500013, 20001, None, 2, datetime(2011, 7, 2, 10, 0), 0.00, 101.0, "United Kingdom"),
        ("C500014", 20001, "LAMPADA RETRO", 1, datetime(2011, 7, 3, 10, 0), 10.00, 101.0, "United Kingdom"),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "InvoiceNo",
            "StockCode",
            "Description",
            "Quantity",
            "InvoiceDate",
            "UnitPrice",
            "CustomerID",
            "Country",
        ],
    )
