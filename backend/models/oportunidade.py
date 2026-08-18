from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


class StatusOportunidade(str, Enum):
    CAPTADA = "CAPTADA"
    INCOMPLETA = "INCOMPLETA"
    RECUSADA = "RECUSADA"
    CALCULADA = "CALCULADA"
    CONTATADA = "CONTATADA"
    PROPOSTA_ENVIADA = "PROPOSTA_ENVIADA"
    EM_NEGOCIACAO = "EM_NEGOCIACAO"
    FECHADA = "FECHADA"
    PERDIDA = "PERDIDA"
    CANCELADA = "CANCELADA"


class OportunidadeEntrada(BaseModel):
    """Anúncio já estruturado, vindo do Claude in Chrome ou do extrator de texto."""

    origem_cidade: str
    origem_uf: str
    destino_cidade: str
    destino_uf: str
    mercadoria: str | None = None
    peso_kg: float | None = Field(default=None, ge=0)
    cubagem_m3: float | None = Field(default=None, ge=0)
    valor_nf: float | None = Field(default=None, ge=0)
    veiculo_pedido: str | None = None
    carroceria: str | None = None
    empresa: str | None = None
    contato: str | None = None
    observacoes: str | None = None
    fonte: str = "cargas.com.br"
    data_anuncio: datetime | None = None
    distancia_km: float | None = Field(default=None, gt=0)
    exige_exclusivo: bool = False
    refrigerada: bool = False
    campos_ausentes: list[str] = []

    @field_validator("origem_uf", "destino_uf")
    @classmethod
    def uf_valida(cls, valor: str) -> str:
        uf = (valor or "").strip().upper()
        if uf not in UFS:
            raise ValueError(f"UF inválida: {valor}")
        return uf

    def hash_dedup(self) -> str:
        chave = f"{self.origem_uf}{self.destino_uf}{self.peso_kg}{(self.empresa or '').strip().lower()}"
        return hashlib.md5(chave.encode("utf-8")).hexdigest()


class Oportunidade(OportunidadeEntrada):
    id: str | None = None
    created_at: datetime | None = None
    tempo_viagem_min: int | None = None
    confianca: str | None = None
    elegibilidade: str | None = None
    motivo_elegibilidade: str | None = None
    faixa_gr: str | None = None
    classificacao_mercadoria: str | None = None
    modalidade: str | None = None
    veiculo_sugerido: str | None = None
    eixos: int | None = None
    fracao_ocupacao: float | None = None
    restricao_dominante: str | None = None
    custo_total: float | None = None
    preco_minimo: float | None = None
    preco_alvo: float | None = None
    preco_maximo: float | None = None
    score: float | None = None
    status: StatusOportunidade = StatusOportunidade.CAPTADA
    hash_dedup_valor: str | None = None
    alertas: list[str] = []
