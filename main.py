# main.py
from fastapi import FastAPI
from gradio.routes import mount_gradio_app
import uvicorn
import os

# Importa o aplicativo Gradio completo (app.py)
from app import app as gradio_app

# Cria o aplicativo FastAPI (servidor principal)
app = FastAPI(title="Terap.ia API")

# Monta o Gradio na raiz (/) do FastAPI
# Isso resolve o conflito Gunicorn/Gradio
app = mount_gradio_app(app, gradio_app) 

# Se for rodar localmente (opcional)
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7860, reload=True)