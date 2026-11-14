import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "frontend"))

from api_client import ApiError, RecommenderAPI


class Resp:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self._data = data or {}

    def json(self):
        return self._data


class Session:
    def __init__(self, resp=None, exc=None):
        self.resp, self.exc, self.calls = resp, exc, []

    def post(self, url, **kw):
        self.calls.append((url, kw))
        if self.exc:
            raise self.exc
        return self.resp

    def get(self, url, **kw):
        if self.exc:
            raise self.exc
        return self.resp


ITEM = {"name": "Forza", "summary": "corrida", "genres": ["Racing"], "rating": 90.0, "score": 0.8, "id": 1}


def test_recommend_converte_resposta_em_objetos():
    s = Session(Resp(200, {"query": "q", "results": [ITEM]}))
    out = RecommenderAPI("http://x/", session=s).recommend("corrida", 3)
    assert out[0].name == "Forza" and out[0].score == 0.8
    url, kw = s.calls[0]
    assert url == "http://x/recommend" and kw["json"] == {"query": "corrida", "top_k": 3}


@pytest.mark.parametrize("status,trecho", [(422, "inválida"), (500, "HTTP 500")])
def test_erros_http_viram_apierror(status, trecho):
    with pytest.raises(ApiError, match=trecho):
        RecommenderAPI("http://x", session=Session(Resp(status))).recommend("q")


def test_503_mostra_detalhe_da_api():
    resp = Resp(503, {"detail": "Catálogo de jogos indisponível."})
    with pytest.raises(ApiError, match="Catálogo"):
        RecommenderAPI("http://x", session=Session(resp)).recommend("q")


def test_api_fora_do_ar_da_mensagem_amigavel():
    s = Session(exc=requests.ConnectionError())
    with pytest.raises(ApiError, match="rodando"):
        RecommenderAPI("http://x", session=s).recommend("q")


def test_health():
    assert RecommenderAPI("http://x", session=Session(Resp(200))).health() is True
    assert RecommenderAPI("http://x", session=Session(exc=requests.ConnectionError())).health() is False
