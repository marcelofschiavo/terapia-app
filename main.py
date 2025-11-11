# main.py (Corrigido a montagem do Gradio)
import uvicorn
from fastapi import FastAPI
from gradio.routes import mount_gradio_app
import os

# 1. Importa o aplicativo Gradio completo (app.py)
from app import app as gradio_app

# 2. Cria o aplicativo FastAPI (servidor principal)
# O título do aplicativo será definido aqui
app = FastAPI(title="Terap.ia - Painel Clínico")

# 3. Monta o Gradio na raiz (/) do FastAPI, definindo o 'path'
app = mount_gradio_app(app, blocks=gradio_app, path="/") 

if __name__ == "__main__":
    # Comando de execução local (para debug)
    uvicorn.run("main:app", host="127.0.0.1", port=7860, reload=True)