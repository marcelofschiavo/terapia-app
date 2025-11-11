# app.py (Mínimo Viável para Teste de Inicialização)
import gradio as gr
import os
import time
from services.db_service import db_service 
from models.schemas import CheckinFinal, GeminiResponse 

# Variável Global: Lista de Psicólogas
# Carrega na inicialização.
print("Carregando lista de psicólogas (na inicialização)...")
LISTA_DE_PSICOLOGAS_CHOICES = db_service.get_psicologas_list_for_signup() 
print(f"Lista de psicólogas carregada: {LISTA_DE_PSICOLOGAS_CHOICES}")


# --- Funções de Lógica Mínima ---

# --- FUNÇÃO CORRIGIDA ---
def fn_login_minimo(username, password):
    """Função de teste de login que só retorna uma string de status."""
    
    # Se o DB não carregou
    if "ERRO NO DB" in LISTA_DE_PSICOLOGAS_CHOICES:
        return "❌ Erro na Conexão SQL. Verifique logs do Render/DB!", gr.update(visible=True)
    
    # 1. Checa o DB (Teste de conexão SQL e credenciais)
    login_valido, role, psicologa_associada = db_service.check_user(username, password)
    
    # 2. Roteador Mínimo
    if login_valido:
        return f"✅ Login bem-sucedido. Usuário: {username}. Perfil: {role}.", gr.update(visible=True)
    else:
        return "❌ Login falhou. Credenciais inválidas.", gr.update(visible=True)

# --- Interface Gráfica (Gradio Blocks) ---
with gr.Blocks(
    theme=gr.themes.Default(), 
    css="body, .gradio-container, .gradio-container * {font-size: 16px !important;}"
) as app: 
    
    gr.Markdown("# 🧠 Teste de Inicialização (Render)")
    gr.Markdown("Este é o seu 'Hello World'. Se você vir a lista de psicólogas, o SQL está OK.")
    
    with gr.Row():
        with gr.Column(): 
            gr.Markdown("---")
            in_login_username = gr.Textbox(label="Usuário", placeholder="Ex: dra_ana")
            in_login_password = gr.Textbox(label="Senha", type="password", placeholder="Ex: senha_da_ana")
            btn_login = gr.Button("Testar Conexão e Login", variant="primary")
            
            # Mostra o status do DB
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
        outputs=[out_login_message, out_login_message] # Repete o output para não quebrar
    )

# --- Lançar a Aplicação ---
if __name__ == "__main__":
    app.launch(debug=True)