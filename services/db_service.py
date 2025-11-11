# services/db_service.py (Corrigido o cache e a chamada de check_user)
import psycopg2
from psycopg2 import sql
from contextlib import contextmanager
from datetime import datetime
from models.schemas import CheckinFinal, GeminiResponse
import os
import json

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
        self.all_users_data = []
        
        try:
            with get_db_connection() as conn:
                print("Conexão com PostgreSQL (Render) bem-sucedida.")
            # Carrega a lista de psicólogas na inicialização
            self.psicologas_list = self.get_psicologas_list_for_signup()
            self.all_users_data = self.get_all_users()
            print(f"{len(self.psicologas_list)} psicólogas carregadas do DB.")
        except Exception as e:
            print(f"Erro Crítico ao conectar ao PostgreSQL: {e}")
            self.psicologas_list = ["ERRO NO DB"]
            self.all_users_data = []

    def get_all_users(self):
        # (Sem mudanças)
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT username, password_hash, role, psicologa_associada FROM usuarios")
                    users = cur.fetchall()
                    return users if users else []
        except Exception as e:
            print(f"Erro ao buscar todos os usuários: {e}")
            return []

    def get_psicologas_list_for_signup(self):
        # (Sem mudanças)
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT username FROM usuarios WHERE role = 'Psicóloga'")
                    psicologas = cur.fetchall()
                    return [p[0] for p in psicologas] if psicologas else ["Nenhuma psicóloga cadastrada"]
        except Exception as e:
            print(f"Erro ao buscar psicólogas: {e}")
            return ["Erro ao carregar lista"]

    def get_pacientes_da_psicologa(self, psicologa_username: str):
        # (Sem mudanças)
        pacientes = []
        try:
            for row in self.all_users_data:
                if len(row) > 3 and row[2] == "Paciente" and row[3] == psicologa_username:
                    pacientes.append(row[0])
            if not pacientes:
                return ["Nenhum paciente vinculado a você"]
            return pacientes
        except Exception as e:
            print(f"Erro ao buscar pacientes: {e}")
            return [f"Erro ao buscar pacientes: {e}"]

    # --- FUNÇÃO CORRIGIDA (Adiciona o cache local) ---
    def check_user(self, username, password):
        """Verifica usuário/senha usando o cache local na memória."""
        try:
            # Col 0 = user, Col 1 = pass, Col 2 = role, Col 3 = psicologa
            for row in self.all_users_data:
                if row and len(row) > 3 and row[0] == username and row[1] == password:
                    role = row[2] 
                    psicologa_associada = row[3] if role == "Paciente" else None
                    return True, role, psicologa_associada
            
            return False, None, None
        except Exception as e:
            print(f"Erro ao checar usuário: {e}")
            return False, None, None
            
    # (Resto das funções omitidas para brevidade, mas devem permanecer no arquivo)

# Cria uma instância única
db_service = DBService()