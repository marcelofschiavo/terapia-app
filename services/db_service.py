# services/db_service.py (Mínimo)
import psycopg2
from contextlib import contextmanager
import os

DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não foi definida.")
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

class DBService:
    def __init__(self):
        self.psicologas_list = []
        try:
            with get_db_connection() as conn:
                print("Conexão com PostgreSQL (Render) bem-sucedida.")
            self.psicologas_list = self.get_psicologas_list_for_signup()
            print(f"{len(self.psicologas_list)} psicólogas carregadas do DB.")
        except Exception as e:
            print(f"Erro Crítico ao conectar ao PostgreSQL: {e}")
            self.psicologas_list = ["ERRO NO DB"] # Lista de erro para UI
    
    def get_psicologas_list_for_signup(self):
        # Apenas tenta buscar os usuários para ver se a tabela existe
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Busca qualquer coisa, apenas para teste
                    cur.execute("SELECT username FROM usuarios WHERE role = 'Psicóloga' LIMIT 10") 
                    psicologas = cur.fetchall()
                    return [p[0] for p in psicologas] if psicologas else ["Nenhuma psicóloga cadastrada"]
        except Exception as e:
            print(f"Erro ao buscar psicólogas (Tabela?): {e}")
            return ["ERRO DE TABELA SQL"]
    
    # As outras funções (check_user, create_user, write_checkin, etc.) não serão usadas.

# Cria uma instância única
db_service = DBService()