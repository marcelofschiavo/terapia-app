# init_db.py
import os
import psycopg2
from psycopg2 import sql

# Define o esquema do banco de dados
SQL_COMMANDS = [
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(50) NOT NULL,
        psicologa_associada VARCHAR(100)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS checkins (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        area VARCHAR(255),
        sentimento INT,
        topicos_selecionados TEXT,
        diario_texto TEXT,
        insight_ia TEXT,
        acao_proposta TEXT,
        sentimento_texto VARCHAR(100),
        temas_gemini TEXT,
        resumo_psicologa TEXT,
        compartilhado BOOLEAN DEFAULT TRUE,
        paciente_id VARCHAR(100),
        psicologa_id VARCHAR(100),
        FOREIGN KEY (paciente_id) REFERENCES usuarios (username),
        FOREIGN KEY (psicologa_id) REFERENCES usuarios (username)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS recados (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        mensagem_texto TEXT,
        psicologa_id VARCHAR(100) REFERENCES usuarios (username),
        paciente_id VARCHAR(100) REFERENCES usuarios (username)
    );
    """,
    """
    -- INSERE A PRIMEIRA PSICÓLOGA (só roda se ela não existir)
    INSERT INTO usuarios (username, password_hash, role, psicologa_associada)
    VALUES ('priscila', '123', 'Psicóloga', NULL)
    ON CONFLICT (username) DO NOTHING;
    """
]

def initialize_database():
    """Conecta ao banco de dados e executa os comandos SQL."""
    
    # --- MUDANÇA AQUI ---
    print("Script init_db.py iniciado...")
    
    try:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            print(">>> ERRO: Variável de ambiente DATABASE_URL não definida.")
            print(">>> Por favor, rode o comando 'export DATABASE_URL=...' antes de rodar este script.")
            return # Para aqui

        # Se a variável FOI encontrada, ele continua
        print("DATABASE_URL encontrada. Conectando ao Render...")
        
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        print("Conectado ao banco de dados no Render...")
        
        for command in SQL_COMMANDS:
            cur.execute(command)
            print("Executando comando SQL...")
        
        conn.commit()
        print("Tabelas 'usuarios', 'checkins', e 'recados' criadas com sucesso!")
        
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Erro ao inicializar o banco de dados: {e}")

if __name__ == "__main__":
    initialize_database()