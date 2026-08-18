"""Acesso ao Postgres (Neon). Opcional: sem DATABASE_URL o backend roda sem persistir."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

CAMPOS_OPORTUNIDADE = (
    "origem_cidade", "origem_uf", "destino_cidade", "destino_uf", "mercadoria", "peso_kg",
    "cubagem_m3", "valor_nf", "veiculo_pedido", "carroceria", "empresa", "contato",
    "observacoes", "fonte", "data_anuncio", "distancia_km", "confianca", "elegibilidade",
    "motivo_elegibilidade", "faixa_gr", "classificacao_mercadoria", "modalidade",
    "veiculo_sugerido", "eixos", "fracao_ocupacao", "restricao_dominante", "custo_total",
    "preco_minimo", "preco_alvo", "preco_maximo", "score", "status", "hash_dedup",
)


def database_url() -> str | None:
    return os.getenv("DATABASE_URL") or None


def disponivel() -> bool:
    if not database_url():
        return False
    try:
        import psycopg  # noqa: F401
    except ImportError:
        return False
    return True


def conectar():
    import psycopg

    url = database_url()
    if not url:
        raise RuntimeError("DATABASE_URL não configurada")
    return psycopg.connect(url)


def migrar() -> list[str]:
    aplicadas = []
    with conectar() as conexao:
        with conexao.cursor() as cursor:
            for arquivo in sorted(MIGRATIONS_DIR.glob("*.sql")):
                cursor.execute(arquivo.read_text(encoding="utf-8"))
                aplicadas.append(arquivo.name)
        conexao.commit()
    return aplicadas


def hash_existe(hash_dedup: str, janela_horas: int = 48) -> bool:
    with conectar() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM oportunidades WHERE hash_dedup = %s AND created_at > now() - make_interval(hours => %s)",
                (hash_dedup, janela_horas),
            )
            return cursor.fetchone() is not None


def salvar_oportunidade(registro: dict[str, Any]) -> str | None:
    campos = [c for c in CAMPOS_OPORTUNIDADE if c in registro]
    colunas = ", ".join(campos)
    marcadores = ", ".join(["%s"] * len(campos))
    valores = [registro[c] for c in campos]
    with conectar() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO oportunidades ({colunas}) VALUES ({marcadores}) "
                "ON CONFLICT (hash_dedup) DO NOTHING RETURNING id",
                valores,
            )
            linha = cursor.fetchone()
        conexao.commit()
    return str(linha[0]) if linha else None
