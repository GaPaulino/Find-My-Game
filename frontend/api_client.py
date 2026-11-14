from dataclasses import dataclass

import requests


class ApiError(Exception):
    """Erro 'amigável' para mostrar ao usuário (a tela não precisa conhecer HTTP)."""


@dataclass
class Recommendation:
    name: str
    summary: str
    genres: list[str]
    rating: float | None
    score: float


class RecommenderAPI:
    """Cliente da API do Find My Game. Isola toda a comunicação HTTP da interface."""

    def __init__(self, base_url: str, session=None, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self.timeout = timeout

    def health(self) -> bool:
        try:
            return self._session.get(f"{self.base_url}/health", timeout=5).status_code == 200
        except requests.RequestException:
            return False

    def recommend(self, query: str, top_k: int = 5) -> list[Recommendation]:
        try:
            resp = self._session.post(
                f"{self.base_url}/recommend",
                json={"query": query, "top_k": top_k},
                timeout=self.timeout,
            )
        except requests.ConnectionError as e:
            raise ApiError(f"Não consegui conectar à API em {self.base_url}. Ela está rodando?") from e
        except requests.Timeout as e:
            raise ApiError("A API demorou demais para responder.") from e

        if resp.status_code == 422:
            raise ApiError("Consulta inválida. Descreva o jogo com pelo menos uma palavra.")
        if resp.status_code in (502, 503):
            raise ApiError(resp.json().get("detail", "Serviço indisponível no momento."))
        if resp.status_code != 200:
            raise ApiError(f"Erro inesperado da API (HTTP {resp.status_code}).")

        return [
            Recommendation(r["name"], r["summary"], r["genres"], r["rating"], r["score"])
            for r in resp.json()["results"]
        ]
