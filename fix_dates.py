import pandas as pd
import os
import re
from datetime import datetime

# --- CONFIGURATION ---
EXCEL_FILE = "/app/data/PlanStatistique.xlsx"

MOIS_FR_MAP = {
    'janvier': 1, 'jan': 1, 'février': 2, 'fevrier': 2, 'fev': 2,
    'mars': 3, 'mar': 3, 'avril': 4, 'avr': 4, 'mai': 5,
    'juin': 6, 'juillet': 7, 'jul': 7, 'août': 8, 'aout': 8, 'aou': 8,
    'septembre': 9, 'sep': 9, 'octobre': 10, 'oct': 10,
    'novembre': 11, 'nov': 11, 'décembre': 12, 'decembre': 12, 'dec': 12
}

def clean_to_iso(val):
    """Transforme '2 mars 26' ou n'importe quoi en '2026-03-02'"""
    if pd.isna(val) or str(val).strip() == "":
        return val
    
    s = str(val).lower().strip()
    
    # Si c'est déjà au format AAAA-MM-JJ, on valide juste
    if re.match(r'\d{4}-\d{2}-\d{2}', s):
        return s

    try:
        # Tentative de parsing du format '2 mars 26'
        parts = re.findall(r'[a-zâéû]+|\d+', s)
        if len(parts) == 3:
            day = int(parts[0])
            month_str = parts[1]
            year_short = int(parts[2])
            
            month = MOIS_FR_MAP.get(month_str, 1)
            year = 2000 + year_short if year_short < 100 else year_short
            
            return datetime(year, month, day).strftime('%Y-%m-%d')
    except:
        pass

    # Dernier recours : laisser pandas deviner
    try:
        return pd.to_datetime(s).strftime('%Y-%m-%d')
    except:
        return val

# 1. Chargement
print(f"Ouverture de {EXCEL_FILE}...")
df = pd.read_excel(EXCEL_FILE)

# 2. Conversion
print("Conversion vers le format AAAA-MM-JJ...")
df['Date'] = df['Date'].apply(clean_to_iso)

# 3. Tri final pour être propre
print("Tri chronologique final...")
df = df.sort_values(by='Date', ascending=True)

# 4. Sauvegarde
df.to_excel(EXCEL_FILE, index=False)
print("✅ Conversion terminée ! Toutes les dates sont au format ISO.")
