# services/vis_service.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from .db_service import db_service # Importa nosso serviço de banco de dados

def _create_clean_dataframe(paciente_id=None, shared_only=True):
    """
    Função helper interna. Busca todos os dados de check-in e os transforma
    em um DataFrame limpo do Pandas, pronto para plotagem.
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
    
    # Converte 'TRUE'/'FALSE' (strings do DB) para Booleanos
    df['compartilhado'] = df['compartilhado'].apply(lambda x: str(x).upper() == 'TRUE' or x == True)
    
    df = df.dropna(subset=['sentimento', 'timestamp'])
    
    # 4. Filtra (se necessário)
    if shared_only:
        df = df[df['compartilhado'] == True]
        
    if paciente_id:
        df = df[df['paciente_id'] == paciente_id]

    return df.sort_values(by='timestamp')


def plot_sentiment_trend_paciente(paciente_id):
    """
    Dashboard 1: Gráfico de Tendência Individual (Pontos + Média Móvel)
    """
    df = _create_clean_dataframe(paciente_id=paciente_id, shared_only=False) # Paciente pode ver tudo
    
    if df.empty:
        return None # Retorna None se não houver dados

    # Calcula a Média Móvel
    df = df.set_index('timestamp')
    df['media_movel_7d'] = df['sentimento'].rolling('7D').mean()
    df = df.reset_index()

    # Cria o Gráfico Plotly (go)
    fig = go.Figure()

    # Adiciona os pontos de dados brutos (Sentimento Diário)
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['sentimento'], 
        mode='markers',
        name='Nota Diária',
        marker=dict(color='rgba(0, 150, 255, 0.6)', size=10),
        hovertext=[f"Área: {a}<br>Tópicos: {t}" for a, t in zip(df['area'], df['topicos_selecionados'])],
        hovertemplate="Data: %{x|%d %b %Y}<br>Nota: %{y}<br>%{hovertext}<extra></extra>"
    ))

    # Adiciona a linha de média móvel
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['media_movel_7d'], 
        mode='lines',
        name='Média Móvel (7 dias)',
        line=dict(color='rgba(255, 100, 100, 0.9)', width=3)
    ))

    fig.update_layout(
        title=f"Jornada de Sentimento: {paciente_id}",
        xaxis_title="Data",
        yaxis_title="Nota de Sentimento (1-5)",
        template="plotly_white",
        height=400
    )
    return fig

def plot_analytics_psicologa(psicologa_id):
    """
    Dashboard 2 (Psicóloga): Gera 3 gráficos para a visão geral.
    """
    df_geral = _create_clean_dataframe(shared_only=True)
    
    # Filtra apenas os pacientes desta psicóloga
    df = df_geral[df_geral['psicologa_id'] == psicologa_id]
    
    if df.empty:
        return None, None, None # Retorna 3 Nones

    # --- Gráfico 1: Tendência Geral de Sentimento (Média da Clínica) ---
    df_resampled = df.set_index('timestamp')['sentimento'].resample('W').mean().reset_index()
    
    fig_trend = px.line(
        df_resampled, 
        x='timestamp', 
        y='sentimento', 
        title="Média de Sentimento (Semanal, Todos Pacientes)"
    )
    fig_trend.update_layout(template="plotly_white", height=350, yaxis_title="Média de Nota (1-5)")

    # --- Gráfico 2: Áreas de Foco (Onde as notas são baixas) ---
    df_low_scores = df[df['sentimento'] <= 2]
    areas_count = df_low_scores['area'].value_counts().reset_index()
    
    fig_areas = px.bar(
        areas_count, 
        x='area', 
        y='count', 
        title="Áreas com Notas Baixas (1 ou 2)"
    )
    fig_areas.update_layout(template="plotly_white", height=350, yaxis_title="Nº de Registros Baixos", xaxis_title="Área")

    # --- Gráfico 3: Temas Mais Comuns (Baseado na IA) ---
    # Limpa e explode a coluna de temas
    temas = df['temas_gemini'].str.split(', ').explode().str.strip()
    temas_count = temas[temas != ''].value_counts().head(10).reset_index()
    
    fig_temas = px.bar(
        temas_count, 
        x='count', 
        y='temas_gemini', 
        orientation='h', 
        title="Top 10 Temas (Detectados pela IA)"
    )
    fig_temas.update_layout(template="plotly_white", height=350, yaxis_title=None, xaxis_title="Contagem")
    fig_temas.update_yaxes(autorange="reversed")
    
    return fig_trend, fig_areas, fig_temas