import streamlit as st
import pandas as pd
import altair as alt
from st_supabase_connection import SupabaseConnection
from datetime import datetime, timedelta

st.set_page_config(page_title="Bruniera - Gestão Jurídica", layout="wide")

st.title("⚖️ Sistema de Gerenciamento Bruniera")

conn = st.connection(
    "supabase",
    type=SupabaseConnection,
    url="https://huqvqyxblkkbkyzorhyc.supabase.co",
    key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh1cXZxeXhibGtrYmt5em9yaHljIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2MzA5MzgsImV4cCI6MjA4ODIwNjkzOH0.vc9kdIRoC7ifM7AQlKpQZQslAT8i0RpulWZKBXpvocw",
)

responsaveis_lista = [
    "Carmem",
    "Miguel_1",
    "Caroline",
    "Caroline_bkp",
    "Marcia",
    "Processos",
    "Debora",
    "Carolina",
    "Victor"
]
responsaveis = ["Todos"] + responsaveis_lista

# The global sidebar filter was removed to prevent duplication

# =========================
# DASHBOARD
# =========================

st.markdown("---")

st.subheader("📊 Painel Geral")

# 3 Column Layout (matching Screenshot)
col_totais, col_status, col_analistas = st.columns([1, 2, 2])

# Fetch Data for dashboard
total_processos = conn.table("processos").select("id", count="exact").execute().count
ativos = conn.table("processos").select("id", count="exact").eq("status","Ativo").execute().count
encerrados = conn.table("processos").select("id", count="exact").eq("status","Encerrado").execute().count
suspensos = conn.table("processos").select("id", count="exact").eq("status","Suspenso").execute().count

with col_totais:
    st.write("#### Totais")
    st.info(f"**Total planilha**\n\n### {total_processos}")
    st.success(f"**Ativos**\n\n### {ativos}")
    st.error(f"**Encerrados**\n\n### {encerrados}")
    st.warning(f"**Suspensos**\n\n### {suspensos}")

with col_status:
    st.write("#### Status da busca")
    # Data for donut
    status_data = pd.DataFrame({
        "Status": ["Ativos", "Encerrados", "Suspensos"],
        "Quantidade": [ativos, encerrados, suspensos]
    })
    # Filter out 0s for cleaner chart
    status_data = status_data[status_data["Quantidade"] > 0]
    
    if not status_data.empty:
        donut_chart = alt.Chart(status_data).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="Quantidade", type="quantitative"),
            color=alt.Color(field="Status", type="nominal", scale=alt.Scale(range=["#1b6ac6", "#73a5d8", "#c8e1f5"])),
            tooltip=["Status", "Quantidade"]
        ).properties(height=300)
        st.altair_chart(donut_chart, use_container_width=True)
    else:
        st.write("Sem dados de status")

with col_analistas:
    st.write("#### Processos por analista")
    responsaveis_df = conn.table("processos").select("responsavel").execute()
    df_resp = pd.DataFrame(responsaveis_df.data)
    
    if not df_resp.empty:
        contagem = df_resp["responsavel"].value_counts().reset_index()
        contagem.columns = ["Analista", "Quantidade"]
        
        click = alt.selection_point(name="Analista", fields=['Analista'])
        
        # Horizontal bar chart ordered by Quantidade, using shades of blue
        bar_chart = alt.Chart(contagem).mark_bar().encode(
            x=alt.X('Quantidade:Q', title='Quantidade'),
            y=alt.Y('Analista:N', sort='-x', title=''),
            color=alt.condition(click, alt.value("#1b6ac6"), alt.value("#8bc0f8")),
            tooltip=['Analista', 'Quantidade']
        ).add_params(click).properties(height=300)
        
        # Make the chart interactive and filter state on click
        event = st.altair_chart(bar_chart, use_container_width=True, on_select="rerun")
        if event and 'selection' in event and 'Analista' in event['selection'] and len(event['selection']['Analista']) > 0:
            st.session_state.sidebar_responsavel_filtro = event['selection']['Analista'][0]['Analista']
    else:
        st.write("Sem dados de analistas")

st.markdown("---")

# PRAZOS PRÓXIMOS
st.subheader("🚨 Prazos Próximos (Próximos 7 dias ou Atrasados)")

hoje = datetime.now()
daqui_a_7_dias = hoje + timedelta(days=7)

# Buscar processos ativos com prazo menor ou igual a hoje + 7 dias
prazos_query = conn.table("processos").select("*").eq("status", "Ativo").lte("prazo_vencimento", daqui_a_7_dias.isoformat()).order("prazo_vencimento").execute()

if prazos_query.data:
    df_prazos = pd.DataFrame(prazos_query.data)
    st.dataframe(
        df_prazos[["numero_processo", "autor", "comarca", "responsavel", "prazo_vencimento"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Nenhum prazo crítico no momento. 🎉")

st.markdown("---")

# =========================
# AÇÕES: CADASTRAR PROCESSO E NOVO ANDAMENTO
# =========================

@st.dialog("➕ Cadastrar Novo Processo")
def dialog_novo_processo():
    with st.form("novo_processo_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            numero_processo = st.text_input("Número do Processo")
            sinistro = st.text_input("Número do Sinistro")
            autor = st.text_input("Cliente (Autor)")
            comarca = st.text_input("Vara (Comarca)")
            instancia = st.text_input("Instância")
        with col2:
            uf = st.selectbox("UF", ["RJ","SP","MG","ES","RS","SC","PR","BA","PE","CE"])
            responsavel_novo = st.selectbox("Responsável", responsaveis_lista)
            status_novo = st.selectbox("Status", ["Ativo","Encerrado","Suspenso"])
            prazo = st.date_input("Prazo de Vencimento")
            
        if st.form_submit_button("Salvar Processo"):
            novo_processo_data = {
                "numero_processo": numero_processo,
                "sinistro_allianz": sinistro,
                "autor": autor,
                "comarca": comarca,
                "instancia": instancia,
                "uf": uf,
                "responsavel": responsavel_novo,
                "status": status_novo,
                "prazo_vencimento": prazo.isoformat() if prazo else None
            }
            conn.table("processos").insert(novo_processo_data).execute()
            st.success("Processo cadastrado!")
            st.rerun()

@st.dialog("➕ Adicionar Andamento Isolado")
def dialog_novo_andamento_global():
    todos_processos = conn.table("processos").select("id, numero_processo").execute()
    lista_processos = pd.DataFrame(todos_processos.data) if todos_processos.data else pd.DataFrame()
    with st.form("novo_and_geral_form"):
        if not lista_processos.empty:
            proc_selecionado = st.selectbox(
                "Pesquise o Processo", 
                lista_processos["numero_processo"].tolist()
            )
        else:
            st.warning("Nenhum processo disponível no banco")
            proc_selecionado = None
            
        descricao = st.text_area("Descrição do Andamento")
        responsavel_nome = st.selectbox("Responsável pelo Andamento", responsaveis_lista)
        
        if st.form_submit_button("Salvar Novo Andamento") and proc_selecionado:
            if descricao.strip():
                proc_id_ref = lista_processos[lista_processos["numero_processo"] == proc_selecionado].iloc[0]["id"]
                novo_andamento = {
                    "processo_id": int(proc_id_ref),
                    "descricao": descricao,
                    "responsavel_nome": responsavel_nome
                }
                conn.table("andamentos").insert(novo_andamento).execute()
                st.success("Andamento registrado com sucesso!")
                st.rerun()
            else:
                st.error("A descrição não pode estar vazia.")

col_btn1, col_btn2, _, _ = st.columns(4)
with col_btn1:
    if st.button("➕ Novo Processo", use_container_width=True):
        dialog_novo_processo()
with col_btn2:
    if st.button("➕ Novo Andamento", use_container_width=True):
        dialog_novo_andamento_global()
# =========================
# CONTROLE DE PÁGINA
# =========================

if "processo_selecionado" not in st.session_state:
    st.session_state.processo_selecionado = None


# =========================
# PÁGINA DO PROCESSO
# =========================

if st.session_state.processo_selecionado:

    processo = st.session_state.processo_selecionado

    st.button("⬅ Voltar", on_click=lambda: st.session_state.update({"processo_selecionado": None}))

    st.header(f"📂 Processo {processo['numero_processo']}")

    col1, col2, col3 = st.columns(3)

    col1.write(f"**Autor:** {processo['autor']}")
    col2.write(f"**Comarca:** {processo['comarca']}")
    col3.write(f"**Responsável:** {processo['responsavel']}")

    st.write(f"**Sinistro:** {processo['sinistro_allianz']}")
    st.write(f"**Status:** {processo['status']}")

    st.markdown("---")

    # BOTÕES STATUS

    colA, colB = st.columns(2)

    if colA.button("📁 Arquivar Processo"):

        conn.table("processos")\
            .update({"status": "Encerrado"})\
            .eq("id", processo["id"])\
            .execute()

        st.success("Processo arquivado!")
        st.rerun()

    if colB.button("🔄 Reativar Processo"):

        conn.table("processos")\
            .update({"status": "Ativo"})\
            .eq("id", processo["id"])\
            .execute()

        st.success("Processo reativado!")
        st.rerun()

    st.markdown("---")

    # HISTÓRICO

    st.subheader("📜 Histórico de Andamentos")

    andamento_query = conn.table("andamentos")\
        .select("*")\
        .eq("processo_id", processo["id"])\
        .order("data_registro", desc=True)\
        .execute()

    if andamento_query.data:

        df_andamentos = pd.DataFrame(andamento_query.data)

        for _, andamento in df_andamentos.iterrows():

            with st.container(border=True):
                st.markdown(
                    f"""
                    #### 📌 {andamento['data_registro'][:10]}
                    
                    {andamento['descricao']}
                    
                    👤 Responsável: **{andamento['responsavel_nome']}**
                    """
                )

    else:

        st.info("Nenhum andamento registrado.")

    # NOVO ANDAMENTO

    st.subheader("➕ Adicionar Andamento")

    with st.form("novo_andamento"):

        descricao = st.text_area("Descrição do Andamento")

        responsavel_nome = st.selectbox(
            "Responsável",
            responsaveis_lista
        )

        salvar_andamento = st.form_submit_button("Salvar Andamento")

        if salvar_andamento and descricao.strip():

            novo_andamento = {
                "processo_id": processo["id"],
                "descricao": descricao,
                "responsavel_nome": responsavel_nome
            }

            conn.table("andamentos").insert(novo_andamento).execute()

            st.success("Andamento registrado!")

            st.rerun()

# =========================
# LISTA DE PROCESSOS
# =========================

else:

    st.sidebar.header("Filtros")

    busca = st.sidebar.text_input("Buscar por Processo / Sinistro / Cliente (Autor) / Vara (Comarca)")

    responsavel = st.sidebar.selectbox(
        "Responsável",
        responsaveis,
        key="sidebar_responsavel_filtro"
    )

    status_filtro = st.sidebar.selectbox(
        "Status",
        ["Todos", "Ativo", "Encerrado", "Suspenso"]
    )
    
    prazo_filtro = st.sidebar.selectbox(
        "Prazos",
        ["Todos", "Próximos 7 dias", "Atrasados"]
    )

    query = conn.table("processos").select("*").range(0,2000)

    if status_filtro != "Todos":
        query = query.eq("status", status_filtro)

    if busca:
        query = query.or_(
            f"numero_processo.ilike.%{busca}%,sinistro_allianz.ilike.%{busca}%,autor.ilike.%{busca}%,comarca.ilike.%{busca}%"
        )

    if responsavel != "Todos":
        query = query.eq("responsavel", responsavel)
        
    if prazo_filtro == "Próximos 7 dias":
        hoje = datetime.now()
        daqui_a_7_dias = hoje + timedelta(days=7)
        query = query.gte("prazo_vencimento", hoje.isoformat()).lte("prazo_vencimento", daqui_a_7_dias.isoformat())
    elif prazo_filtro == "Atrasados":
        hoje = datetime.now()
        query = query.lt("prazo_vencimento", hoje.isoformat())

    dados = query.execute()

    if dados.data:

        df = pd.DataFrame(dados.data)

        st.subheader("📂 Processos")

        # Define the dialog function ABOVE where it's called
        @st.dialog("➕ Adicionar Andamento")
        def dialog_adicionar_andamento(proc_id, proc_num):
            st.write(f"Adicionando andamento para: **{proc_num}**")
            descricao = st.text_area("Descrição do Andamento", key=f"desc_{proc_id}")
            responsavel_nome = st.selectbox("Responsável", responsaveis_lista, key=f"resp_{proc_id}")
            
            if st.button("Salvar Andamento", key=f"salvar_{proc_id}"):
                if descricao.strip():
                    novo_andamento = {
                        "processo_id": proc_id,
                        "descricao": descricao,
                        "responsavel_nome": responsavel_nome
                    }
                    conn.table("andamentos").insert(novo_andamento).execute()
                    st.success("Andamento registrado com sucesso!")
                    st.rerun()
                else:
                    st.error("A descrição não pode estar vazia.")

        # Create a header row for the "spreadsheet" look
        header_col1, header_col2, header_col3, header_col4, header_col5, header_col6 = st.columns([2, 3, 2, 2, 2, 2])
        header_col1.write("**Processo**")
        header_col2.write("**Cliente**")
        header_col3.write("**Vara**")
        header_col4.write("**Responsável**")
        header_col5.write("**Status / Prazo**")
        header_col6.write("**Ações**")
        st.markdown("---")

        for _, row in df.iterrows():

            col1, col2, col3, col4, col5, col6 = st.columns([2, 3, 2, 2, 2, 2])
            
            prazo_str = f"📅 {row['prazo_vencimento'][:10]}" if row.get('prazo_vencimento') else "Sem prazo"

            col1.write(f"**{row['numero_processo']}**")
            col2.write(row['autor'])
            col3.write(row['comarca'])
            col4.write(row['responsavel'])
            col5.write(f"{row['status']} | {prazo_str}")

            with col6:
                if st.button("Abrir", key=f"abrir_{row['id']}", use_container_width=True):
                    st.session_state.processo_selecionado = row
                    st.rerun()
                if st.button("🟢 Andamento", key=f"andamento_{row['id']}", use_container_width=True):
                    dialog_adicionar_andamento(row['id'], row['numero_processo'])

    else:

        st.info("Nenhum processo encontrado.")