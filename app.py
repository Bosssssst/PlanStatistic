import streamlit as st
import pandas as pd
import os
from datetime import datetime
from config import COLONNES_CIBLES, COLONNES_TESTEUR, EXCEL_FILE, DATA_DIR, TZ_NY
from massive_engine import calculer_donnees_trade
from style import apply_custom_styles
# Import du nouveau module statistique
from stats_module import afficher_page_stats

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Trading Hub David", page_icon="🚀", layout="wide")
apply_custom_styles()
today_ny = datetime.now(TZ_NY).date()

# Compteur pour la réinitialisation des champs après enregistrement
if "form_count" not in st.session_state:
    st.session_state.form_count = 0

# --- FONCTIONS UTILITAIRES ---
def parse_valeur_boursiere(val):
    """Convertit 2.75M en 2750000.0 pour les calculs."""
    if pd.isna(val) or val == "": return 0.0
    s = str(val).upper().replace(" ", "").replace(",", ".").replace("X", "")
    mult = 1.0
    if "M" in s: 
        mult = 1_000_000.0
        s = s.replace("M", "")
    elif "K" in s: 
        mult = 1_000.0
        s = s.replace("K", "")
    try: return float(s) * mult
    except: return 0.0

def formater_entree_auto(val, suffixe):
    """Ajoute M ou X automatiquement si l'entrée finit par un chiffre."""
    if not val: return ""
    s = str(val).strip().replace(",", ".")
    if s and s[-1].isdigit(): return s.upper() + suffixe
    return s.upper()

def charger_donnees():
    """Charge le fichier Excel en respectant l'ordre des colonnes existantes."""
    if os.path.exists(EXCEL_FILE):
        try: return pd.read_excel(EXCEL_FILE)
        except: return pd.DataFrame(columns=COLONNES_CIBLES)
    return pd.DataFrame(columns=COLONNES_CIBLES)

# --- 2. STRUCTURE PRINCIPALE ---
df_actuel = charger_donnees()
st.sidebar.title("Navigation")
page = st.sidebar.radio("Aller à", ["Journal de Bord", "Statistiques"])

if page == "Journal de Bord":
    st.title("📓 Journal Statistique")
    st.markdown("### ➕ Nouveau Trade")
    
    # Suffixe dynamique pour vider les champs après submit (sc)
    sc = st.session_state.form_count

    # Ligne 1 : Infos de base
    c1, c2, c3, c4 = st.columns(4)
    t_ticker = c1.text_input("Ticker", key=f"tk_{sc}").upper().strip()
    t_date = c2.date_input("Date du Trade", value=today_ny, key=f"dt_{sc}")
    strat_list = ["Aucune", "FAILED", "Reject vwap", "Double Top PMH", "Double Top DAY", "Double Top Intraday", "Open Drop", "Zone Morte"]
    s1 = c3.selectbox("Stratégie", strat_list, key=f"s1_{sc}")
    s_comb = c4.selectbox("Stratégie Combinée", strat_list, key=f"sc_{sc}")
    
    st.divider()
    # Ligne 2 : News & Filings
    cn1, cn2, cf1, cf2 = st.columns(4)
    sel_news = cn1.multiselect("News", ["🌍 MACRO", "🎈 FLUFF", "💎 FONDAMENTAL", "📉 DILUTION", "📊 TECHNIQUE", "🔗 SYMPATHIE"], key=f"nw_{sc}")
    man_news = cn2.text_input("News Manuelle", key=f"nwm_{sc}")
    fillings = ["6-K", "8-K", "S-1", "S-3", "S-3ASR", "S-4", "424B3", "424B4", "424B5", "EFFECT", "10-Q", "10-K", "NT 10-Q", "NT 10-K", "13-G", "13-D", "RW"]
    sel_fills = cf1.multiselect("Fillings", fillings, key=f"fl_{sc}")
    man_fill = cf2.text_input("Filling Manuel", key=f"flm_{sc}")
    
    st.divider()
    # Ligne 3 : Stats (Navigation TAB optimisée)
    m_cols = st.columns(7)
    m_push = m_cols[0].text_input("Open Push %", key=f"op_{sc}")
    m_po = m_cols[1].text_input("PMH/Open %", key=f"po_{sc}")
    m_ov = m_cols[2].text_input("Open/VWAP %", key=f"ov_{sc}")
    m_md = m_cols[3].text_input("Max Dev %", key=f"md_{sc}")
    m_fs = m_cols[4].text_input("Float (Shares)", key=f"fs_{sc}") 
    m_cv = m_cols[5].text_input("Cum. Vol 4-9h30", key=f"cv_{sc}")
    m_pr = m_cols[6].text_input("PM RVOL", key=f"pr_{sc}")

    st.divider()
    # Ligne 4 : Stopping Volume
    csv_cols = st.columns([1.0, 0.7, 1.0, 0.7, 1.0, 2.6])
    with csv_cols[0]: st.markdown("<p style='margin-top: 32px; font-weight: bold;'>🛑 Stopping Volume</p>", unsafe_allow_html=True)
    with csv_cols[1]:
        st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
        sv1 = st.checkbox("1Min", key=f"sv1_{sc}")
    t_sv1 = csv_cols[2].text_input("Heure 1m", key=f"t1_{sc}")
    with csv_cols[3]:
        st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
        sv3 = st.checkbox("3Min", key=f"sv3_{sc}")
    t_sv3 = csv_cols[4].text_input("Heure 3m", key=f"t3_{sc}")

    comment = st.text_area("Commentaires", height=68, key=f"cm_{sc}")
    
    # UNIQUE MOYEN D'ENREGISTRER
    if st.button("➕ ENREGISTRER LE TRADE", type="primary", use_container_width=True):
        if t_ticker:
            with st.spinner(f"Traitement de {t_ticker}..."):
                stats = calculer_donnees_trade(t_ticker, t_date)
                
                # Formatage auto & Calcul Rotation
                f_fmt = formater_entree_auto(m_fs, "M")
                v_fmt = formater_entree_auto(m_cv, "M")
                r_fmt = formater_entree_auto(m_pr, "X")
                fv_num = parse_valeur_boursiere(f_fmt)
                vv_num = parse_valeur_boursiere(v_fmt)
                rot = str(round(vv_num / fv_num, 2)) + "x" if fv_num > 0 else "0.00x"

                # Création de la ligne (Ordre Excel)
                new_row = {col: "" for col in df_actuel.columns}
                new_row.update(stats)
                new_row.update({
                    "Date": t_date.strftime('%Y-%m-%d'), "Ticker": t_ticker,
                    "PMH to Open %": m_po, "Gap to Open %": stats.get("Gap to Open %", 0.0),
                    "HOD to PMH %": stats.get("HOD to PMH %", 0.0), "Open to VWAP %": m_ov,
                    "Max Dev Vwap %": m_md, "HOD to LOD Drop %": stats.get("HOD to LOD Drop %", 0.0),
                    "Float (Shares)": f_fmt, "Float Rotation %": rot,
                    "Cumulative Vol 4-9AM": v_fmt, "PM RVOL": r_fmt,
                    "Stratégie": s1, "Stratégie Combinée": s_comb, "Commentaires": comment,
                    "Catégorie News": " / ".join(list(sel_news) + ([man_news.upper()] if man_news else [])),
                    "Filling": " / ".join(list(sel_fills) + ([man_fill.upper()] if man_fill else [])),
                    "SV 1min": "OUI" if sv1 else "NON", "Heure Entrée 1m": t_sv1,
                    "SV 3min": "OUI" if sv3 else "NON", "Heure Entrée 3m": t_sv3,
                    "Open Push %": m_push
                })
                
                df_actuel = pd.concat([pd.DataFrame([new_row]), df_actuel], ignore_index=True)
                df_actuel.to_excel(EXCEL_FILE, index=False)
                st.session_state.form_count += 1 # Réinitialise les widgets
                st.rerun()

    # --- 📂 HISTORIQUE ---
    if not df_actuel.empty:
        st.divider()
        h_col1, h_col2 = st.columns([4, 1])
        h_col1.subheader("📂 Historique des Trades")
        if h_col2.button("💾 SAUVEGARDER", use_container_width=True, type="primary"):
            st.session_state.save_trigger = True

        edited_df = st.data_editor(df_actuel, use_container_width=True, hide_index=True, num_rows="dynamic")
        
        if st.session_state.get('save_trigger', False):
            def update_row(row):
                f_r = formater_entree_auto(row["Float (Shares)"], "M")
                v_r = formater_entree_auto(row["Cumulative Vol 4-9AM"], "M")
                r_r = formater_entree_auto(row["PM RVOL"], "X")
                fv = parse_valeur_boursiere(f_r); vv = parse_valeur_boursiere(v_r)
                row["Float (Shares)"] = f_r
                row["Cumulative Vol 4-9AM"] = v_r
                row["PM RVOL"] = r_r
                # Fix du crash de division
                row["Float Rotation %"] = str(round(vv / fv, 2)) + "x" if fv > 0 else "0.00x"
                return row
            
            df_final = edited_df.apply(update_row, axis=1)
            df_final.to_excel(EXCEL_FILE, index=False)
            st.session_state.save_trigger = False
            st.rerun()

    # --- 🔍 TESTEUR ---
    st.divider()
    st.subheader("🔍 Testeur de Ticker")
    test_c1, test_c2, test_c3 = st.columns([2, 2, 1])
    tt = test_c1.text_input("Ticker à tester", key="test_t").upper()
    td = test_c2.date_input("Date du test", value=today_ny, key="test_d")
    if test_c3.button("🚀 TESTER", use_container_width=True):
        if tt:
            res = calculer_donnees_trade(tt, td)
            res["Ticker"], res["Date"] = tt, td.strftime('%Y-%m-%d')
            for col in COLONNES_TESTEUR:
                if col not in res: res[col] = "-"
            st.dataframe(pd.DataFrame([res])[COLONNES_TESTEUR], hide_index=True)

    # --- 🛠️ MAINTENANCE ---
    st.divider()
    st.subheader("🛠️ Maintenance")
    mode_m = st.radio("Mode :", ["Ticker spécifique", "Global"], horizontal=True)
    if mode_m == "Ticker spécifique":
        tks = [""] + sorted([str(t).strip() for t in df_actuel['Ticker'].unique() if pd.notna(t)])
        ticker_sel = st.selectbox("Choisir le ticker :", options=tks)
        if st.button("🔄 MISE À JOUR CIBLÉE"):
            if ticker_sel:
                df_up = df_actuel.copy()
                idxs = df_up[df_up['Ticker'] == ticker_sel].index
                for i in idxs:
                    r = calculer_donnees_trade(ticker_sel, pd.to_datetime(df_up.loc[i, 'Date']).date())
                    for k, v in r.items():
                        if k in df_up.columns: df_up.at[i, k] = v
                df_up.to_excel(EXCEL_FILE, index=False)
                st.success(f"Mise à jour de {ticker_sel} terminée.")
                st.rerun()
    else:
        if st.button("🔄 MISE À JOUR GLOBALE"):
            df_up = df_actuel.copy()
            for i in df_up.index:
                r = calculer_donnees_trade(str(df_up.loc[i, 'Ticker']), pd.to_datetime(df_up.loc[i, 'Date']).date())
                for k, v in r.items():
                    if k in df_up.columns: df_up.at[i, k] = v
            df_up.to_excel(EXCEL_FILE, index=False)
            st.success("Mise à jour globale terminée.")
            st.rerun()

elif page == "Statistiques":
    # Appel de la fonction isolée dans stats_module.py
    afficher_page_stats(df_actuel, parse_valeur_boursiere)
