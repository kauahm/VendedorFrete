from __future__ import annotations

import pytest

from engine.elegibilidade import classificar_mercadoria, verificar_elegibilidade
from models.elegibilidade import ClassificacaoMercadoria, TipoMercadoria
from models.oportunidade import OportunidadeEntrada


def _oportunidade(**campos):
    base = dict(
        origem_cidade="Campinas",
        origem_uf="SP",
        destino_cidade="Curitiba",
        destino_uf="PR",
        mercadoria="paletes de embalagem plástica",
    )
    base.update(campos)
    return OportunidadeEntrada(**base)


def test_nf_acima_do_lmg_bloqueia(params):
    resultado = verificar_elegibilidade(_oportunidade(valor_nf=1_000_001), params)
    assert resultado.status.value == "BLOQUEIO"
    assert "LMG" in resultado.motivo


def test_nf_exatamente_no_lmg_passa(params):
    resultado = verificar_elegibilidade(_oportunidade(valor_nf=1_000_000), params)
    assert resultado.status.value == "APROVADA"
    assert resultado.faixa_gr == "D"


@pytest.mark.parametrize(
    "mercadoria, match",
    [
        ("carga de cigarros", "cigarros"),
        ("transporte de animais vivos", "animais vivos"),
        ("joias e relógios", "pedras preciosas, semipreciosas, joias e pérolas"),
        ("lingotes de níquel", "metais semipreciosos e preciosos e suas ligas"),
        ("veículos rodando para concessionária", "veículos rodando"),
        ("documentos", "documentos em geral"),
    ],
)
def test_mercadoria_excluida_recusa(mercadoria, match, params):
    resultado = verificar_elegibilidade(_oportunidade(mercadoria=mercadoria, valor_nf=50000), params)
    assert resultado.status.value == "RECUSADA"
    assert "EXCLUSAO_APOLICE" in resultado.motivo
    assert match in resultado.motivo


def test_exclusao_ignora_acento_e_caixa(params):
    assert classificar_mercadoria("MOLIBDENIO em barras", params).tipo == TipoMercadoria.EXCLUIDA
    assert classificar_mercadoria("Molibdênio em barras", params).tipo == TipoMercadoria.EXCLUIDA


def test_mercadoria_especifica_traz_exigencias(params):
    resultado = verificar_elegibilidade(_oportunidade(mercadoria="celulares e notebooks", valor_nf=300000), params)
    assert resultado.status.value == "APROVADA"
    assert resultado.classificacao_mercadoria == TipoMercadoria.ESPECIFICA
    assert "isca" in resultado.exigencias_gr
    assert "ACL" in resultado.exigencias_gr


def test_mercadoria_comum_e_nao_especifica(params):
    resultado = verificar_elegibilidade(_oportunidade(mercadoria="sacos de cimento", valor_nf=20000), params)
    assert resultado.status.value == "APROVADA"
    assert resultado.classificacao_mercadoria == TipoMercadoria.NAO_ESPECIFICA


@pytest.mark.parametrize("mercadoria", [None, "", "  ", "xx"])
def test_descricao_vaga_vai_para_revisar(mercadoria, params):
    resultado = verificar_elegibilidade(_oportunidade(mercadoria=mercadoria, valor_nf=20000), params)
    assert resultado.status.value == "REVISAR"


@pytest.mark.parametrize(
    "valor_nf, faixa, exigencia",
    [
        (0, "A", "rastreamento"),
        (130000, "A", "rastreamento"),
        (130001, "B", "ACL"),
        (400000, "B", "ACL"),
        (400001, "C", "escolta"),
        (800000, "C", "escolta"),
        (800001, "D", "plano_gr_completo"),
        (1000000, "D", "plano_gr_completo"),
    ],
)
def test_faixas_de_gr(valor_nf, faixa, exigencia, params):
    resultado = verificar_elegibilidade(_oportunidade(valor_nf=valor_nf), params)
    assert resultado.faixa_gr == faixa
    assert exigencia in resultado.exigencias_gr


def test_sem_nf_nao_tem_faixa_de_gr(params):
    resultado = verificar_elegibilidade(_oportunidade(valor_nf=None), params)
    assert resultado.status.value == "APROVADA"
    assert resultado.faixa_gr is None


def test_classificador_injetado_substitui_o_deterministico(params):
    def classificador_ia(mercadoria, params):
        return ClassificacaoMercadoria(tipo=TipoMercadoria.EXCLUIDA, match="cigarros", confianca=0.99)

    resultado = verificar_elegibilidade(_oportunidade(mercadoria="fardos"), params, classificador=classificador_ia)
    assert resultado.status.value == "RECUSADA"


def test_confianca_baixa_do_classificador_vai_para_revisar(params):
    def classificador_incerto(mercadoria, params):
        return ClassificacaoMercadoria(tipo=TipoMercadoria.NAO_ESPECIFICA, match=None, confianca=0.4)

    resultado = verificar_elegibilidade(_oportunidade(), params, classificador=classificador_incerto)
    assert resultado.status.value == "REVISAR"
    assert "40%" in resultado.motivo


@pytest.mark.parametrize("uf", ["XX", "S", "", "sp1"])
def test_uf_invalida_e_rejeitada(uf):
    with pytest.raises(ValueError):
        _oportunidade(origem_uf=uf)


def test_hash_dedup_e_estavel_e_sensivel_a_empresa():
    a = _oportunidade(peso_kg=1000, empresa="Transportes ABC")
    b = _oportunidade(peso_kg=1000, empresa="transportes abc ")
    c = _oportunidade(peso_kg=1000, empresa="Outra Empresa")
    assert a.hash_dedup() == b.hash_dedup()
    assert a.hash_dedup() != c.hash_dedup()
