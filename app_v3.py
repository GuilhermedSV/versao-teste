import os
import io
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import requests
import pandas as pd
from datetime import datetime, timedelta
from threading import Lock

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

    # Normalizar sistema e marcar atrasados
    for p in processos:
        p['sistema_norm'] = normalizar_sistema(p.get('sistema'))
        p['atrasado'] = is_atrasado(p)

    # Estatísticas gerais
    total = len(processos)
    ativos = sum(1 for p in processos if p.get("status") != "Encerrado")
    encerrados = sum(1 for p in processos if p.get("status") == "Encerrado")
    atrasados = sum(1 for p in processos if p.get("atrasado"))

    estatisticas = {
        "total": total,
        "ativos": ativos,
        "encerrados": encerrados,
        "atrasados": atrasados,
        "semana": get_week_range(),
    }

    # Listas únicas (para dropdowns de filtro)
    sistemas_unicos = sorted(set(p['sistema_norm'] for p in processos if p.get('sistema_norm')))
    comarcas_unicas = sorted(set(p.get('comarca', '') for p in processos if p.get('comarca')))

    # Analistas ordenados por quantidade
    contagem_analista = {}
    for p in processos:
        r = p.get('responsavel')
        if r:
            contagem_analista[r] = contagem_analista.get(r, 0) + 1

    analistas_grafico = [{"name": r, "y": c} for r, c in sorted(contagem_analista.items(), key=lambda x: x[1], reverse=True)]
    ordem_analistas = [a["name"] for a in analistas_grafico]

    # Gráfico PIZZA por Comarca (geral)
    def top_comarcas(procs, limit=8):
        cnt = {}
        for p in procs:
            c = p.get('comarca')
            if c:
                cnt[c] = cnt.get(c, 0) + 1
        sorted_c = sorted(cnt.items(), key=lambda x: x[1], reverse=True)
        top = sorted_c[:limit]
        outros = sum(v for _, v in sorted_c[limit:])
        result = [{"name": k, "y": v} for k, v in top]
        if outros > 0:
            result.append({"name": "Outros", "y": outros})
        return result

    comarcas_grafico = top_comarcas(processos)

    # Comarcas por analista (para atualizar pizza ao filtrar)
    comarcas_por_analista = {}
    for analista in ordem_analistas:
        procs_a = [p for p in processos if p.get('responsavel') == analista]
        comarcas_por_analista[analista] = top_comarcas(procs_a, limit=6)

    # Estatísticas por analista (cards dinâmicos)
    stats_por_analista = {}
    for analista in ordem_analistas:
        procs = [p for p in processos if p.get('responsavel') == analista]
        stats_por_analista[analista] = {
            "total": len(procs),
            "ativos": sum(1 for p in procs if p.get("status") != "Encerrado"),
            "encerrados": sum(1 for p in procs if p.get("status") == "Encerrado"),
            "atrasados": sum(1 for p in procs if p.get("atrasado")),
        }

    return render_template("index_v3.html",
                           processos=processos,
                           estatisticas=estatisticas,
                           analistas_grafico=analistas_grafico,
                           comarcas_grafico=comarcas_grafico,
                           comarcas_por_analista=comarcas_por_analista,
                           ordem_analistas=ordem_analistas,
                           sistemas_unicos=sistemas_unicos,
                           comarcas_unicas=comarcas_unicas,
                           stats_por_analista=stats_por_analista)

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
