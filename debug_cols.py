import pandas as pd
import os

EXCEL_FILE = "ACOMPANHAMENTO PROCESSUAL 2023.xlsx"

if os.path.exists(EXCEL_FILE):
    xl = pd.ExcelFile(EXCEL_FILE)
    if 'Victor' in xl.sheet_names:
        df = xl.parse('Victor')
        with open('victor_cols.txt', 'w') as f:
            f.write(str(df.columns.tolist()))
            f.write("\n\nSample data (first 5 rows):\n")
            f.write(df.head().to_string())
