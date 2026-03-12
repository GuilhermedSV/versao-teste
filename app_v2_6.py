import os
from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secreta_super_segura_aqui"

# Supabase Auth e Headers
SUPABASE_URL = "https://huqvqyxblkkbkyzorhyc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh1cXZxeXhibGtrYmt5em9yaHljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2MzA5MzgsImV4cCI6MjA4ODIwNjkzOH0.vc9kdIRoC7ifM7AQlKpQZQslAT8i0RpulWZKBXpvocw"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

@app.route("/")
def index():
    # Pegar até 3000 processos da API do Supabase (para evitar limite nativo de 100/1000)
    headers_req = HEADERS.copy()
    headers_req["Range"] = "0-2999"
    response = requests.get(f"{SUPABASE_URL}/rest/v1/processos?select=*", headers=headers_req)
    processos = response.json() if response.status_code in [200, 206] else []
    
    # Calcular as estatísticas para o painel de bordo
    estatisticas = {
        "total": len(processos),
        "ativos": sum(1 for p in processos if p.get("status") == "Ativo"),
        "encerrados": sum(1 for p in processos if p.get("status") == "Encerrado"),
        "suspensos": sum(1 for p in processos if p.get("status") == "Suspenso")
    }

    # Agregar dados por status para grafico donut (excluindo zeros)
    status_contagem = {"Ativo": estatisticas["ativos"], "Suspenso": estatisticas["suspensos"], "Encerrado": estatisticas["encerrados"]}
    status_grafico = [{"name": st, "y": val} for st, val in status_contagem.items() if val > 0]
    
    # Agregar processos por analista (responsavel) para gráfico de barras horizontais
    contagem_analista = {}
    for p in processos:
        resp = p.get('responsavel')
        if resp:
            contagem_analista[resp] = contagem_analista.get(resp, 0) + 1
    # Ordenar pelos maiores
    analistas_grafico = [{"name": resp, "y": count} for resp, count in sorted(contagem_analista.items(), key=lambda item: item[1])]

    # Ordenar processos pelos mais novos (para uso na lista / tabela)
    if processos:
        processos.sort(key=lambda x: x.get('id', 0), reverse=True)

    return render_template("index.html", processos=processos, estatisticas=estatisticas, status_grafico=status_grafico, analistas_grafico=analistas_grafico)

@app.route("/api/processos", methods=["POST"])
def novo_processo():
    dados = {
        "numero_processo": request.form.get("numero_processo"),
        "sinistro_allianz": request.form.get("sinistro_allianz"),
        "autor": request.form.get("autor"),
        "comarca": request.form.get("comarca"),
        "uf": request.form.get("uf"),
        "responsavel": request.form.get("responsavel"),
        "status": request.form.get("status"),
        "prazo_vencimento": request.form.get("prazo_vencimento") or None
    }
    
    response = requests.post(f"{SUPABASE_URL}/rest/v1/processos", headers=HEADERS, json=dados)
    if response.status_code in [200, 201]:
        flash("Processo criado com sucesso!", "success")
    else:
        flash("Erro ao criar processo.", "error")
        
    return redirect(url_for("index"))

@app.route("/api/andamentos", methods=["POST"])
def novo_andamento():
    dados = {
        "processo_id": request.form.get("processo_id"),
        "descricao": request.form.get("descricao"),
        "responsavel_nome": request.form.get("responsavel_nome")
    }
    
    response = requests.post(f"{SUPABASE_URL}/rest/v1/andamentos", headers=HEADERS, json=dados)
    if response.status_code in [200, 201]:
        flash("Andamento registrado com sucesso!", "success")
    else:
        flash("Erro ao registrar andamento.", "error")
        
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
