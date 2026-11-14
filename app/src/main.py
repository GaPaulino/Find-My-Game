"""
Ingestão (AWS Lambda): IGDB -> gêneros -> embeddings Gemini -> parquet no S3.

Handler do Lambda: main.lambda_handler
Local: python main.py  (usa LOCAL_DATA_DIR se definido, senão S3)
"""
import json
import logging

from config import Settings
from embeddings import GeminiEmbedder
from genres import GenreMapper
from pipeline import IngestionPipeline
from sources import IGDBClient

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)  # no Lambda, o root logger já tem handler


def build_pipeline(settings: Settings) -> IngestionPipeline:
    """Monta o pipeline com as implementações reais (composição das peças)."""
    return IngestionPipeline(
        source=IGDBClient(
            client_id=settings.igdb_client_id,
            client_secret=settings.igdb_client_secret,
            access_token=settings.igdb_access_token,
        ),
        embedder=GeminiEmbedder(api_key=settings.google_api_key),
        storage=settings.build_storage(),
        genre_mapper=GenreMapper(),
    )


def _response(status: int, payload: dict) -> dict:
    return {"statusCode": status, "body": json.dumps(payload, ensure_ascii=False)}


def lambda_handler(event, context):
    """Evento opcional: {"limit": 500}."""
    limit = int((event or {}).get("limit", 500))
    try:
        settings = Settings.from_env()
        games = build_pipeline(settings).run(limit=limit, key=settings.games_key)
        return _response(200, {
            "message": "Jogos extraídos, embedados e salvos.",
            "jogos_carregados": len(games),
            "destino": settings.local_data_dir or settings.bucket_name,
        })
    except Exception as e:
        logger.exception("Falha na ingestão")
        return _response(500, {"error": f"Falha na ingestão: {e}"})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(json.loads(lambda_handler({"limit": 500}, None)["body"]),
                     indent=2, ensure_ascii=False))
