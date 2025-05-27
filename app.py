import pandas as pd
import gspread
from google.oauth2 import service_account
import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Calculadora de Inspeções Aeronáuticas",
    layout="wide",
    page_icon="✈️"
)

# Função para carregar dados direto do Google Sheets
@st.cache_data
def load_data_from_sheets():
    try:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gc = gspread.authorize(creds)
        sheet_url = st.secrets["sheet_url"]
        spreadsheet = gc.open_by_url(sheet_url)
        worksheet = spreadsheet.get_worksheet(0)
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        df['Intervalo em Horas'] = pd.to_numeric(df.get('Intervalo em Horas', 0), errors='coerce').fillna(0)
        df['Intervalo em Dias'] = pd.to_numeric(df.get('Intervalo em Dias', 0), errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()  # Retorna DataFrame vazio para evitar erros

# Carregar dados do Google Sheets
df_projetos = load_data_from_sheets()

if df_projetos.empty:
    st.error("Nenhum dado válido encontrado na planilha do Google Sheets.")
    st.stop()

# =============================================
# SELEÇÃO DE PROJETO
# =============================================

st.header("1. Seleção do Projeto")
projetos_disponiveis = sorted(df_projetos["Projeto"].unique().tolist())

col1, col2 = st.columns([3,1])
with col1:
    projeto_selecionado = st.selectbox(
        "Selecione o projeto:",
        options=projetos_disponiveis,
        index=0
    )
with col2:
    if len(projetos_disponiveis) == 1:
        st.info("Único projeto disponível")

inspecoes_projeto = df_projetos[df_projetos["Projeto"] == projeto_selecionado]
st.success(f"**{projeto_selecionado}** carregado com {len(inspecoes_projeto)} inspeções")

# =============================================
# PARÂMETROS DE ANÁLISE
# =============================================

st.header("2. Período Avaliado")
col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Início período avaliado", value=datetime.now() - timedelta(days=365))
with col2:
    data_fim = st.date_input("Fim período avaliado", value=datetime.now())

st.header("3. Parâmetros Técnicos")
col1, col2 = st.columns(2)
with col1:
    horas_inicio = st.number_input("Horas de Voo Iniciais (H)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
with col2:
    horas_fim = st.number_input("Horas de Voo Finais (H)", min_value=0.0, value=1000.0, step=0.01, format="%.2f")

col3, col4 = st.columns(2)
with col3:
    ciclos_inicio = st.number_input("Ciclos Iniciais", min_value=0, value=0)
with col4:
    ciclos_fim = st.number_input("Ciclos Finais", min_value=0, value=100)

# =============================================
# CÁLCULOS E RESULTADOS
# =============================================

if st.button("🔄 Calcular Inspeções", type="primary", use_container_width=True):
    if data_fim < data_inicio:
        st.error("A data final não pode ser anterior à data inicial!")
    elif horas_fim < horas_inicio:
        st.error("As horas finais não podem ser menores que as horas iniciais!")
    elif ciclos_fim < ciclos_inicio:
        st.error("Os ciclos finais não podem ser menores que os ciclos iniciais!")
    else:
        total_dias = (data_fim - data_inicio).days
        total_horas = horas_fim - horas_inicio
        total_ciclos = ciclos_fim - ciclos_inicio

        st.header("📊 Resultados do Período")
        cols = st.columns(3)
        cols[0].metric("Total de Dias", f"{total_dias} dias")
        cols[1].metric("Horas de Voo", f"{total_horas:.2f} horas")
        cols[2].metric("Ciclos", f"{total_ciclos} ciclos")

        st.header("📝 Inspeções Requeridas")
        inspecoes_dias = inspecoes_projeto[inspecoes_projeto["Intervalo em Dias"] > 0]

        if inspecoes_dias.empty:
            st.warning("Nenhuma inspeção com intervalo válido encontrada")
        else:
            resultados = []
            for _, row in inspecoes_dias.iterrows():
                intervalo = float(row["Intervalo em Dias"])
                qtd_inspecoes = int(total_dias // intervalo)
                ultima_realizacao = data_inicio + timedelta(days=intervalo)
                resultados.append({
                    "Inspeção": row["Tipo de inspeção"],
                    "Nível": row["Nível"],
                    "Intervalo (dias)": intervalo,
                    "Quantidade": qtd_inspecoes,
                    "Última realização": ultima_realizacao
                })

            df_resultados = pd.DataFrame(resultados).sort_values("Intervalo (dias)")

            st.dataframe(
                df_resultados,
                column_config={
                    "Última realização": st.column_config.DateColumn(format="DD/MM/YYYY"),
                    "Intervalo (dias)": st.column_config.NumberColumn(format="%d dias")
                },
                hide_index=True,
                use_container_width=True
            )

            st.subheader("📅 Próximas Inspeções")
            hoje = datetime.now().date()
            for _, item in df_resultados.iterrows():
                if item["Quantidade"] > 0:
                    proxima = item["Última realização"].date() + timedelta(days=item["Intervalo (dias)"])
                    atraso = (hoje - proxima).days if hoje > proxima else 0
                    if atraso > 0:
                        st.warning(f"⚠️ Atrasado {atraso} dias | {item['Inspeção']} (deveria ter sido em {proxima.strftime('%d/%m/%Y')})")
                    else:
                        st.success(f"✅ Em dia | {item['Inspeção']} (próxima em {proxima.strftime('%d/%m/%Y')})")

# =============================================
# INSTRUÇÕES E RODAPÉ
# =============================================

with st.sidebar:
    st.header("ℹ️ Instruções")
    st.markdown("""
    1. **Os dados são carregados diretamente do Google Sheets.**
    
    2. **Selecione o projeto aeronáutico**
    
    3. **Defina o período de análise**
    
    4. **Insira os parâmetros técnicos**
    
    5. **Calcule as inspeções requeridas**
    """)

    st.markdown("---")
    st.markdown("**📌 Requisitos do Arquivo Google Sheets:**")
    st.markdown("""
    - Formato Excel (.xlsx)
    - Colunas obrigatórias:
      - `Projeto`
      - `Tipo de inspeção`
      - `Intervalo em Dias` (valores numéricos)
    """)

# Visualização dos dados brutos (para depuração)
with st.expander("🔍 Visualizar Dados Brutos (DEBUG)", False):
    st.write("Dados carregados:", df_projetos)
    st.write("Projetos disponíveis:", projetos_disponiveis)
    st.write("Colunas disponíveis:", list(df_projetos.columns))

