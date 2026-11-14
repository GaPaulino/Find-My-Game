import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from embeddings import FakeEmbedder
from models import Game
from recommender import Recommender


def catalogo():
    return [
        Game("Dragon Quest", "RPG medieval com dragoes e magia", ["RPG"]),
        Game("Forza", "Simulador de corrida com carros esportivos", ["Racing"]),
        Game("Zelda", "Aventura de fantasia com cavaleiros e magia", ["Adventure"]),
    ]


def test_game_from_dict_tolera_campos_ausentes_e_nan():
    g = Game.from_dict({"name": "X", "total_rating": float("nan")})
    assert g.summary == "" and g.genres == [] and g.rating is None


def test_game_from_dict_aceita_nan_no_resumo_e_array_de_generos():
    import numpy as np
    g = Game.from_dict({"name": "X", "summary": float("nan"), "genres": np.array(["RPG", "Shooter"])})
    assert g.summary == "" and g.genres == ["RPG", "Shooter"]


def test_embedding_text_inclui_nome_generos_e_resumo():
    t = Game("A", "resumo", ["RPG"]).embedding_text()
    assert "A" in t and "RPG" in t and "resumo" in t


def test_recomenda_o_mais_parecido_primeiro():
    r = Recommender(FakeEmbedder()).fit(catalogo())
    res = r.recommend("rpg com dragoes e magia", top_k=2)
    assert res[0][0].name == "Dragon Quest"
    assert len(res) == 2
    assert res[0][1] >= res[1][1]


def test_consulta_de_corrida_nao_retorna_rpg_primeiro():
    r = Recommender(FakeEmbedder()).fit(catalogo())
    assert r.recommend("corrida de carros", top_k=1)[0][0].name == "Forza"


def test_top_k_maior_que_catalogo_e_consulta_vazia():
    r = Recommender(FakeEmbedder()).fit(catalogo())
    assert len(r.recommend("magia", top_k=50)) == 3
    assert r.recommend("   ") == []
    assert Recommender(FakeEmbedder()).recommend("x") == []


def test_fit_nao_reembeda_jogos_que_ja_tem_vetor():
    class Contador(FakeEmbedder):
        calls = 0

        def embed_documents(self, texts):
            Contador.calls += len(texts)
            return super().embed_documents(texts)

    jogos = catalogo()
    Recommender(Contador()).fit(jogos)
    Recommender(Contador()).fit(jogos)
    assert Contador.calls == 3
