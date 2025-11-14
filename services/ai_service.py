# services/ai_service.py
import os
import json
import google.generativeai as genai
from models.schemas import CheckinContext, DrilldownRequest, CheckinFinal, GeminiResponse
import pandas as pd

class AIService:
    def __init__(self):
        print("Carregando serviços de IA...")
        self.gemini_model = self._load_gemini()
        self.gemini_model_text_only = self._load_gemini(response_mime_type="text/plain")

    def _load_gemini(self, response_mime_type="application/json"):
        # (Sem mudanças)
        try:
            GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
            if not GOOGLE_API_KEY:
                raise ValueError("Variável de ambiente GOOGLE_API_KEY não definida.")
            genai.configure(api_key=GOOGLE_API_KEY)
            generation_config = {"temperature": 0.8, "response_mime_type": response_mime_type} 
            model = genai.GenerativeModel(
                model_name="gemini-flash-latest", 
                generation_config=generation_config
            )
            print(f"Modelo Gemini ({response_mime_type}) configurado com sucesso.")
            return model
        except Exception as e:
            print(f"Erro ao configurar o Gemini: {e}")
            return None

    async def get_suggestions(self, contexto: CheckinContext):
        # (Sem mudanças)
        if not self.gemini_model: raise Exception("Modelo Gemini (JSON) não carregado.")
        sentimento_desc = "muito positivo"
        if contexto.sentimento <= 2: sentimento_desc = "extremamente negativo"
        elif contexto.sentimento <= 3: sentimento_desc = "negativo"
        prompt = f"""
        Contexto: O usuário está fazendo um check-in de bem-estar.
        - Área da Vida: {contexto.area}
        - Sentimento (1-5): {contexto.sentimento} (indica sentimento {sentimento_desc}).
        Gere 4 "gatilhos prováveis" que podem ter causado esse sentimento.
        Seja muito breve e direto (máximo 10 palavras por item, idealmente 5-7).
        Retorne APENAS um objeto JSON válido no formato:
        {{"sugestoes": ["item curto 1", "item curto 2", "item curto 3", "item curto 4"]}}
        """
        try:
            response = await self.gemini_model.generate_content_async(prompt)
            json_data = json.loads(response.text)
            print(f"Sugestões do Gemini: {json_data.get('sugestoes', [])}")
            return json_data
        except Exception as e:
            print(f"Erro ao chamar Gemini (Nível 1): {e}")
            return {"sugestoes": ["Fale sobre seu dia", "O que mais te marcou hoje?"]}

    async def get_drilldown_questions(self, request: DrilldownRequest):
        # (Sem mudanças)
        if not self.gemini_model: raise Exception("Modelo Gemini (JSON) não carregado.")
        prompt = f"""
        Contexto: O usuário selecionou o tópico: "{request.topico_selecionado}"
        Gere 4 perguntas-chave curtas para investigar este tópico.
        Para cada pergunta, inclua 2-3 exemplos de respostas curtas entre parênteses.
        Retorne APENAS um objeto JSON válido no formato:
        {{"perguntas": ["Pergunta 1? (ex: sim, não)", "Pergunta 2? (ex: hoje, ontem)", "Pergunta 3? (ex: raiva, tristeza)", "Pergunta 4? (ex: sim, um pouco, não)"]}}
        """
        try:
            response = await self.gemini_model.generate_content_async(prompt)
            json_data = json.loads(response.text)
            print(f"Perguntas-Chave do Gemini: {json_data.get('perguntas', [])}")
            return json_data
        except Exception as e:
            print(f"Erro ao chamar Gemini (Nível 2): {e}")
            return {"perguntas": ["Pode detalhar mais?", "Como você se sentiu?"]}

    async def process_final_checkin(self, checkin_data: CheckinFinal, diario_para_analise: str) -> GeminiResponse:
        # (Sem mudanças)
        if not self.gemini_model: raise Exception("Modelo Gemini (JSON) não carregado.")
        if not diario_para_analise: 
            return GeminiResponse(
                insight="Seu check-in de sentimento foi salvo.",
                acao="Na próxima vez, tente escrever um diário para receber mais insights."
            )
        prompt_final = f"""
        Contexto Psicológico:
        Um usuário registrou um diário sobre a área "{checkin_data.area}" com nota {checkin_data.sentimento}/5.
        Diário: "{diario_para_analise}" 
        Analise o diário e retorne APENAS um objeto JSON válido com 5 chaves:
        1. "insight": (String) 1 frase empática que valide o sentimento. Não dê conselhos.
        2. "acao": (String) 1 ação concreta e imediata (máx 2 frases) baseada no diário.
        3. "sentimento_texto": (String) Uma única palavra que descreva a emoção principal (ex: "Frustração").
        4. "temas": (Lista de Strings) Uma lista com 2 ou 3 temas principais (ex: ["Conflito", "Prazo"]).
        5. "resumo": (String) Um resumo de 2 frases para uma psicóloga.
        """
        try:
            response = await self.gemini_model.generate_content_async(prompt_final)
            json_data = json.loads(response.text)
            gemini_response = GeminiResponse(**json_data)
            print(f"Análise Final do Gemini: {gemini_response.model_dump_json(indent=2)}")
            return gemini_response
        except Exception as e:
            print(f"Erro ao gerar análise final do Gemini: {e}")
            return GeminiResponse(
                insight="Houve um erro ao analisar seu diário.",
                acao="Tente novamente mais tarde."
            )

    async def get_sugestao_recado_psicologa(self, ultimo_diario_paciente: str, rascunho_psicologa: str):
        # (Sem mudanças)
        if not self.gemini_model_text_only: raise Exception("Modelo Gemini (Texto) não carregado.")
        if not ultimo_diario_paciente:
            return {"recado": "O paciente não deixou um diário para este registro."}
        prompt = f"""
        Contexto: Você é uma psicóloga (TCC). Um paciente enviou o seguinte registro de diário:
        ---
        [DIÁRIO DO PACIENTE]:
        {ultimo_diario_paciente}
        ---
        Você começou a escrever um rascunho de resposta (ou o campo está vazio):
        ---
        [SEU RASCUNHO]:
        {rascunho_psicologa}
        ---
        Sua tarefa é usar AMBOS os textos como contexto. Gere uma mensagem empática e completa. 
        Se o rascunho já tiver um bom começo, continue a partir dele. 
        Se o rascunho estiver vazio, apenas responda ao diário do paciente.
        Retorne APENAS a mensagem sugerida, sem JSON.
        """
        try:
            response = await self.gemini_model_text_only.generate_content_async(prompt)
            return {"recado": response.text}
        except Exception as e:
            print(f"Erro ao gerar sugestão de recado: {e}")
            return {"recado": f"Erro ao gerar sugestão: {e}"}

    # --- NOVA FUNÇÃO (Request 1) ---
    async def get_analytics_summary(self, df: pd.DataFrame, paciente_id_filtro: str):
        """Gera um resumo em markdown da análise dos gráficos."""
        if not self.gemini_model_text_only: raise Exception("Modelo Gemini (Texto) não carregado.")
        if df.empty:
            return "Sem dados para resumir."
            
        try:
            # Prepara os dados para o prompt
            sentimento_medio = df['sentimento'].mean()
            areas_baixas = df[df['sentimento'] <= 2]['area'].value_counts().head(3).to_dict()
            temas_comuns = df['temas_gemini'].str.split(', ').explode().str.strip().value_counts().head(3).to_dict()

            prompt = f"""
            Você é um assistente de IA para uma psicóloga. Analise os seguintes dados brutos de check-in
            para o filtro '{paciente_id_filtro}' e escreva um resumo diagnóstico em 3-4 frases curtas (em markdown).
            
            - Sentimento Médio (1-5): {sentimento_medio:.2f}
            - Contagem de Áreas com nota baixa (<=2): {areas_baixas}
            - Contagem de Temas (IA) mais comuns: {temas_comuns}
            
            Seja direto e foque em insights acionáveis (ex: "A área X está crítica", "O tema Y é recorrente").
            """
            response = await self.gemini_model_text_only.generate_content_async(prompt)
            return response.text
        except Exception as e:
            print(f"Erro ao gerar resumo de analytics: {e}")
            return "Erro ao gerar resumo."

# Cria uma instância única
ai_service = AIService()