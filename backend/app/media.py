"""Almacenamiento de imágenes subidas (planillas, fotos de jugadores)."""
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from .config import settings

MAX_IMAGE_BYTES = 10 * 1024 * 1024
_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _sniff(head: bytes) -> str | None:
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


async def save_image(file: UploadFile, subdir: str) -> tuple[str, str]:
    """Valida y guarda la imagen. Devuelve (ruta relativa, content-type).

    El tipo se detecta por el contenido, no por el Content-Type que declara el cliente.
    """
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "La imagen supera los 10 MB")
    ctype = _sniff(data[:12])
    if not ctype:
        raise HTTPException(415, "Formato no soportado (usá JPG, PNG o WebP)")
    rel = Path(subdir) / f"{uuid.uuid4().hex}{_EXT[ctype]}"
    dest = Path(settings.media_dir) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return rel.as_posix(), ctype


def media_path(rel: str) -> Path:
    return Path(settings.media_dir) / rel


def delete_media(rel: str | None) -> None:
    if rel:
        media_path(rel).unlink(missing_ok=True)
