import os
import io
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import requests
import pandas as pd
from datetime import datetime, timedelta
from threading import Lock
from collections import defaultdict

# ============================================================
# Cache simples em memória (3 minutos)
# ============================================================
_cache = {"data": None, "ts": None}
_cache_lock = Lock()
CACHE_TTL = 180  # segundos

def get_cached_processes():
    with _cache_lock:
        if _cache["data"] is not None and _cache["ts"] is not None:
            if (datetime.now() - _cache["ts"]).total_seconds() < CACHE_TTL:
                return _cache["data"]
        data = fetch_all_processes()
        _cache["data"] = data
        _cache["ts"] = datetime.now()
        return data

def invalidate_cache():
    with _cache_lock:
        _cache["data"] = None
        _cache["ts"] = None

app = Flask(__name__)
app.secret_key = "radar_robustec_v3_ultra"

# Configurações do Supabase
SUPABASE_URL = "https://ndfpegcuwthqsjpayfmp.supabase.co"
SUPABASE_KEY = "sb_publishable_wLoOr_q9VoTj7V7VQJLgVw_oS5Fycke"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def get_week_range():
    today = datetime.now()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=4)
    return f"{start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}"

def fetch_all_processes():
    """Busca todos os processos usando paginação para superar o limite de 1000."""
    all_data = []
    limit = 1000
    offset = 0
    while True:
        headers_req = HEADERS.copy()
        headers_req["Range"] = f"{offset}-{offset + limit - 1}"
        response = requests.get(f"{SUPABASE_URL}/rest/v1/processos?select=*&order=created_at.desc", headers=headers_req)
        if response.status_code not in [200, 206] or not response.json():
            break
        data = response.json()
        all_data.extend(data)
        if len(data) < limit:
            break
        offset += limit
    return all_data

def is_atrasado(processo):
    """Retorna True se o processo está atrasado (sem atualização há mais de 7 dias e não encerrado)."""
    if processo.get("status") == "Encerrado":
        return False
    data_str = processo.get("data_atualizacao") or processo.get("created_at")
    if not data_str:
        return True
    try:
        # Supabase retorna ISO format, pode ter timezone
        data_str_clean = data_str[:19]  # pega só YYYY-MM-DDTHH:MM:SS
        data = datetime.fromisoformat(data_str_clean)
        return (datetime.now() - data).days > 7
    except Exception:
        return True

def normalizar_sistema(s):
    if not s:
        return None
    s_up = str(s).upper().strip()
    if 'SAJ' in s_up:
        return 'E-SAJ'
    elif 'PJE' in s_up:
        return 'PJE'
    elif 'PROC' in s_up:
        return 'E-PROC'
    elif 'ELETRONICO' in s_up or 'ELETR' in s_up:
        return 'ELETRÔNICO'
    return s_up

@app.route("/")
def index():
    processos = get_cached_processes()

    # Passada unica para normalizacao e agregacoes (mais rapido com listas grandes)
    total = 0
    ativos = 0
    encerrados = 0
    atrasados = 0
    contagem_analista = defaultdict(int)
    stats_por_analista = defaultdict(lambda: {"total": 0, "ativos": 0, "encerrados": 0, "atrasados": 0})
    sistemas_set = set()
    comarcas_set = set()

    for p in processos:
        total += 1
        sistema_norm = normalizar_sistema(p.get("sistema"))
        p["sistema_norm"] = sistema_norm
        if sistema_norm:
            sistemas_set.add(sistema_norm)

        comarca = p.get("comarca")
        if comarca:
            comarcas_set.add(comarca)

        status = p.get("status")
        atrasado = is_atrasado(p)
        p["atrasado"] = atrasado

        if status == "Encerrado":
            encerrados += 1
        else:
            ativos += 1
        if atrasado:
            atrasados += 1

        analista = p.get("responsavel")
        if analista:
            contagem_analista[analista] += 1
            stats = stats_por_analista[analista]
            stats["total"] += 1
            if status == "Encerrado":
                stats["encerrados"] += 1
            else:
                stats["ativos"] += 1
            if atrasado:
                stats["atrasados"] += 1

    estatisticas = {
        "total": total,
        "ativos": ativos,
        "encerrados": encerrados,
        "atrasados": atrasados,
        "semana": get_week_range(),
    }

    # Listas unicas (para dropdowns de filtro)
    sistemas_unicos = sorted(sistemas_set)
    comarcas_unicas = sorted(comarcas_set)

    # Analistas ordenados por quantidade
    analistas_ordenados = sorted(contagem_analista.items(), key=lambda x: x[1], reverse=True)
    analistas_grafico = [{"name": r, "y": c} for r, c in analistas_ordenados]
    ordem_analistas = [a["name"] for a in analistas_grafico]
    stats_por_analista_ordenado = {analista: stats_por_analista[analista] for analista in ordem_analistas}

    return render_template("index_v3.html",
                           processos=processos,
                           estatisticas=estatisticas,
                           analistas_grafico=analistas_grafico,
                           ordem_analistas=ordem_analistas,
                           sistemas_unicos=sistemas_unicos,
                           comarcas_unicas=comarcas_unicas,
                           stats_por_analista=stats_por_analista_ordenado)
@app.route("/api/processos", methods=["POST"])
def novo_processo():
    dados = {
        "numero_processo": request.form.get("numero_processo"),
        "sinistro_allianz": request.form.get("sinistro_allianz"),
        "autor": request.form.get("autor"),
        "comarca": request.form.get("comarca"),
        "uf": request.form.get("uf"),
        "sistema": request.form.get("sistema"),
        "responsavel": request.form.get("responsavel"),
        "status": "Ativo",
        "data_atualizacao": datetime.now().isoformat()
    }
    response = requests.post(f"{SUPABASE_URL}/rest/v1/processos", headers=HEADERS, json=dados)
    if response.status_code in [200, 201]:
        invalidate_cache()
        flash("Processo criado com sucesso!", "success")
    else:
        flash("Erro ao criar processo.", "error")
    return redirect(url_for("index"))

@app.route("/api/busca_processo")
def busca_processo():
    query = request.args.get("q", "")
    if not query:
        return jsonify([])
    url = f"{SUPABASE_URL}/rest/v1/processos?or=(numero_processo.eq.{query},sinistro_allianz.eq.{query})&select=id,numero_processo,sinistro_allianz,autor,responsavel"
    response = requests.get(url, headers=HEADERS)
    return jsonify(response.json() if response.status_code == 200 else [])

@app.route("/api/andamentos", methods=["POST"])
def novo_andamento():
    processo_id = request.form.get("processo_id")
    descricao = request.form.get("descricao")

    response = requests.patch(
        f"{SUPABASE_URL}/rest/v1/processos?id=eq.{processo_id}",
        headers=HEADERS,
        json={
            "ultimo_andamento": descricao,
            "data_atualizacao": datetime.now().isoformat()
        }
    )
    if response.status_code in [200, 204]:
        invalidate_cache()
        flash("Andamento salvo com sucesso!", "success")
    else:
        flash("Erro ao salvar andamento.", "error")
    return redirect(url_for("index"))

@app.route("/api/andamentos/editar", methods=["POST"])
def editar_andamento():
    processo_id = request.form.get("processo_id")
    nova_descricao = request.form.get("descricao")

    response = requests.patch(
        f"{SUPABASE_URL}/rest/v1/processos?id=eq.{processo_id}",
        headers=HEADERS,
        json={
            "ultimo_andamento": nova_descricao,
            "data_atualizacao": datetime.now().isoformat()
        }
    )
    if response.status_code in [200, 204]:
        invalidate_cache()
        flash("Andamento editado com sucesso!", "success")
    else:
        flash("Erro ao editar andamento.", "error")
    return redirect(url_for("index"))

@app.route("/api/processos/encerrar", methods=["POST"])
def encerrar_processo():
    processo_id = request.form.get("processo_id")
    response = requests.patch(
        f"{SUPABASE_URL}/rest/v1/processos?id=eq.{processo_id}",
        headers=HEADERS,
        json={"status": "Encerrado"}
    )
    if response.status_code in [200, 204]:
        invalidate_cache()
        flash("Processo encerrado com sucesso!", "success")
    else:
        flash("Erro ao encerrar processo.", "error")
    return redirect(url_for("index"))

@app.route("/api/exportar")
def exportar_excel():
    """Exporta todos os processos como arquivo Excel para download direto no navegador."""
    processos = fetch_all_processes()
    df = pd.DataFrame(processos)

    if not df.empty:
        colunas_remover = ['id', 'created_at']
        df = df.drop(columns=[c for c in colunas_remover if c in df.columns])
        # Renomear colunas
        rename_map = {
            'numero_processo': 'Nº Processo',
            'sinistro_allianz': 'Sinistro Allianz',
            'autor': 'Autor',
            'comarca': 'Comarca',
            'uf': 'UF',
            'sistema': 'Sistema',
            'responsavel': 'Responsável',
            'status': 'Status',
            'ultimo_andamento': 'Último Andamento',
            'data_atualizacao': 'Data Atualização',
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Processos')
    output.seek(0)

    filename = f"EXPORT_BRUNIERA_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)
