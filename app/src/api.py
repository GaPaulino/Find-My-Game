"""
API de recomendação (FastAPI).

Local:  cd app/src && uvicorn api:app --reload
Lambda: handler = api.handler  (via API Gateway; Mangum adapta ASGI -> Lambda)
"""
import logging
from functools import lru_cache
from typing import Annotated, Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel, Field, StringConstraints

from config import Settings
from embeddings import GeminiEmbedder
from recommender import Recommender

logger = logging.getLogger(__name__)


class RecommendRequest(BaseModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    top_k: int = Field(default=5, ge=1, le=20)


class GameOut(BaseModel):
    id: int | None = None
    name: str
    summary: str
    genres: list[str]
    rating: float | None = None
    score: float


class RecommendResponse(BaseModel):
    query: str
    results: list[GameOut]


@lru_cache(maxsize=1)
def default_recommender() -> Recommender:
    """Carrega o catálogo UMA vez por processo. No Lambda, o cache sobrevive entre
    invocações 'quentes', então só o cold start paga o custo de ler o parquet."""
    settings = Settings.from_env()
    games = settings.build_storage().load_games(settings.games_key)
    logger.info("Catálogo carregado: %d jogos", len(games))
    return Recommender(GeminiEmbedder(api_key=settings.google_api_key)).fit(games)


def create_app(get_recommender: Callable[[], Recommender] = default_recommender) -> FastAPI:
    """Fábrica do app. Recebe como obter o Recommender, então os testes injetam um
    com FakeEmbedder e dados falsos, sem AWS nem Gemini."""
    app = FastAPI(title="Find My Game", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_methods=["*"], allow_headers=["*"])

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # `def` (não async): a chamada ao Gemini bloqueia, e o FastAPI roda em thread.
    @app.post("/recommend", response_model=RecommendResponse)
    def recommend(req: RecommendRequest):
        try:
            recommender = get_recommender()
        except Exception:
            logger.exception("Catálogo indisponível")
            raise HTTPException(status_code=503, detail="Catálogo de jogos indisponível.")

        try:
            hits = recommender.recommend(req.query, req.top_k)
        except Exception:
            logger.exception("Erro ao gerar recomendação")
            raise HTTPException(status_code=502, detail="Falha ao gerar a recomendação.")

        return RecommendResponse(
            query=req.query,
            results=[GameOut(**game.to_dict(), score=score) for game, score in hits],
        )

    return app


app = create_app()
handler = Mangum(app)  # ponto de entrada do Lambda
