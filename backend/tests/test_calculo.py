"""Testes de aceitação do motor de preço.

Os valores esperados vieram de um oráculo independente, transcrito a mão da
especificação (tabela ANTT, frota e premissas), não do próprio motor. Tolerância
de R$ 0,01 nos valores em reais; a spec admite ±2% contra a planilha corrigida.
"""

from __future__ import annotations

import pytest

from engine.calculo import calcular_custo, calcular_frete, calcular_preco, estimar_cubagem
from engine.veiculo import fracao_ocupacao, selecionar_veiculo
from models.carga import Carga, Confianca

TOLERANCIA_REAIS = 0.01

CENARIOS = [
    {
        "nome": "Exemplo da planilha (corrigido)",
        "peso_kg": 12000,
        "cubagem_m3": 6.0,
        "km": 2100,
        "esperado": {
            "status": "OK",
            "veiculo": "Bi Truck",
            "eixos": 4,
            "fracao": 0.6,
            "restricao": "peso",
            "modalidade": "FRACIONADO",
            "faixa": "longa",
            "custo_total": 9395.83,
            "preco_minimo": 11275.0,
            "preco_alvo": 11744.79,
            "preco_maximo": 12214.58,
        },
    },
    {
        "nome": "Carga leve volumosa - fracionado",
        "peso_kg": 500,
        "cubagem_m3": 15.0,
        "km": 300,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.6928,
            "restricao": "cubagem",
            "modalidade": "FRACIONADO",
            "faixa": "regional",
            "custo_total": 1613.73,
            "preco_minimo": 2413.73,
            "preco_alvo": 2413.73,
            "preco_maximo": 2413.73,
        },
    },
    {
        "nome": "Carga densa pesada - dedicado",
        "peso_kg": 25000,
        "cubagem_m3": 10.0,
        "km": 800,
        "esperado": {
            "status": "OK",
            "veiculo": "Carreta Simples",
            "eixos": 5,
            "fracao": 1.0,
            "restricao": "peso",
            "modalidade": "DEDICADO",
            "faixa": "media",
            "custo_total": 7373.85,
            "preco_minimo": 8848.62,
            "preco_alvo": 9217.31,
            "preco_maximo": 9586.0,
        },
    },
    {
        "nome": "Carga que nao cabe em nada",
        "peso_kg": 80000,
        "cubagem_m3": 400.0,
        "km": 500,
        "esperado": {"status": "SEM_VEICULO"},
    },
    {
        "nome": "Carga curta - fator 1.35",
        "peso_kg": 1000,
        "cubagem_m3": 3.0,
        "km": 50,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.4,
            "restricao": "peso",
            "modalidade": "FRACIONADO",
            "faixa": "curta",
            "custo_total": 432.37,
            "preco_minimo": 1232.37,
            "preco_alvo": 1232.37,
            "preco_maximo": 1232.37,
        },
    },
    {
        "nome": "Limite exato do 3/4",
        "peso_kg": 2500,
        "cubagem_m3": 21.65,
        "km": 200,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 1.0,
            "restricao": "cubagem",
            "modalidade": "DEDICADO",
            "faixa": "regional",
            "custo_total": 1535.48,
            "preco_minimo": 2335.48,
            "preco_alvo": 2335.48,
            "preco_maximo": 2335.48,
        },
    },
    {
        "nome": "Toco regional fracionado",
        "peso_kg": 3000,
        "cubagem_m3": 20.0,
        "km": 350,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão Toco",
            "eixos": 2,
            "fracao": 0.6,
            "restricao": "peso",
            "modalidade": "FRACIONADO",
            "faixa": "regional",
            "custo_total": 1566.49,
            "preco_minimo": 2366.49,
            "preco_alvo": 2366.49,
            "preco_maximo": 2366.49,
        },
    },
    {
        "nome": "Truck media distancia",
        "peso_kg": 7000,
        "cubagem_m3": 40.0,
        "km": 600,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão Truck",
            "eixos": 3,
            "fracao": 0.875,
            "restricao": "peso",
            "modalidade": "DEDICADO",
            "faixa": "media",
            "custo_total": 4428.59,
            "preco_minimo": 5314.31,
            "preco_alvo": 5535.74,
            "preco_maximo": 5757.17,
        },
    },
    {
        "nome": "Bi Truck cubagem dominante",
        "peso_kg": 6000,
        "cubagem_m3": 70.0,
        "km": 1200,
        "esperado": {
            "status": "OK",
            "veiculo": "Bi Truck",
            "eixos": 4,
            "fracao": 0.8889,
            "restricao": "cubagem",
            "modalidade": "DEDICADO",
            "faixa": "longa",
            "custo_total": 9258.82,
            "preco_minimo": 11110.59,
            "preco_alvo": 11573.53,
            "preco_maximo": 12036.47,
        },
    },
    {
        "nome": "Carreta LS longa",
        "peso_kg": 30000,
        "cubagem_m3": 90.0,
        "km": 1500,
        "esperado": {
            "status": "OK",
            "veiculo": "Carreta LS",
            "eixos": 6,
            "fracao": 0.9375,
            "restricao": "peso",
            "modalidade": "DEDICADO",
            "faixa": "longa",
            "custo_total": 14395.9,
            "preco_minimo": 17275.07,
            "preco_alvo": 17994.87,
            "preco_maximo": 18714.66,
        },
    },
    {
        "nome": "Bitrem longa",
        "peso_kg": 50000,
        "cubagem_m3": 105.0,
        "km": 2500,
        "esperado": {
            "status": "OK",
            "veiculo": "Bitrem 7 eixos",
            "eixos": 7,
            "fracao": 0.9442,
            "restricao": "cubagem",
            "modalidade": "DEDICADO",
            "faixa": "longa",
            "custo_total": 25907.99,
            "preco_minimo": 31089.59,
            "preco_alvo": 32384.99,
            "preco_maximo": 33680.39,
        },
    },
    {
        "nome": "Rodotrem maxima capacidade",
        "peso_kg": 70000,
        "cubagem_m3": 140.0,
        "km": 3000,
        "esperado": {
            "status": "OK",
            "veiculo": "Rodotrem 9 eixos",
            "eixos": 9,
            "fracao": 0.9459,
            "restricao": "peso",
            "modalidade": "DEDICADO",
            "faixa": "longa",
            "custo_total": 35069.05,
            "preco_minimo": 42082.86,
            "preco_alvo": 43836.31,
            "preco_maximo": 45589.76,
        },
    },
    {
        "nome": "Exclusivo forca dedicado",
        "peso_kg": 1000,
        "cubagem_m3": 5.0,
        "km": 400,
        "exclusivo": True,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.4,
            "restricao": "peso",
            "modalidade": "DEDICADO",
            "faixa": "regional",
            "custo_total": 2515.2,
            "preco_minimo": 3315.2,
            "preco_alvo": 3315.2,
            "preco_maximo": 3315.2,
        },
    },
    {
        "nome": "Refrigerada forca dedicado",
        "peso_kg": 2000,
        "cubagem_m3": 10.0,
        "km": 700,
        "refrigerada": True,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.8,
            "restricao": "peso",
            "modalidade": "DEDICADO",
            "faixa": "media",
            "custo_total": 3984.78,
            "preco_minimo": 4784.78,
            "preco_alvo": 4980.98,
            "preco_maximo": 5180.22,
        },
    },
    {
        "nome": "Lucro minimo domina o alvo",
        "peso_kg": 200,
        "cubagem_m3": 1.0,
        "km": 30,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.08,
            "restricao": "peso",
            "modalidade": "FRACIONADO",
            "faixa": "curta",
            "custo_total": 75.89,
            "preco_minimo": 875.89,
            "preco_alvo": 875.89,
            "preco_maximo": 875.89,
        },
    },
    {
        "nome": "Fronteira faixa 100 km",
        "peso_kg": 1000,
        "cubagem_m3": 5.0,
        "km": 100,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.4,
            "restricao": "peso",
            "modalidade": "FRACIONADO",
            "faixa": "curta",
            "custo_total": 564.64,
            "preco_minimo": 1364.64,
            "preco_alvo": 1364.64,
            "preco_maximo": 1364.64,
        },
    },
    {
        "nome": "Fronteira faixa 101 km",
        "peso_kg": 1000,
        "cubagem_m3": 5.0,
        "km": 101,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.4,
            "restricao": "peso",
            "modalidade": "FRACIONADO",
            "faixa": "regional",
            "custo_total": 483.24,
            "preco_minimo": 1283.24,
            "preco_alvo": 1283.24,
            "preco_maximo": 1283.24,
        },
    },
    {
        "nome": "Fronteira faixa 400 km",
        "peso_kg": 1000,
        "cubagem_m3": 5.0,
        "km": 400,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.4,
            "restricao": "peso",
            "modalidade": "FRACIONADO",
            "faixa": "regional",
            "custo_total": 1156.99,
            "preco_minimo": 1956.99,
            "preco_alvo": 1956.99,
            "preco_maximo": 1956.99,
        },
    },
    {
        "nome": "Fronteira faixa 401 km",
        "peso_kg": 1000,
        "cubagem_m3": 5.0,
        "km": 401,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.4,
            "restricao": "peso",
            "modalidade": "FRACIONADO",
            "faixa": "media",
            "custo_total": 1058.44,
            "preco_minimo": 1858.44,
            "preco_alvo": 1858.44,
            "preco_maximo": 1858.44,
        },
    },
    {
        "nome": "Fronteira faixa 800 km",
        "peso_kg": 1000,
        "cubagem_m3": 5.0,
        "km": 800,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.4,
            "restricao": "peso",
            "modalidade": "FRACIONADO",
            "faixa": "media",
            "custo_total": 1879.35,
            "preco_minimo": 2679.35,
            "preco_alvo": 2679.35,
            "preco_maximo": 2679.35,
        },
    },
    {
        "nome": "Fronteira faixa 801 km",
        "peso_kg": 1000,
        "cubagem_m3": 5.0,
        "km": 801,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.4,
            "restricao": "peso",
            "modalidade": "FRACIONADO",
            "faixa": "longa",
            "custo_total": 1791.82,
            "preco_minimo": 2591.82,
            "preco_alvo": 2591.82,
            "preco_maximo": 2591.82,
        },
    },
    {
        "nome": "Fracao exatamente no corte 0.70",
        "peso_kg": 1750,
        "cubagem_m3": 1.0,
        "km": 500,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.7,
            "restricao": "peso",
            "modalidade": "DEDICADO",
            "faixa": "media",
            "custo_total": 3005.06,
            "preco_minimo": 3805.06,
            "preco_alvo": 3805.06,
            "preco_maximo": 3906.58,
        },
    },
    {
        "nome": "Fracao logo abaixo do corte",
        "peso_kg": 1745,
        "cubagem_m3": 1.0,
        "km": 500,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.698,
            "restricao": "peso",
            "modalidade": "FRACIONADO",
            "faixa": "media",
            "custo_total": 2202.41,
            "preco_minimo": 3002.41,
            "preco_alvo": 3002.41,
            "preco_maximo": 3002.41,
        },
    },
    {
        "nome": "Empate peso x cubagem",
        "peso_kg": 1250,
        "cubagem_m3": 10.825,
        "km": 450,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão 3/4",
            "eixos": 2,
            "fracao": 0.5,
            "restricao": "cubagem",
            "modalidade": "FRACIONADO",
            "faixa": "media",
            "custo_total": 1449.07,
            "preco_minimo": 2249.07,
            "preco_alvo": 2249.07,
            "preco_maximo": 2249.07,
        },
    },
    {
        "nome": "Carga pesada que sobe de veiculo",
        "peso_kg": 8001,
        "cubagem_m3": 5.0,
        "km": 900,
        "esperado": {
            "status": "OK",
            "veiculo": "Bi Truck",
            "eixos": 4,
            "fracao": 0.4001,
            "restricao": "peso",
            "modalidade": "FRACIONADO",
            "faixa": "longa",
            "custo_total": 2850.43,
            "preco_minimo": 3650.43,
            "preco_alvo": 3650.43,
            "preco_maximo": 3705.56,
        },
    },
    {
        "nome": "Fracionado longa distancia fator 1.0",
        "peso_kg": 4000,
        "cubagem_m3": 30.0,
        "km": 1800,
        "esperado": {
            "status": "OK",
            "veiculo": "Caminhão Toco",
            "eixos": 2,
            "fracao": 0.8235,
            "restricao": "cubagem",
            "modalidade": "DEDICADO",
            "faixa": "longa",
            "custo_total": 9373.24,
            "preco_minimo": 11247.89,
            "preco_alvo": 11716.55,
            "preco_maximo": 12185.21,
        },
    },
]


def _cotar(cenario, params):
    carga = Carga(
        km=cenario["km"],
        peso_kg=cenario["peso_kg"],
        cubagem_m3=cenario["cubagem_m3"],
        exige_exclusivo=cenario.get("exclusivo", False),
        refrigerada=cenario.get("refrigerada", False),
    )
    return calcular_frete(carga, params)


@pytest.mark.parametrize("cenario", CENARIOS, ids=lambda c: c["nome"])
def test_cenario_de_aceitacao(cenario, params):
    cotacao = _cotar(cenario, params)
    esperado = cenario["esperado"]

    assert cotacao.status.value == esperado["status"]
    if esperado["status"] == "SEM_VEICULO":
        assert cotacao.custo_total is None
        return

    assert cotacao.veiculo_sugerido == esperado["veiculo"]
    assert cotacao.eixos == esperado["eixos"]
    assert cotacao.fracao_ocupacao == pytest.approx(esperado["fracao"], abs=1e-4)
    assert cotacao.restricao_dominante == esperado["restricao"]
    assert cotacao.modalidade == esperado["modalidade"]
    assert cotacao.faixa_distancia == esperado["faixa"]
    assert cotacao.custo_total == pytest.approx(esperado["custo_total"], abs=TOLERANCIA_REAIS)
    assert cotacao.preco_minimo == pytest.approx(esperado["preco_minimo"], abs=TOLERANCIA_REAIS)
    assert cotacao.preco_alvo == pytest.approx(esperado["preco_alvo"], abs=TOLERANCIA_REAIS)
    assert cotacao.preco_maximo == pytest.approx(esperado["preco_maximo"], abs=TOLERANCIA_REAIS)


@pytest.mark.parametrize("cenario", CENARIOS, ids=lambda c: c["nome"])
def test_precos_nunca_invertem(cenario, params):
    cotacao = _cotar(cenario, params)
    if cotacao.status.value == "SEM_VEICULO":
        return
    assert cotacao.custo_total < cotacao.preco_minimo
    assert cotacao.preco_minimo <= cotacao.preco_alvo <= cotacao.preco_maximo


@pytest.mark.parametrize("cenario", CENARIOS, ids=lambda c: c["nome"])
def test_lucro_alvo_respeita_piso_absoluto(cenario, params):
    cotacao = _cotar(cenario, params)
    if cotacao.status.value == "SEM_VEICULO":
        return
    lucro_minimo = cotacao.preco_minimo - cotacao.custo_total
    assert lucro_minimo >= params.lucro_minimo_viagem - TOLERANCIA_REAIS
    assert cotacao.lucro_alvo >= params.lucro_minimo_viagem - TOLERANCIA_REAIS


def test_dedicado_ignora_fracao_no_custo(params):
    custo_meia_carga = calcular_custo(km=1000, eixos=5, fracao=0.5, modalidade="DEDICADO", params=params)
    custo_cheio = calcular_custo(km=1000, eixos=5, fracao=1.0, modalidade="DEDICADO", params=params)
    assert custo_meia_carga == pytest.approx(custo_cheio)


def test_fracionado_e_proporcional_a_fracao(params):
    metade = calcular_custo(km=500, eixos=3, fracao=0.5, modalidade="FRACIONADO", params=params)
    inteiro = calcular_custo(km=500, eixos=3, fracao=1.0, modalidade="FRACIONADO", params=params)
    assert metade == pytest.approx(inteiro / 2)


def test_custo_inclui_apenas_um_bloco_de_impostos(params):
    """23% cobrem impostos + taxas + seguro. Não existe linha extra de 0,2% da NF."""
    km, eixos = 1000, 4
    ccd, cc = params.coeficientes_antt(eixos)
    piso = km * ccd + cc
    custo = calcular_custo(km=km, eixos=eixos, fracao=1.0, modalidade="DEDICADO", params=params)
    assert custo == pytest.approx(piso * (1 + params.impostos_taxas_seguro))


def test_valor_nf_nao_altera_o_preco(params):
    base = Carga(km=900, peso_kg=9000, cubagem_m3=40.0)
    com_nf = base.model_copy(update={"valor_nf": 900000.0})
    assert calcular_frete(base, params).preco_alvo == calcular_frete(com_nf, params).preco_alvo


def test_tabela_b_muda_o_custo(params):
    params_b = params.__class__(**{**params.__dict__, "tabela_antt": "B"})
    custo_a = calcular_custo(km=1000, eixos=5, fracao=1.0, modalidade="DEDICADO", params=params)
    custo_b = calcular_custo(km=1000, eixos=5, fracao=1.0, modalidade="DEDICADO", params=params_b)
    assert custo_a != custo_b
    assert custo_b == pytest.approx((1000 * 5.9334 + 594.62) * 1.23)


def test_colchao_agregado_encarece_proporcionalmente(params):
    params_colchao = params.__class__(**{**params.__dict__, "colchao_agregado": 0.10})
    custo = calcular_custo(km=700, eixos=3, fracao=1.0, modalidade="DEDICADO", params=params)
    custo_colchao = calcular_custo(km=700, eixos=3, fracao=1.0, modalidade="DEDICADO", params=params_colchao)
    assert custo_colchao == pytest.approx(custo * 1.10)


def test_preco_de_carga_barata_e_puxado_pelo_lucro_minimo(params):
    precos = calcular_preco(1000.0, params)
    assert precos["preco_minimo"] == pytest.approx(1800.0)
    assert precos["preco_alvo"] == pytest.approx(1800.0)
    assert precos["preco_maximo"] == pytest.approx(1800.0)


def test_preco_de_carga_cara_usa_as_margens(params):
    precos = calcular_preco(20000.0, params)
    assert precos["preco_minimo"] == pytest.approx(24000.0)
    assert precos["preco_alvo"] == pytest.approx(25000.0)
    assert precos["preco_maximo"] == pytest.approx(26000.0)


def test_km_custo_e_km_alvo(params):
    cotacao = calcular_frete(Carga(km=1000, peso_kg=20000, cubagem_m3=50.0), params)
    assert cotacao.km_custo == pytest.approx(round(cotacao.custo_total / 1000, 2))
    assert cotacao.km_alvo == pytest.approx(round(cotacao.preco_alvo / 1000, 2))


def test_sem_veiculo_nao_gera_preco(params):
    cotacao = calcular_frete(Carga(km=500, peso_kg=80000, cubagem_m3=400.0), params)
    assert cotacao.status.value == "SEM_VEICULO"
    assert cotacao.preco_alvo is None
    assert cotacao.alertas


def test_cubagem_estimada_rebaixa_confianca(params):
    cubagem = estimar_cubagem(3000, params)
    assert cubagem == pytest.approx(10.0)
    carga = Carga(km=400, peso_kg=3000, cubagem_m3=cubagem, confianca=Confianca.BAIXA)
    cotacao = calcular_frete(carga, params)
    assert cotacao.confianca == "BAIXA"
    assert any("Confiança BAIXA" in alerta for alerta in cotacao.alertas)


def test_alerta_de_ocupacao_no_limite(params):
    carga = Carga(km=600, peso_kg=25000, cubagem_m3=20.0)
    cotacao = calcular_frete(carga, params)
    assert any("Ocupação" in alerta for alerta in cotacao.alertas)


def test_alerta_quando_veiculo_pedido_diverge(params):
    carga = Carga(km=600, peso_kg=1000, cubagem_m3=5.0, veiculo_pedido="Carreta Simples")
    cotacao = calcular_frete(carga, params)
    assert any("Carreta Simples" in alerta for alerta in cotacao.alertas)


def test_menor_veiculo_que_cabe(params):
    veiculo = selecionar_veiculo(peso_kg=2600, cubagem_m3=1.0, frota=params.frota)
    assert veiculo.nome == "Caminhão Toco"


def test_fracao_usa_a_maior_restricao(params):
    truck = next(v for v in params.frota if v.nome == "Caminhão Truck")
    assert fracao_ocupacao(4000, 46.88, truck) == pytest.approx(1.0)
    assert fracao_ocupacao(8000, 1.0, truck) == pytest.approx(1.0)


def test_carga_sem_peso_e_sem_cubagem_e_invalida():
    with pytest.raises(ValueError):
        Carga(km=100, peso_kg=0, cubagem_m3=0)


def test_km_zero_e_invalido():
    with pytest.raises(ValueError):
        Carga(km=0, peso_kg=1000, cubagem_m3=5.0)
