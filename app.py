import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="EBD Jovens", layout="centered")

# --- CONEXÃO COM GOOGLE SHEETS ---
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# --- FUNÇÃO INTELIGENTE: INICIALIZAR E CARREGAR ---
def carregar_dados(aba_nome):
    client = conectar_google_sheets()
    spreadsheet = client.open("Relatorio_EBD_2026")
    
    # Tenta abrir a aba "Jovens", se não existir, cria sozinha
    try:
        sheet = spreadsheet.worksheet(aba_nome)
    except:
        # Cria a aba se ela sumiu
        sheet = spreadsheet.add_worksheet(title=aba_nome, rows=100, cols=20)
        
    # Se a aba estiver vazia (sem cabeçalho), cria o cabeçalho padrão
    if not sheet.row_values(1):
        cabecalhos = ["Nome", "Presencas", "Participacoes", "Performance"]
        sheet.append_row(cabecalhos)
        data = []
    else:
        data = sheet.get_all_records()

    # Cria a Tabela no sistema
    if not data:
        # Tabela vazia mas com as colunas certas
        df = pd.DataFrame(columns=["Nome", "Presencas", "Participacoes", "Performance"])
    else:
        df = pd.DataFrame(data)
        
    return df

def salvar_dados(df, aba_nome):
    client = conectar_google_sheets()
    sheet = client.open("Relatorio_EBD_2026").worksheet(aba_nome)
    # Atualiza a planilha inteira
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

def registrar_historico(nome, acao, data):
    client = conectar_google_sheets()
    spreadsheet = client.open("Relatorio_EBD_2026")
    try:
        sheet_hist = spreadsheet.worksheet("Historico")
    except:
        sheet_hist = spreadsheet.add_worksheet(title="Historico", rows=1000, cols=10)
        sheet_hist.append_row(["Data", "Hora", "Classe", "Nome", "Acao"])
        
    hora = datetime.now().strftime("%H:%M:%S")
    linha = [data, hora, "Jovens", nome, acao]
    sheet_hist.append_row(linha)

# --- INTERFACE GRÁFICA ---
st.title("📊 EBD - Jovens 2026")

# CONFIGURAÇÃO FIXA (SÓ JOVENS)
modo_atual = "Jovens"
data_hoje = datetime.now().strftime("%d/%m/%Y")
st.write(f"📅 Data: **{data_hoje}**")

# CARREGAR DADOS
try:
    df = carregar_dados(modo_atual)
    
    # Garantir que os números sejam lidos como números
    cols_num = ["Presencas", "Participacoes", "Performance"]
    for col in cols_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # --- MÉTRICAS GERAIS ---
    if not df.empty:
        total_presencas = int(df["Presencas"].sum())
        total_participacao = int(df["Participacoes"].sum())
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Total Presenças", total_presencas)
        col_m2.metric("Total Participações", total_participacao)
    else:
        st.info("Nenhum aluno cadastrado ainda. Use o botão abaixo.")

    st.divider()

    # --- ÁREA DE CADASTRO (IMPORTANTE PARA COMEÇAR) ---
    with st.expander("➕ Cadastrar Novo Aluno"):
        novo_nome = st.text_input("Nome do Aluno:")
        if st.button("Salvar Novo Aluno"):
            if novo_nome:
                # Verifica se já existe para não duplicar
                if not df.empty and novo_nome in df["Nome"].values:
                    st.warning("Esse nome já existe na lista!")
                else:
                    # Cria a nova linha
                    novo_registro = pd.DataFrame([{"Nome": novo_nome, "Presencas": 0, "Participacoes": 0, "Performance": 0.0}])
                    # Junta com a tabela antiga
                    df = pd.concat([df, novo_registro], ignore_index=True)
                    salvar_dados(df, modo_atual)
                    registrar_historico(novo_nome, "Cadastro", data_hoje)
                    st.success(f"{novo_nome} cadastrado com sucesso!")
                    st.rerun()
            else:
                st.warning("Digite um nome!")

    st.divider()

    # --- LISTA E AÇÕES ---
    if not df.empty:
        lista_alunos = df["Nome"].tolist()
        aluno_sel = st.selectbox("Selecione o Aluno:", lista_alunos)

        if aluno_sel:
            # Pega dados atuais do aluno
            idx = df[df["Nome"] == aluno_sel].index[0]
            val_presenca = int(df.at[idx, "Presencas"])
            val_partic = int(df.at[idx, "Participacoes"])
            val_perf = df.at[idx, "Performance"]

            st.write(f"### 👤 {aluno_sel}")
            
            # --- BOTÕES DE PRESENÇA ---
            st.caption("Controle de Presença")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Marcar Presença", use_container_width=True):
                    df.at[idx, "Presencas"] += 1
                    # Recalcula Performance
                    p, part = df.at[idx, "Presencas"], df.at[idx, "Participacoes"]
                    df.at[idx, "Performance"] = round(part/p, 1) if p > 0 else 0.0
                    
                    salvar_dados(df, modo_atual)
                    registrar_historico(aluno_sel, "Presenca", data_hoje)
                    st.toast("Presença Confirmada!")
                    st.rerun()
            
            with c2:
                if st.button("❌ Anular Presença", use_container_width=True):
                    if val_presenca > 0:
                        df.at[idx, "Presencas"] -= 1
                        # Recalcula Performance
                        p, part = df.at[idx, "Presencas"], df.at[idx, "Participacoes"]
                        df.at[idx, "Performance"] = round(part/p, 1) if p > 0 else 0.0
                        
                        salvar_dados(df, modo_atual)
                        registrar_historico(aluno_sel, "ANULADO - Presenca", data_hoje)
                        st.toast("Presença Removida!")
                        st.rerun()
                    else:
                        st.warning("Já está zero!")

            # --- BOTÕES DE PONTOS ---
            st.caption("Participação")
            c3, c4 = st.columns(2)
            with c3:
                if st.button("➕ Ponto Extra", use_container_width=True):
                    df.at[idx, "Participacoes"] += 1
                    # Recalcula Performance
                    p, part = df.at[idx, "Presencas"], df.at[idx, "Participacoes"]
                    df.at[idx, "Performance"] = round(part/p, 1) if p > 0 else 0.0
                    
                    salvar_dados(df, modo_atual)
                    registrar_historico(aluno_sel, "Ponto Extra", data_hoje)
                    st.toast("Ponto Adicionado!")
                    st.rerun()
            
            with c4:
                if st.button("🔻 Tirar Ponto", use_container_width=True):
                    if val_partic > 0:
                        df.at[idx, "Participacoes"] -= 1
                        # Recalcula Performance
                        p, part = df.at[idx, "Presencas"], df.at[idx, "Participacoes"]
                        df.at[idx, "Performance"] = round(part/p, 1) if p > 0 else 0.0
                        
                        salvar_dados(df, modo_atual)
                        registrar_historico(aluno_sel, "ANULADO - Ponto", data_hoje)
                        st.toast("Ponto Removido!")
                        st.rerun()
                    else:
                        st.warning("Já está zero!")

            # --- TABELA DE RESUMO ---
            st.write("---")
            st.write(f"**Resumo: {aluno_sel}**")
            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("Presenças", val_presenca)
            col_res2.metric("Pontos", val_partic)
            col_res3.metric("Nota", val_perf)

    # --- TABELA GERAL NO FINAL ---
    st.divider()
    with st.expander("Ver Tabela Completa"):
        st.dataframe(df)

except Exception as e:
    st.error(f"Erro no sistema: {e}")
    st.write("Dica: Verifique a conexão com a internet ou as permissões da planilha.")