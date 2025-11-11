# Dockerfile
# Usamos a imagem oficial do Python 3.10
FROM python:3.10-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Define a porta que o Gradio/Gunicorn vai ouvir
ENV PORT 10000

# Copia os arquivos de dependência
COPY requirements.txt .

# Instala as dependências de forma limpa e sem cache
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte
COPY . .

# Comando de inicialização: 
# Gunicorn servindo o objeto app.app_for_public_serving() na porta 10000
CMD gunicorn --worker-class uvicorn.workers.UvicornWorker app:app.app_for_public_serving() --bind 0.0.0.0:$PORT --timeout 120