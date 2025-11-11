# main.py
from fastapi import FastAPI
from gradio.routes import mount_gradio_app
import uvicorn
import os

# Importa o aplicativo Gradio completo (app.py)
from app import app as gradio_app

# 2. Cria o aplicativo FastAPI (servidor principal)
# --- MUDANÇA: Defina o título aqui ---
app = FastAPI(title="Terap.ia - Painel Clínico")

# 3. Monta o Gradio na raiz (/) do FastAPI
app = mount_gradio_app(app, blocks=gradio_app, path="/") 

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=7860, reload=True)