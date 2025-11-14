# app.py (Corrigido o NameError e o ValueError: expected 8, got 10)
import gradio as gr
import os
import time
from services.ai_service import ai_service
from services.db_service import db_service
from services.vis_service import (
    plot_sentiment_trend_paciente, 
    plot_analytics_overview, 
    plot_analytics_ia,
    plot_analytics_area,
    create_clean_dataframe
)
from models.schemas import CheckinContext, DrilldownRequest, CheckinFinal, GeminiResponse
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from babel.dates import format_datetime 
import locale 

# --- Configuração de Local (Request 5) ---
LOCALE = 'pt_BR'
print(f"Usando Local (Babel) para datas: {LOCALE}")

# --- Lista de Áreas (Alfabética) ---
areas_de_vida = [
    "Acadêmica: Estudo, aprendizado, evolução.",
    "Amoroso: Parceria, afeto, intimidade.",
    "Cognitiva: Foco, memória, clareza.",
    "Emoções: Gestão, sentimentos, equilíbrio.",
    "Espiritualidade: Conexão, paz, propósito.",
    "Família: Harmonia, diálogo, vínculos.",
    "Financeiro: Renda, controle, poupança.",
    "Física: Energia, saúde, disposição.",
    "Hobbies: Prazer, diversão, lazer.",
    "Plenitude: Gratidão, felicidade, contentamento.",
    "Realização: Propósito, satisfação, reconhecimento.",
    "Social: Amizades, convívio, conexões."
]

# Variável Global: Lista de Psicólogas
print("Carregando lista de psicólogas (na inicialização)...")
LISTA_DE_PSICOLOGAS_CHOICES = db_service.get_psicologas_list_for_signup() 
print(f"Lista de psicólogas carregada: {LISTA_DE_PSICOLOGAS_CHOICES}")


# --- Funções de Lógica ---

def formatar_data(dt_obj):
    if dt_obj is None:
        return "Data inválida"
    try:
        return format_datetime(dt_obj, "EEEE, d 'de' MMMM, 'às' HH'h'mm", locale=LOCALE)
    except Exception as e:
        print(f"Erro ao formatar data: {e}")
        return str(dt_obj) 

def fn_toggle_signup_form(is_novo_usuario_check):
    return gr.update(visible=is_novo_usuario_check), gr.update(visible=is_novo_usuario_check)

def fn_login(username, password):
    if not username or not password:
        return None, gr.update(value="Usuário ou senha não podem estar em branco.", visible=True)
    login_valido, role, psicologa_associada = db_service.check_user(username, password)
    if login_valido:
        user_data = {"username": username, "role": role, "psicologa_associada": psicologa_associada}
        return user_data, gr.update(value="", visible=False)
    else:
        return None, gr.update(value="Login falhou. Verifique seu usuário e senha.", visible=True)

def fn_handle_role(user_data, request: gr.Request):
    if not user_data: 
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), \
               gr.update(value=""), gr.update(choices=LISTA_DE_PSICOLOGAS_CHOICES), gr.update(choices=[]), gr.update(choices=["Todos"])
    role = user_data.get("role")
    if role == "Paciente":
        psicologa_associada = user_data.get("psicologa_associada", "Nenhuma")
        print(f"Mostrando UI de Paciente para {user_data.get('username')}")
        return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), \
               gr.update(value=psicologa_associada), gr.update(choices=[]), gr.update(choices=[]), gr.update(choices=["Todos"])
    elif role == "Psicóloga":
        print(f"Mostrando UI de Psicóloga para {user_data.get('username')}")
        lista_pacientes = db_service.get_pacientes_da_psicologa(user_data.get("username"))
        lista_filtro_pacientes = ["Todos"] + lista_pacientes
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), \
               gr.update(value="N/A"), gr.update(choices=lista_pacientes), gr.update(choices=lista_pacientes), gr.update(choices=lista_filtro_pacientes)
    else: # Fallback
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), \
               gr.update(value=""), gr.update(choices=LISTA_DE_PSICOLOGAS_CHOICES), gr.update(choices=[]), gr.update(choices=["Todos"])

def fn_create_user(username, password, psicologa_selecionada):
    success, message = db_service.create_user(username, password, psicologa_selecionada)
    return gr.update(value=message, visible=True)

# --- Funções do Paciente (Omitidas para brevidade, sem alterações) ---
async def fn_get_suggestions_paciente(area, sentimento_float):
    try:
        contexto_data = CheckinContext(area=area, sentimento=sentimento_float)
        response_data = await ai_service.get_suggestions(contexto_data)
        sugestoes = response_data.get("sugestoes", [])
        return (
            gr.update(choices=sugestoes, value=None, visible=True), 
            gr.update(visible=True), gr.update(visible=False), 
            gr.update(visible=False), gr.update(visible=False) 
        )
    except Exception as e:
        print(f"Erro ao chamar ai_service.get_suggestions: {e}")
        return (
            gr.update(choices=[], value=None, visible=False), gr.update(visible=False),
            gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
        )
async def fn_get_drilldown_paciente(topicos_selecionados):
    if not topicos_selecionados:
        return gr.update(visible=False), gr.update(label="Meu Diário"), gr.update(value=None), gr.update(visible=False), gr.update(visible=False)
    primeiro_topico = topicos_selecionados[0]
    try:
        request_data = DrilldownRequest(topico_selecionado=primeiro_topico)
        response_data = await ai_service.get_drilldown_questions(request_data)
        perguntas = response_data.get("perguntas", [])
        markdown_text = "### Pontos-chave para detalhar:\n" + "\n".join(f"* {p}" for p in perguntas)
        return gr.update(visible=True), gr.update(label=f"Sobre: '{primeiro_topico}'"), gr.update(value=markdown_text), gr.update(visible=True), gr.update(visible=True)
    except Exception as e:
        return gr.update(visible=False), gr.update(label="Meu Diário"), gr.update(value=None), gr.update(visible=False), gr.update(visible=False)
def fn_update_diario_from_outro(outro_topico_texto):
    if not outro_topico_texto:
        return (
            gr.update(visible=False), gr.update(label="Meu Diário"), 
            gr.update(value=""), gr.update(visible=False), gr.update(visible=False)
        )
    markdown_text = "### Pontos-chave para detalhar:\n(Descreva seu tópico acima)"
    return (
        gr.update(visible=True), gr.update(label=f"Sobre: '{outro_topico_texto}'"),
        gr.update(value=markdown_text), gr.update(visible=True), gr.update(visible=True)
    )
async def fn_submit_checkin_paciente(user_data_do_state, area, sentimento_float, topicos_selecionados, outro_topico_texto, diaro_texto, compartilhado_bool):
    if not user_data_do_state or "username" not in user_data_do_state:
        return gr.update(value="### ❌ Erro: Usuário não autenticado.", visible=True), gr.update(visible=False)
    paciente_id = user_data_do_state["username"]
    role = user_data_do_state["role"]
    psicologa_id = user_data_do_state["psicologa_associada"] if role == "Paciente" else user_data_do_state["username"]
    if not psicologa_id: psicologa_id = "N/A" 
    try:
        topicos_finais = topicos_selecionados
        diario_para_salvar = diaro_texto
        diario_para_analise = diaro_texto
        if outro_topico_texto:
            topicos_finais.append(f"Outro: {outro_topico_texto}")
            diario_para_analise = f"Tópico principal escrito pelo usuário: {outro_topico_texto}.\n\nDiário: {diaro_texto}"
        checkin_data = CheckinFinal(area=area, sentimento=sentimento_float,
                                    topicos_selecionados=topicos_finais, diario_texto=diario_para_salvar)
        gemini_data = await ai_service.process_final_checkin(checkin_data, diario_para_analise)
        db_service.write_checkin(checkin_data, gemini_data, paciente_id, psicologa_id, compartilhado_bool)
        msg = f"Check-in de {paciente_id} salvo com sucesso!"
        if compartilhado_bool:
            msg_compartilhado = f"Este registro **foi compartilhado** com {psicologa_id}."
        else:
            msg_compartilhado = "Este registro **NÃO** foi compartilhado (privado)."
        feedback = f"""
        ### ✅ {msg}
        **Status:** {msg_compartilhado}
        **Insight Rápido:** {gemini_data.insight}
        ---
        **Uma Pequena Ação para Agora:** {gemini_data.acao}
        ---
        **Síntese acrescentada ao registro:**
        * **Sentimento Detectado no Texto:** {gemini_data.sentimento_texto}
        * **Temas Principais:** {", ".join(gemini_data.temas)}
        * **Resumo:** {gemini_data.resumo}
        """
        return gr.update(value=feedback, visible=True), gr.update(visible=True)
    except Exception as e:
        print(f"Erro no fn_submit_checkin: {e}")
        return gr.update(value=f"Erro ao processar o check-in: {e}", visible=True), gr.update(visible=False)
def fn_delete_last_record_paciente(user_data_do_state):
    if not user_data_do_state: return gr.update(visible=False), gr.update(value="Erro: Usuário não logado.")
    paciente_id = user_data_do_state["username"]
    db_service.delete_last_record(paciente_id)
    return gr.update(visible=False), gr.update(value="### ✅ Registro descartado com sucesso.", visible=True)
def fn_load_history_paciente(user_data_do_state):
    if not user_data_do_state: 
        return None, gr.update(value=None), gr.update(value="Erro: Usuário não logado.", visible=True)
    
    paciente_id = user_data_do_state["username"]
    
    fig = plot_sentiment_trend_paciente(paciente_id) 
    
    if fig is None:
         return None, gr.update(value=None), gr.update(value="Nenhum histórico encontrado para este usuário.", visible=True)
         
    headers, all_rows = db_service.get_all_checkin_data()
    id_col_index = headers.index('paciente_id')
    user_history_rows = [row for row in all_rows if len(row) > id_col_index and row[id_col_index] == paciente_id]
    user_history_rows.reverse() 
    
    colunas_db = ['timestamp', 'area', 'sentimento', 'topicos_selecionados', 'diario_texto', 'insight_ia', 'acao_proposta', 'sentimento_texto', 'temas_gemini', 'resumo_psicologa', 'psicologa_id', 'compartilhado']
    
    try:
        col_indices = [headers.index(col) for col in colunas_db]
    except ValueError as e:
        return None, gr.update(value=None), gr.update(value=f"Erro: A coluna {e} não foi encontrada.", visible=True)
        
    display_data = [[row[i] for i in col_indices] for row in user_history_rows[:20]]
    
    try:
        timestamp_index = colunas_db.index('timestamp')
        compartilhado_index = colunas_db.index('compartilhado')
        
        for row in display_data:
            row[timestamp_index] = formatar_data(row[timestamp_index]) 
            row[compartilhado_index] = "✅ Sim" if row[compartilhado_index] else "❌ Não"
            
    except Exception as e:
        print(f"Erro ao formatar dados da tabela: {e}")
        
    return fig, gr.update(value=display_data, visible=True), gr.update(visible=False) # [Gráfico, Tabela, Msg]
def fn_load_recados_paciente(user_data_do_state):
    if not user_data_do_state: return gr.update(value=None), gr.update(value="Erro: Usuário não logado.", visible=True)
    paciente_id = user_data_do_state["username"]
    headers, recados = db_service.get_recados_paciente(paciente_id)
    if not recados:
        return gr.update(value=None), gr.update(value="Nenhum recado encontrado.", visible=True)
    colunas_db = ['timestamp', 'psicologa_id', 'mensagem_texto']
    try:
        col_indices = [headers.index(col) for col in colunas_db]
    except ValueError as e:
        return gr.update(value=None), gr.update(value=f"Erro: A coluna {e} não foi encontrada.", visible=True)
    display_data = [[row[i] for i in col_indices] for row in recados]
    try:
        timestamp_index = colunas_db.index('timestamp')
        for row in display_data:
            row[timestamp_index] = formatar_data(row[timestamp_index])
    except Exception as e:
         print(f"Erro ao formatar datas dos recados: {e}")
    return gr.update(value=display_data, visible=True), gr.update(visible=False)

# --- Funções da Psicóloga ---
async def fn_load_analytics_psicologa(user_data_do_state, paciente_id_filtro):
    if not user_data_do_state: 
        return None, None, None, None, None, None, None, gr.update(value="Erro: Usuário não logado.", visible=True)
    psicologa_id = user_data_do_state.get("username")
    fig_trend, fig_areas = plot_analytics_overview(psicologa_id, paciente_id_filtro)
    fig_temas, fig_sentimentos_ia = plot_analytics_ia(psicologa_id, paciente_id_filtro)
    fig_boxplot, fig_heatmap = plot_analytics_area(psicologa_id, paciente_id_filtro)
    if fig_trend is None:
        msg = "Nenhum dado compartilhado encontrado para gerar análises."
        return None, None, None, None, None, None, None, gr.update(value=msg, visible=True)
    df_para_resumo = create_clean_dataframe(psicologa_id=psicologa_id, paciente_id=paciente_id_filtro)
    resumo_evolucao = await ai_service.get_analytics_summary(df_para_resumo, paciente_id_filtro, "evolucao")
    resumo_temas = await ai_service.get_analytics_summary(df_para_resumo, paciente_id_filtro, "temas_ia")
    resumo_desempenho = await ai_service.get_analytics_summary(df_para_resumo, paciente_id_filtro, "desempenho")
    return fig_trend, fig_areas, fig_temas, fig_sentimentos_ia, fig_boxplot, fig_heatmap, gr.update(value=resumo_evolucao, visible=True), gr.update(value=resumo_temas, visible=True), gr.update(value=resumo_desempenho, visible=True), gr.update(visible=False) # 10 outputs
def fn_load_history_psicologa(paciente_selecionado):
    if not paciente_selecionado or "Nenhum" in paciente_selecionado:
        return gr.update(value=None), gr.update(value=None), gr.update(value="Por favor, selecione um paciente.", visible=True)
    print(f"Psicóloga carregando histórico de: {paciente_selecionado}")
    headers_checkin, all_rows_checkin = db_service.get_all_checkin_data()
    if not headers_checkin:
        return gr.update(value=None), gr.update(value=None), gr.update(value="Nenhum dado encontrado.", visible=True)
    try:
        id_col_index = headers_checkin.index('paciente_id')
        share_col_index = headers_checkin.index('compartilhado')
    except ValueError as e:
        return gr.update(value=None), gr.update(value=None), gr.update(value=f"Erro: A coluna {e} não foi encontrada.", visible=True)
    paciente_history = [
        row for row in all_rows_checkin 
        if len(row) > id_col_index and len(row) > share_col_index
        and row[id_col_index] == paciente_selecionado
        and row[share_col_index] == True 
    ]
    if not paciente_history:
        return gr.update(value=None), gr.update(value=None), gr.update(value=f"Nenhum registro *compartilhado* encontrado para {paciente_selecionado}.", visible=True)
    paciente_history.reverse()
    colunas_db = ['timestamp', 'area', 'sentimento', 'topicos_selecionados', 'diario_texto', 'sentimento_texto', 'temas_gemini', 'resumo_psicologa']
    try:
        col_indices_checkin = [headers_checkin.index(col) for col in colunas_db]
    except ValueError as e:
        return gr.update(value=None), gr.update(value=None), gr.update(value=f"Erro: A coluna {e} não foi encontrada.", visible=True)
    display_data_checkin = [[row[i] for i in col_indices_checkin] for row in paciente_history[:50]]
    try:
        timestamp_index_checkin = colunas_db.index('timestamp')
        for row in display_data_checkin:
            row[timestamp_index_checkin] = formatar_data(row[timestamp_index_checkin])
    except Exception as e:
        print(f"Erro ao formatar datas de checkin: {e}")
    headers_recados, recados_rows = db_service.get_recados_paciente(paciente_selecionado)
    display_data_recados = []
    if recados_rows:
        colunas_db_recados = ['timestamp', 'psicologa_id', 'mensagem_texto']
        col_indices_recados = [headers_recados.index(col) for col in colunas_db_recados]
        display_data_recados = [[row[i] for i in col_indices_recados] for row in recados_rows]
        try:
            timestamp_index_recados = colunas_db_recados.index('timestamp')
            for row in display_data_recados:
                row[timestamp_index_recados] = formatar_data(row[timestamp_index_recados])
        except Exception as e:
            print(f"Erro ao formatar datas de recados: {e}")
    return gr.update(value=display_data_checkin, visible=True), gr.update(value=display_data_recados, visible=True), gr.update(visible=False)
def fn_populate_registros_dropdown(paciente_selecionado):
    if not paciente_selecionado or "Nenhum" in paciente_selecionado:
        return gr.update(choices=[], value=None)
    choices = db_service.get_checkin_list_for_paciente(paciente_selecionado)
    return gr.update(choices=choices, value=None)
def fn_load_diario_psicologa(checkin_id):
    if not checkin_id:
        return gr.update(value=""), gr.update(value="Selecione um registro da lista acima.", visible=True)
    diario, msg = db_service.get_diario_by_checkin_id(checkin_id)
    if not diario:
        return gr.update(value=""), gr.update(value=msg, visible=True)
    return gr.update(value=diario), gr.update(visible=False)
async def fn_gerar_sugestao_recado_psicologa(diario_do_paciente, rascunho_atual):
    if not diario_do_paciente:
        return gr.update(value="Carregue o diário do paciente primeiro.")
    try:
        response_data = await ai_service.get_sugestao_recado_psicologa(diario_do_paciente, rascunho_atual)
        return gr.update(value=response_data["recado"]) 
    except Exception as e:
        print(f"Erro na fn_gerar_sugestao_recado: {e}")
        return gr.update(value=f"Erro: {e}")
def fn_send_recado_psicologa(user_data_do_state, paciente_selecionado, mensagem_texto):
    if not user_data_do_state or "username" not in user_data_do_state:
        return gr.update(value="Erro: Usuário não autenticado.", visible=True)
    if not paciente_selecionado or "Nenhum" in paciente_selecionado:
        return gr.update(value="Erro: Selecione um paciente.", visible=True)
    if not mensagem_texto:
        return gr.update(value="Erro: A mensagem não pode estar vazia.", visible=True)
    psicologa_id = user_data_do_state["username"]
    success, message = db_service.send_recado(psicologa_id, paciente_selecionado, mensagem_texto)
    if success:
        return gr.update(value=message, visible=True)
    else:
        return gr.update(value=f"Erro: {message}", visible=True)

# --- Interface Gráfica (Gradio Blocks) ---
with gr.Blocks(
    theme=gr.themes.Default(), 
    title="Terap.ia - Painel Clínico",
    css="body, .gradio-container, .gradio-container * {font-size: 16px !important;}"
) as app: 
    
    state_user = gr.State(None)
    gr.Markdown("# 🧠 Terap.ia - Painel Clínico")
    
    with gr.Row(visible=True) as login_view:
        with gr.Column(): 
            gr.Markdown("Por favor, faça o login para continuar ou crie um novo usuário.")
            in_login_username = gr.Textbox(label="Usuário", placeholder="Ex: marcelo")
            in_login_password = gr.Textbox(label="Senha", type="password", placeholder="Ex: senha123")
            btn_login = gr.Button("Entrar", variant="primary")
            chk_novo_usuario = gr.Checkbox(label="Sou novo usuário", value=False)
            in_signup_psicologa = gr.Dropdown(
                label="Selecione sua Psicóloga",
                choices=LISTA_DE_PSICOLOGAS_CHOICES, 
                visible=False
            )
            btn_create_user = gr.Button("Criar novo usuário", variant="secondary", visible=False)
            out_login_message = gr.Markdown(visible=False, value="", elem_classes=["error"])

    # --- VISÃO DO PACIENTE (Começa Oculta) ---
    with gr.Row(visible=False) as paciente_view:
        with gr.Tabs() as paciente_tabs:
            with gr.Tab("Fazer Check-in", id=0) as checkin_tab_paciente:
                in_psicologa_nome = gr.Textbox(label="Sua Psicóloga Vinculada", interactive=False, visible=True)
                gr.Markdown("Faça seu check-in diário...")
                with gr.Row():
                    with gr.Column(scale=1):
                        in_area_paciente = gr.Dropdown(choices=areas_de_vida, label="Sobre qual área?", value=areas_de_vida[0])
                        in_sentimento_paciente = gr.Slider(1, 5, step=1, label="Como você avalia essa área HOJE?", value=3)
                        btn_reload_paciente = gr.Button("Atualizar Sugestões (IA)", variant="secondary")
                    with gr.Column(scale=2):
                        out_sugestoes_paciente = gr.CheckboxGroup(label="O que aconteceu? (IA Nível 1)", visible=False)
                        in_outro_topico_paciente = gr.Textbox(label="Outro tópico (opcional)", visible=False)
                with gr.Row(visible=False) as components_n3_paciente:
                    with gr.Column(scale=2):
                        in_diario_texto_paciente = gr.Textbox(label="Meu Diário", lines=8, visible=True, placeholder="Descreva o que aconteceu...")
                    with gr.Column(scale=1, min_width=200):
                        out_perguntas_chave_paciente = gr.Markdown("### Pontos-chave para detalhar:")
                in_compartilhar_paciente = gr.Checkbox(label="Permitir que minha psicóloga acesse este registro", value=True, visible=False)
                btn_submit_paciente = gr.Button("Registrar Check-in", visible=False)
                out_feedback_paciente = gr.Markdown(visible=False)
                btn_discard_paciente = gr.Button("Prefiro descartar este registro/não acrescentar no histórico", variant="secondary", visible=False)

            with gr.Tab("Meu Histórico", id=1) as history_tab_paciente:
                gr.Markdown("## Seu Histórico e Tendência")
                out_history_plot_paciente = gr.Plot(label="Tendência de Sentimento", visible=True) 
                btn_load_history_paciente = gr.Button("Carregar meu histórico")
                out_history_message_paciente = gr.Markdown(visible=False)
                out_history_df_paciente = gr.DataFrame(
                    label="Detalhes dos Registros", 
                    visible=False, wrap=True,
                    headers=["Data", "Área", "Nota (1-5)", "Tópicos Selecionados", "Meu Diário", "Insight", "Ação", "Sentimento (IA)", "Temas (IA)", "Resumo", "Psicóloga", "Compartilhado?"]
                )

            with gr.Tab("Recados da Psicóloga", id=2) as recados_tab_paciente:
                gr.Markdown("Veja os últimos recados enviados pela sua psicóloga.")
                btn_load_recados_paciente = gr.Button("Verificar novos recados")
                out_recados_message_paciente = gr.Markdown(visible=False)
                out_recados_df_paciente = gr.DataFrame(label="Seus Recados", visible=False, wrap=True, headers=["Data", "De", "Mensagem"])

    # --- VISÃO DA PSICÓLOGA (Começa Oculta) ---
    with gr.Row(visible=False) as psicologa_view:
        
        # --- MUDANÇA (Layout Regressivo): Componentes de filtro movidos para dentro da aba ---
        
        with gr.Tabs() as psicologa_tabs:
            
            with gr.Tab("Tendências e Evolução", id=0) as analytics_tab_psicologa:
                gr.Markdown("## Dashboard de Análise de Pacientes")
                with gr.Row():
                    in_paciente_dropdown_analytics = gr.Dropdown(label="Filtrar Paciente (para Gráficos)", choices=["Todos"], value="Todos")
                    btn_load_analytics = gr.Button("Carregar Gráficos (Analytics)")
                out_analytics_summary_evolucao = gr.Markdown(visible=False) # <-- MUDANÇA (Request 1)
                out_analytics_message = gr.Markdown(visible=False)
                with gr.Row():
                    out_analytics_plot_trend = gr.Plot(label="Tendência Geral (Diária)")
                    out_analytics_plot_areas = gr.Plot(label="Áreas de Atenção")

            with gr.Tab("Temas e Sentimentos (IA)", id=1):
                gr.Markdown("## Análises de Tópicos e Sentimentos (IA)")
                out_analytics_summary_temas = gr.Markdown(visible=False) # <-- MUDANÇA (Request 3)
                with gr.Row():
                    out_analytics_plot_temas = gr.Plot(label="Temas Comuns (IA)")
                    out_analytics_plot_sentimentos = gr.Plot(label="Sentimentos Detectados (IA)")

            with gr.Tab("Desempenho por Área", id=2):
                gr.Markdown("## Análise de Desempenho e Atividade")
                out_analytics_summary_desempenho = gr.Markdown(visible=False) # <-- MUDANÇA (Request 3)
                with gr.Row():
                    out_analytics_plot_boxplot = gr.Plot(label="Distribuição de Notas por Área")
                    out_analytics_plot_heatmap = gr.Plot(label="Horários de Atividade")

            with gr.Tab("Ver Histórico (Tabela)", id=3) as history_tab_psicologa:
                gr.Markdown("Selecione um paciente para ver seu histórico de check-ins (apenas registros compartilhados).")
                in_paciente_dropdown_hist = gr.Dropdown(label="Selecione um Paciente", choices=["Carregando..."])
                btn_load_history_psicologa = gr.Button("Carregar Histórico do Paciente")
                out_history_message_psicologa = gr.Markdown(visible=False)
                out_history_df_psicologa = gr.DataFrame(
                    label="Registros de Check-in", 
                    visible=False, wrap=True,
                    headers=["Data", "Área", "Nota (1-5)", "Tópicos", "Diário do Paciente", "Sentimento (IA)", "Temas (IA)", "Resumo (IA)"]
                )
                gr.Markdown("### Recados Enviados para este Paciente")
                out_recados_df_psicologa = gr.DataFrame(label="Recados Enviados", visible=True, wrap=True, headers=["Data", "De", "Mensagem"])

            with gr.Tab("Enviar Recado", id=4) as recado_tab_psicologa:
                in_paciente_dropdown_reg = gr.Dropdown(label="Selecione um Paciente", choices=["Carregando..."])
                in_registro_dropdown_recado = gr.Dropdown(label="Selecione um Registro como Base", choices=["Selecione um paciente primeiro..."], interactive=True)
                out_diario_paciente_para_recado = gr.Textbox(label="Diário do Paciente (Base)", lines=5, interactive=False, visible=True)
                out_diario_paciente_msg = gr.Markdown(visible=False)
                gr.Markdown("Escreva seu recado abaixo ou complemente a sugestão da IA.")
                in_recado_texto = gr.Textbox(label="Seu Recado para o Paciente", lines=3)
                with gr.Row():
                    btn_gerar_sugestao_recado = gr.Button("Complementar o texto (IA)")
                    btn_enviar_recado = gr.Button("Enviar Recado", variant="primary")
                out_feedback_recado_psicologa = gr.Markdown(visible=False)

    # --- Conexões (Event Listeners) ---
    
    chk_novo_usuario.change(
        fn=fn_toggle_signup_form,
        inputs=[chk_novo_usuario],
        outputs=[in_signup_psicologa, btn_create_user],
        show_progress="minimal" 
    )
    
    btn_create_user.click(
        fn=fn_create_user,
        inputs=[in_login_username, in_login_password, in_signup_psicologa],
        outputs=[out_login_message],
        show_progress="minimal" 
    )
    
    btn_login.click(
        fn=fn_login,
        inputs=[in_login_username, in_login_password],
        outputs=[state_user, out_login_message],
        show_progress="minimal" 
    )
    
    state_user.change(
        fn=fn_handle_role,
        inputs=[state_user],
        outputs=[
            login_view,
            paciente_view, 
            psicologa_view, 
            in_psicologa_nome, 
            in_paciente_dropdown_hist, 
            in_paciente_dropdown_reg,
            in_paciente_dropdown_analytics
        ],
        show_progress="minimal" 
    )
    
    # --- Conexões do Paciente ---
    in_sentimento_paciente.release(
        fn=fn_get_suggestions_paciente,
        inputs=[in_area_paciente, in_sentimento_paciente], 
        outputs=[
            out_sugestoes_paciente, in_outro_topico_paciente, components_n3_paciente, 
            btn_submit_paciente, out_feedback_paciente
        ],
        show_progress="full"
    )
    btn_reload_paciente.click(
        fn=fn_get_suggestions_paciente,
        inputs=[in_area_paciente, in_sentimento_paciente],
        outputs=[
            out_sugestoes_paciente, in_outro_topico_paciente, components_n3_paciente, 
            btn_submit_paciente, out_feedback_paciente
        ],
        show_progress="full"
    )
    out_sugestoes_paciente.select(
        fn=fn_get_drilldown_paciente,
        inputs=[out_sugestoes_paciente],
        outputs=[
            components_n3_paciente, in_diario_texto_paciente, 
            out_perguntas_chave_paciente, btn_submit_paciente,
            in_compartilhar_paciente
        ],
        show_progress="minimal" 
    )
    
    in_outro_topico_paciente.submit(
        fn=fn_update_diario_from_outro,
        inputs=[in_outro_topico_paciente], 
        outputs=[
            components_n3_paciente, 
            in_diario_texto_paciente, 
            out_perguntas_chave_paciente, 
            btn_submit_paciente,
            in_compartilhar_paciente
        ],
        show_progress="minimal" 
    )
    
    btn_submit_paciente.click(
        fn=fn_submit_checkin_paciente,
        inputs=[
            state_user, in_area_paciente, in_sentimento_paciente, 
            out_sugestoes_paciente, in_outro_topico_paciente, in_diario_texto_paciente,
            in_compartilhar_paciente
        ],
        outputs=[out_feedback_paciente, btn_discard_paciente],
        show_progress="full"
    )
    btn_discard_paciente.click(
        fn=fn_delete_last_record_paciente,
        inputs=[state_user],
        outputs=[btn_discard_paciente, out_feedback_paciente],
        show_progress="minimal" 
    )
    btn_load_history_paciente.click(
        fn=fn_load_history_paciente,
        inputs=[state_user],
        outputs=[out_history_plot_paciente, out_history_df_paciente, out_history_message_paciente],
        show_progress="full"
    )
    btn_load_recados_paciente.click(
        fn=fn_load_recados_paciente,
        inputs=[state_user],
        outputs=[out_recados_df_paciente, out_recados_message_paciente],
        show_progress="full"
    )

    # --- Conexões da Psicóloga ---
    
    # --- MUDANÇA (ValueError Fix): Retornando 10 valores ---
    btn_load_analytics.click(
        fn=fn_load_analytics_psicologa,
        inputs=[state_user, in_paciente_dropdown_analytics],
        outputs=[
            out_analytics_plot_trend,
            out_analytics_plot_areas,
            out_analytics_plot_temas,
            out_analytics_plot_sentimentos,
            out_analytics_plot_boxplot, 
            out_analytics_plot_heatmap, 
            out_analytics_summary_evolucao,   # <-- MUDANÇA
            out_analytics_summary_temas,      # <-- MUDANÇA
            out_analytics_summary_desempenho, # <-- MUDANÇA
            out_analytics_message
        ],
        show_progress="full"
    )
    
    btn_load_history_psicologa.click(
        fn=fn_load_history_psicologa,
        inputs=[in_paciente_dropdown_hist],
        outputs=[
            out_history_df_psicologa, 
            out_recados_df_psicologa, 
            out_history_message_psicologa
        ],
        show_progress="full"
    )
    
    in_paciente_dropdown_reg.change(
        fn=fn_populate_registros_dropdown,
        inputs=[in_paciente_dropdown_reg],
        outputs=[in_registro_dropdown_recado],
        show_progress="full"
    )
    in_registro_dropdown_recado.change(
        fn=fn_load_diario_psicologa,
        inputs=[in_registro_dropdown_recado],
        outputs=[out_diario_paciente_para_recado, out_diario_paciente_msg],
        show_progress="full"
    )
    
    btn_gerar_sugestao_recado.click(
        fn=fn_gerar_sugestao_recado_psicologa,
        inputs=[
            out_diario_paciente_para_recado, 
            in_recado_texto
        ],
        outputs=[in_recado_texto],
        show_progress="full"
    )
    btn_enviar_recado.click(
        fn=fn_send_recado_psicologa,
        inputs=[state_user, in_paciente_dropdown_reg, in_recado_texto],
        outputs=[out_feedback_recado_psicologa],
        show_progress="full"
    )

# --- Lançar a Aplicação ---
if __name__ == "__main__":
    app.launch(debug=True)