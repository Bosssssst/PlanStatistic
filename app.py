import streamlit as st
import pandas as pd
import numpy as np
from polygon import RESTClient
from datetime import datetime, time as dt_time, timedelta, date
import os
import io

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

# --- FONCTIONS DE CALCUL ---
def get_avg_pm_basis(ticker, target_date):
    try:
        start_h = (target_date - timedelta(days=10)).strftime("%Y-%m-%d")
        end_h = (target_date - timedelta(days=1)).strftime("%Y-%m-%d")
        hist = list(client.get_aggs(ticker, 1, "day", start_h, end_h, adjusted=True))
        if not hist: return 1.0
        return np.mean([a.volume for a in hist]) * 0.15
    except: return 1.0

def get_stat(target_ticker, target_date, s1, s2, news_val, filling_val, entry_time, comment_text):
    start_s = (target_date - timedelta(days=5)).strftime("%Y-%m-%d")
    end_s = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        details = client.get_ticker_details(target_ticker)
        raw_float = getattr(details, 'weighted_shares_outstanding', 0)
        float_display = f"{raw_float / 1_000_000:.2f}M" if raw_float >= 1_000_000 else str(raw_float)
        aggs = list(client.get_aggs(target_ticker, 1, "minute", from_=start_s, to=end_s, limit=50000, adjusted=True))
    except Exception as e: return None, f"Erreur API : {e}"
    
    if not aggs: return None, "Aucune donnée trouvée."

    data = []
    for a in aggs:
        ts = pd.to_datetime(a.timestamp, unit='ms', utc=True).tz_convert('America/New_York')
        data.append({"date": ts.date(), "time": ts.time(), "o": float(a.open), "h": float(a.high), "l": float(a.low), "c": float(a.close), "v": a.volume, "vwap_candle": float(a.vwap)})
    df_temp = pd.DataFrame(data)
    day_df = df_temp[df_temp['date'] == target_date].copy()
    if day_df.empty: return None, "Aucune donnée pour ce jour."
    
    pm_df = day_df[day_df['time'] < dt_time(9, 30)]
    current_pm_vol = pm_df['v'].sum() if not pm_df.empty else 0
    
    float_rot_raw = (current_pm_vol / raw_float * 100) if raw_float > 0 else 0.0
    avg_basis = get_avg_pm_basis(target_ticker, target_date)
    rvol_raw = current_pm_vol / avg_basis if avg_basis > 0 else 0.0

    rth_df = day_df[(day_df['time'] >= dt_time(9, 30)) & (day_df['time'] <= dt_time(12, 0))].copy()
    y_close = df_temp[df_temp['date'] < target_date].iloc[-1]['c'] if not df_temp[df_temp['date'] < target_date].empty else day_df.iloc[0]['o']
    day_df['VWAP'] = (day_df['vwap_candle'] * day_df['v']).cumsum() / day_df['v'].cumsum()
    
    open_930 = float(rth_df.iloc[0]['o'])
    hod_12h, lod_12h = float(rth_df['h'].max()), float(rth_df['l'].min())
    hod_time = rth_df.loc[rth_df['h'].idxmax(), 'time']

    row = {
        "Date": target_date.strftime("%Y-%m-%d"),
        "Ticker": target_ticker.upper(),
        "Float (Shares)": float_display,
        "Float Rotation %": f"{float_rot_raw:.2f}%", 
        "PM RVOL": f"{rvol_raw:.2f}x",
        "Stratégie": s1 if s1 != "Aucune" else "",
        "Stratégie Combinée": s2 if s2 != "Aucune" else "",
        "Entry After 1min Red": entry_time,
        "Gap to Open %": round(((open_930 - y_close) / y_close) * 100, 2),
        "HOD to LOD Drop %": round(((lod_12h - hod_12h) / hod_12h) * 100, 2),
        "Heure HOD": str(hod_time),
        "Prev_Close ($)": y_close,
        "PM_High ($)": float(pm_df['h'].max()) if not pm_df.empty else 0,
        "Open_9h30 ($)": open_930,
        "HOD ($)": hod_12h,
        "LOD ($)": lod_12h,
        "NEWS": news_val,
        "Filling": filling_val,
        "Commentaires": comment_text
    }
    return pd.DataFrame([row]), "Succès"

# --- INTERFACE ---
st.set_page_config(page_title="Plan Statistique", layout="wide")

# 🚀 INJECTION CSS POUR FORCER LES MAJUSCULES VISUELLES
st.markdown("""
    <style>
        input {
            text-transform: uppercase;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Générateur de Plan Statistique")

st.write("### Ajouter une entrée")
col_t, col_d, col_s1, col_s2 = st.columns(4)
# On garde le .upper() en Python pour la sécurité des données
with col_t: t_ticker = st.text_input("Ticker").upper() 
with col_d: t_date = st.date_input("Date", value=date.today() - timedelta(days=1))
with col_s1: s1 = st.selectbox("Stratégie", LISTE_STRATEGIES)
with col_s2: s2 = st.selectbox("Stratégie Combinée", LISTE_STRATEGIES)

st.write("---")
c_h, c_m, c_news, c_fill = st.columns([1, 1, 2, 2])
with c_h: h_sel = st.selectbox("Heure", LISTE_HEURES)
with c_m: m_sel = st.selectbox("Min", LISTE_MINUTES)
with c_news: st.write(""); news_checked = st.checkbox("NEWS")
with c_fill:
    fill_sel = st.multiselect("Filling Type", LISTE_FILLING_DEFAUT)
    custom_fill = ""
    if "AUTRE..." in fill_sel:
        custom_fill = st.text_input("👉 Précisez le type")

comment = st.text_area("Commentaires")
submitted = st.button("➕ Ajouter au Plan", type="primary")

if submitted and t_ticker:
    entry_time_f = "" if h_sel == "NONE" else f"{h_sel}:{m_sel}"
    filling_list = [f for f in fill_sel if f not in ["AUTRE...", "Aucun"]]
    if custom_fill: filling_list.append(custom_fill)
    filling_f = ", ".join(filling_list) if filling_list else "Aucun"
    
    res, msg = get_stat(t_ticker, t_date, s1, s2, ("Yes" if news_checked else "No"), filling_f, entry_time_f, comment)
    
    if res is not None:
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            if "Commentaire" in df.columns: df.rename(columns={"Commentaire": "Commentaires"}, inplace=True)
            final_df = pd.concat([df, res], ignore_index=True)
        else: final_df = res

        # Réorganisation blindée
        all_cols = list(final_df.columns)
        target_order = ["Date", "Ticker", "Float (Shares)", "Float Rotation %", "PM RVOL"]
        new_cols = [c for c in target_order if c in all_cols]
        new_cols += [c for c in all_cols if c not in target_order]
        
        final_df = final_df[new_cols]
        final_df.sort_values(by="Date", ascending=True).to_excel(EXCEL_FILE, index=False)
        st.success(f"✅ {t_ticker} ajouté !"); st.rerun()
    else: st.error(msg)

# --- ÉDITEUR ---
st.divider()
if os.path.exists(EXCEL_FILE):
    df_view = pd.read_excel(EXCEL_FILE)
    if "Commentaire" in df_view.columns: df_view.rename(columns={"Commentaire": "Commentaires"}, inplace=True)
    st.subheader(f"Journal ({len(df_view)} entrées)")
    edited_df = st.data_editor(df_view, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    col_save, col_down = st.columns([1, 1])
    with col_save:
        if st.button("💾 SAUVEGARDER LES MODIFICATIONS"):
            edited_df.sort_values(by="Date", ascending=True).to_excel(EXCEL_FILE, index=False)
            st.success("Journal mis à jour !"); st.rerun()
    with col_down:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_view.to_excel(writer, index=False)
        st.download_button(label="📥 Télécharger Journal", data=buffer.getvalue(), file_name="PlanStatistique_Journal.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
