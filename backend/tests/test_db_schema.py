"""Garante que db.py e o motor não escrevam colunas que a migration não criou."""

from __future__ import annotations

import re

import db
from engine.pipeline import processar_oportunidade
from models.oportunidade import OportunidadeEntrada

COLUNAS_ESPERADAS_NO_INSERT = 33


def colunas_da_migration(tabela: str) -> set[str]:
    sql = (db.MIGRATIONS_DIR / "001_init.sql").read_text(encoding="utf-8")
    corpo = re.search(rf"CREATE TABLE IF NOT EXISTS {tabela} \((.*?)\n\);", sql, re.DOTALL).group(1)
    colunas = set()
    for linha in corpo.splitlines():
        linha = linha.strip()
        casamento = re.match(r"^([a-z_0-9]+)\s+(UUID|TEXT|NUMERIC|INTEGER|BOOLEAN|TIMESTAMPTZ|DATE|CHAR)", linha)
        if casamento:
            colunas.add(casamento.group(1))
    return colunas


def test_campos_do_insert_existem_na_tabela():
    colunas = colunas_da_migration("oportunidades")
    assert set(db.CAMPOS_OPORTUNIDADE) <= colunas
    assert len(db.CAMPOS_OPORTUNIDADE) == COLUNAS_ESPERADAS_NO_INSERT


def test_migration_cria_o_indice_unico_de_dedup():
    sql = (db.MIGRATIONS_DIR / "001_init.sql").read_text(encoding="utf-8")
    assert "UNIQUE(hash_dedup)" in sql


def test_oportunidade_calculada_cabe_no_insert(params):
    entrada = OportunidadeEntrada(
        origem_cidade="Campinas",
        origem_uf="SP",
        destino_cidade="Curitiba",
        destino_uf="PR",
        mercadoria="paletes de embalagem plástica",
        peso_kg=12000,
        cubagem_m3=6.0,
        valor_nf=37000,
        empresa="Embalagens ABC",
        distancia_km=2100,
    )
    oportunidade, _, _ = processar_oportunidade(entrada, params)
    registro = oportunidade.model_dump(mode="json", exclude={"id", "created_at", "alertas", "hash_dedup_valor"})
    registro = {chave: valor for chave, valor in registro.items() if chave in db.CAMPOS_OPORTUNIDADE}
    registro["hash_dedup"] = entrada.hash_dedup()

    colunas = colunas_da_migration("oportunidades")
    assert set(registro) <= colunas
    assert registro["status"] == "CALCULADA"
    assert registro["veiculo_sugerido"] == "Bi Truck"


def test_valores_de_status_do_motor_passam_no_check_da_tabela():
    sql = (db.MIGRATIONS_DIR / "001_init.sql").read_text(encoding="utf-8")
    from models.oportunidade import StatusOportunidade

    permitidos = re.search(r"status TEXT DEFAULT 'CAPTADA' CHECK \(status IN \((.*?)\)\)", sql, re.DOTALL).group(1)
    permitidos = {valor.strip().strip("'") for valor in permitidos.replace("\n", "").split(",")}
    assert {s.value for s in StatusOportunidade} <= permitidos


def test_sem_database_url_o_backend_segue_funcionando(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert db.disponivel() is False
