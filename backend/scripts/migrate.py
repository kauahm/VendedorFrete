"""Aplica as migrations em DATABASE_URL. Uso: python scripts/migrate.py"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

import db  # noqa: E402

if __name__ == "__main__":
    load_dotenv()
    if not db.disponivel():
        raise SystemExit("DATABASE_URL ausente ou psycopg não instalado")
    for nome in db.migrar():
        print(f"aplicada: {nome}")
