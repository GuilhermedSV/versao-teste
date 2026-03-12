import pandas as pd

def analyze_excel(file_path):
    xl = pd.ExcelFile(file_path)
    for sheet in ['Processos', 'Miguel_1']:
        print(f"\n--- Aba: {sheet} ---")
        df = xl.parse(sheet, nrows=5)
        print("Colunas:", df.columns.tolist())
        print("Dados (primeiras 2 linhas):")
        print(df.head(2).to_dict(orient='records'))

if __name__ == "__main__":
    analyze_excel('ACOMPANHAMENTO PROCESSUAL 2023.xlsx')
