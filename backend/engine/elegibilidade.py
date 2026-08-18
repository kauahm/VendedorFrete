"""Filtro de elegibilidade: roda ANTES do cálculo.

Tudo determinístico. A classificação de mercadoria aceita um classificador
injetado (a versão com IA entra na semana 2); o padrão é um matcher de termos
contra data/exclusoes.yaml e data/mercadorias_especificas.yaml.
"""

from __future__ import annotations

from typing import Callable, Protocol

from config import Params, normalizar
from models.elegibilidade import ClassificacaoMercadoria, ElegibilidadeResult, StatusElegibilidade, TipoMercadoria

CONFIANCA_MINIMA = 0.8
DESCRICAO_MINIMA_CARACTERES = 3


class CargaElegivel(Protocol):
    valor_nf: float | None
    mercadoria: str | None


Classificador = Callable[[str | None, Params], ClassificacaoMercadoria]


def classificar_mercadoria(mercadoria: str | None, params: Params) -> ClassificacaoMercadoria:
    descricao = normalizar(mercadoria or "")
    if len(descricao) < DESCRICAO_MINIMA_CARACTERES:
        return ClassificacaoMercadoria(tipo=TipoMercadoria.REVISAR, match=None, confianca=0.0)

    for excluida in params.exclusoes:
        if excluida.casa_com(descricao):
            return ClassificacaoMercadoria(tipo=TipoMercadoria.EXCLUIDA, match=excluida.item, confianca=0.95)

    for especifica in params.mercadorias_especificas:
        if especifica.casa_com(descricao):
            return ClassificacaoMercadoria(
                tipo=TipoMercadoria.ESPECIFICA,
                match=especifica.item,
                confianca=0.9,
                exigencias=list(especifica.exigencias),
            )

    return ClassificacaoMercadoria(
        tipo=TipoMercadoria.NAO_ESPECIFICA,
        match=None,
        confianca=params.confianca_classificador_deterministico,
    )


def verificar_elegibilidade(
    carga: CargaElegivel,
    params: Params,
    classificador: Classificador = classificar_mercadoria,
) -> ElegibilidadeResult:
    valor_nf = getattr(carga, "valor_nf", None)

    if valor_nf is not None and valor_nf > params.lmg_maximo:
        return ElegibilidadeResult(
            status=StatusElegibilidade.BLOQUEIO,
            motivo=f"NF R$ {valor_nf:,.2f} excede o LMG de R$ {params.lmg_maximo:,.2f}",
        )

    classificacao = classificador(getattr(carga, "mercadoria", None), params)

    if classificacao.tipo == TipoMercadoria.EXCLUIDA:
        return ElegibilidadeResult(
            status=StatusElegibilidade.RECUSADA,
            motivo=f"EXCLUSAO_APOLICE: mercadoria excluída da apólice ({classificacao.match})",
            classificacao_mercadoria=classificacao.tipo,
        )

    faixa = params.faixa_gr(valor_nf)
    exigencias = sorted(set(list(classificacao.exigencias) + list(faixa.exigencias if faixa else [])))

    if classificacao.confianca < CONFIANCA_MINIMA:
        return ElegibilidadeResult(
            status=StatusElegibilidade.REVISAR,
            motivo=f"Classificação incerta: {classificacao.tipo.value} ({classificacao.confianca:.0%})",
            classificacao_mercadoria=TipoMercadoria.REVISAR,
            faixa_gr=faixa.faixa if faixa else None,
            exigencias_gr=exigencias,
        )

    return ElegibilidadeResult(
        status=StatusElegibilidade.APROVADA,
        motivo=None,
        classificacao_mercadoria=classificacao.tipo,
        faixa_gr=faixa.faixa if faixa else None,
        exigencias_gr=exigencias,
    )
