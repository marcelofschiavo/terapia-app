# seed_db.py
import os
import psycopg2
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não foi definida. Exporte a variável de ambiente.")
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

# DADOS DE TESTE (REQUEST 1)
# (Altere 'marcelo' e 'priscila' para os nomes de usuário reais que você criou)
checkin_data = [
    ('Acadêmica: Estudo, aprendizado, evolução.', 2, 'Sobrecarga de estudos, Procrastinação', 'Não consigo focar, estou exausto.', 'Insight da IA...', 'Ação da IA...', 'Exaustão', 'Sobrecarga, Procrastinação', 'Resumo da IA...', True, 'marcelo', 'priscila'),
    ('Física: Energia, saúde, disposição.', 1, 'Dor crônica, Insônia', 'Minhas costas doem muito e não dormi nada.', 'Insight da IA...', 'Ação da IA...', 'Dor', 'Dor Crônica, Insônia', 'Resumo da IA...', True, 'marcelo', 'priscila'),
    ('Amoroso: Parceria, afeto, intimidade.', 5, 'Comunicação boa', 'Tivemos uma ótima conversa ontem.', 'Insight da IA...', 'Ação da IA...', 'Felicidade', 'Comunicação, Vínculo', 'Resumo da IA...', True, 'marcelo', 'priscila'),
    ('Financeiro: Renda, controle, poupança.', 2, 'Dívida de cartão', 'A fatura veio muito alta, estou preocupado.', 'Insight da IA...', 'Ação da IA...', 'Ansiedade', 'Dívida, Estresse Financeiro', 'Resumo da IA...', True, 'ferreira', 'priscila'),
    ('Social: Amizades, convívio, conexões.', 3, 'Discussão com amigo', 'Briguei com meu melhor amigo.', 'Insight da IA...', 'Ação da IA...', 'Tristeza', 'Conflito Interpessoal', 'Resumo da IA...', False, 'ferreira', 'priscila'), # <-- Não compartilhado
    ('Hobbies: Prazer, diversão, lazer.', 4, 'Comecei a pintar', 'Foi muito relaxante, me senti bem.', 'Insight da IA...', 'Ação da IA...', 'Relaxamento', 'Novo Hobby, Mindfulness', 'Resumo da IA...', True, 'ferreira', 'priscila'),
]

recado_data = [
    ('priscila', 'marcelo', 'Olá marcelo, notei que mencionou dor crônica. Vamos focar em técnicas de relaxamento na próxima sessão.'),
    ('priscila', 'ferreira', 'Olá ferreira, vi seu registro sobre o novo hobby de pintura. Fico feliz que tenha encontrado algo relaxante!')
]

def seed_database():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                print("Conectado ao DB. Inserindo dados de teste...")

                # Inserir Check-ins
                insert_query_checkins = """
                INSERT INTO checkins (
                    area, sentimento, topicos_selecionados, diario_texto, 
                    insight_ia, acao_proposta, sentimento_texto, temas_gemini, 
                    resumo_psicologa, compartilhado, paciente_id, psicologa_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cur.executemany(insert_query_checkins, checkin_data)
                print(f"{len(checkin_data)} registros de check-in inseridos.")
                
                # Inserir Recados
                insert_query_recados = """
                INSERT INTO recados (psicologa_id, paciente_id, mensagem_texto) 
                VALUES (%s, %s, %s)
                """
                cur.executemany(insert_query_recados, recado_data)
                print(f"{len(recado_data)} recados inseridos.")

                conn.commit()
                print("Dados de teste inseridos com sucesso!")

    except Exception as e:
        print(f"Erro ao inserir dados: {e}")

if __name__ == "__main__":
    # Lembre-se de exportar sua DATABASE_URL antes de rodar!
    seed_database()