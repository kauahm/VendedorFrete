"""Motor de preço. Determinístico, sem IA: todo número sai de data/*.yaml."""

from __future__ import annotations

from config import Params, Veiculo
from engine.veiculo import (
    DEDICADO,
    classificar_modalidade,
    fracao_ocupacao,
    restricao_dominante,
    selecionar_veiculo,
)
from models.carga import Carga, Confianca
from models.cotacao import Cotacao, StatusCotacao

FRACAO_ALERTA_LIMITE = 0.95


def estimar_cubagem(peso_kg: float, params: Params) -> float:
    """Cubagem presumida quando o anúncio não informa. Rebaixa a confiança para BAIXA."""
    return peso_kg / params.densidade_estimada_kg_m3


def calcular_custo(km: float, eixos: int, fracao: float, modalidade: str, params: Params) -> float:
    ccd, cc = params.coeficientes_antt(eixos)
    piso_antt = (km * ccd) + cc

    if modalidade == DEDICADO:
        custo_agregado = piso_antt
    else:
        custo_agregado = piso_antt * params.fator_faixa(km) * fracao

    custo_agregado *= 1 + params.colchao_agregado
    return custo_agregado * (1 + params.impostos_taxas_seguro)


def calcular_preco(custo_total: float, params: Params) -> dict[str, float]:
    """Piso de lucro absoluto manda: em carga barata o mínimo puxa alvo e máximo para cima."""
    preco_minimo = max(
        custo_total + params.lucro_minimo_viagem,
        custo_total * (1 + params.margem_minima),
    )
    preco_alvo = max(custo_total * (1 + params.margem_alvo), preco_minimo)
    preco_maximo = max(custo_total * (1 + params.margem_maxima), preco_alvo)

    return {
        "preco_minimo": round(preco_minimo, 2),
        "preco_alvo": round(preco_alvo, 2),
        "preco_maximo": round(preco_maximo, 2),
    }


def gerar_alertas(carga: Carga, veiculo: Veiculo, fracao: float, custo_total: float, params: Params) -> list[str]:
    alertas: list[str] = []

    if carga.confianca != Confianca.ALTA:
        alertas.append(f"Confiança {carga.confianca.value}: dados do anúncio incompletos ou estimados")
    if fracao >= FRACAO_ALERTA_LIMITE:
        alertas.append(f"Ocupação de {fracao:.0%} no {veiculo.nome}: sem folga para volume adicional")
    if custo_total * (1 + params.margem_alvo) < custo_total + params.lucro_minimo_viagem:
        alertas.append(
            f"Margem alvo abaixo do lucro mínimo de R$ {params.lucro_minimo_viagem:,.2f}: preço alvo elevado ao piso"
        )
    if carga.valor_nf is None:
        alertas.append("Valor da NF ausente: faixa de GR e checagem de LMG não avaliadas")
    else:
        if carga.valor_nf > params.lmg_maximo:
            alertas.append(
                f"Valor da NF R$ {carga.valor_nf:,.2f} acima do LMG de R$ {params.lmg_maximo:,.2f}"
            )
        faixa = params.faixa_gr(carga.valor_nf)
        if faixa and faixa.exigencias:
            alertas.append(f"Faixa de GR {faixa.faixa}: exige {', '.join(faixa.exigencias)}")
    if carga.veiculo_pedido and carga.veiculo_pedido.strip().lower() != veiculo.nome.lower():
        alertas.append(f"Embarcador pediu {carga.veiculo_pedido}; motor sugere {veiculo.nome}")
    if carga.carroceria and veiculo.carroceria and carga.carroceria.strip().lower() != veiculo.carroceria.lower():
        alertas.append(f"Carroceria pedida ({carga.carroceria}) difere da padrão do {veiculo.nome} ({veiculo.carroceria})")

    return alertas


def calcular_frete(carga: Carga, params: Params) -> Cotacao:
    veiculo = selecionar_veiculo(carga.peso_kg, carga.cubagem_m3, params.frota)
    if veiculo is None:
        maior = max(params.frota, key=lambda v: v.ordem)
        return Cotacao(
            status=StatusCotacao.SEM_VEICULO,
            confianca=carga.confianca.value,
            alertas=[
                f"Carga de {carga.peso_kg:,.0f} kg e {carga.cubagem_m3:,.2f} m³ excede o maior veículo da frota "
                f"({maior.nome}: {maior.lotacao_kg:,.0f} kg / {maior.cubagem_m3:,.2f} m³)"
            ],
        )

    fracao = fracao_ocupacao(carga.peso_kg, carga.cubagem_m3, veiculo)
    modalidade = classificar_modalidade(fracao, carga.exige_exclusivo, carga.refrigerada, params)
    custo_total = calcular_custo(carga.km, veiculo.eixos, fracao, modalidade, params)
    precos = calcular_preco(custo_total, params)
    faixa = params.faixa_distancia(carga.km)

    return Cotacao(
        status=StatusCotacao.OK,
        veiculo_sugerido=veiculo.nome,
        eixos=veiculo.eixos,
        fracao_ocupacao=round(fracao, 4),
        restricao_dominante=restricao_dominante(carga.peso_kg, carga.cubagem_m3, veiculo),
        modalidade=modalidade,
        faixa_distancia=faixa.nome,
        fator_faixa=faixa.fator,
        custo_total=round(custo_total, 2),
        km_custo=round(custo_total / carga.km, 2),
        km_alvo=round(precos["preco_alvo"] / carga.km, 2),
        lucro_alvo=round(precos["preco_alvo"] - custo_total, 2),
        confianca=carga.confianca.value,
        alertas=gerar_alertas(carga, veiculo, fracao, custo_total, params),
        **precos,
    )
