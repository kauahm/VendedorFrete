from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class StatusCotacao(str, Enum):
    OK = "OK"
    SEM_VEICULO = "SEM_VEICULO"


class Cotacao(BaseModel):
    status: StatusCotacao = StatusCotacao.OK
    veiculo_sugerido: str | None = None
    eixos: int | None = None
    fracao_ocupacao: float | None = None
    restricao_dominante: str | None = None
    modalidade: str | None = None
    faixa_distancia: str | None = None
    fator_faixa: float | None = None
    custo_total: float | None = None
    km_custo: float | None = None
    preco_minimo: float | None = None
    preco_alvo: float | None = None
    preco_maximo: float | None = None
    km_alvo: float | None = None
    lucro_alvo: float | None = None
    confianca: str | None = None
    alertas: list[str] = []
