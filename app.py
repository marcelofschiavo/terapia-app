# app.py (Mínimo Viável para Teste de Inicialização)
import gradio as gr
import os
import time
# Apenas os imports essenciais para o login e a base
from services.db_service import db_service 
from models.schemas import CheckinFinal, GeminiResponse 

# Variável Global: Lista de Psicólogas
# Carrega na inicialização.
print("Carregando lista de psicólogas (na inicialização)...")
LISTA_DE_PSICOLOGAS_CHOICES = db_service.get_psicologas_list_for_signup() 
print(f"Lista de psicólogas carregada: {LISTA_DE_PSICOLOGAS_CHOICES}")


# --- Funções de Lógica Mínima ---

def fn_login_minimo(username, password):
    """Função de teste de login que só retorna uma string de status."""
    
    # 1. Checa o DB (Teste de conexão SQL e credenciais)
    login_valido, role, psicologa_associada = db_service.check_user(username, password)
    
    if login_valido:
        # Se for válido, retorna o nome do usuário e a função
        return f"✅ Login bem-sucedido. Usuário: {username}. Perfil: {role}. Conexão SQL OK."
    elif "ERRO" in LISTA_DE_PSICOLOGAS_CHOICES[0]:
         return "❌ Erro na Conexão SQL. Verifique logs do Render/DB!"
    else:
        return "❌ Login falhou. Credenciais inválidas."

# --- Interface Gráfica (Gradio Blocks) ---
with gr.Blocks(
    theme=gr.themes.Default(), 
    css="body, .gradio-container, .gradio-container * {font-size: 16px !important;}"
) as app: 
    
    gr.Markdown("# 🧠 Teste de Inicialização (Render)")
    gr.Markdown("Se este app iniciar, significa que o Gunicorn/Gradio/SQL estão sincronizados.")
    
    with gr.Row():
        with gr.Column(): 
            gr.Markdown("---")
            in_login_username = gr.Textbox(label="Usuário", placeholder="Ex: dra_ana")
            in_login_password = gr.Textbox(label="Senha", type="password", placeholder="Ex: senha_da_ana")
            btn_login = gr.Button("Testar Conexão e Login", variant="primary")
            
            # Resultado do teste de inicialização
            gr.Textbox(
                label="Status de Inicialização do DB",
                value=f"Lista de Psicólogas Carregada: {LISTA_DE_PSICOLOGAS_CHOICES}",
                interactive=False
            )
            
            out_login_message = gr.Markdown("Aguardando teste...")

    # --- Conexões (Event Listeners) ---
    
    btn_login.click(
        fn=fn_login_minimo,
        inputs=[in_login_username, in_login_password],
        outputs=[out_login_message]
    )

# --- Lançar a Aplicação ---
if __name__ == "__main__":
    # O Gradio é um aplicativo FastAPI disfarçado. 
    # Ele inicia o servidor uvicorn interno e expõe o aplicativo.
    app.launch(server_name="0.0.0.0", server_port=10000)