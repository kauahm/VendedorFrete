"""API do JCN FreightOS. Semana 1: motor de preço e elegibilidade."""

from __future__ import annotations

from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import db
from config import params_padrao
from engine.calculo import calcular_frete, estimar_cubagem
from engine.elegibilidade import verificar_elegibilidade
from engine.pipeline import definir_confianca, processar_oportunidade
from models.carga import Carga, Confianca
from models.cotacao import Cotacao
from models.elegibilidade import ElegibilidadeResult
from models.oportunidade import Oportunidade, OportunidadeEntrada

load_dotenv()

app = FastAPI(title="JCN FreightOS", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CalcularRequest(BaseModel):
    distancia_km: float = Field(gt=0)
    peso_kg: float | None = Field(default=None, ge=0)
    cubagem_m3: float | None = Field(default=None, ge=0)
    valor_nf: float | None = Field(default=None, ge=0)
    mercadoria: str | None = None
    exige_exclusivo: bool = False
    refrigerada: bool = False
    veiculo_pedido: str | None = None
    carroceria: str | None = None


class CalcularResponse(BaseModel):
    cotacao: Cotacao
    elegibilidade: ElegibilidadeResult
    cubagem_utilizada_m3: float
    cubagem_estimada: bool


class ExtrairRequest(BaseModel):
    itens: list[OportunidadeEntrada] = []
    texto_bruto: str | None = None
    persistir: bool = True


class ExtrairResponse(BaseModel):
    oportunidades: list[Oportunidade]
    duplicadas: int
    persistidas: int


@app.get("/health")
def health() -> dict[str, Any]:
    params = params_padrao()
    return {
        "status": "ok",
        "tabela_antt": params.tabela_antt,
        "veiculos": len(params.frota),
        "banco": db.disponivel(),
    }


@app.get("/api/premissas")
def premissas() -> dict[str, Any]:
    params = params_padrao()
    return {
        "tabela_antt": params.tabela_antt,
        "impostos_taxas_seguro": params.impostos_taxas_seguro,
        "colchao_agregado": params.colchao_agregado,
        "lucro_minimo_viagem": params.lucro_minimo_viagem,
        "margens": {
            "minima": params.margem_minima,
            "alvo": params.margem_alvo,
            "maxima": params.margem_maxima,
        },
        "corte_dedicado_fracao": params.corte_dedicado_fracao,
        "lmg_maximo": params.lmg_maximo,
        "apolice": {
            "numero": params.apolice_numero,
            "seguradora": params.seguradora,
            "vigencia_fim": params.apolice_vigencia_fim,
        },
        "faixas_distancia": [f.__dict__ for f in params.fatores_faixa_distancia],
        "faixas_gr": [f.__dict__ for f in params.faixas_gr],
        "frota": [v.__dict__ for v in params.frota],
    }


@app.post("/api/calcular", response_model=CalcularResponse)
def calcular(requisicao: CalcularRequest) -> CalcularResponse:
    params = params_padrao()

    if not requisicao.peso_kg and not requisicao.cubagem_m3:
        raise HTTPException(status_code=422, detail="informe peso_kg ou cubagem_m3")

    cubagem_estimada = requisicao.cubagem_m3 is None and bool(requisicao.peso_kg)
    cubagem = estimar_cubagem(requisicao.peso_kg, params) if cubagem_estimada else (requisicao.cubagem_m3 or 0.0)

    carga = Carga(
        km=requisicao.distancia_km,
        peso_kg=requisicao.peso_kg or 0.0,
        cubagem_m3=cubagem,
        valor_nf=requisicao.valor_nf,
        mercadoria=requisicao.mercadoria,
        exige_exclusivo=requisicao.exige_exclusivo,
        refrigerada=requisicao.refrigerada,
        veiculo_pedido=requisicao.veiculo_pedido,
        carroceria=requisicao.carroceria,
        confianca=Confianca.BAIXA if cubagem_estimada else Confianca.ALTA,
    )

    return CalcularResponse(
        cotacao=calcular_frete(carga, params),
        elegibilidade=verificar_elegibilidade(carga, params),
        cubagem_utilizada_m3=round(cubagem, 4),
        cubagem_estimada=cubagem_estimada,
    )


@app.post("/api/extrair", response_model=ExtrairResponse)
def extrair(requisicao: ExtrairRequest) -> ExtrairResponse:
    """Recebe anúncios já estruturados (Claude in Chrome) e devolve tudo calculado.

    O parser de texto livre com IA entra na semana 2; até lá `texto_bruto` é recusado.
    """
    if requisicao.texto_bruto and not requisicao.itens:
        raise HTTPException(
            status_code=501,
            detail="parser de texto bruto chega na semana 2 — envie os anúncios em 'itens'",
        )
    if not requisicao.itens:
        raise HTTPException(status_code=422, detail="nenhum anúncio recebido")

    params = params_padrao()
    persistir = requisicao.persistir and db.disponivel()

    oportunidades: list[Oportunidade] = []
    vistos: set[str] = set()
    duplicadas = 0
    persistidas = 0

    for entrada in requisicao.itens:
        hash_dedup = entrada.hash_dedup()
        if hash_dedup in vistos or (persistir and db.hash_existe(hash_dedup)):
            duplicadas += 1
            continue
        vistos.add(hash_dedup)

        oportunidade, _, _ = processar_oportunidade(entrada, params)
        if persistir:
            registro = oportunidade.model_dump(mode="json", exclude={"id", "created_at", "alertas", "hash_dedup_valor"})
            registro = {chave: valor for chave, valor in registro.items() if chave in db.CAMPOS_OPORTUNIDADE}
            registro["hash_dedup"] = hash_dedup
            oportunidade.id = db.salvar_oportunidade(registro)
            persistidas += 1 if oportunidade.id else 0
        oportunidades.append(oportunidade)

    return ExtrairResponse(oportunidades=oportunidades, duplicadas=duplicadas, persistidas=persistidas)
