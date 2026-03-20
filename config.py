import pytz
import os

# --- API & FICHIERS ---
POLYGON_API_KEY = "9uWQVGlAzmX2gDu08CIoDTpj1Lpl0Xl1"
DATA_DIR = "data"
EXCEL_FILE = os.path.join(DATA_DIR, "PlanStatistique.xlsx")

# --- TIMEZONE ---
TZ_NY = pytz.timezone('America/New_York')

# --- TOUTES LES COLONNES (EXCEL) ---
COLONNES_CIBLES = [
    "Date", "Ticker", "Stratégie", "Stratégie Combinée", "Catégorie News", "Filling",
    "SV 1min", "Heure Entrée 1m", "SV 3min", "Heure Entrée 3m",
    "Gap to Open %", "PMH to Open %", "HOD to PMH %", "Open to VWAP %",
    "Max Dev Vwap %", "HOD to LOD Drop %", "Heure HOD", "Open Push %",
    "Float (Shares)", "Float Rotation %", "Cumulative Vol 4-9AM", "PM RVOL",
    "Prev_Close ($)", "PM_High ($)", "Open_9h30 ($)", "HOD ($)", "LOD ($)", "Commentaires"
]

# --- COLONNES POUR LE TESTEUR ---
COLONNES_TESTEUR = [
    "Date", "Ticker", "Gap to Open %", "PMH to Open %", "HOD to PMH %", 
    "Open to VWAP %", "Max Dev Vwap %", "HOD to LOD Drop %", "Heure HOD", 
    "Float (Shares)", "Cumulative Vol 4-9AM", "PM RVOL", "Prev_Close ($)", 
    "PM_High ($)", "Open_9h30 ($)", "HOD ($)", "LOD ($)"
]
