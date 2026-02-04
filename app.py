import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Diário EBD", page_icon="✝️", layout="wide")

# Tenta Google
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    HAS_GOOGLE_LIBS = True
except ImportError:
    HAS_GOOGLE_LIBS = False

# IDs e Arquivos
SHEET_ID = "137YLYAmAdg-l_TeHhRClR4dJMG4GIK8ZqeReFY157mQ" 
ARQUIVO_LOCAL = "dados_backup_local.csv"
ARQUIVO_HISTORICO_LOCAL = "historico_local.csv"

# --- CONEXÃO ---
def get_google_client():
    if not HAS_GOOGLE_LIBS or not os.path.exists("credentials.json"):
        return None
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    return client

# --- CARREGAR ---
def carregar_dados():
    client = get_google_client()
    if client:
        try:
            sh = client.open_by_key(SHEET_ID)
            data = sh.worksheet("Dados").get_all_records()
            if data:
                df = pd.DataFrame(data)
                for col in ["Presencas", "Participacoes", "Performance"]:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                return df, "google"
        except: pass
    
    if os.path.exists(ARQUIVO_LOCAL):
        return pd.read_csv(ARQUIVO_LOCAL), "local"
    return pd.DataFrame(columns=["Nome", "Status", "Presencas", "Participacoes", "Performance"]), "novo"

def carregar_historico(modo):
    if modo == "google":
        try:
            client = get_google_client()
            if client:
                data = client.open_by_key(SHEET_ID).worksheet("Historico").get_all_records()
                return pd.DataFrame(data)
        except: pass

    if os.path.exists(ARQUIVO_HISTORICO_LOCAL):
        return pd.read_csv(ARQUIVO_HISTORICO_LOCAL)
    return pd.DataFrame(columns=["Data", "Aluno", "Acao"])

# --- SALVAR ---
def salvar_dados(df, modo):
    df.to_csv(ARQUIVO_LOCAL, index=False)
    if modo == "google":
        try:
            client = get_google_client()
            if client:
                client.open_by_key(SHEET_ID).worksheet("Dados").update([df.columns.values.tolist()] + df.values.tolist())
        except: pass

def registrar_historico(nome, acao, data_registro, modo):
    data_str = data_registro.strftime("%d/%m")
    
    novo_log = pd.DataFrame([[data_str, nome, acao]], columns=["Data", "Aluno", "Acao"])
    if not os.path.exists(ARQUIVO_HISTORICO_LOCAL):
        novo_log.to_csv(ARQUIVO_HISTORICO_LOCAL, index=False)
    else:
        novo_log.to_csv(ARQUIVO_HISTORICO_LOCAL, mode='a', header=False, index=False)

    if modo == "google":
        try:
            client = get_google_client()
            if client:
                client.open_by_key(SHEET_ID).worksheet("Historico").append_row([data_str, nome, acao])
        except: pass

# --- SIDEBAR (Entrada de Dados) ---
df, modo_atual = carregar_dados()

if modo_atual == "google": st.sidebar.success("🟢 Online")
elif modo_atual == "local": st.sidebar.warning("🟠 Offline")
else: st.sidebar.info("⚪ Novo")

with st.sidebar:
    st.header("Chamada")
    data_selecionada = st.date_input("Data da Aula", date.today())
    st.divider()
    
    with st.expander("➕ Novo Aluno"):
        novo_nome = st.text_input("Nome").upper()
        if st.button("Cadastrar"):
            if novo_nome and "Nome" in df.columns and novo_nome not in df["Nome"].values:
                novo = pd.DataFrame([{"Nome": novo_nome, "Status": "Ativo", "Presencas": 0, "Participacoes": 0, "Performance": 0.0}])
                df = pd.concat([df, novo], ignore_index=True)
                salvar_dados(df, modo_atual)
                st.rerun()

    if not df.empty and "Nome" in df.columns:
        alunos = df.sort_values("Nome")["Nome"].tolist()
        aluno_sel = st.selectbox("Aluno", alunos)
        c1, c2 = st.columns(2)
        
        if c1.button("✅ Presente"):
            idx = df[df["Nome"] == aluno_sel].index[0]
            df.at[idx, "Presencas"] += 1
            p, part = df.at[idx, "Presencas"], df.at[idx, "Participacoes"]
            df.at[idx, "Performance"] = round(part/p, 1) if p > 0 else 0.0
            
            salvar_dados(df, modo_atual)
            registrar_historico(aluno_sel, "Presença", data_selecionada, modo_atual)
            st.toast("Salvo!")
            st.rerun()

        if c2.button("🙋‍♂️ Participou"):
            idx = df[df["Nome"] == aluno_sel].index[0]
            df.at[idx, "Participacoes"] += 1
            p, part = df.at[idx, "Presencas"], df.at[idx, "Participacoes"]
            df.at[idx, "Performance"] = round(part/p, 1) if p > 0 else 0.0
            
            salvar_dados(df, modo_atual)
            registrar_historico(aluno_sel, "Participação", data_selecionada, modo_atual)
            st.toast("Salvo!")
            st.rerun()

# --- TELA PRINCIPAL ---
st.title("Diário de Classe")

tab1, tab2 = st.tabs(["📊 Geral (Totais)", "📅 Histórico (Datas)"])

# --- ABA 1: SÓ OS TOTAIS (O Momento Atual) ---
with tab1:
    st.subheader("Situação Atual")
    if not df.empty and "Nome" in df.columns:
        # Mostra a tabela limpa, apenas com os números totais
        # Mantive a barra azul na Performance pq ajuda a visualizar rápido, mas sem datas aqui.
        st.dataframe(
            df[['Nome', 'Status', 'Presencas', 'Participacoes', 'Performance']].style
            .format({"Performance": "{:.1f}", "Presencas": "{:.0f}", "Participacoes": "{:.0f}"})
            .bar(subset=["Performance"], color='#4cc9f0', vmin=0, vmax=3.0),
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("Cadastre alunos na barra lateral.")

# --- ABA 2: HISTÓRICO DE DATAS (O Passado) ---
with tab2:
    st.subheader("Frequência por Domingo")
    
    if not df.empty and "Nome" in df.columns:
        # Pega a lista de alunos para garantir que todos apareçam na tabela
        df_alunos = df[['Nome']].set_index('Nome')
        
        # Carrega histórico
        df_hist = carregar_historico(modo_atual)
        
        if not df_hist.empty and "Acao" in df_hist.columns:
            df_presencas = df_hist[df_hist['Acao'] == 'Presença']
            
            if not df_presencas.empty:
                # Pivot: Transforma Datas em Colunas
                matriz_datas = df_presencas.pivot_table(
                    index='Aluno', 
                    columns='Data', 
                    values='Acao', 
                    aggfunc=lambda x: '✅', 
                    fill_value='-'
                )
                matriz_datas.columns.name = None # Remove nome "Data" do topo
                
                # Junta com a lista completa de alunos (Left Join)
                # Assim, quem nunca veio aparece na lista com traços "-"
                tabela_final = df_alunos.join(matriz_datas, how='left')
                tabela_final.fillna('-', inplace=True)
                
                # Mostra a tabela de datas
                st.dataframe(
                    tabela_final.style.applymap(lambda v: 'color: transparent' if v == '-' else ''), 
                    use_container_width=True
                )
            else:
                st.info("Nenhuma presença registrada ainda.")
        else:
            st.info("Histórico vazio.")