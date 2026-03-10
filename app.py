import streamlit as st
import pandas as pd
import numpy as np
from polygon import RESTClient
from datetime import datetime, time as dt_time, timedelta, date
import os
import io
import time

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Trading Hub David", page_icon="🚀", layout="wide")
st.markdown("<style>input[type='text'] {text-transform: uppercase;}</style>", unsafe_allow_html=True)

POLYGON_API_KEY = "9uWQVGlAzmX2gDu08CIoDTpj1Lpl0Xl1" 
client = RESTClient(POLYGON_API_KEY)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
EXCEL_FILE = os.path.join(DATA_DIR, "PlanStatistique.xlsx")

# --- COLONNES ---
COLONNES_CIBLES = [
    "Date", "Ticker", "Entry Time", "Stratégie", "Stratégie Combinée", "Catégorie News", "Filling",
    "SV 1min", "Heure Entrée 1m", "SV 3min", "Heure Entrée 3m",
    "Gap to Open %", "PMH to Open %", "HOD to PMH %", "Open to VWAP %",
    "Max Dev Vwap %", "HOD to LOD Drop %", "Heure HOD", "Open Push %",
    "Float (Shares)", "Float Rotation %", "Cumulative Vol 4-9AM", "PM RVOL",
    "Prev_Close ($)", "PM_High ($)", "Open_9h30 ($)", "HOD ($)", "LOD ($)", "Commentaires"
]

def charger_donnees():
    if os.path.exists(EXCEL_FILE):
        try: 
            df = pd.read_excel(EXCEL_FILE)
            if "Stratégie 2" in df.columns and "Stratégie Combinée" not in df.columns:
                df = df.rename(columns={"Stratégie 2": "Stratégie Combinée"})
            for col in COLONNES_CIBLES:
                if col not in df.columns:
                    df[col] = np.nan
            df["Stratégie"] = df["Stratégie"].astype(str).replace('nan', '')
            df["Stratégie Combinée"] = df["Stratégie Combinée"].astype(str).replace('nan', '')
            return df[COLONNES_CIBLES]
        except: 
            return pd.DataFrame(columns=COLONNES_CIBLES)
    return pd.DataFrame(columns=COLONNES_CIBLES)

def calculer_donnees_trade(ticker, trade_date):
    res = {col: 0.0 for col in COLONNES_CIBLES if "$" in col or "%" in col or "RVOL" in col}
    res.update({"Float (Shares)": "N/A", "Heure HOD": "N/A", "Cumulative Vol 4-9AM": 0})
    try:
        details = client.get_ticker_details(ticker)
        f_val = getattr(details, 'weighted_shares_outstanding', 0)
        if f_val: res["Float (Shares)"] = f"{f_val/1e6:.2f}M"
        prev_aggs = list(client.get_aggs(ticker, 1, "day", (trade_date - timedelta(days=5)).strftime("%Y-%m-%d"), (trade_date - timedelta(days=1)).strftime("%Y-%m-%d")))
        pc = prev_aggs[-1].close if prev_aggs else 0
        res["Prev_Close ($)"] = pc
        day_aggs = list(client.get_aggs(ticker, 1, "minute", trade_date.strftime("%Y-%m-%d"), trade_date.strftime("%Y-%m-%d")))
        if day_aggs:
            df = pd.DataFrame([{"dt": pd.to_datetime(a.timestamp, unit='ms', utc=True).tz_convert('America/New_York'),
                                "o": a.open, "h": a.high, "l": a.low, "c": a.close, "v": a.volume, "vw": getattr(a, 'vwap', a.close)} for a in day_aggs])
            pm_df = df[df['dt'].dt.time < dt_time(9, 30)]
            if not pm_df.empty:
                res["PM_High ($)"] = pm_df['h'].max()
                vol_pm = int(pm_df[pm_df['dt'].dt.time >= dt_time(4, 0)]['v'].sum())
                res["Cumulative Vol 4-9AM"] = vol_pm
                res["PM RVOL"] = round(vol_pm / 1000000, 2)
            rth_df = df[(df['dt'].dt.time >= dt_time(9, 30)) & (df['dt'].dt.time <= dt_time(16, 0))]
            if not rth_df.empty:
                o_val, h_val, l_val = rth_df.iloc[0]['o'], rth_df['h'].max(), rth_df['l'].min()
                res.update({"Open_9h30 ($)": o_val, "HOD ($)": h_val, "LOD ($)": l_val})
                res["Heure HOD"] = rth_df.loc[rth_df['h'].idxmax(), 'dt'].strftime('%H:%M')
                if pc > 0: res["Gap to Open %"] = round(((o_val - pc) / pc) * 100, 2)
    except Exception as e:
        st.error(f"Erreur Polygon: {e}")
    return res

# --- 3. INTERFACE ---
df_actuel = charger_donnees()
page = st.sidebar.radio("Navigation", ["Journal de Bord", "Statistiques"])

if page == "Journal de Bord":
    st.title("📓 Journal Statistique David")
    
    with st.form("trade_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        t_ticker = c1.text_input("Ticker").upper().strip()
        t_date = c2.date_input("Date du Trade", value=date.today())
        strat_options = ["Aucune", "FAILED", "Reject vwap", "Double Top DAY", "Double Top Intraday", "Niveau Dilution", "Open Drop", "Zone Morte"]
        s1 = c3.selectbox("Stratégie", strat_options)
        s_comb = c4.selectbox("Stratégie Combinée", strat_options)
        
        st.divider()
        cn1, cn2, cf1, cf2 = st.columns(4)
        with cn1: sel_news = st.multiselect("News (Sélection)", ["🌍 MACRO", "🎈 FLUFF", "💎 FONDAMENTAL", "📉 DILUTION", "📊 TECHNIQUE", "🔗 SYMPATHIE", "🗣️ RUMEUR"])
        with cn2: manual_news = st.text_input("News Manuelle", placeholder="ex: FDA...")
        with cf1: sel_fills = st.multiselect("Fillings (Sélection)", ["6-K", "8-K", "S-1", "S-1/A", "EFFECT", "424B5", "10-Q", "10-K"])
        with cf2: manual_fill = st.text_input("Filling Manuel", placeholder="ex: S-3...")
        
        cp1, cp2 = st.columns([1, 3])
        with cp1: manual_push = st.text_input("Open Push %", value="0.0")

        st.divider()
        st.markdown("**🛑 Stopping Volume**")
        c_entry, cs1_ch, cs1_h, cs2_ch, cs2_h = st.columns([1.5, 0.8, 1.5, 0.8, 1.5])
        with c_entry: t_entry_time = st.text_input("Heure Entry", placeholder="09:35")
        with cs1_ch: 
            st.markdown("<div style='height: 35px;'></div>", unsafe_allow_html=True)
            sv1_ch = st.checkbox("SV 1m")
        with cs1_h: sv1_h = st.text_input("Heure 1m ", placeholder="09:45")
        with cs2_ch: 
            st.markdown("<div style='height: 35px;'></div>", unsafe_allow_html=True)
            sv3_ch = st.checkbox("SV 3m")
        with cs2_h: sv3_h = st.text_input("Heure 3m ", placeholder="10:15")
        
        st.divider()
        comment = st.text_area("Commentaires", height=68)
        submit = st.form_submit_button("➕ ENREGISTRER LE TRADE", type="primary", use_container_width=True)

    if submit and t_ticker:
        stats = calculer_donnees_trade(t_ticker, t_date)
        all_news = list(sel_news) + ([manual_news.upper()] if manual_news.strip() else [])
        all_fills = list(sel_fills) + ([manual_fill.upper()] if manual_fill.strip() else [])
        new_row = {col: "" for col in COLONNES_CIBLES}
        new_row.update({
            "Date": t_date.strftime('%Y-%m-%d'), "Ticker": t_ticker, "Entry Time": t_entry_time,
            "Stratégie": s1, "Stratégie Combinée": s_comb, "Catégorie News": " / ".join(all_news), "Filling": " / ".join(all_fills),
            "SV 1min": "OUI" if sv1_ch else "NON", "Heure Entrée 1m": sv1_h,
            "SV 3min": "OUI" if sv3_ch else "NON", "Heure Entrée 3m": sv3_h,
            "Open Push %": manual_push, "Commentaires": comment
        })
        new_row.update(stats)
        # INSERTION EN HAUT : Le nouveau trade est placé avant l'historique actuel
        df_final = pd.concat([pd.DataFrame([new_row]), df_actuel], ignore_index=True)
        df_final.to_excel(EXCEL_FILE, index=False)
        st.success(f"✅ Trade sur {t_ticker} enregistré en haut de la liste !")
        st.rerun()

    if not df_actuel.empty:
        st.divider()
        hist_col1, hist_col2 = st.columns([4, 1])
        hist_col1.subheader("📂 Historique")
        with hist_col2:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            save_hist = st.button("💾 SAUVEGARDER", use_container_width=True)
        
        edited_df = st.data_editor(df_actuel, use_container_width=True, hide_index=True, num_rows="dynamic")
        if save_hist:
            edited_df.to_excel(EXCEL_FILE, index=False)
            st.success("Modifications enregistrées !")
            st.rerun()
        if os.path.exists(EXCEL_FILE):
            st.download_button("📥 Télécharger l'Excel complet", data=open(EXCEL_FILE, 'rb'), file_name="PlanStatistique.xlsx", use_container_width=True)

    st.divider()
    st.subheader("🔍 Testeur de Ticker")
    test_c1, test_c2, test_c3 = st.columns([2, 2, 1])
    with test_c1: test_t = st.text_input("Ticker à tester ").upper()
    with test_c2: test_d = st.date_input("Date du test ", value=date.today())
    with test_c3:
        st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 TESTER", use_container_width=True):
            if test_t:
                st.write(f"Résultats pour {test_t} au {test_d} :")
                st.table(pd.DataFrame([calculer_donnees_trade(test_t, test_d)]))

    st.divider()
    st.subheader("🛠️ Maintenance")
    if not df_actuel.empty:
        mode_m = st.radio("Recalcul :", ["Ticker spécifique", "Tout l'historique"], horizontal=True)
        t_m = None
        if mode_m == "Ticker spécifique":
            t_m = st.selectbox("Choisir le ticker :", sorted(df_actuel['Ticker'].unique()))
        if st.button("🚀 LANCER LA MISE À JOUR"):
            indices = df_actuel[df_actuel['Ticker'] == t_m].index if mode_m == "Ticker spécifique" else df_actuel.index
            df_up = df_actuel.copy()
            pb = st.progress(0)
            for i, idx in enumerate(indices):
                tk = str(df_up.loc[idx, 'Ticker']).strip().upper()
                dt_v = pd.to_datetime(df_up.loc[idx, 'Date']).date() if isinstance(df_up.loc[idx, 'Date'], str) else df_up.loc[idx, 'Date']
                res_m = calculer_donnees_trade(tk, dt_v)
                for k, v in res_m.items():
                    if mode_m == "Ticker spécifique" or pd.isna(df_up.loc[idx, k]) or df_up.loc[idx, k] in [0.0, "N/A", ""]:
                        df_up.at[idx, k] = v
                pb.progress((i + 1) / len(indices))
                time.sleep(0.1)
            df_up.to_excel(EXCEL_FILE, index=False)
            st.success("Mise à jour terminée !")
            st.rerun()
