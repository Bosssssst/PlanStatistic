import streamlit as st
import pandas as pd

def afficher_page_stats(df_actuel, parse_func):
    # --- CSS ---
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem; padding-bottom: 0rem; }
            .stCheckbox { margin-bottom: -15px; }
        </style>
    """, unsafe_allow_html=True)

    # --- FONCTIONS ---
    def time_to_min(t):
        if pd.isna(t) or str(t).strip() == "" or ":" not in str(t): return None
        try:
            parts = str(t).strip().split(':')
            return int(parts[0]) * 60 + int(parts[1])
        except: return None

    def min_to_time(m):
        if m is None or pd.isna(m): return "--:--"
        return f"{int(m // 60) % 24:02d}:{int(m % 60):02d}"

    # --- ENTÊTE ---
    c_title, c_target = st.columns([2, 1])
    c_title.subheader("📊 Probabilités & Timing")
    target_drop = c_target.number_input("Cible Drop %", value=20, step=5)

    with st.expander("🔍 CONFIGURER LE SETUP", expanded=True):
        # --- FORCE LA LISTE ICI ---
        # Cette liste DOIT correspondre à celle de ton Journal (app.py)
        LISTE_STRATS_OFFICIELLE = [
            "FAILED", 
            "Reject vwap", 
            "Double Top PMH", 
            "Double Top DAY", 
            "Double Top Intraday", 
            "Open Drop", 
            "Zone Morte", 
            "Open Push" # <--- IL EST ICI EN DUR
        ]

        c_strat, c_comb = st.columns(2)
        # On utilise la liste fixe pour être certain qu'il s'affiche
        f_strat = c_strat.multiselect("Stratégie", options=LISTE_STRATS_OFFICIELLE, placeholder="Choisir Stratégie")
        f_strat_comb = c_comb.multiselect("Stratégie Combinée", options=LISTE_STRATS_OFFICIELLE, placeholder="Choisir Combinée")

        st.divider()

        # FILTRES TECHNIQUES
        t1, t2, t3 = st.columns(3)
        on_gap = t1.checkbox("G (Gap)", value=True)
        f_gap = t1.slider("Gap %", -50, 150, 50, disabled=not on_gap, label_visibility="collapsed")
        
        on_fl = t2.checkbox("F (Float)", value=True)
        f_fl_val = t2.select_slider("Float (M)", options=[0, 1, 2, 5, 10, 20, 50, 100, 500], value=10, disabled=not on_fl, label_visibility="collapsed")
        
        on_vol = t3.checkbox("V (Volume)", value=True)
        f_vol = t3.select_slider("Vol PM (M)", options=[0, 1, 5, 10, 20, 50, 100], value=10, disabled=not on_vol, label_visibility="collapsed")

        btn = st.button("🚀 ANALYSER L'EDGE", type="primary", use_container_width=True)

    if btn:
        df = df_actuel.copy()
        def clean(x):
            try: return float("".join(c for c in str(x) if c.isdigit() or c in ".-"))
            except: return 0.0

        df['gap_n'] = df['Gap to Open %'].apply(clean)
        df['push_n'] = df['Open Push %'].apply(clean)
        df['float_n'] = df['Float (Shares)'].apply(parse_func)
        df['vol_n'] = df['Cumulative Vol 4-9AM'].apply(parse_func)
        df['hod_min'] = df['Heure HOD'].apply(time_to_min)
        df['is_win'] = df['HOD to LOD Drop %'].apply(clean) <= (target_drop * -1)

        stats = []
        def add_s(nom, sub):
            if not sub.empty:
                v_hod = sub['hod_min'].dropna()
                stats.append({
                    "Critère": nom, "N": len(sub), 
                    "WR": sub['is_win'].mean()*100, 
                    "Push Avg": sub['push_n'].mean(), 
                    "HOD": min_to_time(v_hod.mean()) if not v_hod.empty else "--:--"
                })

        if f_strat: add_s("Stratégie(s)", df[df['Stratégie'].isin(f_strat)])
        if f_strat_comb: add_s("Combinée(s)", df[df['Stratégie Combinée'].isin(f_strat_comb)])
        if on_gap: add_s(f"Gap >= {f_gap}%", df[df['gap_n'] >= f_gap])

        # LE MATCH FINAL
        dm = df.copy()
        if f_strat: dm = dm[dm['Stratégie'].isin(f_strat)]
        if f_strat_comb: dm = dm[dm['Stratégie Combinée'].isin(f_strat_comb)]
        if on_gap: dm = dm[dm['gap_n'] >= f_gap]
        if on_fl:
            fl_min, fl_max = f_fl_val * 0.75 * 1e6, f_fl_val * 1.25 * 1e6
            dm = dm[dm['float_n'].between(fl_min, fl_max)]
        if on_vol: dm = dm[dm['vol_n'] >= f_vol * 1e6]

        if stats:
            ds = pd.DataFrame(stats)
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("WIN RATE MOYEN", f"{ds['WR'].mean():.1f}%")
            r2.metric("PUSH MOYEN", f"{ds['Push Avg'].mean():.1f}%")
            t_hods = ds.apply(lambda x: time_to_min(x['HOD']), axis=1).dropna()
            r3.metric("HEURE HOD AVG", min_to_time(t_hods.mean()) if not t_hods.empty else "--:--")
            r4.metric("MATCHS", len(dm))

            st.table(ds.set_index('Critère').style.format({"WR": "{:.1f}%", "Push Avg": "{:.1f}%"}))
            
            if not dm.empty:
                st.dataframe(dm[['Date', 'Ticker', 'Stratégie', 'Stratégie Combinée', 'Open Push %', 'HOD to LOD Drop %']], use_container_width=True, hide_index=True)
        else:
            st.warning("Aucune donnée pour ces filtres.")
