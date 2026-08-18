"""Trava os YAMLs contra a especificação: edição errada quebra aqui, não em produção."""

from __future__ import annotations

import pytest

from config import carregar_params, validar_params


def test_frota_completa_e_ordenada(params):
    assert [v.nome for v in params.frota] == [
        "Caminhão 3/4",
        "Caminhão Toco",
        "Caminhão Truck",
        "Bi Truck",
        "Carreta Simples",
        "Carreta LS",
        "Bitrem 7 eixos",
        "Rodotrem 9 eixos",
    ]


@pytest.mark.parametrize(
    "nome, cubagem_m3, lotacao_kg, eixos",
    [
        ("Caminhão 3/4", 21.65, 2500, 2),
        ("Caminhão Toco", 36.43, 5000, 2),
        ("Caminhão Truck", 46.88, 8000, 3),
        ("Bi Truck", 78.75, 20000, 4),
        ("Carreta Simples", 100.0, 25000, 5),
        ("Carreta LS", 110.0, 32000, 6),
        ("Bitrem 7 eixos", 111.21, 57000, 7),
        ("Rodotrem 9 eixos", 151.65, 74000, 9),
    ],
)
def test_capacidades_conservadoras_do_pdf(nome, cubagem_m3, lotacao_kg, eixos, params):
    veiculo = next(v for v in params.frota if v.nome == nome)
    assert (veiculo.cubagem_m3, veiculo.lotacao_kg, veiculo.eixos) == (cubagem_m3, lotacao_kg, eixos)


@pytest.mark.parametrize(
    "eixos, ccd, cc",
    [
        (2, 3.9826, 451.84),
        (3, 5.0977, 541.86),
        (4, 5.7822, 588.86),
        (5, 6.6718, 657.56),
        (6, 7.3547, 671.93),
        (7, 8.0927, 831.66),
        (9, 9.2027, 903.32),
    ],
)
def test_coeficientes_antt_tabela_a(eixos, ccd, cc, params):
    assert params.coeficientes_antt(eixos) == (ccd, cc)


def test_todo_veiculo_tem_coeficiente_antt(params):
    for veiculo in params.frota:
        assert params.coeficientes_antt(veiculo.eixos)


def test_premissas_comerciais(params):
    assert params.impostos_taxas_seguro == 0.23
    assert params.lucro_minimo_viagem == 800
    assert (params.margem_minima, params.margem_alvo, params.margem_maxima) == (0.20, 0.25, 0.30)
    assert params.lmg_maximo == 1_000_000
    assert params.colchao_agregado == 0.0
    assert params.folga_maximo_sobre_minimo == 0.05


def test_corte_dedicado_confirmado_pelo_dono(params):
    """0,70 é decisão do dono do negócio, não hipótese pendente."""
    assert params.corte_dedicado_fracao == 0.70


def test_mercadorias_especificas_seguem_nao_validadas(params):
    """Enquanto a corretora não revisar a lista, ela não pode alimentar elegibilidade."""
    assert params.mercadorias_especificas_validadas is False


@pytest.mark.parametrize(
    "km, fator, nome",
    [(0, 1.35, "curta"), (100, 1.35, "curta"), (101, 1.15, "regional"), (400, 1.15, "regional"),
     (401, 1.05, "media"), (800, 1.05, "media"), (801, 1.0, "longa"), (5000, 1.0, "longa")],
)
def test_fatores_de_faixa(km, fator, nome, params):
    assert params.fator_faixa(km) == fator
    assert params.faixa_distancia(km).nome == nome


def test_km_dentro_do_vao_entre_faixas_cai_na_faixa_seguinte(params):
    assert params.fator_faixa(100.4) == 1.15


def test_km_acima_da_ultima_faixa_falha(params):
    with pytest.raises(ValueError):
        params.fator_faixa(100_000)


def test_eixos_sem_coeficiente_falha(params):
    with pytest.raises(ValueError):
        params.coeficientes_antt(8)


def test_margens_incoerentes_sao_rejeitadas(params):
    invalido = params.__class__(**{**params.__dict__, "margem_alvo": 0.5, "margem_maxima": 0.3})
    with pytest.raises(ValueError):
        validar_params(invalido)


def test_yamls_do_repositorio_carregam():
    assert carregar_params().frota
