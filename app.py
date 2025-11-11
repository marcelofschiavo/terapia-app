# app.py (Hello World + Login)
import gradio as gr
import os
from services.db_service import db_service # Importamos o DB simplificado

# Variável Global: Lista de Psicólogas
# Carrega na inicialização. Se falhar, a lista será "ERRO DE TABELA SQL"
LISTA_DE_PSICOLOGAS_CHOICES = db_service.get_psicologas_list_for_signup() 

# --- Funções de Lógica ---

def fn_login(username, password):
    """Função de teste para login."""
    if username == "admin" and password == "123":
        return "Logado como ADMIN! (DB: OK)", gr.update(visible=True)
    elif "ERRO" in LISTA_DE_PSICOLOGAS_CHOICES[0]:
         return "Erro na Conexão SQL. Verifique logs do Render!", gr.update(visible=True)
    else:
        return f"Login falhou. Psicólogas carregadas: {LISTA_DE_PSICOLOGAS_CHOICES}", gr.update(visible=True)

# --- Interface Gráfica (Gradio Blocks) ---
with gr.Blocks(
    theme=gr.themes.Default(), 
    css="body, .gradio-container, .gradio-container * {font-size: 16px !important;}"
) as app: 
    
    gr.Markdown("# 🧠 Teste de Inicialização (Render)")
    gr.Markdown("Este é o seu 'Hello World'. Se você vir a lista de psicólogas, o SQL está OK.")
    
    with gr.Row(visible=True) as login_view:
        with gr.Column(): 
            gr.Markdown("---")
            in_login_username = gr.Textbox(label="Usuário", placeholder="admin")
            in_login_password = gr.Textbox(label="Senha", type="password", placeholder="123")
            btn_login = gr.Button("Entrar (Teste)", variant="primary")
            
            # Mostra o status do DB
            out_status_db = gr.Textbox(
                label="Status do DB",
                value=f"Lista de Psicólogas Carregada: {LISTA_DE_PSICOLOGAS_CHOICES}",
                interactive=False
            )
            
            out_login_message = gr.Markdown(visible=False, value="")

    # --- Conexões (Event Listeners) ---
    
    btn_login.click(
        fn=fn_login,
        inputs=[in_login_username, in_login_password],
        outputs=[out_login_message, out_login_message]
    )


# --- Lançar a Aplicação ---
if __name__ == "__main__":
    app.launch(debug=True)