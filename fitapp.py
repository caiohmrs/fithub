import streamlit as st
from datetime import datetime
from pypdf import PdfReader
import re
import time
from supabase import create_client, Client

# 1. Configuração de Página e Conexão
st.set_page_config(page_title="Hub de Saúde", layout="centered", initial_sidebar_state="collapsed")

try:
    url = "https://sfkreuklfpexolakblko.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNma3JldWtsZnBleG9sYWtibGtvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2OTI3OTcsImV4cCI6MjA4OTI2ODc5N30._G6GJ59O605cy_roMfM0BXwYSltHyD_fm8juFvHyWKo"
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Erro ao conectar ao Supabase.")
    st.stop()

# 2. CSS (Equalização de Botões e Popovers)
st.markdown("""
    <style>
    /* Fundo Principal */
    .stApp { background-color: #1e1e1e; color: #f8fafc; }
    header {visibility: hidden;}
    
    /* Configuração Base para Botões E Popovers */
    /* O seletor 'button' dentro do popover precisa ser forçado */
    div.stButton > button, 
    div[data-testid="stPopover"] > button,
    div[data-testid="stPopover"] [data-testid="stBaseButton-secondary"] {
        background-color: #1e293b !important;
        color: ##65c9ff !important;
        border: 2px solid #334155 !important;
        border-radius: 12px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        height: 45px !important; /* Altura fixa para alinhar todos */
        transition: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* Botão de Água (+250ml) - Borda Azul */
    div.stButton > button:contains("+250ml") {
        border-color: #65c9ff !important;
        color: #65c9ff !important;
    }

    /* Popover de Refeição - Borda Rosa (Igual aos outros) */
    div[data-testid="stPopover"] > button {
        border-color: #65c9ff !important;
        color: #65c9ff !important;
    }
    
    /* Remove o efeito de foco/hover branco do Streamlit no Popover */
    div[data-testid="stPopover"] > button:focus, 
    div[data-testid="stPopover"] > button:active,
    div[data-testid="stPopover"] > button:hover {
        background-color: #65c9ff !important;
        border-color: #65c9ff !important;
        color: #65c9ff !important;
    }

    /* Botão de Treino - Borda Laranja */
    div.stButton > button:contains("Treinei!") {
        border-color: #fb923c !important;
        color: #fb923c !important;
    }

    /* Ajuste do texto e ícone dentro do popover */
    div[data-testid="stPopover"] p {
        color: inherit !important;
        margin: 0 !important;
    }

    /* Estilo do Botão "Sair" */
    div.stButton > button:contains("Sair") {
        width: auto !important;
        height: auto !important;
        border-color: #475569 !important;
        color: #94a3b8 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Funções de Banco de Dados
def get_perfis():
    return supabase.table("perfis").select("*").execute().data

def carregar_perfil_completo(nome):
    return supabase.table("perfis").select("*").eq("nome", nome).single().execute().data

def get_progresso_hoje(nome):
    hoje = datetime.now().date().isoformat()
    res = supabase.table("progresso_diario").select("*").eq("usuario_nome", nome).eq("data", hoje).execute()
    if not res.data:
        novo = {"usuario_nome": nome, "data": hoje, "agua_consumida": 0, "refeicoes_completas": 0}
        return supabase.table("progresso_diario").insert(novo).execute().data[0]
    return res.data[0]

def atualizar_progresso(id_progresso, campo, valor):
    supabase.table("progresso_diario").update({campo: valor}).eq("id", id_progresso).execute()

def salvar_dieta_db(nome, texto):
    supabase.table("perfis").update({"dieta_texto": texto}).eq("nome", nome).execute()

def adicionar_log_db(msg, comentario=""):
    usuario = st.session_state.usuario_atual
    log_data = {"usuario_nome": usuario, "texto": msg.replace(usuario, f"<b>{usuario}</b>"), "comentario": comentario}
    supabase.table("atividades").insert(log_data).execute()

def get_feed():
    return supabase.table("atividades").select("*").order("created_at", desc=True).limit(20).execute().data

# 4. Inicialização de Estado
if 'usuario_atual' not in st.session_state: st.session_state.usuario_atual = None

# --- TELA 1: SELEÇÃO DE PERFIL ---
if st.session_state.usuario_atual is None:
    perfis = get_perfis()
    st.write("<br><br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>Quem está acessando?</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    for i, p in enumerate(perfis):
        with col1 if i == 0 else col2:
            st.image(p["foto_url"], use_container_width=True)
            if st.button(p["nome"], key=f"btn_{p['nome']}", use_container_width=True):
                st.session_state.usuario_atual = p["nome"]
                perfil_db = carregar_perfil_completo(p["nome"])
                st.session_state.meta_agua = perfil_db["meta_agua"]
                st.session_state.meta_refeicoes = perfil_db["meta_refeicoes"]
                st.session_state.dieta_texto = perfil_db.get("dieta_texto")
                st.rerun()

# --- TELA 2: APP PRINCIPAL ---
else:
    user = st.session_state.usuario_atual
    progresso = get_progresso_hoje(user)

    col_head1, col_head2 = st.columns([4, 1])
    col_head1.markdown(f"## Olá, {user} 👋")
    if col_head2.button("Sair"):
        st.session_state.clear() # Limpa tudo ao sair
        st.rerun()

    tab_home, tab_dieta, tab_treino, tab_saude = st.tabs(["🏠 Home", "🥗 Dieta", "💪 Treino", "🏥 Saúde"])

    horarios_refeicoes = [
        {"nome": "☕ Café da Manhã", "hora": "09:00", "h_int": 9},
        {"nome": "🍎 Lanche da Manhã", "hora": "10:30", "h_int": 10},
        {"nome": "🍽️ Almoço", "hora": "12:30", "h_int": 12},
        {"nome": "🥞 Merenda", "hora": "16:00", "h_int": 16},
        {"nome": "🌙 Jantar", "hora": "21:00", "h_int": 21},
    ]

    with tab_home:
        # Puxa a foto do perfil sem loop (usando o session_state se possível)
        c1, c2 = st.columns([1, 3])
        c1.markdown(f"![Perfil](https://api.dicebear.com/9.x/avataaars/svg?seed={user})", unsafe_allow_html=True)
        with c2:
            st.markdown(f"**Água:** {progresso['agua_consumida']}/{st.session_state.meta_agua}ml")
            st.progress(min(progresso['agua_consumida']/st.session_state.meta_agua, 1.0))
            st.markdown(f"**Refeições:** {progresso['refeicoes_completas']}/{st.session_state.meta_refeicoes}")
            st.progress(min(progresso['refeicoes_completas']/st.session_state.meta_refeicoes, 1.0))

        st.write("---")
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("💧 +250ml", use_container_width=True):
                atualizar_progresso(progresso['id'], "agua_consumida", progresso['agua_consumida'] + 250)
                adicionar_log_db(f"💧 {user} bebeu 250ml de água.")
                st.rerun()
        with col_btn2:
            with st.popover("🍽️ Refeição", use_container_width=True):
                comentario_ref = st.text_input("O que comeu?")
                if st.button("Confirmar"):
                    atualizar_progresso(progresso['id'], "refeicoes_completas", progresso['refeicoes_completas'] + 1)
                    adicionar_log_db(f"🍽️ {user} completou uma refeição.", comentario_ref)
                    st.rerun()
        with col_btn3:
            if st.button("✅ Treinei!", use_container_width=True):
                adicionar_log_db(f"🔥 {user} finalizou o treino do dia!")
                st.rerun()

        st.subheader("Atividades Recentes")
        for log in get_feed():
            cor_borda = "#65c9ff" if log["usuario_nome"] == "Caio" else "#ffadd2"
            hora_f = datetime.fromisoformat(log["created_at"]).strftime("%H:%M")
            st.markdown(f"<div style='background-color: #1e293b; padding: 12px; border-radius: 10px; margin-bottom: 8px; border-left: 4px solid {cor_borda}; color: #cbd5e1;'><b>{log['texto']}</b> <span style='float:right; font-size: 0.7rem;'>{hora_f}</span><br><small>{log['comentario'] or ''}</small></div>", unsafe_allow_html=True)

    with tab_dieta:
        st.subheader("🥗 Plano Alimentar")
        
        # O segredo para parar o loop: processar o arquivo e limpar o uploader com st.rerun()
        arquivo_pdf = st.file_uploader("Subir nova dieta (PDF)", type="pdf")
        if arquivo_pdf:
            reader = PdfReader(arquivo_pdf)
            texto_extraido = "".join(page.extract_text() for page in reader.pages)
            salvar_dieta_db(user, texto_extraido)
            st.session_state.dieta_texto = texto_extraido
            st.success("Dieta atualizada com sucesso!")
            time.sleep(1)
            st.rerun()

        texto_dieta = st.session_state.get("dieta_texto")
        if texto_dieta:
            hora_agora = datetime.now().hour
            proxima_ref = next((r for r in horarios_refeicoes if hora_agora < r["h_int"]), horarios_refeicoes[-1])
            
            for i, ref in enumerate(horarios_refeicoes):
                with st.expander(f"{ref['nome']} - {ref['hora']}", expanded=(ref == proxima_ref)):
                    # Busca segura do texto entre os horários
                    inicio = texto_dieta.find(ref['hora'])
                    if inicio != -1:
                        # Busca o fim baseado na próxima refeição ou no final das receitas
                        proximo_horario = horarios_refeicoes[i+1]['hora'] if i+1 < len(horarios_refeicoes) else "Receita"
                        fim = texto_dieta.find(proximo_horario, inicio + 5)
                        
                        trecho = texto_dieta[inicio:fim] if fim != -1 else texto_dieta[inicio:]
                        
                        # Limpeza e Formatação
                        trecho = re.sub(r"Página \d+/\d+.*?\d{2}/\d{2}/\d{4}\.", "", trecho)
                        linhas = trecho.split('\n')
                        for linha in linhas:
                            linha = linha.strip()
                            if not linha or ":" in linha[:8]: continue
                            if "Opções" in linha: st.markdown(f"<small style='color:#94a3b8;'>🔄 {linha}</small>", unsafe_allow_html=True)
                            else: st.markdown(f"✅ {re.sub(r'(\d+.*?\(.*?\))', r'<b>\1</b>', linha)}", unsafe_allow_html=True)
                    else:
                        st.warning("Horário não encontrado no texto do PDF.")
        else:
            st.info("Nenhum plano salvo. Use o botão acima para importar seu PDF.")

    with tab_treino: st.info("Em breve...")
    with tab_saude: st.info("Em breve...")