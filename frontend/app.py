"""
Frontend do Find My Game (Streamlit).

Rodar:  streamlit run frontend/app.py
Config: API_URL (variável de ambiente ou barra lateral). Padrão: http://127.0.0.1:8000
"""
import os

import streamlit as st

from api_client import ApiError, Recommendation, RecommenderAPI

EXAMPLES = [
    "RPG medieval com dragões e magia",
    "jogo de corrida com carros esportivos",
    "puzzle relaxante para jogar sozinho",
    "shooter multiplayer em equipes",
]

st.set_page_config(page_title="Find My Game", page_icon="🎮", layout="centered")


def render_card(rec: Recommendation) -> None:
    with st.container(border=True):
        left, right = st.columns([4, 1])
        left.subheader(rec.name)
        right.metric("Similaridade", f"{rec.score:.0%}")
        meta = []
        if rec.genres:
            meta.append(" · ".join(rec.genres))
        if rec.rating is not None:
            meta.append(f"⭐ {rec.rating:.0f}/100")
        if meta:
            st.caption("  |  ".join(meta))
        st.write(rec.summary if len(rec.summary) <= 300 else rec.summary[:300].rstrip() + "…")
        if len(rec.summary) > 300:
            with st.expander("Ler resumo completo"):
                st.write(rec.summary)


# ---- Barra lateral -------------------------------------------------------
with st.sidebar:
    st.header("Configurações")
    api_url = st.text_input("URL da API", os.getenv("API_URL", "http://127.0.0.1:8000"))
    top_k = st.slider("Quantos jogos mostrar", 1, 20, 5)
    api = RecommenderAPI(api_url)
    if api.health():
        st.success("API online")
    else:
        st.error("API offline")

# ---- Página --------------------------------------------------------------
st.title("🎮 Find My Game")
st.write("Descreva o tipo de jogo que você procura e eu encontro os mais parecidos.")

if "query" not in st.session_state:
    st.session_state.query = ""

st.caption("Exemplos:")
cols = st.columns(len(EXAMPLES))
for col, example in zip(cols, EXAMPLES):
    if col.button(example, use_container_width=True):
        st.session_state.query = example

with st.form("search"):
    query = st.text_input("O que você quer jogar?", key="query",
                          placeholder="Ex.: aventura de fantasia com cavaleiros e magia")
    submitted = st.form_submit_button("Buscar", type="primary")

if submitted or st.session_state.query:
    if not query.strip():
        st.warning("Digite uma descrição para buscar.")
    else:
        try:
            with st.spinner("Buscando jogos..."):
                results = api.recommend(query.strip(), top_k)
        except ApiError as e:
            st.error(str(e))
        else:
            if not results:
                st.info("Nenhum jogo encontrado.")
            else:
                st.subheader(f"{len(results)} jogos para “{query.strip()}”")
                for rec in results:
                    render_card(rec)
