# populatedb.py
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

# DADOS DE TESTE (REQUEST 4)
checkin_data = [
    # Paciente: Marcelo (Foco em Academia e Finanças)
    ('Acadêmica: Estudo, aprendizado, evolução.', 1, 'Procrastinação extrema', 'Não consigo começar a estudar. Estou paralisado.', 'Insight...', 'Ação...', 'Ansiedade', 'Procrastinação, Ansiedade de Desempenho', 'Resumo...', True, 'marcelo', 'priscila'),
    ('Acadêmica: Estudo, aprendizado, evolução.', 2, 'Sobrecarga de estudos', 'Muitas provas, sinto que não vou dar conta.', 'Insight...', 'Ação...', 'Sobrecarga', 'Estresse Acadêmico, Gestão do Tempo', 'Resumo...', True, 'marcelo', 'priscila'),
    ('Financeiro: Renda, controle, poupança.', 1, 'Dívida inesperada', 'Meu cartão foi clonado, estou com uma dívida que não é minha.', 'Insight...', 'Ação...', 'Pânico', 'Crise Financeira, Fraude', 'Resumo...', True, 'marcelo', 'priscila'),
    ('Hobbies: Prazer, diversão, lazer.', 4, 'Voltei a desenhar', 'Foi bom ter um tempo para mim, me senti relaxado.', 'Insight...', 'Ação...', 'Relaxamento', 'Autocuidado, Hobby', 'Resumo...', True, 'marcelo', 'priscila'),
    ('Social: Amizades, convívio, conexões.', 3, 'Discussão com colega', 'Falei algo errado no trabalho e o clima ficou péssimo.', 'Insight...', 'Ação...', 'Culpa', 'Conflito Interpessoal, Comunicação', 'Resumo...', False, 'marcelo', 'priscila'), # Não compartilhado

    # Paciente: Ferreira (Foco em Relacionamentos e Saúde Física)
    ('Amoroso: Parceria, afeto, intimidade.', 5, 'Comunicação boa', 'Tivemos uma ótima conversa ontem, muito aberta.', 'Insight...', 'Ação...', 'Conexão', 'Comunicação, Vínculo', 'Resumo...', True, 'ferreira', 'priscila'),
    ('Física: Energia, saúde, disposição.', 2, 'Insônia', 'Não durmo direito há 3 dias. Estou um caco.', 'Insight...', 'Ação...', 'Exaustão', 'Insônia, Estresse', 'Resumo...', True, 'ferreira', 'priscila'),
    ('Profissional: Carreira, propósito, equilíbrio.', 3, 'Sobrecarga de trabalho', 'Muita reunião, pouca produção. Estou frustrado.', 'Insight...', 'Ação...', 'Frustração', 'Sobrecarga, Reuniões', 'Resumo...', True, 'ferreira', 'priscila'),
    ('Amoroso: Parceria, afeto, intimidade.', 2, 'Ciúmes', 'Me senti inseguro e acabei causando uma briga.', 'Insight...', 'Ação...', 'Insegurança', 'Ciúmes, Conflito', 'Resumo...', True, 'ferreira', 'priscila'),
    ('Física: Energia, saúde, disposição.', 5, 'Comecei a academia', 'Primeiro dia foi ótimo, me senti com mais energia.', 'Insight...', 'Ação...', 'Energia', 'Exercício Físico, Saúde', 'Resumo...', True, 'ferreira', 'priscila'),
]

recado_data = [
    ('priscila', 'marcelo', 'Marcelo, notei seus registros sobre procrastinação. Vamos conversar sobre quebrar essas tarefas em passos menores na próxima sessão.'),
    ('priscila', 'marcelo', 'Sobre a questão financeira, sinto muito pelo ocorrido. Lembre-se de focar no que você pode controlar agora: ligar para o banco.'),
    ('priscila', 'ferreira', 'Ferreira, que ótimo que voltou a se exercitar! Fique atento em como seu sono reage a essa nova rotina.'),
    ('priscila', 'ferreira', 'Sobre a discussão de ciúmes, vamos explorar essa insegurança e os gatilhos dela na nossa próxima consulta. Foi um passo importante você reconhecer isso.')
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
                ON CONFLICT (id) DO NOTHING;
                """
                cur.executemany(insert_query_checkins, checkin_data)
                print(f"{len(checkin_data)} registros de check-in inseridos.")
                
                # Inserir Recados
                insert_query_recados = """
                INSERT INTO recados (psicologa_id, paciente_id, mensagem_texto) 
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING;
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