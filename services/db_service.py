# services/db_service.py (Com Dual-Writing e Funções de Leitura)
import psycopg2
from psycopg2 import sql
from contextlib import contextmanager
from datetime import datetime
from models.schemas import CheckinFinal, GeminiResponse
import os
from .sheets_connector import SheetsConnector # <-- NOVO IMPORT

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
        self.psicologas_list = []
        self.all_users_data = []
        self.sheets_connector = None # Inicializa o conector Sheets como None
        
        try:
            with get_db_connection() as conn:
                print("Conexão com PostgreSQL (Render) bem-sucedida.")
            
            # Tenta carregar o conector Sheets (pode falhar, mas o app continua)
            try:
                self.sheets_connector = SheetsConnector()
                print("Google Sheets Connector ativado para backup.")
            except Exception as e:
                print("Alerta: Google Sheets (Backup) desativado.")
            
            # Carrega a lista de psicólogas na inicialização
            self.psicologas_list = self.get_psicologas_list_for_signup()
            self.all_users_data = self.get_all_users()
            print(f"{len(self.psicologas_list)} psicólogas carregadas do DB.")
        except Exception as e:
            print(f"Erro Crítico ao conectar ao PostgreSQL: {e}")
            self.psicologas_list = ["ERRO NO DB"]
            self.all_users_data = []

    def get_all_users(self):
        # (Funções de Login/Cadastro, sem mudanças, usam o cache)
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
        # (Funções de Login/Cadastro, sem mudanças, usam o cache)
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
        # (Funções de Login/Cadastro, sem mudanças, usam o cache)
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
        # (Funções de Login/Cadastro, sem mudanças, usam o cache)
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
        # (Funções de Login/Cadastro, sem mudanças, usam o cache)
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

    # --- FUNÇÃO DE ESCRITA (DUAL-WRITING) ---
    def write_checkin(self, checkin: CheckinFinal, gemini_data: GeminiResponse, paciente_id: str, psicologa_id: str, compartilhado: bool):
        """Salva no SQL e faz o backup no Google Sheets."""
        
        # 1. SALVAR NO POSTGRESQL (Prioridade)
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
            print(f"Erro Crítico ao escrever no SQL (checkin): {e}")
            raise # Levanta o erro se o SQL falhar
            
        # 2. SALVAR NO GOOGLE SHEETS (Backup Opcional)
        if self.sheets_connector:
            try:
                self.sheets_connector.write_checkin(checkin, gemini_data, paciente_id, psicologa_id, compartilhado)
                print("Backup para Google Sheets bem-sucedido.")
            except Exception as e:
                print(f"AVISO: Falha no backup para Google Sheets: {e}")
                # Não levantamos o erro aqui; o check-in já está salvo no SQL.


    def get_all_checkin_data(self):
        # (Função de Leitura - Sem mudanças)
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM checkins")
                    rows = cur.fetchall()
                    headers = [desc[0] for desc in cur.description]
                    return headers, rows if rows else ([], [])
        except Exception as e:
            print(f"Erro ao ler o histórico: {e}")
            return [], []

    def get_recados_paciente(self, paciente_id: str):
        # (Função de Leitura - Sem mudanças)
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT timestamp, psicologa_id, mensagem_texto FROM recados WHERE paciente_id = %s ORDER BY timestamp DESC LIMIT 20",
                        (paciente_id,)
                    )
                    rows = cur.fetchall()
                    headers = ['timestamp', 'psicologa_id', 'mensagem_texto']
                    return headers, rows if rows else ([], [])
        except Exception as e:
            print(f"Erro ao ler recados: {e}")
            return [], []

    def get_ultimo_diario_paciente(self, paciente_id: str):
        # (Função de Leitura - Sem mudanças)
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT topicos_selecionados, diario_texto FROM checkins 
                        WHERE paciente_id = %s AND compartilhado = TRUE 
                        ORDER BY timestamp DESC LIMIT 1
                        """,
                        (paciente_id,)
                    )
                    row = cur.fetchone()
                    if row:
                        topicos = row[0]
                        diario = row[1]
                        return f"Tópicos: {topicos}\n\nDiário: {diario}", f"Último diário (compartilhado) de {paciente_id} carregado."
                    else:
                        return None, f"Nenhum diário compartilhado encontrado para {paciente_id}."
        except Exception as e:
            print(f"Erro ao buscar último diário: {e}")
            return None, f"Erro ao buscar diário: {e}"

    def send_recado(self, psicologa_id: str, paciente_id: str, mensagem_texto: str):
        # --- FUNÇÃO DE ESCRITA (DUAL-WRITING) ---
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO recados (psicologa_id, paciente_id, mensagem_texto) VALUES (%s, %s, %s)",
                        (psicologa_id, paciente_id, mensagem_texto)
                    )
                    conn.commit()
                    print(f"Recado enviado por {psicologa_id} para {paciente_id} no SQL.")
                    
                    # Tenta o backup no Google Sheets
                    if self.sheets_connector:
                         self.sheets_connector.send_recado(psicologa_id, paciente_id, mensagem_texto)
                         print("Backup de Recado para Sheets bem-sucedido.")
                         
                    return True, f"Recado enviado com sucesso para {paciente_id}!"
        except Exception as e:
            print(f"Erro ao enviar recado: {e}")
            return False, f"Erro no servidor ao enviar recado: {e}"

    def delete_last_record(self, paciente_id: str):
        # (Função de Delete - Sem mudanças)
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM checkins WHERE paciente_id = %s ORDER BY timestamp DESC LIMIT 1",
                        (paciente_id,)
                    )
                    last_record = cur.fetchone()
                    
                    if last_record:
                        record_id = last_record[0]
                        cur.execute("DELETE FROM checkins WHERE id = %s", (record_id,))
                        conn.commit()
                        print(f"Registro ID {record_id} ({paciente_id}) apagado do SQL.")
                        return True
                    else:
                        print(f"Nenhum registro encontrado para apagar para {paciente_id}")
                        return False
        except Exception as e:
            print(f"Erro ao apagar o registro: {e}")
            return False

# Cria uma instância única
db_service = DBService()