import pandas as pd
import requests
import time
import os
import re
from datetime import datetime, time as dt_time

# --- CONFIGURATION ---
API_KEY = "9uWQVGlAzmX2gDu08CIoDTpj1Lpl0Xl1"
EXCEL_FILE = "/app/data/PlanStatistique.xlsx"

# Dictionnaire de traduction des mois français
MOIS_FR = {
    'jan': '01', 'janvier': '01',
    'fev': '02', 'février': '02', 'fevrier': '02',
    'mar': '03', 'mars': '03',
    'avr': '04', 'avril': '04',
    'mai': '05',
    'jun': '06', 'juin': '06',
    'jul': '07', 'juillet': '07',
    'aou': '08', 'août': '08', 'aout': '08',
    'sep': '09', 'septembre': '09',
    'oct': '10', 'octobre': '10',
    'nov': '11', 'novembre': '11',
    'dec': '12', 'décembre': '12', 'decembre': '12'
}

def clean_fr_date(date_val):
    """Convertit '2 mars 26' ou '20 fev 26' en '2026-MM-DD'"""
    s = str(date_val).lower().strip()
    # Si c'est déjà au format ISO YYYY-MM-DD, on ne touche à rien
    if re.match(r'\d{4}-\d{2}-\d{2}', s):
        return s
    
    # On découpe la chaîne (ex: ['2', 'mars', '26'])
    parts = re.findall(r'[a-zâéû]+|\d+', s)
    if len(parts) == 3:
        day = parts[0].zfill(2)
        month_str = parts[1]
        year = parts[2]
        
        # Correction de l'année (26 -> 2026)
        if len(year) == 2: year = "20" + year
        
        # Traduction du mois
        month = MOIS_FR.get(month_str, "01")
        return f"{year}-{month}-{day}"
    return s

if not os.path.exists(EXCEL_FILE):
    print(f"Erreur : Le fichier {EXCEL_FILE} est introuvable.")
    exit()

df = pd.read_excel(EXCEL_FILE)

# On cible uniquement les lignes vides
mask_missing = df['Prev_Close ($)'].isna() | (df['Prev_Close ($)'] == 0) | (df['Prev_Close ($)'] == "")
rows_to_fix = df[mask_missing]

print(f"Correction de {len(rows_to_fix)} entrées avec support des dates en français.")

for index, row in rows_to_fix.iterrows():
    ticker = str(row['Ticker']).upper()
    
    # 🟢 Nettoyage de la date spécifique au format français
    date_str = clean_fr_date(row['Date'])
    
    try:
        # Validation finale par pandas
        date_iso = pd.to_datetime(date_str).strftime('%Y-%m-%d')
        print(f"[{ticker} - {date_iso}] Analyse en cours...")
        
        # 1. Previous Close
        prev_url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={API_KEY}"
        r_prev = requests.get(prev_url)
        
        if r_prev.status_code == 429:
            print("🛑 Limite API atteinte (429). Pause de 65 secondes...")
            time.sleep(65)
            continue 

        prev_data = r_prev.json()
        prev_close = prev_data.get('results', [{}])[0].get('c', 0)
        time.sleep(13) # Délai de sécurité

        # 2. Données minute
        aggs_url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{date_iso}/{date_iso}?adjusted=true&sort=asc&apiKey={API_KEY}"
        r_aggs = requests.get(aggs_url)
        results = r_aggs.json().get('results', [])

        if results:
            temp_data = []
            for a in results:
                ts = pd.to_datetime(a['t'], unit='ms', utc=True).tz_convert('America/New_York')
                temp_data.append({'time': ts.time(), 'h': a['h'], 'l': a['l'], 'o': a['o']})
            
            t_df = pd.DataFrame(temp_data)
            pm_df = t_df[t_df['time'] < dt_time(9, 30)]
            rth_df = t_df[(t_df['time'] >= dt_time(9, 30)) & (t_df['time'] <= dt_time(12, 0))]

            if not rth_df.empty:
                df.at[index, 'Prev_Close ($)'] = prev_close
                df.at[index, 'PM_High ($)'] = pm_df['h'].max() if not pm_df.empty else 0
                df.at[index, 'Open_9h30 ($)'] = rth_df.iloc[0]['o']
                df.at[index, 'HOD ($)'] = rth_df['h'].max()
                df.at[index, 'LOD ($)'] = rth_df['l'].min()
                print(f"✅ Succès pour {ticker}")
            else:
                print(f"⚠️ Pas de données RTH pour {ticker}")
        else:
            print(f"❌ Données minute introuvables pour {ticker} le {date_iso}")

        # Sauvegarde
        df.to_excel(EXCEL_FILE, index=False)
        time.sleep(13)

    except Exception as e:
        print(f"❌ Erreur sur {ticker} : {e}")
        time.sleep(10)

print("\nHistorique mis à jour !")
