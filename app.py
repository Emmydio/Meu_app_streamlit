import pandas as pd
import gspread
from google.oauth2 import service_account
import streamlit as st

# Configuração do Streamlit
st.set_page_config(page_title="Análise de Inspeções F-5", layout="wide")
st.title("📊 Painel de Inspeções F-5")
arquivo = st.file_uploader("Ou selecione o arquivo", type="xlsx", label_visibility="collapsed")
# Autenticação simplificada (Streamlit Secrets)
@st.cache_data
def load_data():
    try:
        # Se usar Streamlit Secrets (recomendado para deploy)
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gc = gspread.authorize(creds)
        
        # Abrir planilha
        sheet_url = st.secrets["sheet_url"]
        spreadsheet = gc.open_by_url(sheet_url)
        worksheet = spreadsheet.get_worksheet(0)
        records = worksheet.get_all_records()
        
        # Processar dados
        df = pd.DataFrame(records)
        df['Intervalo em Horas'] = pd.to_numeric(df['Intervalo em Horas'], errors='coerce').fillna(0)
        df['Intervalo em Dias'] = pd.to_numeric(df['Intervalo em Dias'], errors='coerce').fillna(0)
        return df
    
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

# Carregar dados
df = load_data()

if df is not None:
    # Mostrar dados
    st.dataframe(df, use_container_width=True)
    
    # Métricas principais
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Inspeções", len(df))
    col2.metric("Inspeções por Horas", len(df[df['Intervalo em Horas'] > 0]))
    col3.metric("Inspeções por Dias", len(df[df['Intervalo em Dias'] > 0]))
    
    # Filtros interativos
    nivel = st.selectbox("Filtrar por Nível", df['Nível'].unique())
    st.bar_chart(df[df['Nível'] == nivel]['Intervalo em Horas'].value_counts())

# =============================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================

st.set_page_config(
    page_title="Calculadora de Inspeções Aeronáuticas", 
    layout="wide",
    page_icon="✈️"
)
st.title("✈️ Calculadora de Inspeções Aeronáuticas")

# =============================================
# CARREGAMENTO DE DADOS
# =============================================

with st.expander("🔧 Configuração de Arquivo", expanded=True):
    usar_exemplo = st.checkbox("Usar dados de exemplo", help="Ative para testar sem arquivo externo")
    
    if not usar_exemplo:
        col1, col2 = st.columns([4,1])
        with col1:
            caminho_arquivo = st.text_input(
                "Caminho completo do arquivo Excel:",
                value=""
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            arquivo = st.file_uploader("Ou selecione o arquivo", type="xlsx", label_visibility="collapsed")
        
        if arquivo:
            try:
                df_projetos = pd.read_excel(arquivo, engine='openpyxl')
                df_projetos = sanitizar_dados(df_projetos)
            except Exception as e:
                st.error(f"Falha ao ler arquivo: {str(e)}")
                st.stop()
        elif caminho_arquivo:
            valido, mensagem = verificar_arquivo(caminho_arquivo)
            if not valido:
                st.error(mensagem)
                st.stop()
            try:
                df_projetos = pd.read_excel(caminho_arquivo, engine='openpyxl')
                df_projetos = sanitizar_dados(df_projetos)
            except Exception as e:
                st.error(f"Falha ao ler arquivo: {str(e)}")
                st.stop()
        else:
            st.warning("Por favor, selecione um arquivo ou use dados de exemplo")
            st.stop()
    else:
        df_projetos = carregar_dados_exemplo()

# Verificação final dos dados
if df_projetos.empty:
    st.error("Nenhum dado válido encontrado. Verifique o arquivo de entrada.")
    st.stop()

# =============================================
# SELEÇÃO DE PROJETO
# =============================================

st.header("1. Seleção do Projeto")

# Obter projetos disponíveis
projetos_disponiveis = sorted(df_projetos["Projeto"].unique().tolist())

# Seletor de projeto
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

# Filtrar inspeções do projeto
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
    # Validações
    if data_fim < data_inicio:
        st.error("A data final não pode ser anterior à data inicial!")
    elif horas_fim < horas_inicio:
        st.error("As horas finais não podem ser menores que as horas iniciais!")
    elif ciclos_fim < ciclos_inicio:
        st.error("Os ciclos finais não podem ser menores que os ciclos iniciais!")
    else:
        # Cálculos
        total_dias = (data_fim - data_inicio).days
        total_horas = horas_fim - horas_inicio
        total_ciclos = ciclos_fim - ciclos_inicio
        
        # Exibir métricas
        st.header("📊 Resultados do Período")
        cols = st.columns(3)
        cols[0].metric("Total de Dias", f"{total_dias} dias")
        cols[1].metric("Horas de Voo", f"{total_horas:.2f} horas")
        cols[2].metric("Ciclos", f"{total_ciclos} ciclos")
        
        # Cálculo de inspeções
        st.header("📝 Inspeções Requeridas")
        
        inspecoes_dias = inspecoes_projeto[inspecoes_projeto["Intervalo em Dias"].notna()]
        
        if inspecoes_dias.empty:
            st.warning("Nenhuma inspeção com intervalo válido encontrada")
        else:
            resultados = []
            for _, row in inspecoes_dias.iterrows():
                try:
                    intervalo = float(row["Intervalo em Dias"])
                    if intervalo > 0:
                        qtd_inspecoes = int(total_dias // intervalo)
                        resultados.append({
                            "Inspeção": row["Tipo de inspeção"],
                            "Nível": row["Nível"],
                            "Intervalo (dias)": intervalo,
                            "Quantidade": qtd_inspecoes,
                            "Última realização": data_inicio + timedelta(days=intervalo)
                        })
                except:
                    continue
            
            if resultados:
                df_resultados = pd.DataFrame(resultados)
                
                # Ordenar por intervalo
                df_resultados = df_resultados.sort_values("Intervalo (dias)")
                
                st.dataframe(
                    df_resultados,
                    column_config={
                        "Última realização": st.column_config.DateColumn(format="DD/MM/YYYY"),
                        "Intervalo (dias)": st.column_config.NumberColumn(format="%d dias")
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Sugestão de agendamento
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
            else:
                st.info("Nenhuma inspeção requerida para o período informado")

# =============================================
# INSTRUÇÕES E RODAPÉ
# =============================================

with st.sidebar:
    st.header("ℹ️ Instruções")
    st.markdown("""
    1. **Carregue os dados**:
       - Selecione um arquivo Excel OU
       - Use dados de exemplo
    
    2. **Selecione o projeto** aeronáutico
    
    3. **Defina o período** de análise
    
    4. **Insira os parâmetros** técnicos
    
    5. **Calcule** as inspeções requeridas
    """)
    
    st.markdown("---")
    st.markdown("**📌 Requisitos do Arquivo:**")
    st.markdown("""
    - Formato Excel (.xlsx)
    - Colunas obrigatórias:
      - `Projeto`
      - `Tipo de inspeção`
      - `Intervalo em Dias` (valores numéricos)
    """)
    
    st.markdown("---")
    st.markdown("**🔍 Dados de Exemplo:**")
    st.markdown("""
    - Projetos: F-5 (17 inspeções) e F-16 (15 inspeções)
    - Intervalos de 25 a 1500 dias
    """)

# Visualização dos dados brutos (para depuração)
with st.expander("🔍 Visualizar Dados Brutos (DEBUG)", False):
    st.write("Dados carregados:", df_projetos)
    st.write("Projetos disponíveis:", projetos_disponiveis)
    st.write("Colunas disponíveis:", list(df_projetos.columns))
