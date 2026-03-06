import streamlit as st
import pandas as pd
import numpy as np
import requests
from polygon import RESTClient
from datetime import datetime, time as dt_time, timedelta, date
import os
import io

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Trading Hub David",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INJECTION CSS POUR FORCER LES MAJUSCULES VISUELLES ---
st.markdown("""
    <style>
    input[type="text"] {
        text-transform: uppercase;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURATION API ---
POLYGON_API_KEY = "9uWQVGlAzmX2gDu08CIoDTpj1Lpl0Xl1" 
client = RESTClient(POLYGON_API_KEY)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
EXCEL_FILE = os.path.join(DATA_DIR, "PlanStatistique.xlsx")

# --- 3. NAVIGATION (SIDEBAR) ---
st.sidebar.title("🚀 Trading Hub David")
page = st.sidebar.radio("Navigation", ["Plan Statistique", "Scanner Dilution (News)", "Statistiques"])
st.sidebar.divider()
st.sidebar.info(f"📍 Trois-Rivières\n🕒 {datetime.now().strftime('%H:%M')} EST")

# ==========================================
# PAGE 1 : PLAN STATISTIQUE (Intouché)
# ==========================================
if page == "Plan Statistique":
    st.title("📈 Journal Statistique Professionnel")
    
    LISTE_STRATEGIES = ["Aucune", "FAILED", "Reject vwap", "Double Top PMH / HOD", "Niveau Dilution", "Open Drop", "Zone Morte"]
    LISTE_FILLING_DEFAUT = ["Aucun", "6-K", "8-K", "S-1", "EFFECT", "424B3", "424B5", "13G", "FORM 1-A", "AUTRE..."]
    LISTE_HEURES = ["NONE"] + [f"{h:02d}" for h in range(7, 17)]
    LISTE_MINUTES = [f"{m:02d}" for m in range(60)]
    DICT_CAT_NEWS = {
        "AUCUNE": "🔘 AUCUNE", "MACRO": "🔴 MACRO", "FLUFF": "🟢 FLUFF",
        "FONDAMENTAL": "🟡 FONDAMENTAL", "DILUTION": "💸 DILUTION",
        "SYMPATHIE": "🤝 SYMPATHIE", "RUMEUR": "🔥 RUMEUR", "TECHNIQUE": "📊 TECHNIQUE"
    }

    with st.container():
        c1, c2, c3, c4 = st.columns(4)
        with c1: t_ticker = st.text_input("Ticker").upper()
        with c2: t_date = st.date_input("Date du Trade", value=date.today() - timedelta(days=1))
        with c3: s1 = st.selectbox("Stratégie 1", LISTE_STRATEGIES)
        with c4: s2 = st.selectbox("Stratégie 2 (Optionnelle)", LISTE_STRATEGIES)

    st.write("---")
    
    with st.container():
        c_h, c_m, c_cat, c_fill = st.columns([1, 1, 3, 2])
        with c_h: h_sel = st.selectbox("Heure Entry", LISTE_HEURES)
        with c_m: m_sel = st.selectbox("Min", LISTE_MINUTES)
        with c_cat: sel_news = st.multiselect("Catégories News", list(DICT_CAT_NEWS.keys()))
        with c_fill: 
            f_sel = st.multiselect("Filling Type", LISTE_FILLING_DEFAUT)
            f_txt = st.text_input("Précisez si Autre") if "AUTRE..." in f_sel else ""

    comment = st.text_area("Commentaires / Notes sur le trade")

    def get_full_stats(ticker, target_date, s1, s2, cats, filling, entry_time, note):
        try:
            details = client.get_ticker_details(ticker)
            raw_float = getattr(details, 'weighted_shares_outstanding', 0)
            start_s = (target_date - timedelta(days=5)).strftime("%Y-%m-%d")
            end_s = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
            aggs = list(client.get_aggs(ticker, 1, "minute", start_s, end_s, adjusted=True))
            data = [{"date": pd.to_datetime(a.timestamp, unit='ms', utc=True).tz_convert('America/New_York').date(),
                     "time": pd.to_datetime(a.timestamp, unit='ms', utc=True).tz_convert('America/New_York').time(),
                     "o": a.open, "h": a.high, "l": a.low, "c": a.close, "v": a.volume} for a in aggs]
            df_t = pd.DataFrame(data)
            day_df = df_t[df_t['date'] == target_date].copy()
            if day_df.empty: return None, "Aucune donnée trouvée."
            
            pm_df = day_df[day_df['time'] < dt_time(9, 30)]
            vol_pm = pm_df['v'].sum()
            vol_4_9 = day_df[(day_df['time'] >= dt_time(4, 0)) & (day_df['time'] < dt_time(9, 0))]['v'].sum()
            
            hist = list(client.get_aggs(ticker, 1, "day", (target_date - timedelta(days=10)).strftime("%Y-%m-%d"), (target_date - timedelta(days=1)).strftime("%Y-%m-%d"), adjusted=True))
            avg_basis = np.mean([a.volume for a in hist]) * 0.15 if hist else 1.0
            
            rth_df = day_df[(day_df['time'] >= dt_time(9, 30)) & (day_df['time'] <= dt_time(12, 0))].copy()
            y_close = df_t[df_t['date'] < target_date].iloc[-1]['c'] if not df_t[df_t['date'] < target_date].empty else day_df.iloc[0]['o']
            
            open_930_val = float(rth_df.iloc[0]['o']) if not rth_df.empty else 0
            hod_val = float(rth_df['h'].max()) if not rth_df.empty else 0
            open_push_val = round(((hod_val - open_930_val) / open_930_val) * 100, 2) if open_930_val > 0 else 0
            
            row = {
                "Date": target_date.strftime("%Y-%m-%d"), "Ticker": ticker, "Float (Shares)": f"{raw_float/1e6:.2f}M",
                "Float Rotation %": f"{(vol_pm/raw_float*100):.2f}%" if raw_float > 0 else "0%", 
                "Cumulative Vol 4-9AM": f"{int(vol_4_9):,}", "PM RVOL": f"{(vol_pm/avg_basis):.2f}x",
                "Catégorie News": " / ".join([DICT_CAT_NEWS[cat] for cat in cats]) if cats else "🔘 AUCUNE",
                "Stratégie": s1, "Stratégie Combinée": s2, "Entry Time": entry_time,
                "Gap to Open %": round(((rth_df.iloc[0]['o']-y_close)/y_close)*100, 2) if not rth_df.empty else 0,
                "HOD to LOD Drop %": round(((rth_df['l'].min()-rth_df['h'].max())/rth_df['h'].max())*100, 2) if not rth_df.empty else 0,
                "Heure HOD": str(rth_df.loc[rth_df['h'].idxmax(), 'time']) if not rth_df.empty else "N/A",
                "Prev_Close ($)": y_close, "PM_High ($)": float(pm_df['h'].max()) if not pm_df.empty else 0,
                "Open_9h30 ($)": open_930_val,
                "HOD ($)": hod_val, 
                "LOD ($)": float(rth_df['l'].min()) if not rth_df.empty else 0,
                "Open Push %": open_push_val,
                "Filling": filling, "Commentaires": note
            }
            return pd.DataFrame([row]), "Succès"
        except Exception as e: return None, str(e)

    if st.button("➕ AJOUTER AU JOURNAL", type="primary", use_container_width=True):
        if t_ticker:
            e_time = "" if h_sel == "NONE" else f"{h_sel}:{m_sel}"
            f_final = ", ".join([f for f in f_sel if f != "AUTRE..."] + ([f_txt] if f_txt else []))
            res, msg = get_full_stats(t_ticker, t_date, s1, s2, sel_news, f_final, e_time, comment)
            if res is not None:
                df = pd.read_excel(EXCEL_FILE) if os.path.exists(EXCEL_FILE) else pd.DataFrame()
                
                if "Open to HOD %" in df.columns: df.rename(columns={"Open to HOD %": "Open Push %"}, inplace=True)
                if "Open Push" in df.columns: df.rename(columns={"Open Push": "Open Push %"}, inplace=True)
                
                pd.concat([df, res], ignore_index=True).sort_values(by="Date", ascending=True).to_excel(EXCEL_FILE, index=False)
                st.success(f"✅ {t_ticker} ajouté au journal !"); st.rerun()
            else: st.error(f"Erreur : {msg}")

    if os.path.exists(EXCEL_FILE):
        st.divider()
        df_v = pd.read_excel(EXCEL_FILE)
        
        renamed = False
        if "Open to HOD %" in df_v.columns: 
            df_v.rename(columns={"Open to HOD %": "Open Push %"}, inplace=True)
            renamed = True
        if "Open Push" in df_v.columns:
            df_v.rename(columns={"Open Push": "Open Push %"}, inplace=True)
            renamed = True
        if renamed:
            df_v.to_excel(EXCEL_FILE, index=False)
            
        st.subheader(f"Journal des Statistiques ({len(df_v)} entrées)")
        st.session_state.ed_df = st.data_editor(df_v.sort_values(by="Date", ascending=False), num_rows="dynamic", use_container_width=True, hide_index=True)

# ==========================================
# PAGE 2 : SCANNER DILUTION (Intouché)
# ==========================================
elif page == "Scanner Dilution (News)":
    st.title("🔍 Scanner de Dilution (0.80$ - 10$)")
    mots_cles = ["offering", "prospectus", "common stock", "pricing", "warrants", "S-1", "424B5", "dividend"]
    
    if st.button("🔄 Rafraîchir les alertes ciblées", use_container_width=True):
        st.cache_data.clear()

    @st.cache_data(ttl=60)
    def scan_news_filtered():
        url = f"https://api.polygon.io/v2/reference/news?limit=50&apiKey={POLYGON_API_KEY}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                results = r.json().get("results", [])
                alerts = []
                for n in results:
                    title, summary = n.get("title", ""), n.get("description", "")
                    full = (title + " " + summary).lower()
                    mot = next((word for word in mots_cles if word in full), None)
                    
                    if mot:
                        ticker = n.get("tickers", ["N/A"])[0]
                        if ticker != "N/A":
                            try:
                                prev = client.get_previous_close_agg(ticker)[0]
                                prix = prev.close
                                if 0.80 <= prix <= 10.00:
                                    alerts.append({
                                        "Heure": pd.to_datetime(n.get("published_utc")).tz_convert('America/New_York').strftime('%H:%M'),
                                        "Ticker": ticker, "Prix ($)": f"{prix:.2f}$", "Titre": title,
                                        "Sentiment": n.get("insights", [{}])[0].get("sentiment", "neutral"),
                                        "Mot Détecté": mot.upper(), "Lien": n.get("article_url")
                                    })
                            except: continue
                return pd.DataFrame(alerts)
            return pd.DataFrame()
        except: return pd.DataFrame()

    def highlight_dilution(row):
        target = row['Mot Détecté'].lower()
        if any(x in target for x in ["offering", "s-1", "424b5"]):
            return ['background-color: #7d1a1a; color: white'] * len(row)
        return [''] * len(row)

    with st.spinner("Analyse des prix et des news..."):
        df_news = scan_news_filtered()

    if not df_news.empty:
        cols = ["Heure", "Ticker", "Prix ($)", "Titre", "Sentiment", "Mot Détecté", "Lien"]
        st.dataframe(df_news[cols].style.apply(highlight_dilution, axis=1), 
                     column_config={"Lien": st.column_config.LinkColumn("Lire"), "Titre": st.column_config.TextColumn("Titre", width="large")},
                     hide_index=True, use_container_width=True)

# ==========================================
# PAGE 3 : STATISTIQUES (Format Ligne Compact)
# ==========================================
elif page == "Statistiques":
    st.title("📊 Analyse de Performance du Journal")
    
    if not os.path.exists(EXCEL_FILE):
        st.warning("Journal vide. Ajoute des trades pour voir les statistiques.")
    else:
        df = pd.read_excel(EXCEL_FILE)
        total = len(df)
        
        if "Open to HOD %" in df.columns: df.rename(columns={"Open to HOD %": "Open Push %"}, inplace=True)
        if "Open Push" in df.columns: df.rename(columns={"Open Push": "Open Push %"}, inplace=True)
        
        if "Open Push %" not in df.columns:
            df["Open Push %"] = np.nan
            
        missing_push = df["Open Push %"].isna()
        if missing_push.any() and "Open_9h30 ($)" in df.columns and "HOD ($)" in df.columns:
            df.loc[missing_push, "Open Push %"] = np.where(
                df.loc[missing_push, "Open_9h30 ($)"] > 0, 
                ((df.loc[missing_push, "HOD ($)"] - df.loc[missing_push, "Open_9h30 ($)"]) / df.loc[missing_push, "Open_9h30 ($)"]) * 100, 
                0
            )

        st.write("---")

        # --- LIGNE 1 : VOLUME & FLOAT (GÉNÉRAL EN HAUT) ---
        c7, c8, c9 = st.columns([1, 1, 1])
        c7.markdown("**📊 Général**")
        
        if "HOD to LOD Drop %" in df.columns:
            clean_drop = df['HOD to LOD Drop %'].astype(str).str.replace('%', '', regex=False).str.replace(',', '.', regex=False)
            df['HOD to LOD Drop % Clean'] = pd.to_numeric(clean_drop, errors='coerce')
            global_drop = df['HOD to LOD Drop % Clean'].mean()
            c8.markdown(f"Drop Moyen : **{global_drop:.2f}%**" if pd.notna(global_drop) else "Drop Moyen : **N/A**")
        else:
            c8.markdown("Drop Moyen : **N/A**")
            
        if "Float (Shares)" in df.columns:
            try:
                # Remplacement spécifique de la virgule par un point pour la gestion décimale francophone
                clean_floats = df['Float (Shares)'].astype(str).str.upper().str.replace('M', '', regex=False).str.replace(',', '.', regex=False)
                floats = pd.to_numeric(clean_floats, errors='coerce')
                # Sécurité : Si le nombre est supérieur à 1000, c'est probablement un nombre brut sans le 'M'
                floats = floats.apply(lambda x: x / 1e6 if x > 1000 else x)
                c9.markdown(f"Float Moyen : **{floats.mean():.2f}M**")
            except:
                c9.markdown("Float Moyen : **N/A**")
        else:
            c9.markdown("Float Moyen : **N/A**")
        
        st.write("---")

        # --- LIGNE 2 : ANALYSE OPEN PUSH ---
        if "Open Push %" in df.columns:
            clean_push = df['Open Push %'].astype(str).str.replace('%', '', regex=False).str.replace(',', '.', regex=False)
            df['Open Push % Clean'] = pd.to_numeric(clean_push, errors='coerce')
            
            avg_push = df['Open Push % Clean'].mean()
            weak_push_df = df[df['Open Push % Clean'] <= 5.0]
            weak_push_rate = (len(weak_push_df) / total * 100) if total > 0 else 0
            
            c1, c2, c3 = st.columns([1, 1, 1])
            c1.markdown("**📈 Open Push %**")
            c2.markdown(f"Moyen : **{avg_push:.2f}%**" if pd.notna(avg_push) else "Moyen : **N/A**")
            c3.markdown(f"Faible (<= 5%) : **{weak_push_rate:.1f}%**")
        else:
            st.info("La colonne 'Open Push %' est absente.")

        st.write("---")

        # --- LIGNE 3 : MAX DEV VWAP ---
        if "Max Dev Vwap %" in df.columns:
            clean_dev = df['Max Dev Vwap %'].astype(str).str.replace('%', '', regex=False).str.replace(',', '.', regex=False)
            numeric_dev = pd.to_numeric(clean_dev, errors='coerce')
            
            if numeric_dev.max() > 0 and numeric_dev.max() < 5:
                numeric_dev = numeric_dev * 100
            
            dev_positives = numeric_dev[numeric_dev > 0]
            avg_max_dev = dev_positives.mean() if not dev_positives.empty else np.nan
            freq_depassement = (len(dev_positives) / total * 100) if total > 0 else 0
            
            c_v1, c_v2, c_v3 = st.columns([1, 1, 1])
            c_v1.markdown("**🌊 Max Dev Vwap %**")
            c_v2.markdown(f"Moyenne (quand dépassé) : **{avg_max_dev:.2f}%**" if pd.notna(avg_max_dev) else "Moyenne : **N/A**")
            c_v3.markdown(f"Fréquence dépassement : **{freq_depassement:.1f}%**")
        else:
            st.info("La colonne 'Max Dev Vwap %' est absente.")

        st.write("---")

        # --- LIGNE 4 : ANALYSE HOD vs PM HIGH ---
        if "HOD ($)" in df.columns and "PM_High ($)" in df.columns:
            if "HOD to LOD Drop % Clean" not in df.columns:
                if "HOD to LOD Drop %" in df.columns:
                    clean_drop = df['HOD to LOD Drop %'].astype(str).str.replace('%', '', regex=False).str.replace(',', '.', regex=False)
                    df['HOD to LOD Drop % Clean'] = pd.to_numeric(clean_drop, errors='coerce')
                else:
                    df['HOD to LOD Drop % Clean'] = np.nan

            df_pm = df[df['HOD ($)'] <= df['PM_High ($)']]
            freq_pm = (len(df_pm) / total * 100) if total > 0 else 0
            drop_pm = df_pm['HOD to LOD Drop % Clean'].mean() if not df_pm.empty else 0
            
            c4, c5, c6 = st.columns([1, 1, 1])
            c4.markdown("**🛡️ HOD vs PM High**")
            c5.markdown(f"Respecté : **{freq_pm:.1f}%**")
            c6.markdown(f"Drop Moyen : **{drop_pm:.2f}%**" if pd.notna(drop_pm) else "Drop Moyen : **N/A**")
        else:
            st.info("Colonnes HOD ($) ou PM_High ($) absentes.")
            
        st.write("---")
