import pandas as pd
import requests
from io import BytesIO

url_excel = "https://1drv.ms/x/c/0d5c40b4737f8815/IQDzUkM5JHqdQYcpgfqJ2La3AQi7vEk3zjDk8OOFdcNJANs?download=1"
response = requests.get(url_excel)
arquivo = BytesIO(response.content)

abas = pd.read_excel(arquivo, sheet_name=None)
print("ABAS ENCONTRADAS:")
for nome in abas.keys():
    print(f"'{nome}' - len: {len(nome)}")
