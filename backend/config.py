"""Carrega os YAMLs de data/ e expõe os parâmetros de negócio como objetos imutáveis.

Os YAMLs são a fonte única de verdade do motor: nenhum número de negócio pode
aparecer hardcoded no código Python.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

DATA_DIR = Path(__file__).resolve().parent / "data"


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


@dataclass(frozen=True)
class Veiculo:
    nome: str
    ordem: int
    eixos: int
    cubagem_m3: float
    lotacao_kg: float
    pallets_max: int
    carroceria: str
    comprimento_m: float | None = None
    largura_m: float | None = None
    altura_m: float | None = None


@dataclass(frozen=True)
class FaixaDistancia:
    de: float
    ate: float
    fator: float
    nome: str


@dataclass(frozen=True)
class FaixaGR:
    faixa: str
    de: float
    ate: float
    exigencias: tuple[str, ...]


@dataclass(frozen=True)
class ItemMercadoria:
    item: str
    termos: tuple[str, ...]
    exigencias: tuple[str, ...] = ()

    def casa_com(self, descricao_normalizada: str) -> bool:
        return any(normalizar(t) in descricao_normalizada for t in self.termos)


@dataclass(frozen=True)
class Params:
    tabela_antt: str
    colchao_agregado: float
    impostos_taxas_seguro: float
    lucro_minimo_viagem: float
    margem_minima: float
    margem_alvo: float
    margem_maxima: float
    corte_dedicado_fracao: float
    densidade_estimada_kg_m3: float
    confianca_classificador_deterministico: float
    lmg_maximo: float
    apolice_numero: str
    apolice_vigencia_fim: str
    seguradora: str
    piso_base_km: float
    fatores_faixa_distancia: tuple[FaixaDistancia, ...]
    faixas_gr: tuple[FaixaGR, ...]
    frota: tuple[Veiculo, ...]
    antt: Mapping[str, Any]
    exclusoes: tuple[ItemMercadoria, ...]
    mercadorias_especificas: tuple[ItemMercadoria, ...]
    regra_subcontratacao: str

    def coeficientes_antt(self, eixos: int) -> tuple[float, float]:
        chave = "tabela_a" if self.tabela_antt.upper() == "A" else "tabela_b"
        tabela = self.antt[chave]
        if eixos not in tabela:
            raise ValueError(f"Eixos {eixos} sem coeficiente na {chave} do antt.yaml")
        return float(tabela[eixos]["ccd"]), float(tabela[eixos]["cc"])

    def fator_faixa(self, km: float) -> float:
        return self.faixa_distancia(km).fator

    def faixa_distancia(self, km: float) -> FaixaDistancia:
        for faixa in self.fatores_faixa_distancia:
            if km <= faixa.ate:
                return faixa
        raise ValueError(f"Distância {km} km fora das faixas de premissas.yaml")

    def faixa_gr(self, valor_nf: float | None) -> FaixaGR | None:
        if valor_nf is None:
            return None
        for faixa in self.faixas_gr:
            if faixa.de <= valor_nf <= faixa.ate:
                return faixa
        return None


def _ler_yaml(data_dir: Path, nome: str) -> Any:
    with (data_dir / nome).open(encoding="utf-8") as arquivo:
        return yaml.safe_load(arquivo)


def _itens_mercadoria(registros: list[dict[str, Any]] | None) -> tuple[ItemMercadoria, ...]:
    return tuple(
        ItemMercadoria(
            item=registro["item"],
            termos=tuple(registro.get("termos") or [registro["item"]]),
            exigencias=tuple(registro.get("exigencias") or []),
        )
        for registro in (registros or [])
    )


def carregar_params(data_dir: Path | str = DATA_DIR) -> Params:
    data_dir = Path(data_dir)
    premissas = _ler_yaml(data_dir, "premissas.yaml")
    frota = _ler_yaml(data_dir, "frota.yaml")
    antt = _ler_yaml(data_dir, "antt.yaml")
    exclusoes = _ler_yaml(data_dir, "exclusoes.yaml")
    especificas = _ler_yaml(data_dir, "mercadorias_especificas.yaml")

    veiculos = tuple(
        sorted(
            (
                Veiculo(
                    nome=v["nome"],
                    ordem=int(v["ordem"]),
                    eixos=int(v["eixos"]),
                    cubagem_m3=float(v["cubagem_m3"]),
                    lotacao_kg=float(v["lotacao_kg"]),
                    pallets_max=int(v.get("pallets_max", 0)),
                    carroceria=v.get("carroceria", ""),
                    comprimento_m=v.get("comprimento_m"),
                    largura_m=v.get("largura_m"),
                    altura_m=v.get("altura_m"),
                )
                for v in frota["veiculos"]
            ),
            key=lambda v: v.ordem,
        )
    )

    faixas_distancia = tuple(
        sorted(
            (
                FaixaDistancia(de=float(f["de"]), ate=float(f["ate"]), fator=float(f["fator"]), nome=f["nome"])
                for f in premissas["fatores_faixa_distancia"]
            ),
            key=lambda f: f.ate,
        )
    )

    faixas_gr = tuple(
        sorted(
            (
                FaixaGR(
                    faixa=f["faixa"],
                    de=float(f["de"]),
                    ate=float(f["ate"]),
                    exigencias=tuple(f.get("exigencias") or []),
                )
                for f in premissas["faixas_gr"]
            ),
            key=lambda f: f.de,
        )
    )

    params = Params(
        tabela_antt=str(premissas["tabela_antt"]),
        colchao_agregado=float(premissas["colchao_agregado"]),
        impostos_taxas_seguro=float(premissas["impostos_taxas_seguro"]),
        lucro_minimo_viagem=float(premissas["lucro_minimo_viagem"]),
        margem_minima=float(premissas["margem_minima"]),
        margem_alvo=float(premissas["margem_alvo"]),
        margem_maxima=float(premissas["margem_maxima"]),
        corte_dedicado_fracao=float(premissas["corte_dedicado_fracao"]),
        densidade_estimada_kg_m3=float(premissas["densidade_estimada_kg_m3"]),
        confianca_classificador_deterministico=float(premissas["confianca_classificador_deterministico"]),
        lmg_maximo=float(premissas["lmg_maximo"]),
        apolice_numero=str(premissas["apolice_numero"]),
        apolice_vigencia_fim=str(premissas["apolice_vigencia_fim"]),
        seguradora=str(premissas["seguradora"]),
        piso_base_km=float(antt["piso_base_km"]),
        fatores_faixa_distancia=faixas_distancia,
        faixas_gr=faixas_gr,
        frota=veiculos,
        antt=antt,
        exclusoes=_itens_mercadoria(exclusoes.get("exclusoes")),
        mercadorias_especificas=_itens_mercadoria(especificas.get("mercadorias_especificas")),
        regra_subcontratacao=str(exclusoes.get("regra_subcontratacao", "")),
    )
    validar_params(params)
    return params


def validar_params(params: Params) -> None:
    if params.tabela_antt.upper() not in ("A", "B"):
        raise ValueError("tabela_antt deve ser 'A' ou 'B'")
    if not (params.margem_minima <= params.margem_alvo <= params.margem_maxima):
        raise ValueError("margens devem obedecer minima <= alvo <= maxima")
    if not 0 < params.corte_dedicado_fracao <= 1:
        raise ValueError("corte_dedicado_fracao deve estar entre 0 e 1")
    if not params.frota:
        raise ValueError("frota.yaml sem veículos")
    for veiculo in params.frota:
        params.coeficientes_antt(veiculo.eixos)
    ordens = [v.ordem for v in params.frota]
    if len(set(ordens)) != len(ordens):
        raise ValueError("frota.yaml com ordem duplicada")


@lru_cache(maxsize=1)
def params_padrao() -> Params:
    return carregar_params()
