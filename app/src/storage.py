import io
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import pandas as pd

from models import Game

logger = logging.getLogger(__name__)

DEFAULT_KEY = "jogos_embeddings.parquet"


class Storage(ABC):
    """Onde o catálogo (com embeddings) fica guardado.

    Padrão Template Method: a lógica comum (converter jogos <-> parquet) vive
    aqui, na classe base. As subclasses só implementam COMO ler e gravar
    bytes (_read / _write): disco, S3, etc.
    """

    @abstractmethod
    def _read(self, key: str) -> bytes: ...

    @abstractmethod
    def _write(self, key: str, data: bytes) -> None: ...

    def save_games(self, games: list[Game], key: str = DEFAULT_KEY) -> None:
        df = pd.DataFrame({
            "id": [g.id for g in games],
            "name": [g.name for g in games],
            "summary": [g.summary for g in games],
            "genres": [g.genres for g in games],
            "rating": [g.rating for g in games],
            "embedding": [None if g.embedding is None else g.embedding.tolist() for g in games],
        })
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        self._write(key, buf.getvalue())
        logger.info("%d jogos salvos em %s", len(games), key)

    def load_games(self, key: str = DEFAULT_KEY) -> list[Game]:
        df = pd.read_parquet(io.BytesIO(self._read(key)))
        games = []
        for row in df.to_dict("records"):
            emb = row["embedding"]
            rating = row["rating"]
            games.append(Game(
                id=None if pd.isna(row["id"]) else int(row["id"]),
                name=row["name"],
                summary=row["summary"] or "",
                genres=list(row["genres"]),
                rating=None if pd.isna(rating) else float(rating),
                embedding=None if emb is None else np.asarray(emb, dtype=np.float32),
            ))
        logger.info("%d jogos carregados de %s", len(games), key)
        return games


class LocalStorage(Storage):
    """Guarda em uma pasta do disco. Útil em desenvolvimento e testes."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)

    def _read(self, key: str) -> bytes:
        return (self.base_dir / key).read_bytes()

    def _write(self, key: str, data: bytes) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / key).write_bytes(data)


class S3Storage(Storage):
    """Guarda em um bucket S3. O cliente pode ser injetado (testes)."""

    def __init__(self, bucket: str, client=None):
        self.bucket = bucket
        self._client = client or self._create_client()

    @staticmethod
    def _create_client():
        """Chaves do .env se existirem; senão a IAM role do Lambda (cadeia padrão do boto3)."""
        import boto3
        key, secret = os.getenv("AWS_ACCESS_KEY_ID"), os.getenv("AWS_SECRET_ACCESS_KEY")
        region = os.getenv("AWS_REGION")
        if key and secret:
            return boto3.client("s3", aws_access_key_id=key,
                                aws_secret_access_key=secret, region_name=region)
        return boto3.client("s3", region_name=region)

    def _read(self, key: str) -> bytes:
        return self._client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def _write(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data)
