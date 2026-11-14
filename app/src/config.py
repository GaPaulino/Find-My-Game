import os
from dataclasses import dataclass

from dotenv import load_dotenv

from storage import DEFAULT_KEY, LocalStorage, S3Storage, Storage

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Configuração lida do ambiente UMA vez e passada adiante.

    frozen=True deixa o objeto imutável: ninguém altera a config por engano
    depois de criada.
    """

    igdb_client_id: str | None = None
    igdb_client_secret: str | None = None  # permite renovar o token sozinho
    igdb_access_token: str | None = None   # alternativa: token fixo
    google_api_key: str | None = None
    bucket_name: str | None = None
    local_data_dir: str | None = None      # se definido, usa disco em vez de S3
    games_key: str = DEFAULT_KEY

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            igdb_client_id=os.getenv("CLIENT_ID"),
            igdb_client_secret=os.getenv("CLIENT_SECRET"),
            igdb_access_token=os.getenv("ACCESS_TOKEN"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            bucket_name=os.getenv("BUCKET_NAME"),
            local_data_dir=os.getenv("LOCAL_DATA_DIR"),
            games_key=os.getenv("GAMES_KEY", DEFAULT_KEY),
        )

    def build_storage(self) -> Storage:
        """Fábrica: escolhe a implementação de Storage conforme a configuração."""
        if self.local_data_dir:
            return LocalStorage(self.local_data_dir)
        if not self.bucket_name:
            raise ValueError("Defina BUCKET_NAME (S3) ou LOCAL_DATA_DIR (disco).")
        return S3Storage(self.bucket_name)
