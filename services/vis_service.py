# services/vis_service.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from .db_service import db_service # Importa nosso serviço de banco de dados

def _create_clean_dataframe(psicologa_id: str, paciente_id: str = "Todos"):
    """
    Função helper interna. Busca todos os dados de check-in e os transforma
    em um DataFrame limpo do Pandas, pronto para plotagem.
    (Request 2 e 4: Lógica de filtro "Todos" corrigida)
    """
    
    # 1. Busca dados brutos do DB
    headers, all_rows = db_service.get_all_checkin_data()
    if not headers or not all_rows:
        return pd.DataFrame() # Retorna DF vazio

    # 2. Converte para DataFrame
    df = pd.DataFrame(all_rows, columns=headers)
    
    # 3. Limpeza de Dados
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['sentimento'] = pd.to_numeric(df['sentimento'], errors='coerce')
    df['compartilhado'] = df['compartilhado'].apply(lambda x: str(x).upper() == 'TRUE' or x == True)
    df = df.dropna(subset=['sentimento', 'timestamp'])
    
    # 4. Filtra
    # Primeiro, pega apenas os registros COMPARTILHADOS desta psicóloga
    df_psicologa = df[(df['compartilhado'] == True) & (df['psicologa_id'] == psicologa_id)]
    
    # Se o filtro for "Todos", retorna todos os pacientes da psicóloga
    if paciente_id == "Todos":
        return df_psicologa.sort_values(by='timestamp')
    else:
        # Senão, filtra por aquele paciente específico
        df_paciente = df_psicologa[df_psicologa['paciente_id'] == paciente_id]
        return df_paciente.sort_values(by='timestamp')


def plot_sentiment_trend_paciente(paciente_id):
    """
    Gráfico 1 (Paciente): Tendência Individual (Pontos + Média Móvel)
    """
    # Paciente pode ver seus próprios registros (shared_only=False)
    df = _create_clean_dataframe(paciente_id=paciente_id, shared_only=False, psicologa_id=None) 
    
    if df.empty:
        return None 

    df = df.set_index('timestamp')
    df['media_movel_7d'] = df['sentimento'].rolling('7D').mean()
    df = df.reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['sentimento'], mode='markers', name='Nota Diária',
        marker=dict(color='rgba(0, 150, 255, 0.6)', size=10),
        hovertext=[f"Área: {a}<br>Tópicos: {t}" for a, t in zip(df['area'], df['topicos_selecionados'])],
        hovertemplate="Data: %{x|%d %b %Y}<br>Nota: %{y}<br>%{hovertext}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['media_movel_7d'], mode='lines', name='Média Móvel (7 dias)',
        line=dict(color='rgba(255, 100, 100, 0.9)', width=3)
    ))
    fig.update_layout(title=f"Jornada de Sentimento: {paciente_id}", yaxis_title="Nota (1-5)", template="plotly_white", height=400)
    return fig

# --- FUNÇÕES ATUALIZADAS (Request 3 e 4) ---
def plot_analytics_overview(psicologa_id, paciente_id_filtro):
    """
    Dashboard 1 (Psicóloga): Gera 2 gráficos para a visão geral.
    (Request 4: Gráfico de Tendência Corrigido)
    """
    df = _create_clean_dataframe(psicologa_id=psicologa_id, paciente_id=paciente_id_filtro)
    
    if df.empty:
        return None, None # Retorna 2 Nones

    # --- Gráfico 1: Tendência Geral de Sentimento (CORRIGIDO) ---
    # MUDANÇA: 'W' (Semanal) para 'D' (Diário) para evitar gráfico vazio
    df_resampled = df.set_index('timestamp')['sentimento'].resample('D').mean().reset_index()
    
    fig_trend = px.line(
        df_resampled, 
        x='timestamp', 
        y='sentimento', 
        title=f"Média de Sentimento Diária ({paciente_id_filtro})"
    )
    fig_trend.update_layout(template="plotly_white", height=350, yaxis_title="Média de Nota (1-5)")

    # --- Gráfico 2: Áreas de Foco (Onde as notas são baixas) ---
    df_low_scores = df[df['sentimento'] <= 2]
    areas_count = df_low_scores['area'].value_counts().reset_index()
    
    fig_areas = px.bar(
        areas_count, 
        x='area', 
        y='count', 
        title=f"Áreas com Notas Baixas (1 ou 2) ({paciente_id_filtro})"
    )
    fig_areas.update_layout(template="plotly_white", height=350, yaxis_title="Nº de Registros Baixos", xaxis_title="Área")
    
    return fig_trend, fig_areas

def plot_analytics_ia(psicologa_id, paciente_id_filtro):
    """
    Dashboard 2 (Psicóloga): Gera 2 gráficos de análise de IA.
    """
    df = _create_clean_dataframe(psicologa_id=psicologa_id, paciente_id=paciente_id_filtro)
    
    if df.empty:
        return None, None # Retorna 2 Nones

    # --- Gráfico 1: Temas Mais Comuns (Baseado na IA) ---
    temas = df['temas_gemini'].str.split(', ').explode().str.strip()
    temas_count = temas[temas != ''].value_counts().head(10).reset_index()
    
    fig_temas = px.bar(
        temas_count, 
        x='count', 
        y='temas_gemini', 
        orientation='h', 
        title=f"Top 10 Temas (IA) ({paciente_id_filtro})"
    )
    fig_temas.update_layout(template="plotly_white", height=350, yaxis_title=None, xaxis_title="Contagem")
    fig_temas.update_yaxes(autorange="reversed")

    # --- Gráfico 2: Sentimentos Mais Comuns (Baseado na IA) ---
    sentimentos_ia_count = df['sentimento_texto'].value_counts().reset_index()
    
    fig_sentimentos_ia = px.pie(
        sentimentos_ia_count, 
        names='sentimento_texto', 
        values='count', 
        title=f"Sentimentos Detectados (IA) ({paciente_id_filtro})"
    )
    fig_sentimentos_ia.update_layout(template="plotly_white", height=350)
    
    return fig_temas, fig_sentimentos_ia