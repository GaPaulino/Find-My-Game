"""
Frontend do Find My Game (Streamlit).

Rodar (de dentro da pasta frontend, para carregar o tema):
    cd frontend && streamlit run app.py
Config: API_URL (variável de ambiente ou barra lateral). Padrão: http://127.0.0.1:8000
"""
import hashlib
import html
import os

import streamlit as st

from api_client import ApiError, Recommendation, RecommenderAPI

EXAMPLES = [
    ("🐉", "RPG medieval com dragões e magia"),
    ("🏎️", "jogo de corrida com carros esportivos"),
    ("🧩", "puzzle relaxante para jogar sozinho"),
    ("🧟", "terror de sobrevivência com zumbis"),
]
SUMMARY_PREVIEW = 260

st.set_page_config(page_title="Find My Game", page_icon="🎮", layout="centered")

CSS = """
<style>
.block-container { padding-top: 2.2rem; max-width: 820px; }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }

/* ---------- hero ---------- */
.hero { text-align: center; padding: 1.2rem 0 0.4rem; }
.hero h1 {
  font-size: 3.1rem; font-weight: 800; letter-spacing: -0.02em; margin: 0;
  background: linear-gradient(90deg, #8B5CF6 0%, #EC4899 55%, #F59E0B 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero p { color: #98A2B8; font-size: 1.08rem; margin: .5rem 0 0; }

/* ---------- busca ---------- */
div[data-testid="stForm"] {
  background: linear-gradient(180deg, #131A2B 0%, #0F1524 100%);
  border: 1px solid #243049; border-radius: 16px; padding: 1.1rem 1.2rem .6rem;
  box-shadow: 0 8px 30px rgba(139, 92, 246, .08);
}
div[data-testid="stForm"] input { font-size: 1.05rem; }
.stButton > button, div[data-testid="stFormSubmitButton"] > button {
  border-radius: 12px; border: 1px solid #243049; transition: all .15s ease;
}
.stButton > button:hover {
  border-color: #8B5CF6; color: #C4B5FD; transform: translateY(-1px);
}
div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
  background: linear-gradient(90deg, #8B5CF6, #EC4899); border: none; font-weight: 700;
}
div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
  filter: brightness(1.1); transform: translateY(-1px); color: #fff;
}

/* ---------- resultados ---------- */
.results-title { color: #98A2B8; margin: 1.6rem 0 .6rem; font-size: .95rem; }
.results-title b { color: #E6EAF2; }
.card {
  display: flex; gap: 1rem; padding: 1.1rem 1.2rem; margin-bottom: .9rem;
  background: #131A2B; border: 1px solid #243049; border-radius: 16px;
  transition: transform .15s ease, border-color .15s ease, box-shadow .15s ease;
}
.card:hover {
  transform: translateY(-2px); border-color: #8B5CF6;
  box-shadow: 0 10px 30px rgba(139, 92, 246, .18);
}
.rank {
  flex: 0 0 2.4rem; height: 2.4rem; border-radius: 12px; display: flex;
  align-items: center; justify-content: center; font-weight: 800;
  color: #C4B5FD; background: rgba(139, 92, 246, .14);
  border: 1px solid rgba(139, 92, 246, .35);
}
.card:first-of-type .rank { color: #1B1300; background: #F59E0B; border-color: #F59E0B; }
.body { flex: 1; min-width: 0; }
.top { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
.top h3 { margin: 0; padding: 0; font-size: 1.2rem; font-weight: 700; line-height: 1.3; }
.match { text-align: right; flex: 0 0 auto; line-height: 1.1; }
.match span { font-size: 1.35rem; font-weight: 800; color: #A78BFA; }
.match small { display: block; color: #6B7690; font-size: .7rem; text-transform: uppercase; letter-spacing: .08em; }
.bar { height: 5px; background: #1D2740; border-radius: 99px; margin: .7rem 0 .8rem; overflow: hidden; }
.fill { height: 100%; border-radius: 99px; background: linear-gradient(90deg, #8B5CF6, #EC4899); }
.meta { display: flex; flex-wrap: wrap; gap: .4rem; align-items: center; margin-top: .55rem; }
.chip {
  font-size: .72rem; font-weight: 600; padding: .18rem .6rem; border-radius: 99px;
  background: hsla(var(--h), 70%, 55%, .14); color: hsl(var(--h), 85%, 74%);
  border: 1px solid hsla(var(--h), 70%, 55%, .35);
}
.rating {
  font-size: .72rem; font-weight: 700; padding: .18rem .6rem; border-radius: 8px;
  margin-left: auto;
}
.r-high { background: rgba(34, 197, 94, .15); color: #4ADE80; }
.r-mid  { background: rgba(245, 158, 11, .15); color: #FBBF24; }
.r-low  { background: rgba(148, 163, 184, .15); color: #94A3B8; }
.summary { color: #B5BDD0; font-size: .93rem; line-height: 1.55; margin: 0; }
details { margin-top: .5rem; }
details summary { color: #A78BFA; cursor: pointer; font-size: .85rem; }
details p { color: #B5BDD0; font-size: .93rem; line-height: 1.55; margin-top: .5rem; }

.empty { text-align: center; color: #6B7690; padding: 2.5rem 0; }
.empty .big { font-size: 2.6rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------- componentes visuais ----------
def genre_chip(genre: str) -> str:
    """Cor estável por gênero: o mesmo gênero sempre tem o mesmo matiz."""
    hue = int(hashlib.md5(genre.encode()).hexdigest(), 16) % 360
    return f'<span class="chip" style="--h:{hue}">{html.escape(genre)}</span>'


def rating_badge(rating: float | None) -> str:
    if rating is None:
        return ""
    css = "r-high" if rating >= 80 else "r-mid" if rating >= 60 else "r-low"
    return f'<span class="rating {css}">⭐ {rating:.0f}</span>'


def card_html(rank: int, rec: Recommendation) -> str:
    """Tudo que vem da API é escapado (html.escape): nunca injetamos HTML de terceiros."""
    pct = max(0, min(100, round(rec.score * 100)))
    summary = rec.summary.strip()
    short = summary if len(summary) <= SUMMARY_PREVIEW else summary[:SUMMARY_PREVIEW].rstrip() + "…"
    more = ""
    if len(summary) > SUMMARY_PREVIEW:
        more = f"<details><summary>Ler resumo completo</summary><p>{html.escape(summary)}</p></details>"
    chips = "".join(genre_chip(g) for g in rec.genres)
    # Sem indentação nas linhas: o markdown trataria 4 espaços como bloco de código.
    return (
        f'<div class="card"><div class="rank">{rank}</div><div class="body">'
        f'<div class="top"><h3>{html.escape(rec.name)}</h3>'
        f'<div class="match"><span>{pct}%</span><small>similaridade</small></div></div>'
        f'<div class="meta">{chips}{rating_badge(rec.rating)}</div>'
        f'<div class="bar"><div class="fill" style="width:{pct}%"></div></div>'
        f'<p class="summary">{html.escape(short)}</p>{more}</div></div>'
    )


# ---------- barra lateral ----------
with st.sidebar:
    st.header("⚙️ Configurações")
    api_url = st.text_input("URL da API", os.getenv("API_URL", "http://127.0.0.1:8000"))
    top_k = st.slider("Quantos jogos mostrar", 1, 20, 5)
    api = RecommenderAPI(api_url)
    if api.health():
        st.success("API online")
    else:
        st.error("API offline")

# ---------- página ----------
st.markdown(
    '<div class="hero"><h1>🎮 Find My Game</h1>'
    "<p>Descreva o jogo dos seus sonhos e descubra os mais parecidos.</p></div>",
    unsafe_allow_html=True,
)

if "query" not in st.session_state:
    st.session_state.query = ""

st.write("")
cols = st.columns(len(EXAMPLES))
for col, (icon, text) in zip(cols, EXAMPLES):
    if col.button(f"{icon} {text}", use_container_width=True):
        st.session_state.query = text

with st.form("search", border=False):
    query = st.text_input("O que você quer jogar?", key="query",
                          placeholder="Ex.: aventura de fantasia com cavaleiros e magia",
                          label_visibility="collapsed")
    submitted = st.form_submit_button("🔍  Buscar jogos", type="primary", use_container_width=True)

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
                st.markdown('<div class="empty"><div class="big">🕹️</div>'
                            "Nenhum jogo encontrado.</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="results-title"><b>{len(results)} jogos</b> '
                    f"para “{html.escape(query.strip())}”</div>",
                    unsafe_allow_html=True,
                )
                st.markdown("".join(card_html(i, r) for i, r in enumerate(results, 1)),
                            unsafe_allow_html=True)
else:
    st.markdown('<div class="empty"><div class="big">🕹️</div>'
                "Escolha um exemplo ou escreva o que procura.</div>", unsafe_allow_html=True)
