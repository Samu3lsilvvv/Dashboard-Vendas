# --- Importação de Bibliotecas e Configuração da Página ---

# Banco de dados
import sqlite3 

# Manipulação de dados
import numpy as np   
import pandas as pd  

# Visualização
import plotly.express as px  
import streamlit as st       

# Gerar reporte
from fpdf import FPDF
from fpdf.enums import XPos, YPos  

# Gerenciar datas
from datetime import datetime, date, timedelta  

# Configuração Inicial do Streamlit
st.set_page_config(
    page_title="Dashboard de Vendas",  
    page_icon=":100:",                  
    layout="wide",                      
    initial_sidebar_state="expanded",   
)

def init_db(conn):

    """
    Inicializa o banco de dados.
    - Cria a tabela 'tb_vendas' se ela não existir.
    - Gera dados fictícios (180 dias) se estiver vazia
    """

    # Cria um objeto 'cursor' para executar comandos SQL na conexão fornecida
    cursor = conn.cursor()
    
    # Cria a tabela
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tb_vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            date TEXT,
            regiao TEXT,
            categoria TEXT,
            produto TEXT,
            faturamento REAL,
            quantidade INTEGER
        )
    """)

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM tb_vendas")

    if cursor.fetchone()[0] == 0:

        # Geração de Dados Fictícios 
        np.random.seed(42)
        
        # Define uma data de início fixa (1º de Jan de 2026) para os dados
        start_date = date(2026, 1, 1)
        
        datas = [start_date + timedelta(days = i) for i in range(180)]
        
        regioes = ["Norte", "Nordeste", "Sul", "Sudeste", "Centro-Oeste"]
        categorias = ["Eletrônicos", "Roupas", "Alimentos", "Serviços"]
        
        dict_produtos = {
            "Eletrônicos": {"Smartphone": 1200, "Laptop": 3500, "Tablet": 800},
            "Roupas": {"Camiseta": 50, "Terno": 150, "Casaco": 300},
            "Alimentos": {"Congelados": 40, "Bebidas": 15, "Limpeza": 25},
            "Serviços": {"Consultoria": 1000, "Instalação": 400, "Suporte": 200}
        }

        # Lista vazia para armazenar todas as linhas de dados
        rows = []

        # Loop para cada dia na lista de datas
        for d in datas:

            vendas_diarias = np.random.randint(5, 15)

            for _ in range(vendas_diarias):

                r = np.random.choice(regioes)
                c = np.random.choice(categorias)
                
                p = np.random.choice(list(dict_produtos[c].keys()))
                
                # Obtém o preço base do produto escolhido
                preco_base = dict_produtos[c][p]
                
                quantidade = np.random.randint(1, 25) 
                
                base_faturamento = preco_base * quantidade
                
                # Adiciona "ruído" (noise) de +/- 20% para simular dados realistas
                noise = np.random.uniform(-0.20, 0.20)
                faturamento = base_faturamento * (1 + noise)
                
                # Garante que o faturamento nunca seja negativo
                faturamento = max(0, faturamento)

                # Adiciona a linha de venda à lista 'rows'
                # O formato da tupla deve corresponder exatamente à ordem das colunas no INSERT
                rows.append((d.isoformat(), r, c, p, round(faturamento, 2), quantidade))

        # Inserção em Massa
        cursor.executemany(
            "INSERT INTO tb_vendas (date, regiao, categoria, produto, faturamento, quantidade) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )

        # Confirma a transação de inserção de dados
        conn.commit()


# Função de Conexão com o Banco de Dados

# Função de conexão ao banco de dados
def cria_conexao(db_path = "database.db"):

    # Cria a conexão com o banco de dados SQLite
    conn = sqlite3.connect(db_path, check_same_thread = False)
    return conn


# Função de Carregamento de Dados com Cache

# Decorador de Cache do Streamlit
@st.cache_data(ttl=600) 
def carrega_dados():

    
    #Função principal para carregar os dados.
    conn = cria_conexao()

    init_db(conn) 
    
    # Executa uma consulta SQL para selecionar TUDO (*) da 'tb_vendas'
    df = pd.read_sql_query("SELECT * FROM tb_vendas", conn, parse_dates = ["date"])
    conn.close()
    
    return df


# Função da Sidebar e Filtros

# Função com os filtros na barra lateral
def filtros_sidebar(df):
    
    # --- Banner da Sidebar ---
    st.sidebar.markdown(
        """
        <div style="background-color:#00CC96; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 15px;">
            <h3 style="color:white; margin:0; font-weight:bold;">Dashboard de Vendas</h3>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Adiciona um cabeçalho para a seção de filtros
    st.sidebar.header("Filtros")
    
    # Filtro de Data

    # Encontra a data mínima e máxima no DataFrame para definir os limites do filtro
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    
    # Cria o widget de seleção de intervalo de datas (calendário)
    date_range = st.sidebar.date_input("Período de Análise", (min_date, max_date), min_value = min_date, max_value = max_date)

    # --- Filtros de Seleção Múltipla (Multiselect) ---

    # Filtro de Região
    all_regioes = sorted(df["regiao"].unique())
    selected_regioes = st.sidebar.multiselect("Regiões", all_regioes, default = all_regioes)

    # Filtro de Categoria 
    all_categorias = sorted(df["categoria"].unique())
    selected_categorias = st.sidebar.multiselect("Categorias", all_categorias, default = all_categorias)
    
    # Filtro de Produto 
    all_produtos = sorted(df["produto"].unique())
    selected_produtos = st.sidebar.multiselect("Produtos", all_produtos, default = all_produtos)

    # --- Lógica de Aplicação dos Filtros ---

    # Validação para garantir que o 'date_range' retornou um início e fim
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    # Aplica a filtragem no DataFrame principal
    df_filtrado = df[

        # 1. Filtro de Data: Compara a data da linha com o 'start_date' e 'end_date'
        (df["date"].dt.date >= start_date) &
        (df["date"].dt.date <= end_date) &
        
        # 2. Filtros de Categoria: '.isin()' verifica se o valor da linha está presente na lista de itens selecionados no multiselect
        (df["regiao"].isin(selected_regioes)) &
        (df["categoria"].isin(selected_categorias)) &
        (df["produto"].isin(selected_produtos))
    ].copy() # .copy() cria um novo DataFrame independente

    # --- Rodapé da Sidebar ---
    st.sidebar.markdown("---")

    with st.sidebar.expander("🆘 Suporte / Fale conosco", expanded = False):
        st.write("Se tiver dúvidas envie mensagem para samuel20152001@gmail.com")

    return df_filtrado


# --- Função para Renderizar os Cards de KPIs ---

def renderiza_cards_kpis(df):
    # --- 1. Cálculos dos KPIs ---
    
    # Soma a coluna 'faturamento' para obter o total
    total_faturamento = df["faturamento"].sum()
    total_qty = df["quantidade"].sum()
    
    # Calcula o Ticket Médio (Faturamento / Quantidade)
    avg_ticket = total_faturamento / total_qty if total_qty > 0 else 0
    
    # Gera um número aleatório para SIMULAR uma variação (delta) vs. meta.
    delta_rev = np.random.uniform(-5, 15)
    
    # --- 2. Criação do Layout ---

    # cria 4 colunas virtuais
    c1, c2, c3, c4 = st.columns(4)
    
    # --- 3. Renderização dos Cards ---
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Receita Total</h3>
            <h2>R$ {total_faturamento:,.0f}</h2>
            <div class="delta" style="color: {'#4CAF50' if delta_rev > 0 else '#FF5252'}">
                {delta_rev:+.1f}% vs meta
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Vendas (Qtd)</h3>
            <h2>{total_qty:,.0f}</h2>
            <div class="delta">Unidades vendidas</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Ticket Médio</h3>
            <h2>R$ {avg_ticket:,.2f}</h2>
            <div class="delta">Por transação</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        transactions = df.shape[0]
        st.markdown(f"""
        <div class="metric-card">
            <h3>Transações</h3>
            <h2>{transactions}</h2>
            <div class="delta">Volume total</div>
        </div>
        """, unsafe_allow_html=True)
        
    # Retorna os valores calculados para que a função 'main' possa passá-los para a função de gerar o PDF
    return total_faturamento, total_qty, avg_ticket


# --- Função de Geração de Relatório PDF ---
def gera_pdf_report(df_filtrado, total_faturamento, total_quantidade, avg_ticket):

    # Gera um relatório PDF customizado usando a biblioteca FPDF.

    
    # --- 1. Configuração Inicial do PDF ---
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- 2. Título e Metadados ---
    pdf.set_font("Helvetica", "B", 16)
    
    # Cria a célula do título.
    pdf.cell(0, 10, "Relatorio Executivo de Vendas", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # Adiciona o carimbo de data/hora da geração
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # --- 3. Bloco de Resumo de KPIs (com fundo cinza) ---
    
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, 35, 190, 25, 'F')
    pdf.set_y(40)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(60, 8, f"Receita Total", align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(60, 8, f"Quantidade", align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(60, 8, f"Ticket Medio", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(60, 8, f"R$ {total_faturamento:,.2f}", align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(60, 8, f"{total_quantidade:,}", align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(60, 8, f"R$ {avg_ticket:,.2f}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(15)

    # --- 4. Tabela "Top 15 Vendas" ---
    
    # Adiciona o subtítulo da tabela
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Top 15 Vendas (por receita):", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    col_widths = [30, 30, 30, 40, 25, 30] 
    headers = ["Data", "Regiao", "Categoria", "Produto", "Qtd", "Receita"]
    
    # Loop para desenhar o CABEÇALHO da tabela
    pdf.set_font("Helvetica", "B", 9)
    for i, h in enumerate(headers):
        
        pdf.cell(col_widths[i], 8, h, 1, align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)
    
    pdf.ln()
    
    # --- 5. População da Tabela com Dados ---

    pdf.set_font("Helvetica", "", 9)
    df_top = df_filtrado.sort_values("faturamento", ascending=False).head(15)
    
    # Loop principal (externo): itera sobre cada linha do DataFrame df_top
    for _, row in df_top.iterrows():
        
        # Extrai os dados da linha do Pandas para uma lista simples
        data = [
            str(row['date'].date()),
            row['regiao'],
            row['categoria'],
            row['produto'][:20], 
            str(row['quantidade']),
            f"R$ {row['faturamento']:,.2f}"
        ]
        
        # Loop interno: itera sobre cada item (célula) da linha atual
        for i, d in enumerate(data):

            safe_txt = str(d).encode("latin-1", "replace").decode("latin-1")
            
            pdf.cell(col_widths[i], 7, safe_txt, 1, align=('C' if i==4 else 'L'), new_x=XPos.RIGHT, new_y=YPos.TOP)
        
        pdf.ln() # Quebra a linha após desenhar todas as células da linha

    # --- 6. Geração e Retorno do PDF ---
    result = pdf.output() 
    return result.encode("latin-1") if isinstance(result, str) else bytes(result)


# --- Bloco 8: Função de Estilização (Tema Customizado) ---

# Função para customização da interface com CSS
def set_custom_theme():

    # --- 1. Definição das Cores do Tema ---
    card_bg_color = "#262730"  
    text_color = "#FAFAFA"     
    gold_color = "#E1C16E"    
    dark_text = "#1E1E1E"     
    
    # --- 2. Criação do Bloco de Estilo CSS ---

    css = f"""
    <style>

        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div:first-child {{
            min-height: 100px !important; 
            overflow-y: auto !important;   
        }}
    
        .metric-card {{
            background-color: {card_bg_color};
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #444;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.3); /* Sombra sutil */
            text-align: center;
            margin-bottom: 10px; /* Espaçamento inferior */
        }}

        .metric-card h3 {{
            margin: 0;
            font-size: 1.2rem;
            color: #AAA; /* Cinza claro */
            font-weight: normal;
        }}

        .metric-card h2 {{
            margin: 10px 0 0 0;
            font-size: 2rem;
            color: {text_color};
            font-weight: bold;
        }}

        .metric-card .delta {{
            font-size: 0.9rem;
            color: #4CAF50; /* Verde (padrão) */
            margin-top: 5px;
        }}
                
        [data-baseweb="tag"] {{
            background-color: {gold_color} !important;
            color: {dark_text} !important;
            border-radius: 4px !important;
        }}
        
        [data-baseweb="tag"] svg {{
            color: {dark_text} !important;
        }}
        
        [data-baseweb="tag"] svg:hover {{
            color: #FF0000 !important; 
        }}
        
    </style>
    """
    
    # --- 3. Injeção do CSS na Página ---
    st.markdown(css, unsafe_allow_html = True)


# --- Função Principal ---

# Esta é a função que "orquestra" todo o aplicativo.
# Ela define a ordem em que as coisas acontecem:
# 1. Configura o tema
# 2. Carrega os dados
# 3. Renderiza a sidebar e obtém os filtros
# 4. Renderiza o conteúdo da página principal (títulos, KPIs, abas)

# Função principal
def layout():

    set_custom_theme()
    df = carrega_dados()
    df_filtrado = filtros_sidebar(df)

    # --- Início: Layout da Página Principal ---
    
    st.title("📊 Dashboard de Vendas")
    st.write("Navegue pelo dashboard e use os filtros na barra lateral para diferentes visualizações. Os dados podem ser exportados para formato CSV e PDF.")
    st.markdown("---")
    st.markdown(f"Visão Consolidada de Vendas com KPIs.")

    # --- Verificação de Segurança ---
    if df_filtrado.empty:
        st.warning("⚠️ Nenhum dado encontrado com os filtros selecionados.")
        return

    total_faturamento, total_qty, avg_ticket = renderiza_cards_kpis(df_filtrado)

    # Linha horizontal para separar os KPIs das abas
    st.markdown("---")

    # Layout de Abas (Tabs)

    # Cria a navegação principal da página com duas abas
    tab1, tab2 = st.tabs(["📈 Visão Gráfica", "📄 Dados Detalhados & Exportação (CSV e PDF)"])

    # --- Aba 1: Gráficos ---
    with tab1:

        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            
            st.subheader("Evolução da Receita Diária")
            
            daily_rev = df_filtrado.groupby("date")[["faturamento"]].sum().reset_index()
            
            # Cria o gráfico de linha com Plotly Express
            fig_line = px.line(daily_rev, x = "date", y = "faturamento", template = "plotly_dark", height = 400)
            fig_line.update_traces(fill = 'tozeroy', line = dict(color = '#00CC96', width = 3))
            st.plotly_chart(fig_line, width = 'stretch') 

        # Gráfico 2: Mix de Categorias (Coluna da Direita)
        with col_right:
            
            st.subheader("Mix de Categorias")

            # Agrupa por categoria e soma o faturamento
            cat_rev = df_filtrado.groupby("categoria")[["faturamento"]].sum().reset_index()
            
            # Cria um gráfico de pizza
            fig_pie = px.pie(cat_rev, values="faturamento", names="categoria", hole=0.4, template="plotly_dark", height=400)
            st.plotly_chart(fig_pie, width='stretch') 

        # Cria a segunda linha de layout da aba: duas colunas de tamanho igual
        c_a, c_b = st.columns(2)
        
        # Gráfico 3: Performance Regional
        with c_a:

            st.subheader("Performance Regional")
            fig_bar = px.bar(
                df_filtrado.groupby("regiao")[["faturamento"]].sum().reset_index(),
                x="regiao", y="faturamento", color="regiao", template="plotly_dark", text_auto='.2s'
            )

            st.plotly_chart(fig_bar, width='stretch') 
            
        # Gráfico 4: Análise de Dia da Semana (com tradução)
        with c_b:

            st.subheader("Análise Dia da Semana")
            # Mapeamento para traduzir os dias da semana para Português
            dias_pt_map = {
                0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira",
                3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"
            }

            dias_pt_ordem = [
                "Segunda-feira", "Terça-feira", "Quarta-feira", 
                "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"
            ]

            # Criação das colunas de dia da semana (número e nome em PT)
            df_filtrado["weekday_num"] = df_filtrado["date"].dt.dayofweek
            
            df_filtrado["dia_semana"] = df_filtrado["weekday_num"].map(dias_pt_map)

            wd_rev = df_filtrado.groupby("dia_semana")[["faturamento"]].mean().reindex(dias_pt_ordem).reset_index()

            # Cria o gráfico de barras
            fig_heat = px.bar(wd_rev, x="dia_semana", y="faturamento", title="Receita Média x Dia", template="plotly_dark")
            st.plotly_chart(fig_heat, width='stretch')
            
        # Gráfico 5: Dispersão (Scatter Plot)
        st.subheader("Dispersão: Quantidade x Faturamento x Produto")
        
        # Este gráfico mostra a correlação positiva que criamos nos dados fictícios
        fig_scat = px.scatter(
            df_filtrado, x="quantidade", y="faturamento", color="categoria", size="faturamento",
            hover_data=["produto"], template="plotly_dark", height=500
        )
        
        st.plotly_chart(fig_scat, width='stretch') 

    # --- Aba 2: Dados e Exportação ---
    with tab2:

        st.subheader("Visualização Tabular")
        st.dataframe(df_filtrado, width='stretch', height=400)         
        st.markdown("### 📥 Área de Exportação")
        
        # Cria duas colunas para os botões de download
        c_exp1, c_exp2 = st.columns(2)
        
        # Botão 1: Download CSV
        with c_exp1:
            
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
            
            # Cria o botão de download
            st.download_button(
                label = "💾 Baixar CSV (Excel)",
                data = csv,
                file_name = "dados_filtrados.csv",
                mime = "text/csv",
                width = 'stretch' 
            )
            
        # Botão 2: Download PDF
        with c_exp2:

            if st.button("📄 Gerar Relatório PDF", width='stretch'): 
                
                with st.spinner("Renderizando PDF..."):
                    
                    pdf_bytes = gera_pdf_report(df_filtrado, total_faturamento, total_qty, avg_ticket)
                    
                    # 4. O botão de download aparece para o usuário clicar
                    st.download_button(
                        label = "⬇️ Clique aqui para Salvar PDF",
                        data = pdf_bytes,
                        file_name = f"Relatorio_Vendas_{date.today()}.pdf",
                        mime = "application/pdf",
                        key = "pdf-download-final" # Chave única para o widget
                    )

    # --- Rodapé da Página Principal ---
    st.markdown("---")
    
    with st.expander("ℹ️ Sobre Esta Data App", expanded=False):
        st.info("Este dashboard combina práticas de visualização e manipulação de dados.")
        st.markdown("""
        **Recursos Integrados:**
        - **Engine:** Python + Streamlit + SQLite.
        - **Visualização:** Plotly Express e tema Dark no Streamlit.
        - **Relatórios:** Geração de PDF com FPDF (compatível com Latin-1).
        - **Performance:** Cache de dados (`@st.cache_data`).
        """)


# --- Ponto de Entrada da Execução ---
if __name__ == "__main__":
    layout()