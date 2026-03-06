import streamlit as st
import pandas as pd
import numpy as np
from polygon import RESTClient
from datetime import datetime, time as dt_time, timedelta, date
import os
import io

# --- 1. CONFIGURATION ---
POLYGON_API_KEY = "9uWQVGlAzmX2gDu08CIoDTpj1Lpl0Xl1" 
client = RESTClient(POLYGON_API_KEY)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
EXCEL_FILE = os.path.join(DATA_DIR, "PlanStatistique.xlsx")

# --- 2. LISTES GLOBALES ---
LISTE_STRATEGIES = ["Aucune", "FAILED", "Reject vwap", "Double Top PMH / HOD", "Niveau Dilution", "Open Drop", "Zone Morte"]
LISTE_FILLING_DEFAUT = ["Aucun", "6-K", "8-K", "S-1", "EFFECT", "424B3", "424B5", "13G", "FORM 1-A", "AUTRE..."]
LISTE_HEURES = ["NONE"] + [f"{h:02d}" for h in range(7, 17)]
LISTE_MINUTES = [f"{m:02d}" for m in range(60)]

DICT_CAT_NEWS = {
    "AUCUNE": "🔘 AUCUNE",
    "MACRO (Zone Interdite)": "🔴 MACRO",
    "FLUFF (Cible Idéale)": "🟢 FLUFF",
    "FONDAMENTAL (Prudence)": "🟡 FONDAMENTAL",
    "DILUTION (Offering/Split)": "💸 DILUTION",
    "SYMPATHIE (Secteur)": "🤝 SYMPATHIE",
    "RUMEUR (Twitter/X)": "🔥 RUMEUR",
    "TECHNIQUE (No News)": "📊 TECHNIQUE",
    "AUTRE": "⚪ AUTRE"
}

# --- 3. FONCTIONS ---

@st.cache_data(ttl=3600)
def get_ticker_details_cached(ticker):
    try:
        details = client.get_ticker_details(ticker)
        return getattr(details, 'weighted_shares_outstanding', 0)
    except: return 0

def get_avg_pm_basis(ticker, target_date):
    try:
        start_h = (target_date - timedelta(days=10)).strftime("%Y-%m-%d")
        end_h = (target_date - timedelta(days=1)).strftime("%Y-%m-%d")
        hist = list(client.get_aggs(ticker, 1, "day", start_h, end_h, adjusted=True))
        return np.mean([a.volume for a in hist]) * 0.15 if hist else 1.0
    except: return 1.0

def get_stat(target_ticker, target_date, s1, s2, selected_cats, filling_val, entry_time, comment_text):
    start_s = (target_date - timedelta(days=5)).strftime("%Y-%m-%d")
    end_s = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        raw_float = get_ticker_details_cached(target_ticker)
        float_display = f"{raw_float / 1_000_000:.2f}M" if raw_float >= 1_000_000 else str(raw_float)
        
        aggs = list(client.get_aggs(target_ticker, 1, "minute", from_=start_s, to=end_s, limit=50000, adjusted=True))
        if not aggs: return None, "Aucune donnée trouvée."

        data = []
        for a in aggs:
            ts = pd.to_datetime(a.timestamp, unit='ms', utc=True).tz_convert('America/New_York')
            data.append({"date": ts.date(), "time": ts.time(), "o": float(a.open), "h": float(a.high), "l": float(a.low), "c": float(a.close), "v": a.volume})
        
        df_temp = pd.DataFrame(data)
        day_df = df_temp[df_temp['date'] == target_date].copy()
        if day_df.empty: return None, "Aucune donnée pour ce jour."
        
        # Calcul du volume cumulatif 4AM - 9AM
        vol_4_9_df = day_df[(day_df['time'] >= dt_time(4, 0)) & (day_df['time'] < dt_time(9, 0))]
        cum_vol_4_9 = vol_4_9_df['v'].sum() if not vol_4_9_df.empty else 0
        
        pm_df = day_df[day_df['time'] < dt_time(9, 30)]
        current_pm_vol = pm_df['v'].sum() if not pm_df.empty else 0
        avg_basis = get_avg_pm_basis(target_ticker, target_date)

        rth_df = day_df[(day_df['time'] >= dt_time(9, 30)) & (day_df['time'] <= dt_time(12, 0))].copy()
        y_close_rows = df_temp[df_temp['date'] < target_date]
        y_close = y_close_rows.iloc[-1]['c'] if not y_close_rows.empty else day_df.iloc[0]['o']
        
        open_930 = float(rth_df.iloc[0]['o']) if not rth_df.empty else 0
        hod_12h = float(rth_df['h'].max()) if not rth_df.empty else 0
        lod_12h = float(rth_df['l'].min()) if not rth_df.empty else 0
        hod_time = rth_df.loc[rth_df['h'].idxmax(), 'time'] if not rth_df.empty else "N/A"

        news_display = " / ".join([DICT_CAT_NEWS[cat] for cat in selected_cats]) if selected_cats else "🔘 AUCUNE"

        row = {
            "Date": target_date.strftime("%Y-%m-%d"),
            "Ticker": target_ticker.upper(),
            "Float (Shares)": float_display,
            "Float Rotation %": f"{(current_pm_vol / raw_float * 100) if raw_float > 0 else 0:.2f}%", 
            "Cumulative Vol 4-9AM": f"{cum_vol_4_9:,}",
            "PM RVOL": f"{(current_pm_vol / avg_basis) if avg_basis > 0 else 0:.2f}x",
            "Catégorie News": news_display,
            "Stratégie": s1 if s1 != "Aucune" else "",
            "Stratégie Combinée": s2 if s2 != "Aucune" else "",
            "Entry After 1min Red": entry_time,
            "Gap to Open %": round(((open_930 - y_close) / y_close) * 100, 2) if y_close != 0 else 0,
            "HOD to LOD Drop %": round(((lod_12h - hod_12h) / hod_12h) * 100, 2) if hod_12h != 0 else 0,
            "Heure HOD": str(hod_time),
            "Prev_Close ($)": y_close,
            "PM_High ($)": float(pm_df['h'].max()) if not pm_df.empty else 0,
            "Open_9h30 ($)": open_930,
            "HOD ($)": hod_12h,
            "LOD ($)": lod_12h,
            "Filling": filling_val,
            "Commentaires": comment_text
        }
        return pd.DataFrame([row]), "Succès"
    except Exception as e: return None, f"Erreur : {str(e)[:25]}"

# --- 4. INTERFACE ---
st.set_page_config(page_title="Plan Statistique", layout="wide")
st.markdown("<style>input {text-transform: uppercase;}</style>", unsafe_allow_html=True)
st.title("📈 Générateur de Plan Statistique")

col_t, col_d, col_s1, col_s2 = st.columns(4)
with col_t: t_ticker = st.text_input("Ticker").upper() 
with col_d: t_date = st.date_input("Date", value=date.today() - timedelta(days=1))
with col_s1: s1 = st.selectbox("Stratégie", LISTE_STRATEGIES)
with col_s2: s2 = st.selectbox("Stratégie Combinée", LISTE_STRATEGIES)

st.write("---")
c_h, c_m, c_cat, c_fill = st.columns([1, 1, 3, 2])
with c_h: h_sel = st.selectbox("Heure", LISTE_HEURES)
with c_m: m_sel = st.selectbox("Min", LISTE_MINUTES)
with c_cat: sel_news = st.multiselect("Catégories News", list(DICT_CAT_NEWS.keys()))
with c_fill:
    fill_sel = st.multiselect("Filling Type", LISTE_FILLING_DEFAUT)
    custom_fill = st.text_input("👉 Précisez") if "AUTRE..." in fill_sel else ""

comment = st.text_area("Commentaires")
submitted = st.button("➕ Ajouter au Plan", type="primary")

if submitted and t_ticker:
    entry_f = "" if h_sel == "NONE" else f"{h_sel}:{m_sel}"
    filling_l = [f for f in fill_sel if f not in ["AUTRE...", "Aucun"]]
    if custom_fill: filling_l.append(custom_fill)
    filling_str = ", ".join(filling_l) if filling_l else "Aucun"
    
    res, msg = get_stat(t_ticker, t_date, s1, s2, sel_news, filling_str, entry_f, comment)
    
    if res is not None:
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            final_df = pd.concat([df, res], ignore_index=True)
        else: final_df = res

        target_order = ["Date", "Ticker", "Float (Shares)", "Float Rotation %", "Cumulative Vol 4-9AM", "PM RVOL", "Catégorie News"]
        all_cols = list(final_df.columns)
        new_cols = [c for c in target_order if c in all_cols] + [c for c in all_cols if c not in target_order]
        
        final_df[new_cols].sort_values(by="Date", ascending=True).to_excel(EXCEL_FILE, index=False)
        st.success(f"✅ {t_ticker} ajouté !"); st.rerun()
    else: st.error(msg)

# --- 5. ÉDITEUR ---
st.divider()
if os.path.exists(EXCEL_FILE):
    df_view = pd.read_excel(EXCEL_FILE)
    
    # Header et Sauvegarde alignés
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1: 
        st.subheader(f"Journal ({len(df_view)} entrées) - Récents en haut")
    
    df_sorted = df_view.sort_values(by="Date", ascending=False)
    edited_df = st.data_editor(df_sorted, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    with h_col2:
        if st.button("💾 SAUVEGARDER", type="primary", use_container_width=True):
            edited_df.sort_values(by="Date", ascending=True).to_excel(EXCEL_FILE, index=False)
            st.success("Enregistré !"); st.rerun()

    # 📥 BOUTON DE TÉLÉCHARGEMENT (NOM FIXE)
    st.write("") 
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_view.sort_values(by="Date", ascending=True).to_excel(writer, index=False)
    
    st.download_button(
        label="📥 Télécharger le fichier Excel",
        data=buffer.getvalue(),
        file_name="PlanStatistique.xlsx", # 👈 Nom du fichier corrigé
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
