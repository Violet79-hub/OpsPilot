import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./opspilot.db")
AS_OF = "2026-10-07"
MAX_UPLOAD = 5 * 1024 * 1024
EMBEDDING_DIM = 512
