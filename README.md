# JCN FreightOS

Motor de venda de fretes rodoviários da JCN Logística. Preço determinístico a partir do piso
ANTT, filtro de elegibilidade contra a apólice e fila de oportunidades priorizada.

**Estado: semana 1 concluída** — motor de cálculo, elegibilidade, YAMLs de negócio,
suíte de aceitação, banco no Neon migrado e os endpoints `/api/calcular` e `/api/extrair`.

> ### ⚠️ NÃO-VALIDADO: `backend/data/mercadorias_especificas.yaml`
>
> A lista de mercadorias específicas **não** veio da apólice: foi montada a partir de
> categorias usuais de GR e ainda não foi revisada com a corretora. Enquanto
> `mercadorias_especificas_validadas: false` em `premissas.yaml`, ela **não alimenta
> decisão de elegibilidade** — não classifica como `ESPECIFICA`, não acrescenta exigência
> de GR, não muda status; apenas emite aviso para conferência manual. **Não vire esse flag
> para `true` em produção antes da revisão com a corretora.**
>
> As exclusões da apólice (`exclusoes.yaml`) são validadas e seguem recusando normalmente.

## Rodar

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest                 # 208 testes
.venv/bin/uvicorn main:app --reload        # http://127.0.0.1:8000/docs
```

Banco: o projeto Neon `jcn-freightos` já está criado e com as migrations aplicadas
(tabelas `oportunidades` e `followups`). Copie `.env.example` para `.env` e preencha
`DATABASE_URL` com a string de conexão do Neon — o `.env` é ignorado pelo git e a senha
nunca entra no repositório. Para um banco novo do zero:
`.venv/bin/python scripts/migrate.py`. Sem `DATABASE_URL` a API funciona normalmente,
apenas não persiste.

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
└── tests/                  # 208 testes
```

CI: `.github/workflows/backend.yml` roda a suíte a cada push ou PR que toque
`jcn-freight/backend/`.

## Onde ficam os números

Todos em `backend/data/*.yaml`, editáveis pelo dono do negócio sem tocar em código.
Decisões fechadas: corte dedicado/fracionado em 0,70 e preço máximo =
`max(custo × 1,30, mínimo × 1,05)` — o mínimo de 5% de banda evita que os três preços
colapsem no piso de lucro em carga barata.
`tests/test_config.py` trava esses valores contra a especificação: edição indevida quebra o CI.
Regras, decisões e itens em aberto: [`docs/REGRAS_NEGOCIO.md`](docs/REGRAS_NEGOCIO.md).

## Regra de ouro

O motor de preço é Python puro. IA só entra em extração de texto, classificação de mercadoria
e rascunho de mensagem — **nunca** no cálculo.

## Próximo (semana 2)

Parser de anúncios com Claude, `engine/distancia.py` com cache, `engine/score.py` e
`GET /api/oportunidades` ordenado por score.
