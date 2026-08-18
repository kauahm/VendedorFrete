from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Confianca(str, Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"


class Carga(BaseModel):
    """Entrada do motor de cálculo. Já normalizada: km e cubagem resolvidos."""

    km: float = Field(gt=0)
    peso_kg: float = Field(ge=0)
    cubagem_m3: float = Field(ge=0)
    valor_nf: float | None = Field(default=None, ge=0)
    mercadoria: str | None = None
    exige_exclusivo: bool = False
    refrigerada: bool = False
    veiculo_pedido: str | None = None
    carroceria: str | None = None
    confianca: Confianca = Confianca.ALTA

    @model_validator(mode="after")
    def exige_peso_ou_cubagem(self) -> "Carga":
        if self.peso_kg <= 0 and self.cubagem_m3 <= 0:
            raise ValueError("carga precisa de peso_kg ou cubagem_m3 maior que zero")
        return self
