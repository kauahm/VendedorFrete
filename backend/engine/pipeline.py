"""Do anúncio estruturado até a cotação: normaliza, filtra e calcula."""

from __future__ import annotations

from config import Params
from engine.calculo import calcular_frete, estimar_cubagem
from engine.elegibilidade import Classificador, classificar_mercadoria, verificar_elegibilidade
from models.carga import Carga, Confianca
from models.cotacao import Cotacao, StatusCotacao
from models.elegibilidade import ElegibilidadeResult, StatusElegibilidade
from models.oportunidade import Oportunidade, OportunidadeEntrada, StatusOportunidade


def definir_confianca(entrada: OportunidadeEntrada, cubagem_estimada: bool) -> Confianca:
    if cubagem_estimada:
        return Confianca.BAIXA
    if entrada.campos_ausentes or entrada.valor_nf is None:
        return Confianca.MEDIA
    return Confianca.ALTA


def montar_carga(entrada: OportunidadeEntrada, params: Params) -> tuple[Carga | None, list[str]]:
    faltando = []
    if entrada.distancia_km is None:
        faltando.append("distancia_km")
    if not entrada.peso_kg and not entrada.cubagem_m3:
        faltando.append("peso_kg")
    if faltando:
        return None, faltando

    cubagem_estimada = entrada.cubagem_m3 is None and bool(entrada.peso_kg)
    cubagem = estimar_cubagem(entrada.peso_kg, params) if cubagem_estimada else (entrada.cubagem_m3 or 0.0)

    carga = Carga(
        km=entrada.distancia_km,
        peso_kg=entrada.peso_kg or 0.0,
        cubagem_m3=cubagem,
        valor_nf=entrada.valor_nf,
        mercadoria=entrada.mercadoria,
        exige_exclusivo=entrada.exige_exclusivo,
        refrigerada=entrada.refrigerada,
        veiculo_pedido=entrada.veiculo_pedido,
        carroceria=entrada.carroceria,
        confianca=definir_confianca(entrada, cubagem_estimada),
    )
    return carga, []


def _status(elegibilidade: ElegibilidadeResult, cotacao: Cotacao | None, faltando: list[str]) -> StatusOportunidade:
    if elegibilidade.status in (StatusElegibilidade.RECUSADA, StatusElegibilidade.BLOQUEIO):
        return StatusOportunidade.RECUSADA
    if faltando or cotacao is None or cotacao.status == StatusCotacao.SEM_VEICULO:
        return StatusOportunidade.INCOMPLETA
    return StatusOportunidade.CALCULADA


def processar_oportunidade(
    entrada: OportunidadeEntrada,
    params: Params,
    classificador: Classificador = classificar_mercadoria,
) -> tuple[Oportunidade, Cotacao | None, ElegibilidadeResult]:
    elegibilidade = verificar_elegibilidade(entrada, params, classificador=classificador)

    carga, faltando = montar_carga(entrada, params)
    cotacao = None
    if carga is not None and elegibilidade.calcula:
        cotacao = calcular_frete(carga, params)

    alertas = list(cotacao.alertas) if cotacao else []
    alertas.extend(elegibilidade.avisos)
    if faltando:
        alertas.append(f"Campos ausentes para cotar: {', '.join(faltando)}")

    oportunidade = Oportunidade(
        **entrada.model_dump(),
        confianca=carga.confianca.value if carga else None,
        elegibilidade=elegibilidade.status.value,
        motivo_elegibilidade=elegibilidade.motivo,
        faixa_gr=elegibilidade.faixa_gr,
        classificacao_mercadoria=(
            elegibilidade.classificacao_mercadoria.value if elegibilidade.classificacao_mercadoria else None
        ),
        modalidade=cotacao.modalidade if cotacao else None,
        veiculo_sugerido=cotacao.veiculo_sugerido if cotacao else None,
        eixos=cotacao.eixos if cotacao else None,
        fracao_ocupacao=cotacao.fracao_ocupacao if cotacao else None,
        restricao_dominante=cotacao.restricao_dominante if cotacao else None,
        custo_total=cotacao.custo_total if cotacao else None,
        preco_minimo=cotacao.preco_minimo if cotacao else None,
        preco_alvo=cotacao.preco_alvo if cotacao else None,
        preco_maximo=cotacao.preco_maximo if cotacao else None,
        status=_status(elegibilidade, cotacao, faltando),
        hash_dedup_valor=entrada.hash_dedup(),
        alertas=alertas,
    )
    if carga is not None:
        oportunidade.cubagem_m3 = carga.cubagem_m3
    return oportunidade, cotacao, elegibilidade
