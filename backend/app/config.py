from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # desarrollo: SQLite junto al backend; producción: postgresql+psycopg://...
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'torneos.db').as_posix()}"
    media_dir: str = str(BACKEND_DIR / "media")  # fotos de planillas
    secret_key: str = "cambiar-en-produccion"
    access_token_minutes: int = 60 * 12


settings = Settings()
