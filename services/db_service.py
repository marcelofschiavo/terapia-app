# services/db_service.py (Versão Mínima)
import psycopg2
from psycopg2 import sql
from contextlib import contextmanager
from datetime import datetime
from models.schemas import CheckinFinal, GeminiResponse
import os

DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_db_connection():
    """Função 'helper' para conectar e fechar o banco de dados com segurança."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não foi definida. Exporte a variável de ambiente.")
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

class DBService:
    def __init__(self):
        # Testa a conexão na inicialização
        try:
            with get_db_connection() as conn:
                print("Conexão com PostgreSQL (Render) bem-sucedida.")
            # Carrega a lista de psicólogas na inicialização
            self.psicologas_list = self.get_psicologas_list_for_signup()
            self.all_users_data = self.get_all_users()
            print(f"{len(self.psicologas_list)} psicólogas carregadas do DB.")
        except Exception as e:
            print(f"Erro Crítico ao conectar ao PostgreSQL: {e}")
            self.psicologas_list = []
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
                    return [p[0] for p in psicologas] if psicologas else ["Nenhuma psicóloga encontrada"]
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

    def check_user(self, username, password):
        # (Sem mudanças)
        try:
            for row in self.all_users_data:
                if row and len(row) > 3 and row[0] == username and row[1] == password:
                    role = row[2] 
                    psicologa_associada = row[3] if role == "Paciente" else None
                    print(f"Login SQL bem-sucedido para: {username}, Role: {role}")
                    return True, role, psicologa_associada
            print(f"Login SQL falhou para: {username}")
            return False, None, None
        except Exception as e:
            print(f"Erro ao checar usuário: {e}")
            return False, None, None

    def create_user(self, username, password, psicologa_selecionada):
        # (Sem mudanças)
        if not username or not password or len(username) < 3 or len(password) < 3:
            return False, "Usuário e senha devem ter pelo menos 3 caracteres."
        if not psicologa_selecionada or psicologa_selecionada == "Nenhuma psicóloga encontrada":
            return False, "Por favor, selecione uma psicóloga da lista."
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO usuarios (username, password_hash, role, psicologa_associada) VALUES (%s, %s, %s, %s)",
                        (username, password, "Paciente", psicologa_selecionada)
                    )
                    conn.commit()
                    self.all_users_data.append((username, password, "Paciente", psicologa_selecionada))
                    if psicologa_selecionada not in self.psicologas_list:
                         self.psicologas_list = self.get_psicologas_list_for_signup()
                    print(f"Novo usuário 'Paciente' criado: {username}, vinculado a {psicologa_selecionada}")
                    return True, f"Paciente de usuário '{username}' criado com sucesso! Agora você pode fazer o login."
        except psycopg2.errors.UniqueViolation:
            return False, "Esse nome de usuário já existe. Tente outro."
        except Exception as e:
            print(f"Erro ao criar usuário: {e}")
            return False, f"Erro no servidor ao tentar criar usuário: {e}"

    def write_checkin(self, checkin: CheckinFinal, gemini_data: GeminiResponse, paciente_id: str, psicologa_id: str, compartilhado: bool):
        # (Sem mudanças)
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    topicos_str = ", ".join(checkin.topicos_selecionados)
                    temas_gemini_str = ", ".join(gemini_data.temas)
                    cur.execute(
                        """
                        INSERT INTO checkins (
                            area, sentimento, topicos_selecionados, diario_texto, 
                            insight_ia, acao_proposta, sentimento_texto, temas_gemini, 
                            resumo_psicologa, compartilhado, paciente_id, psicologa_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            checkin.area, checkin.sentimento, topicos_str, checkin.diario_texto,
                            gemini_data.insight, gemini_data.acao, gemini_data.sentimento_texto,
                            temas_gemini_str, gemini_data.resumo, compartilhado,
                            paciente_id, psicologa_id
                        )
                    )
                    conn.commit()
                    print(f"Dados de '{paciente_id}' (Psic: {psicologa_id}) salvos no SQL. Compartilhado: {compartilhado}")
        except Exception as e:
            print(f"Erro ao escrever no SQL (checkin): {e}")
            raise

    # --- FUNÇÕES DE BUSCA DELETADAS ---
    # delete_last_record, get_all_checkin_data, get_recados_paciente, get_ultimo_diario_paciente foram removidas.

# Cria uma instância única
db_service = DBService()