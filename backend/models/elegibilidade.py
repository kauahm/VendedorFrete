from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class StatusElegibilidade(str, Enum):
    APROVADA = "APROVADA"
    RECUSADA = "RECUSADA"
    BLOQUEIO = "BLOQUEIO"
    REVISAR = "REVISAR"


class TipoMercadoria(str, Enum):
    EXCLUIDA = "EXCLUIDA"
    ESPECIFICA = "ESPECIFICA"
    NAO_ESPECIFICA = "NAO_ESPECIFICA"
    REVISAR = "REVISAR"


class ClassificacaoMercadoria(BaseModel):
    tipo: TipoMercadoria
    match: str | None = None
    confianca: float
    exigencias: list[str] = []


class ElegibilidadeResult(BaseModel):
    status: StatusElegibilidade
    motivo: str | None = None
    classificacao_mercadoria: TipoMercadoria | None = None
    faixa_gr: str | None = None
    exigencias_gr: list[str] = []

    @property
    def calcula(self) -> bool:
        return self.status in (StatusElegibilidade.APROVADA, StatusElegibilidade.REVISAR)
