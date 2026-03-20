import streamlit as st
import pandas as pd

def afficher_page_stats(df_actuel, parse_func):
    # --- CSS POUR RÉDUIRE L'ESPACE EN HAUT ---
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem; padding-bottom: 0rem; }
            .stCheckbox { margin-bottom: -15px; }
        </style>
    """, unsafe_allow_html=True)

    # --- FONCTIONS UTILITAIRES ---
    def time_to_min(t):
        if pd.isna(t) or str(t).strip() == "" or ":" not in str(t): return None
        try:
            parts = str(t).strip().split(':')
            return int(parts[0]) * 60 + int(parts[1])
        except: return None

    def min_to_time(m):
        if m is None or pd.isna(m): return "--:--"
        return f"{int(m // 60) % 24:02d}:{int(m % 60):02d}"

    # --- ENTÊTE ET CIBLE ---
    c_title, c_target = st.columns([2, 1])
    c_title.subheader("📊 Probabilités & Timing")
    target_drop = c_target.number_input("Cible Drop %", value=20, step=5, help="Définit le seuil de réussite (ex: -20% pour un succès).")

    with st.expander("🔍 CONFIGURER LE SETUP", expanded=True):
        # --- SECTION : PRÉ MARKET ---
        st.markdown("##### 🕒 Pré market")
        c1, c2, c3 = st.columns(3)
        f_news = c1.multiselect("News", options=sorted(df_actuel['Catégorie News'].dropna().unique()) if not df_actuel.empty else [], label_visibility="collapsed", placeholder="News")
        f_fill = c2.multiselect("Fillings", options=sorted(df_actuel['Filling'].dropna().unique()) if not df_actuel.empty else [], label_visibility="collapsed", placeholder="Fillings")
        
        st.write("") 

        # Ligne 1 : Gap, RVOL, Volume
        l1_1, l1_2, l1_3 = st.columns(3)
        gc1, gc2 = l1_1.columns([0.25, 0.75])
        on_gap = gc1.checkbox("G", value=True, help="Gap to Open % : Écart entre clôture veille et ouverture.")
        f_gap = gc2.slider("Gap", -50, 150, 50, disabled=not on_gap, label_visibility="collapsed")
        
        rc1, rc2 = l1_2.columns([0.25, 0.75])
        on_rvol = rc1.checkbox("R", value=True, help="PM RVOL : Volume relatif en Pre-market.")
        f_pm_rvol = rc2.slider("RVOL", 0.0, 50.0, 3.0, 0.5, disabled=not on_rvol, label_visibility="collapsed")
        
        vc1, vc2 = l1_3.columns([0.25, 0.75])
        on_vol = vc1.checkbox("V", value=True, help="Cumulative Vol : Volume total échangé avant 9h30.")
        f_vol = vc2.select_slider("Vol", options=[0, 1, 5, 10, 20, 50, 100, 500], value=10, disabled=not on_vol, label_visibility="collapsed")

        # Ligne 2 : Float et Rotation (Average)
        l2_1, l2_2 = st.columns(2)
        fc1, fc2 = l2_1.columns([0.15, 0.85])
        on_fl = fc1.checkbox("F", value=True, help="Float : Taille du float cible (M). Analyse à +/- 25%.")
        f_fl_val = fc2.select_slider("Float", options=[0, 1, 2, 5, 10, 20, 50, 100, 500], value=10, disabled=not on_fl, label_visibility="collapsed")
        
        rtc1, rtc2 = l2_2.columns([0.15, 0.85])
        on_rot = rtc1.checkbox("X", value=True, help="Rotation : Rotation du float cible (x). Analyse à +/- 25%.")
        f_rot_val = rtc2.select_slider("Rot", options=[i/2.0 for i in range(0, 61)], value=5.0, disabled=not on_rot, label_visibility="collapsed")

        # --- SECTION : OUVERTURE ---
        st.markdown("##### 🔔 Données d'ouverture")
        l3_1, l3_2 = st.columns(2)
        ovc1, ovc2 = l3_1.columns([0.2, 0.8])
        on_ov = ovc1.checkbox("W", value=True, help="Open to VWAP % : Distance entre prix d'ouverture et VWAP.")
        f_ov = ovc2.slider("VWAP", -20, 20, -2, disabled=not on_ov, label_visibility="collapsed")
        
        pmc1, pmc2 = l3_2.columns([0.2, 0.8])
        on_pmh = pmc1.checkbox("P", value=True, help="PMH to Open % : Distance entre le plus haut PM et l'ouverture.")
        f_pmh = pmc2.slider("PMH/O", -100, 100, -20, disabled=not on_pmh, label_visibility="collapsed")

        btn = st.button("🚀 ANALYSER L'EDGE", type="primary", use_container_width=True)

    if btn:
        df = df_actuel.copy()
        def clean(x):
            try: return float("".join(c for c in str(x) if c.isdigit() or c in ".-"))
            except: return 0.0

        df['gap_n'] = df['Gap to Open %'].apply(clean)
        df['pmh_n'] = df['PMH to Open %'].apply(clean)
        df['ov_n'] = df['Open to VWAP %'].apply(clean)
        df['rot_n'] = df['Float Rotation %'].apply(clean)
        df['rvol_n'] = df['PM RVOL'].apply(clean)
        df['vol_n'] = df['Cumulative Vol 4-9AM'].apply(parse_func)
        df['push_n'] = df['Open Push %'].apply(clean)
        df['float_n'] = df['Float (Shares)'].apply(parse_func)
        df['hod_min'] = df['Heure HOD'].apply(time_to_min)
        # Succès basé sur l'entrée manuelle
        df['is_win'] = df['HOD to LOD Drop %'].apply(clean) <= (target_drop * -1)

        stats = []
        def add_s(nom, sub):
            if not sub.empty:
                v_hod = sub['hod_min'].dropna()
                stats.append({"Critère": nom, "N": len(sub), "WR": sub['is_win'].mean()*100, "Push": sub['push_n'].mean(), "HOD": min_to_time(v_hod.mean()) if not v_hod.empty else "--:--"})

        fl_min, fl_max = f_fl_val * 0.75 * 1e6, f_fl_val * 1.25 * 1e6
        rot_min, rot_max = f_rot_val * 0.75, f_rot_val * 1.25

        if f_news: add_s("News", df[df['Catégorie News'].isin(f_news)])
        if f_fill: add_s("Fillings", df[df['Filling'].isin(f_fill)])
        if on_gap: add_s("Gap", df[df['gap_n'] >= f_gap])
        if on_rvol: add_s("RVOL", df[df['rvol_n'] >= f_pm_rvol])
        if on_vol: add_s("Volume", df[df['vol_n'] >= f_vol * 1e6])
        if on_fl:  add_s(f"Float (~{f_fl_val}M)", df[df['float_n'].between(fl_min, fl_max)])
        if on_rot: add_s(f"Rot (~{f_rot_val}x)", df[df['rot_n'].between(rot_min, rot_max)])
        if on_ov:  add_s("VWAP", df[df['ov_n'] <= f_ov])
        if on_pmh: add_s("PMH/O", df[df['pmh_n'] >= f_pmh])

        dm = df.copy()
        if f_news: dm = dm[dm['Catégorie News'].isin(f_news)]
        if f_fill: dm = dm[dm['Filling'].isin(f_fill)]
        if on_gap: dm = dm[dm['gap_n'] >= f_gap]
        if on_rvol: dm = dm[dm['rvol_n'] >= f_pm_rvol]
        if on_vol: dm = dm[dm['vol_n'] >= f_vol * 1e6]
        if on_fl:  dm = dm[dm['float_n'].between(fl_min, fl_max)]
        if on_rot: dm = dm[dm['rot_n'].between(rot_min, rot_max)]
        if on_ov:  dm = dm[dm['ov_n'] <= f_ov]
        if on_pmh: dm = dm[dm['pmh_n'] >= f_pmh]

        if stats:
            ds = pd.DataFrame(stats)
            r1, r2, r3, r4 = st.columns(4)
            r1.metric(f"WIN RATE (-{target_drop}%)", f"{ds['WR'].mean():.1f}%")
            r2.metric("PUSH AVG", f"{ds['Push'].mean():.1f}%")
            t_hods = ds.apply(lambda x: time_to_min(x['HOD']), axis=1).dropna()
            r3.metric("HEURE HOD", min_to_time(t_hods.mean()) if not t_hods.empty else "--:--")
            r4.metric("MATCHS", len(dm))

            st.table(ds.set_index('Critère').style.format({"WR": "{:.1f}%", "Push": "{:.1f}%"}))
            if not dm.empty:
                st.dataframe(dm[['Date', 'Ticker', 'PMH to Open %', 'Open to VWAP %', 'Heure HOD', 'Open Push %', 'HOD to LOD Drop %']], use_container_width=True, hide_index=True)
