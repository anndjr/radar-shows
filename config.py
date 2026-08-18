import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("RADAR_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "radar.sqlite3"
JSON_OUT = DATA_DIR / "oportunidades.json"

# --- PNCP ------------------------------------------------------------------
PNCP_CONSULTA = "https://pncp.gov.br/api/consulta"          # API oficial de dados abertos
PNCP_SEARCH = "https://pncp.gov.br/api/search/"             # endpoint do proprio portal (full-text)
PNCP_ITEM_URL = "https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"

# codigoModalidadeContratacao (PNCP). Os que interessam para show/cultura:
MODALIDADES = {
    1: "Leilao - Eletronico",
    2: "Dialogo Competitivo",
    3: "Concurso",
    4: "Concorrencia - Eletronica",
    5: "Concorrencia - Presencial",
    6: "Pregao - Eletronico",
    7: "Pregao - Presencial",
    8: "Dispensa de Licitacao",
    9: "Inexigibilidade",
    10: "Manifestacao de Interesse",
    11: "Pre-qualificacao",
    12: "Credenciamento",
    13: "Leilao - Presencial",
}
# Ordem de prioridade para o sweep diario
MODALIDADES_ALVO = [9, 12, 8, 3, 10]

UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
       "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
       "SP", "SE", "TO"]

# Deixe vazio para varrer o Brasil inteiro. Ex: ["SP","MG","GO","MS","MT","PR"]
UFS_FOCO = [u for u in os.getenv("RADAR_UFS", "").split(",") if u.strip()]

# --- Querido Diario --------------------------------------------------------
QD_API = "https://queridodiario.ok.org.br/api"

# --- Execucao --------------------------------------------------------------
DIAS_JANELA = int(os.getenv("RADAR_DIAS", "3"))       # quantos dias retroativos varrer
SCORE_MINIMO = int(os.getenv("RADAR_SCORE_MIN", "10"))
CONCORRENCIA = int(os.getenv("RADAR_CONCURRENCY", "6"))
TIMEOUT = float(os.getenv("RADAR_TIMEOUT", "40"))
TAM_PAGINA = 50                                        # limite pratico do PNCP
USER_AGENT = os.getenv(
    "RADAR_UA",
    "radar-shows/1.0 (monitoramento de editais culturais; contato@exemplo.com)",
)

# --- Alertas ---------------------------------------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
WEBHOOK_URL = os.getenv("RADAR_WEBHOOK", "")
