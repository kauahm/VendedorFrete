from __future__ import annotations

import pytest

from engine.veiculo import DEDICADO, FRACIONADO, classificar_modalidade, fracao_ocupacao, restricao_dominante, selecionar_veiculo


@pytest.mark.parametrize(
    "peso_kg, cubagem_m3, esperado",
    [
        (100, 1.0, "Caminhão 3/4"),
        (2500, 21.65, "Caminhão 3/4"),
        (2501, 1.0, "Caminhão Toco"),
        (100, 21.66, "Caminhão Toco"),
        (5000, 36.43, "Caminhão Toco"),
        (5001, 1.0, "Caminhão Truck"),
        (8001, 1.0, "Bi Truck"),
        (100, 78.76, "Carreta Simples"),
        (20001, 1.0, "Carreta Simples"),
        (25001, 1.0, "Carreta LS"),
        (32001, 1.0, "Bitrem 7 eixos"),
        (57001, 1.0, "Rodotrem 9 eixos"),
        (74000, 151.65, "Rodotrem 9 eixos"),
    ],
)
def test_seleciona_o_menor_que_cabe(peso_kg, cubagem_m3, esperado, params):
    veiculo = selecionar_veiculo(peso_kg, cubagem_m3, params.frota)
    assert veiculo is not None
    assert veiculo.nome == esperado


@pytest.mark.parametrize("peso_kg, cubagem_m3", [(74001, 1.0), (1.0, 151.66), (80000, 400.0)])
def test_carga_acima_da_frota_nao_tem_veiculo(peso_kg, cubagem_m3, params):
    assert selecionar_veiculo(peso_kg, cubagem_m3, params.frota) is None


def test_ordem_da_frota_manda_na_selecao(params):
    frota_embaralhada = list(reversed(params.frota))
    veiculo = selecionar_veiculo(1000, 10.0, frota_embaralhada)
    assert veiculo.nome == "Caminhão 3/4"


def test_fracao_e_a_maior_entre_peso_e_cubagem(params):
    tres_quartos = params.frota[0]
    assert fracao_ocupacao(1250, 1.0, tres_quartos) == pytest.approx(0.5)
    assert fracao_ocupacao(1.0, 10.825, tres_quartos) == pytest.approx(0.5)
    assert fracao_ocupacao(1250, 21.65, tres_quartos) == pytest.approx(1.0)


def test_restricao_dominante(params):
    tres_quartos = params.frota[0]
    assert restricao_dominante(2000, 1.0, tres_quartos) == "peso"
    assert restricao_dominante(100, 20.0, tres_quartos) == "cubagem"
    assert restricao_dominante(1250, 10.825, tres_quartos) == "cubagem"


def test_corte_de_dedicado_e_inclusivo(params):
    assert classificar_modalidade(0.70, False, False, params) == DEDICADO
    assert classificar_modalidade(0.6999, False, False, params) == FRACIONADO


def test_exclusivo_e_refrigerada_forcam_dedicado(params):
    assert classificar_modalidade(0.01, True, False, params) == DEDICADO
    assert classificar_modalidade(0.01, False, True, params) == DEDICADO


def test_corte_vem_do_yaml_e_nao_do_codigo(params):
    params_agressivo = params.__class__(**{**params.__dict__, "corte_dedicado_fracao": 0.5})
    assert classificar_modalidade(0.6, False, False, params) == FRACIONADO
    assert classificar_modalidade(0.6, False, False, params_agressivo) == DEDICADO
