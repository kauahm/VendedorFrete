# Processo comercial — onde a semana 1 se encaixa

```
anúncio (cargas.com.br)
   → captação            [semana 2: Claude in Chrome / colar texto]
   → validação + dedup   [semana 1: /api/extrair com itens estruturados]
   → distância           [semana 2: engine/distancia.py com cache]
   → elegibilidade       [semana 1: LMG, exclusões da apólice, faixa de GR]
   → cotação             [semana 1: motor determinístico]
   → score               [semana 2]
   → primeiro contato    [semana 3]
   → proposta            [semana 4]
   → follow-up D+1/3/7/30[semana 4]
   → resultado           [semana 4]
```

## Status da oportunidade após a semana 1

| Status | Quando |
|---|---|
| `CALCULADA` | elegível, com distância, peso/cubagem e veículo que cabe |
| `INCOMPLETA` | falta distância ou peso/cubagem, ou nenhum veículo comporta a carga |
| `RECUSADA` | LMG estourado ou mercadoria excluída da apólice |

`REVISAR` na elegibilidade não impede o cálculo — a cotação sai com alerta, para o vendedor decidir.

## O que o motor entrega ao vendedor

Veículo sugerido, eixos, fração de ocupação, restrição dominante (peso ou cubagem), modalidade,
custo total, R$/km de custo e de venda, três preços (mínimo, alvo, máximo), lucro alvo,
faixa de GR com exigências e a lista de alertas.

## O que ainda é manual

Distância (informar `distancia_km` no payload), confirmação de peso/cubagem/NF com o embarcador,
e a decisão final de preço dentro da banda.
