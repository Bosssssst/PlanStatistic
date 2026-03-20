import streamlit as st

def apply_custom_styles():
    """Applique le design personnalisé à l'application."""
    custom_css = """
    <style>
        /* Force les majuscules dans les champs texte */
        input[type='text'] {
            text-transform: uppercase;
        }

        /* Style pour les boutons principaux */
        .stButton>button {
            border-radius: 8px;
            font-weight: bold;
        }

        /* Amélioration de la visibilité des tableaux */
        .stDataEditor, .stDataFrame {
            border: 1px solid #f0f2f6;
            border-radius: 10px;
        }

        /* Style spécifique pour les titres */
        h1 {
            color: #FF4B4B;
        }

        /* Espacement pour les icônes Stopping Volume */
        .sv-header {
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 10px;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
