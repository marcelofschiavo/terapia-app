# services/sheets_connector.py
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from models.schemas import CheckinFinal, GeminiResponse
import os
import json

"""
CONECTOR PARA GOOGLE SHEETS (USADO APENAS PARA BACKUP/TABLEAU PUBLIC).
Esta classe é chamada pelo DBService.
"""

# Configurações
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

# ⚠️ SUBSTITUA PELO SEU ID REAL DA PLANILHA DE DADOS ⚠️
SHEET_ID = "1QhiPEx0z-_vnKgcGhr05ie1KucDjGkPXm4HBb0UKdGw" 

# Nome da variável de ambiente que guarda o JSON
GOOGLE_SHEETS_CREDS_SECRET_NAME = "GOOGLE_SHEETS_CREDENTIALS"

class SheetsConnector:
    def __init__(self):
        self.checkins_sheet = None
        self.recados_sheet = None
        
        try:
            creds_json_str = os.getenv(GOOGLE_SHEETS_CREDS_SECRET_NAME)
            if not creds_json_str:
                raise ValueError(f"Secret '{GOOGLE_SHEETS_CREDS_SECRET_NAME}' não encontrado.")
            
            creds_dict = json.loads(creds_json_str)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            client = gspread.authorize(creds)
            
            spreadsheet = client.open_by_key(SHEET_ID)
            self.checkins_sheet = spreadsheet.worksheet("Checkins") 
            self.recados_sheet = spreadsheet.worksheet("Recados")
            
            print("Google Sheets Connector: Conexão Sheets OK.")
            
        except Exception as e:
            print(f"Erro no Sheets Connector: {e}")
            raise # Levanta o erro para que o DBService saiba que não pode usar o backup

    def write_checkin(self, checkin: CheckinFinal, gemini_data: GeminiResponse, paciente_id: str, psicologa_id: str, compartilhado: bool):
        """Prepara e escreve a linha na aba 'Checkins'."""
        if not self.checkins_sheet:
            raise Exception("Sheets Connector: Aba 'Checkins' não conectada.")

        agora = datetime.now().isoformat()
        topicos_str = ", ".join(checkin.topicos_selecionados)
        temas_gemini_str = ", ".join(gemini_data.temas)

        # 13 COLUNAS
        nova_linha = [
            agora,                     # A
            checkin.area,              # B
            checkin.sentimento,        # C
            topicos_str,               # D 
            checkin.diario_texto,      # E
            gemini_data.insight,       # F
            gemini_data.acao,          # G
            gemini_data.sentimento_texto, # H
            temas_gemini_str,          # I
            gemini_data.resumo,        # J
            paciente_id,               # K
            psicologa_id,              # L
            compartilhado              # M (NOVA - Compartilhado)
        ]
        
        self.checkins_sheet.append_row(nova_linha)
        
    def send_recado(self, psicologa_id: str, paciente_id: str, mensagem_texto: str):
        """Salva um novo recado na aba 'Recados'."""
        if not self.recados_sheet:
            raise Exception("Sheets Connector: Aba 'Recados' não conectada.")

        nova_linha = [
            datetime.now().isoformat(), # timestamp
            psicologa_id,
            paciente_id,
            mensagem_texto
        ]
        self.recados_sheet.append_row(nova_linha)