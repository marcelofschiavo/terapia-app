# main.py
from fastapi import FastAPI
from gradio.routes import mount_gradio_app
import uvicorn
import os

# Importa o aplicativo Gradio completo
from app import app as gradio_app

# Cria o aplicativo FastAPI (servidor principal)
app = FastAPI(title="Terap.ia API")

# 3. Monta o Gradio na raiz (/) do FastAPI
# --- MUDANÇA: Adiciona o argumento 'path' ---
app = mount_gradio_app(app, gradio_app, path="/") 

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=7860, reload=True)