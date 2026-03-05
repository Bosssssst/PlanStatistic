import streamlit as st
import pandas as pd
from polygon import RESTClient
from datetime import datetime, time as dt_time, timedelta, date
import os

# --- CONFIGURATION ---
API_KEY = "9uWQVGlAzmX2gDu08CIoDTpj1Lpl0Xl1" 
client = RESTClient(API_KEY)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
EXCEL_FILE = os.path.join(DATA_DIR, "PlanStatistique.xlsx")

# Listes pour les menus
LISTE_STRATEGIES = ["Aucune", "FAILED", "Reject vwap", "Double Top PMH / HOD", "Niveau Dilution", "Open Drop", "Zone Morte"]
LISTE_FILLING_DEFAUT = ["Aucun", "6-K", "8-K", "S-1", "EFFECT", "424B3", "424B5", "13G", "FORM 1-A", "AUTRE..."]
LISTE_HEURES = ["NONE"] + [f"{h:02d}" for h in range(7, 17)]
LISTE_MINUTES = [f"{m:02d}" for m in range(60)]

# --- FONCTION D'ANALYSE ---
def get_stat(target_ticker, target_date, s1, s2, news_val, filling_val, entry_time, comment_text):
    start_s = (target_date - timedelta(days=5)).strftime("%Y-%m-%d")
    end_s = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
    
    try:
        # Récupération du Float
        details = client.get_ticker_details(target_ticker)
        raw_float = getattr(details, 'weighted_shares_outstanding', 0)
        if raw_float >= 1_000_000:
            float_display = f"{raw_float / 1_000_000:.2f}M"
        elif raw_float >= 1_000:
            float_display = f"{raw_float / 1_000:.2f}K"
        else:
            float_display = str(raw_float)

        aggs = list(client.get_aggs(target_ticker, 1, "minute", from_=start_s, to=end_s, limit=50000, adjusted=True))
    except Exception as e: return None, f"Erreur API : {e}"
    
    if not aggs: return None, "Aucune donnée trouvée."

    data = []
    for a in aggs:
        ts = pd.to_datetime(a.timestamp, unit='ms', utc=True).tz_convert('America/New_York')
        data.append({"date": ts.date(), "time": ts.time(), "o": float(a.open), "h": float(a.high), "l": float(a.low), "c": float(a.close), "v": a.volume, "vwap_candle": float(a.vwap)})
    df_temp = pd.DataFrame(data)
    
    unique_dates = sorted(df_temp['date'].unique())
    if target_date not in unique_dates: return None, "Aucune donnée pour ce jour."
    
    idx = unique_dates.index(target_date)
    y_close = df_temp[df_temp['date'] == unique_dates[idx-1]].iloc[-1]['c'] if idx > 0 else df_temp[df_temp['date'] == target_date].iloc[0]['o']
    
    day_df = df_temp[df_temp['date'] == target_date].copy()
    day_df['VWAP'] = (day_df['vwap_candle'] * day_df['v']).cumsum() / day_df['v'].cumsum()
    
    pm_df = day_df[day_df['time'] < dt_time(9, 30)]
    rth_df = day_df[(day_df['time'] >= dt_time(9, 30)) & (day_df['time'] <= dt_time(12, 0))].copy()
    
    if rth_df.empty: return None, "Pas de données après 9h30."
    
    pm_high = float(pm_df['h'].max()) if not pm_df.empty else 0
    open_930, vwap_930 = float(rth_df.iloc[0]['o']), float(rth_df.iloc[0]['VWAP'])
    hod_12h, lod_12h = float(rth_df['h'].max()), float(rth_df['l'].min())
    hod_time = rth_df.loc[rth_df['h'].idxmax(), 'time']

    row = {
        "Date": target_date.strftime("%Y-%m-%d"), # 🟢 Format AAAA-MM-JJ
        "Ticker": target_ticker.upper(),
        "Float (Shares)": float_display,
        "Stratégie": "" if s1 == "Aucune" else s1,
        "Stratégie Combinée": "" if s2 == "Aucune" else s2,
        "Entry After 1min Red": entry_time,
        "Gap to Open %": round(((open_930 - y_close) / y_close) * 100, 2),
        "PMH to Open %": round(((open_930 - pm_high) / pm_high) * 100, 2) if pm_high > 0 else 0,
        "HOD to PMH %": round(((hod_12h - pm_high) / pm_high) * 100, 2) if pm_high > 0 else 0,
        "Open to VWAP %": round(((open_930 - vwap_930) / vwap_930) * 100, 2),
        "Max Dev Vwap %": round(float(((rth_df['h'] - rth_df['VWAP']) / rth_df['VWAP'] * 100).max()), 2),
        "Open to HOD %": round(((hod_12h - open_930) / open_930) * 100, 2),
        "HOD to LOD Drop %": round(((lod_12h - hod_12h) / hod_12h) * 100, 2),
        "Heure HOD": str(hod_time),
        "Prev_Close ($)": y_close,
        "PM_High ($)": pm_high,
        "Open_9h30 ($)": open_930,
        "HOD ($)": hod_12h,
        "LOD ($)": lod_12h,
        "NEWS": news_val,
        "Filling": filling_val,
        "Commentaire": comment_text
    }
    return pd.DataFrame([row]), "Succès"

# --- INTERFACE ---
st.set_page_config(page_title="Plan Statistique", layout="wide")
st.title("📈 Générateur de Plan Statistique")

with st.form("stat_form", clear_on_submit=True):
    col_t, col_d, col_s1, col_s2 = st.columns(4)
    with col_t: t_ticker = st.text_input("Ticker").upper()
    with col_d: t_date = st.date_input("Date", value=date.today() - timedelta(days=1))
    with col_s1: s1 = st.selectbox("Stratégie", LISTE_STRATEGIES)
    with col_s2: s2 = st.selectbox("Stratégie Combinée", LISTE_STRATEGIES)
    
    st.write("---")
    st.write("**Entry After 1Min Red**")
    c_h, c_m, c_news, c_fill = st.columns([1, 1, 1, 3])
    with c_h: h_sel = st.selectbox("Heure", LISTE_HEURES)
    with c_m: m_sel = st.selectbox("Min", LISTE_MINUTES)
    with c_news: st.write(""); news_checked = st.checkbox("NEWS")
    with c_fill:
        fill_sel = st.selectbox("Filling Type", LISTE_FILLING_DEFAUT)
        custom_fill = st.text_input("Saisir personnalisé") if fill_sel == "AUTRE..." else ""
    
    comment = st.text_area("Commentaire")
    submitted = st.form_submit_button("Ajouter au Plan")

if submitted:
    if not t_ticker:
        st.warning("Veuillez entrer un Ticker.")
    else:
        entry_time_final = "" if h_sel == "NONE" else f"{h_sel}:{m_sel}"
        filling_final = custom_fill if fill_sel == "AUTRE..." else ("" if fill_sel == "Aucun" else fill_sel)
        news_final = "Yes" if news_checked else "No"
        
        if os.path.exists(EXCEL_FILE):
            existing_df = pd.read_excel(EXCEL_FILE)
            res, msg = get_stat(t_ticker.upper(), t_date, s1, s2, news_final, filling_final, entry_time_final, comment)
            if res is not None:
                final_df = pd.concat([existing_df, res], ignore_index=True)
                # 🟢 Tri ultra-simple grâce au format AAAA-MM-JJ
                final_df = final_df.sort_values(by="Date", ascending=True)
                final_df.to_excel(EXCEL_FILE, index=False)
                st.success("✅ Ajouté et Trié !"); st.rerun()
            else: st.error(msg)
        else:
            res, msg = get_stat(t_ticker.upper(), t_date, s1, s2, news_final, filling_final, entry_time_final, comment)
            if res is not None:
                res.to_excel(EXCEL_FILE, index=False)
                st.success("✅ Journal créé !"); st.rerun()

# --- ÉDITEUR ---
st.divider()
if os.path.exists(EXCEL_FILE):
    df_view = pd.read_excel(EXCEL_FILE)
    st.subheader(f"Journal ({len(df_view)} entrées)")
    edited_df = st.data_editor(df_view, num_rows="dynamic", use_container_width=True, hide_index=True)

    if not edited_df.equals(df_view):
        if st.button("💾 SAUVEGARDER LES MODIFICATIONS"):
            # 🟢 Tri automatique avant sauvegarde
            edited_df = edited_df.sort_values(by="Date", ascending=True)
            edited_df.to_excel(EXCEL_FILE, index=False)
            st.success("Journal mis à jour !"); st.rerun()
