# JCN FreightOS

Motor de venda de fretes rodoviários da JCN Logística. Preço determinístico a partir do piso
ANTT, filtro de elegibilidade contra a apólice e fila de oportunidades priorizada.

**Estado: semana 1 concluída** — motor de cálculo, elegibilidade, YAMLs de negócio,
suíte de aceitação e os endpoints `/api/calcular` e `/api/extrair`.

## Rodar

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest                 # 194 testes
.venv/bin/uvicorn main:app --reload        # http://127.0.0.1:8000/docs
```

Banco (opcional na semana 1): copie `.env.example` para `.env`, preencha `DATABASE_URL`
com a string do Neon e rode `.venv/bin/python scripts/migrate.py`. Sem `DATABASE_URL` a API
funciona normalmente, apenas não persiste.

## Estrutura

```
backend/
├── main.py                 # FastAPI: /health, /api/premissas, /api/calcular, /api/extrair
├── config.py               # carrega e valida os YAMLs
├── db.py                   # Postgres opcional (psycopg)
├── engine/
│   ├── veiculo.py          # seleção do menor veículo, ocupação, modalidade
│   ├── calculo.py          # motor de preço
│   ├── elegibilidade.py    # LMG, exclusões da apólice, faixa de GR
│   └── pipeline.py         # anúncio estruturado → oportunidade cotada
├── models/                 # Pydantic: carga, cotação, elegibilidade, oportunidade
├── data/                   # premissas, frota, antt, exclusoes, mercadorias_especificas
├── migrations/001_init.sql
└── tests/                  # 194 testes
```

## Onde ficam os números

Todos em `backend/data/*.yaml`, editáveis pelo dono do negócio sem tocar em código.
`tests/test_config.py` trava esses valores contra a especificação: edição indevida quebra o CI.
Regras, decisões e itens em aberto: [`docs/REGRAS_NEGOCIO.md`](docs/REGRAS_NEGOCIO.md).

## Regra de ouro

O motor de preço é Python puro. IA só entra em extração de texto, classificação de mercadoria
e rascunho de mensagem — **nunca** no cálculo.

## Próximo (semana 2)

Parser de anúncios com Claude, `engine/distancia.py` com cache, `engine/score.py` e
`GET /api/oportunidades` ordenado por score.
