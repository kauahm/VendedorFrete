from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def cliente():
    return TestClient(app)


def _anuncio(**campos):
    base = dict(
        origem_cidade="Campinas",
        origem_uf="SP",
        destino_cidade="Curitiba",
        destino_uf="PR",
        mercadoria="paletes de embalagem plástica",
        peso_kg=12000,
        cubagem_m3=6.0,
        valor_nf=37000,
        empresa="Embalagens ABC",
        distancia_km=2100,
    )
    base.update(campos)
    return base


def test_health(cliente):
    corpo = cliente.get("/health").json()
    assert corpo["status"] == "ok"
    assert corpo["veiculos"] == 8


def test_premissas_expoe_a_frota_e_as_margens(cliente):
    corpo = cliente.get("/api/premissas").json()
    assert corpo["impostos_taxas_seguro"] == 0.23
    assert len(corpo["frota"]) == 8
    assert corpo["margens"]["alvo"] == 0.25


def test_calcular_devolve_cotacao_e_elegibilidade(cliente, params):
    resposta = cliente.post(
        "/api/calcular",
        json={"distancia_km": 2100, "peso_kg": 12000, "cubagem_m3": 6.0, "valor_nf": 37000, "mercadoria": "peças plásticas"},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["cotacao"]["veiculo_sugerido"] == "Bi Truck"
    assert corpo["cotacao"]["preco_alvo"] == pytest.approx(11744.79, abs=0.01)
    assert corpo["elegibilidade"]["status"] == "APROVADA"
    assert corpo["cubagem_estimada"] is False


def test_calcular_estima_cubagem_ausente(cliente):
    corpo = cliente.post("/api/calcular", json={"distancia_km": 400, "peso_kg": 3000}).json()
    assert corpo["cubagem_estimada"] is True
    assert corpo["cubagem_utilizada_m3"] == pytest.approx(10.0)
    assert corpo["cotacao"]["confianca"] == "BAIXA"


def test_calcular_recusa_carga_sem_peso_e_sem_cubagem(cliente):
    assert cliente.post("/api/calcular", json={"distancia_km": 400}).status_code == 422


def test_calcular_recusa_distancia_invalida(cliente):
    assert cliente.post("/api/calcular", json={"distancia_km": 0, "peso_kg": 1000}).status_code == 422


def test_calcular_sinaliza_bloqueio_de_lmg(cliente):
    corpo = cliente.post(
        "/api/calcular",
        json={"distancia_km": 500, "peso_kg": 5000, "cubagem_m3": 20.0, "valor_nf": 1_500_000, "mercadoria": "máquinas industriais"},
    ).json()
    assert corpo["elegibilidade"]["status"] == "BLOQUEIO"
    assert any("LMG" in alerta for alerta in corpo["cotacao"]["alertas"])


def test_extrair_calcula_e_ordena_os_anuncios(cliente):
    resposta = cliente.post("/api/extrair", json={"persistir": False, "itens": [_anuncio()]})
    assert resposta.status_code == 200
    corpo = resposta.json()
    oportunidade = corpo["oportunidades"][0]
    assert oportunidade["status"] == "CALCULADA"
    assert oportunidade["veiculo_sugerido"] == "Bi Truck"
    assert oportunidade["preco_alvo"] == pytest.approx(11744.79, abs=0.01)
    assert corpo["persistidas"] == 0


def test_extrair_deduplica_no_mesmo_lote(cliente):
    corpo = cliente.post("/api/extrair", json={"persistir": False, "itens": [_anuncio(), _anuncio()]}).json()
    assert len(corpo["oportunidades"]) == 1
    assert corpo["duplicadas"] == 1


def test_extrair_marca_incompleta_sem_distancia(cliente):
    corpo = cliente.post(
        "/api/extrair", json={"persistir": False, "itens": [_anuncio(distancia_km=None)]}
    ).json()
    oportunidade = corpo["oportunidades"][0]
    assert oportunidade["status"] == "INCOMPLETA"
    assert oportunidade["preco_alvo"] is None
    assert any("distancia_km" in alerta for alerta in oportunidade["alertas"])


def test_extrair_recusa_mercadoria_excluida(cliente):
    corpo = cliente.post(
        "/api/extrair", json={"persistir": False, "itens": [_anuncio(mercadoria="cargas de cigarros")]}
    ).json()
    oportunidade = corpo["oportunidades"][0]
    assert oportunidade["status"] == "RECUSADA"
    assert oportunidade["elegibilidade"] == "RECUSADA"
    assert oportunidade["custo_total"] is None


def test_extrair_estima_cubagem_e_marca_confianca_baixa(cliente):
    corpo = cliente.post(
        "/api/extrair", json={"persistir": False, "itens": [_anuncio(cubagem_m3=None, peso_kg=3000)]}
    ).json()
    oportunidade = corpo["oportunidades"][0]
    assert oportunidade["confianca"] == "BAIXA"
    assert oportunidade["cubagem_m3"] == pytest.approx(10.0)


def test_extrair_sem_itens_falha(cliente):
    assert cliente.post("/api/extrair", json={"itens": []}).status_code == 422


def test_extrair_texto_bruto_ainda_nao_implementado(cliente):
    resposta = cliente.post("/api/extrair", json={"texto_bruto": "carga de Campinas para Curitiba"})
    assert resposta.status_code == 501
    assert "semana 2" in resposta.json()["detail"]


def test_extrair_rejeita_uf_invalida(cliente):
    assert cliente.post("/api/extrair", json={"persistir": False, "itens": [_anuncio(origem_uf="XX")]}).status_code == 422


def test_calcular_avisa_sobre_lista_de_especificas_nao_validada(cliente):
    corpo = cliente.post(
        "/api/calcular",
        json={"distancia_km": 700, "peso_kg": 4000, "cubagem_m3": 30.0, "valor_nf": 250000, "mercadoria": "celulares"},
    ).json()
    assert corpo["elegibilidade"]["classificacao_mercadoria"] == "NAO_ESPECIFICA"
    assert any("não foi validada com a corretora" in aviso for aviso in corpo["elegibilidade"]["avisos"])


def test_extrair_leva_o_aviso_para_os_alertas(cliente):
    corpo = cliente.post(
        "/api/extrair", json={"persistir": False, "itens": [_anuncio(mercadoria="notebooks e monitores")]}
    ).json()
    assert any("não foi validada com a corretora" in alerta for alerta in corpo["oportunidades"][0]["alertas"])


def test_premissas_expoe_o_estado_da_lista_nao_validada(cliente):
    corpo = cliente.get("/api/premissas").json()
    assert corpo["mercadorias_especificas_validadas"] is False
