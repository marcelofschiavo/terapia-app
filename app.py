# app.py (Com Plotly NATIVO, sem Tableau)
import gradio as gr
import os
import time
from services.ai_service import ai_service
from services.db_service import db_service
from services.vis_service import plot_sentiment_trend_paciente, plot_analytics_psicologa # <-- NOVO
from models.schemas import CheckinContext, DrilldownRequest, CheckinFinal, GeminiResponse
import pandas as pd # Mantido para os DataFrames de histórico

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
               gr.update(value=""), gr.update(choices=LISTA_DE_PSICOLOGAS_CHOICES), gr.update(choices=LISTA_DE_PSICOLOGAS_CHOICES)

    role = user_data.get("role")
    
    if role == "Paciente":
        psicologa_associada = user_data.get("psicologa_associada", "Nenhuma")
        print(f"Mostrando UI de Paciente para {user_data.get('username')}")
        return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), \
               gr.update(value=psicologa_associada), gr.update(choices=[], value=None), gr.update(choices=[], value=None)
        
    elif role == "Psicóloga":
        print(f"Mostrando UI de Psicóloga para {user_data.get('username')}")
        lista_pacientes = db_service.get_pacientes_da_psicologa(user_data.get("username"))
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), \
               gr.update(value="N/A"), gr.update(choices=lista_pacientes, value=None), gr.update(choices=lista_pacientes, value=None)
    
    else: # Fallback
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), \
               gr.update(value=""), gr.update(choices=LISTA_DE_PSICOLOGAS_CHOICES), gr.update(choices=LISTA_DE_PSICOLOGAS_CHOICES)

def fn_create_user(username, password, psicologa_selecionada):
    success, message = db_service.create_user(username, password, psicologa_selecionada)
    return gr.update(value=message, visible=True)

# --- Funções do Paciente ---
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

# --- FUNÇÃO ATUALIZADA: Nova função para carregar dados para o Plotly ---
def fn_load_history_paciente(user_data_do_state):
    """Carrega o histórico e o gráfico Plotly para o paciente."""
    if not user_data_do_state: 
        return None, gr.update(value=None), gr.update(value="Erro: Usuário não logado.", visible=True)
    
    paciente_id = user_data_do_state["username"]
    headers, all_rows = db_service.get_all_checkin_data() # Busca todos os checkins
    
    if not headers:
        return None, gr.update(value=None), gr.update(value="Nenhum dado encontrado na planilha.", visible=True)
    
    # 1. GERA O GRÁFICO PLOTLY
    # Filtra os dados (para o paciente)
    id_col_index = headers.index('paciente_id')
    user_history_rows = [row for row in all_rows if len(row) > id_col_index and row[id_col_index] == paciente_id]
    
    if not user_history_rows:
        return None, gr.update(value=None), gr.update(value="Nenhum histórico encontrado para este usuário.", visible=True)
        
    fig, msg_plot = plot_sentiment_trend_paciente(paciente_id) # Usa a função do vis_service
    
    # 2. GERA A TABELA DE DADOS BRUTOS (sem pandas)
    user_history_rows.reverse() # Mais recentes primeiro
    colunas_db = ['timestamp', 'area', 'sentimento', 'topicos_selecionados', 'diario_texto', 'insight_ia', 'acao_proposta', 'sentimento_texto', 'temas_gemini', 'resumo_psicologa', 'psicologa_id', 'compartilhado']
    colunas_display = ["Data", "Área", "Nota (1-5)", "Tópicos Selecionados", "Meu Diário", "Insight", "Ação", "Sentimento (IA)", "Temas (IA)", "Resumo", "Psicóloga", "Compartilhado?"]
    
    try:
        col_indices = [headers.index(col) for col in colunas_db]
    except ValueError as e:
        return None, gr.update(value=None), gr.update(value=f"Erro: A coluna {e} não foi encontrada.", visible=True)
        
    display_data = [[row[i] for i in col_indices] for row in user_history_rows[:20]]
    
    try:
        compartilhado_index = colunas_db.index('compartilhado')
        for row in display_data:
            if row[compartilhado_index]: 
                row[compartilhado_index] = "✅ Sim"
            else:
                row[compartilhado_index] = "❌ Não"
    except Exception as e:
        print(f"Erro ao formatar coluna 'compartilhado': {e}")
        
    return fig, gr.update(value=display_data, visible=True), gr.update(value=msg_plot, visible=bool(msg_plot))

def fn_load_recados_paciente(user_data_do_state):
    # (Sem mudanças)
    if not user_data_do_state: return gr.update(value=None), gr.update(value="Erro: Usuário não logado.", visible=True)
    paciente_id = user_data_do_state["username"]
    headers, recados = db_service.get_recados_paciente(paciente_id)
    if not recados:
        return gr.update(value=None), gr.update(value="Nenhum recado encontrado.", visible=True)
    colunas_db = ['timestamp', 'psicologa_id', 'mensagem_texto']
    colunas_display = ["Data", "De", "Mensagem"]
    try:
        col_indices = [headers.index(col) for col in colunas_db]
    except ValueError as e:
        return gr.update(value=None), gr.update(value=f"Erro: A coluna {e} não foi encontrada.", visible=True)
    display_data = [[row[i] for i in col_indices] for row in recados]
    return gr.update(value=display_data, visible=True), gr.update(visible=False)

# --- Funções da Psicóloga ---
def fn_load_history_psicologa(paciente_selecionado):
    # (Sem mudanças)
    if not paciente_selecionado or "Nenhum" in paciente_selecionado:
        return gr.update(value=None), gr.update(value="Por favor, selecione um paciente.", visible=True)
    print(f"Psicóloga carregando histórico de: {paciente_selecionado}")
    headers, all_rows = db_service.get_all_checkin_data()
    if not headers:
        return gr.update(value=None), gr.update(value="Nenhum dado encontrado.", visible=True)
    try:
        id_col_index = headers.index('paciente_id')
        share_col_index = headers.index('compartilhado')
    except ValueError as e:
        return gr.update(value=None), gr.update(value=f"Erro: A coluna {e} não foi encontrada.", visible=True)
    paciente_history = [
        row for row in all_rows 
        if len(row) > id_col_index and len(row) > share_col_index
        and row[id_col_index] == paciente_selecionado
        and row[share_col_index] == True 
    ]
    if not paciente_history:
        return gr.update(value=None), gr.update(value=f"Nenhum registro *compartilhado* encontrado para {paciente_selecionado}.", visible=True)
    paciente_history.reverse()
    colunas_db = ['timestamp', 'area', 'sentimento', 'topicos_selecionados', 'diario_texto', 'sentimento_texto', 'temas_gemini', 'resumo_psicologa']
    colunas_display = ["Data", "Área", "Nota (1-5)", "Tópicos", "Diário do Paciente", "Sentimento (IA)", "Temas (IA)", "Resumo (IA)"]
    try:
        col_indices = [headers.index(col) for col in colunas_db]
    except ValueError as e:
        return gr.update(value=None), gr.update(value=f"Erro: A coluna {e} não foi encontrada.", visible=True)
    display_data = [[row[i] for i in col_indices] for row in paciente_history[:50]]
    return gr.update(value=display_data, visible=True), gr.update(visible=False)

def fn_load_ultimo_diario_psicologa(paciente_selecionado):
    if not paciente_selecionado or "Nenhum" in paciente_selecionado:
        return gr.update(value=""), gr.update(value="Selecione um paciente para carregar o diário.", visible=True)
    diario, msg = db_service.get_ultimo_diario_paciente(paciente_selecionado)
    if not diario:
        return gr.update(value=""), gr.update(value=msg, visible=True)
    return gr.update(value=diario), gr.update(visible=False)

async def fn_gerar_sugestao_recado_psicologa(diario_do_paciente, rascunho_atual):
    if not diario_do_paciente:
        return gr.update(value="Carregue o diário do paciente primeiro.")
    try:
        response_data = await ai_service.get_sugestao_recado_psicologa(diario_do_paciente, rascunho_atual)
        recado_sugerido = response_data.get("recado", "Não foi possível gerar sugestão.")
        return gr.update(value=recado_sugerido)
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

# --- FUNÇÃO REMOVIDA ---
# def get_tableau_html():
#     pass

# --- Interface Gráfica (Gradio Blocks) ---
with gr.Blocks(
    theme=gr.themes.Default(), 
    css="body, .gradio-container, .gradio-container * {font-size: 16px !important;}"
) as app: 
    
    state_user = gr.State(None)
    gr.Markdown("# 🧠 Painel de Bem-Estar 360°")
    
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
                
                # --- MUDANÇA: Novo Slot para Gráfico Plotly ---
                out_history_plot_paciente = gr.Plot(label="Tendência de Sentimento", visible=False)
                
                btn_load_history_paciente = gr.Button("Carregar meu histórico")
                out_history_message_paciente = gr.Markdown(visible=False)
                out_history_df_paciente = gr.DataFrame(
                    label="Detalhes dos Registros", 
                    visible=False, 
                    wrap=True,
                    headers=["Data", "Área", "Nota (1-5)", "Tópicos Selecionados", "Meu Diário", "Insight", "Ação", "Sentimento (IA)", "Temas (IA)", "Resumo", "Psicóloga", "Compartilhado?"]
                )

            with gr.Tab("Recados da Psicóloga", id=2) as recados_tab_paciente:
                gr.Markdown("Veja os últimos recados enviados pela sua psicóloga.")
                btn_load_recados_paciente = gr.Button("Verificar novos recados")
                out_recados_message_paciente = gr.Markdown(visible=False)
                out_recados_df_paciente = gr.DataFrame(label="Seus Recados", visible=False, wrap=True, headers=["Data", "De", "Mensagem"])

    # --- VISÃO DA PSICÓLOGA (Começa Oculta) ---
    with gr.Row(visible=False) as psicologa_view:
        with gr.Tabs() as psicologa_tabs:
            with gr.Tab("Analytics (Visão Geral)", id=0) as analytics_tab_psicologa:
                # --- MUDANÇA: Substitui Tableau por Mensagem ---
                gr.Markdown("## Dashboard de Análise de Pacientes (Seguro)")
                gr.Markdown("**Acesse o Dashboard completo de Análise e Estatísticas na Planilha de Google Sheets.**\n\n*(Este painel está desativado para garantir a segurança dos dados clínicos no Render)*")
                
            with gr.Tab("Ver Histórico (Paciente)", id=1) as history_tab_psicologa:
                gr.Markdown("Selecione um paciente para ver seu histórico de check-ins (apenas registros compartilhados).")
                in_paciente_dropdown_hist = gr.Dropdown(label="Selecione um Paciente", choices=["Carregando..."])
                btn_load_history_psicologa = gr.Button("Carregar Histórico do Paciente")
                
                # --- MUDANÇA: Novo Slot para Gráfico Plotly ---
                out_history_plot_psicologa = gr.Plot(label="Tendência de Sentimento do Paciente", visible=False)
                
                out_history_message_psicologa = gr.Markdown(visible=False)
                out_history_df_psicologa = gr.DataFrame(
                    label="Registros do Paciente", 
                    visible=False, 
                    wrap=True,
                    headers=["Data", "Área", "Nota (1-5)", "Tópicos", "Diário do Paciente", "Sentimento (IA)", "Temas (IA)", "Resumo (IA)"]
                )

            with gr.Tab("Enviar Recado", id=2) as recado_tab_psicologa:
                in_paciente_dropdown_reg = gr.Dropdown(label="Selecione um Paciente", choices=["Carregando..."])
                btn_load_ultimo_diario = gr.Button("Carregar último diário como base")
                out_diario_paciente_para_recado = gr.Textbox(label="Último Diário do Paciente", lines=5, interactive=False, visible=True)
                out_diario_paciente_msg = gr.Markdown(visible=False)
                gr.Markdown("Escreva seu recado abaixo ou gere uma sugestão da IA.")
                in_recado_texto = gr.Textbox(label="Seu Recado para o Paciente", lines=3)
                with gr.Row():
                    btn_gerar_sugestao_recado = gr.Button("Complementar o texto (IA)")
                    btn_enviar_recado = gr.Button("Enviar Recado", variant="primary")
                out_feedback_recado_psicologa = gr.Markdown(visible=False)

    # --- Conexões (Event Listeners) ---
    
    chk_novo_usuario.change(
        fn=fn_toggle_signup_form,
        inputs=[chk_novo_usuario],
        outputs=[in_signup_psicologa, btn_create_user]
    )
    
    btn_create_user.click(
        fn=fn_create_user,
        inputs=[in_login_username, in_login_password, in_signup_psicologa],
        outputs=[out_login_message]
    )
    
    btn_login.click(
        fn=fn_login,
        inputs=[in_login_username, in_login_password],
        outputs=[state_user, out_login_message]
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
            in_paciente_dropdown_reg
        ]
    )
    
    # --- Conexões do Paciente ---
    in_sentimento_paciente.release(
        fn=fn_get_suggestions_paciente,
        inputs=[in_area_paciente, in_sentimento_paciente], 
        outputs=[
            out_sugestoes_paciente, in_outro_topico_paciente, components_n3_paciente, 
            btn_submit_paciente, out_feedback_paciente
        ]
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
        ]
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
        ]
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
        outputs=[btn_discard_paciente, out_feedback_paciente]
    )
    
    # --- MUDANÇA: Conexão de Histórico (AGORA RETORNA 3 VALORES) ---
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
    btn_load_history_psicologa.click(
        fn=fn_load_history_psicologa,
        inputs=[in_paciente_dropdown_hist],
        outputs=[out_history_plot_psicologa, out_history_df_psicologa, out_history_message_psicologa],
        show_progress="full"
    )
    btn_load_ultimo_diario.click(
        fn=fn_load_ultimo_diario_psicologa,
        inputs=[in_paciente_dropdown_reg],
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