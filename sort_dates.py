import pandas as pd
import os
import re
from datetime import datetime

# --- CONFIGURATION ---
EXCEL_FILE = "/app/data/PlanStatistique.xlsx"

MOIS_FR_MAP = {
    'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6,
    'juillet': 7, 'août': 8, 'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
}

MOIS_FR_LIST = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]

def to_datetime(val):
    """Convertit '2 mars 26' en objet datetime pour le tri"""
    try:
        parts = str(val).split()
        if len(parts) == 3:
            day = int(parts[0])
            month = MOIS_FR_MAP.get(parts[1].lower(), 1)
            year = 2000 + int(parts[2])
            return datetime(year, month, day)
    except:
        pass
    return pd.to_datetime(val, errors='coerce')

def to_str_format(dt):
    """Convertit datetime en '2 mars 26'"""
    if pd.isna(dt): return ""
    return f"{dt.day} {MOIS_FR_LIST[dt.month - 1]} {str(dt.year)[-2:]}"

# 1. Chargement
df = pd.read_excel(EXCEL_FILE)

# 2. Tri chronologique
print("Tri chronologique en cours...")
df['temp_date'] = df['Date'].apply(to_datetime)
df = df.sort_values(by='temp_date', ascending=True)

# 3. Ré-application du format texte
df['Date'] = df['temp_date'].apply(to_str_format)
df = df.drop(columns=['temp_date'])

# 4. Sauvegarde
df.to_excel(EXCEL_FILE, index=False)
print("✅ Historique trié du plus vieux au plus récent !")
