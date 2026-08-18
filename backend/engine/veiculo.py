"""Seleção de veículo, ocupação e classificação de modalidade. Python puro, sem IA."""

from __future__ import annotations

from typing import Iterable

from config import Params, Veiculo

DEDICADO = "DEDICADO"
FRACIONADO = "FRACIONADO"


def selecionar_veiculo(peso_kg: float, cubagem_m3: float, frota: Iterable[Veiculo]) -> Veiculo | None:
    """Menor veículo (por ordem) cuja cubagem E lotação atendem a carga."""
    for veiculo in sorted(frota, key=lambda v: v.ordem):
        if veiculo.cubagem_m3 >= cubagem_m3 and veiculo.lotacao_kg >= peso_kg:
            return veiculo
    return None


def fracao_ocupacao(peso_kg: float, cubagem_m3: float, veiculo: Veiculo) -> float:
    return max(cubagem_m3 / veiculo.cubagem_m3, peso_kg / veiculo.lotacao_kg)


def restricao_dominante(peso_kg: float, cubagem_m3: float, veiculo: Veiculo) -> str:
    ocupacao_peso = peso_kg / veiculo.lotacao_kg
    ocupacao_cubagem = cubagem_m3 / veiculo.cubagem_m3
    return "peso" if ocupacao_peso > ocupacao_cubagem else "cubagem"


def classificar_modalidade(
    fracao: float,
    exige_exclusivo: bool,
    refrigerada: bool,
    params: Params,
) -> str:
    """VALIDAR com o dono: corte_dedicado_fracao (0.70) é hipótese, vive no premissas.yaml."""
    if exige_exclusivo or refrigerada or fracao >= params.corte_dedicado_fracao:
        return DEDICADO
    return FRACIONADO
