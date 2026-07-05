"""Guardado y recuperación de imágenes de recibo adjuntas a transacciones."""
import uuid
from pathlib import Path

from fastapi import UploadFile

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".pdf"}


def save_receipt(upload: UploadFile | None) -> str:
    """Guarda el archivo subido con un nombre único y devuelve ese nombre
    (para almacenar en Transaction.attachment_name). Devuelve '' si no hay archivo."""
    if not upload or not upload.filename:
        return ""
    suffix = Path(upload.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        suffix = ".bin"
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    dest = UPLOADS_DIR / stored_name
    with dest.open("wb") as f:
        f.write(upload.file.read())
    return stored_name


def receipt_path(stored_name: str) -> Path | None:
    if not stored_name:
        return None
    # Evita traversal: solo aceptamos un nombre de archivo simple.
    p = (UPLOADS_DIR / stored_name).resolve()
    if p.parent != UPLOADS_DIR.resolve() or not p.exists():
        return None
    return p
