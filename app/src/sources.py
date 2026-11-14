import logging
import time
from abc import ABC, abstractmethod

import requests

logger = logging.getLogger(__name__)


class GameSource(ABC):
    """De onde vêm os jogos brutos (lista de dicts). A IGDB é uma implementação."""

    @abstractmethod
    def fetch(self, limit: int) -> list[dict]:
        """Retorna até `limit` jogos com campos id, name, summary, genres, total_rating."""


class IGDBClient(GameSource):
    """Busca jogos na IGDB: paginado, com rate limit e renovação de token."""

    API_URL = "https://api.igdb.com/v4/games"
    TOKEN_URL = "https://id.twitch.tv/oauth2/token"
    PAGE_SIZE = 500  # máximo permitido pela IGDB por requisição
    FIELDS = "id,name,summary,genres,total_rating"

    def __init__(self, client_id: str, client_secret: str | None = None,
                 access_token: str | None = None, min_rating_count: int = 5,
                 session=None, min_interval: float = 0.26, timeout: int = 30):
        if not client_secret and not access_token:
            raise ValueError("Informe client_secret (renova o token) ou access_token.")
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = access_token
        self.min_rating_count = min_rating_count
        self._session = session or requests.Session()
        self.min_interval = min_interval  # IGDB permite ~4 req/s
        self.timeout = timeout
        self._last_request = 0.0

    # ---- API pública -----------------------------------------------------
    def fetch(self, limit: int) -> list[dict]:
        games: dict[int, dict] = {}  # por id: a paginação pode repetir itens em empates
        offset = 0
        while len(games) < limit:
            size = min(self.PAGE_SIZE, limit - len(games))
            page = self._query(size, offset)
            for g in page:
                games.setdefault(g["id"], g)
            logger.info("IGDB: %d jogos até agora (offset %d)", len(games), offset)
            if len(page) < size:  # acabou o catálogo
                break
            offset += size
        return list(games.values())[:limit]

    # ---- internos --------------------------------------------------------
    def _query(self, limit: int, offset: int) -> list[dict]:
        body = (f"fields {self.FIELDS}; "
                f"where summary != null & total_rating_count > {self.min_rating_count}; "
                f"sort total_rating_count desc; limit {limit}; offset {offset};")
        return self._post(body).json()

    def _refresh_token(self) -> None:
        if not self.client_secret:
            raise RuntimeError("Token inválido e sem client_secret para renová-lo.")
        resp = self._session.post(self.TOKEN_URL, params={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }, timeout=self.timeout)
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        logger.info("Token da IGDB renovado")

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def _post(self, body: str, retries: int = 3):
        if not self._token:
            self._refresh_token()
        refreshed = False
        for attempt in range(retries):
            self._throttle()
            resp = self._session.post(self.API_URL, data=body, timeout=self.timeout, headers={
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "text/plain",
            })
            if resp.status_code == 401 and not refreshed:
                self._refresh_token()  # token expirou: renova e tenta de novo
                refreshed = True
                continue
            if resp.status_code == 429:
                time.sleep(2 ** attempt)  # rate limit: espera e repete
                continue
            resp.raise_for_status()
            return resp
        raise RuntimeError("IGDB: tentativas esgotadas")
