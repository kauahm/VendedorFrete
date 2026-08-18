# Regras de negócio — motor de preço

Fonte única de verdade: `backend/data/*.yaml`. Nenhum número de negócio existe em código Python.
Toda decisão de preço é rastreável a um parâmetro de YAML.

## Cadeia de cálculo

1. **Seleção de veículo** — primeiro veículo por `ordem` cuja `cubagem_m3` **e** `lotacao_kg` cabem a carga.
   Nenhum couber ⇒ `SEM_VEICULO`, sem preço.
2. **Fração de ocupação** — `max(cubagem / cubagem_veiculo, peso / lotacao_veiculo)`.
3. **Modalidade** — `DEDICADO` se exclusivo, refrigerada ou `fração >= corte_dedicado_fracao`; senão `FRACIONADO`.
4. **Custo**
   - piso ANTT = `km × CCD + CC` (tabela A ou B conforme `tabela_antt`)
   - dedicado: custo agregado = piso integral
   - fracionado: custo agregado = piso × `fator_faixa(km)` × fração
   - `× (1 + colchao_agregado)` e `× (1 + impostos_taxas_seguro)`
5. **Preço**
   - `preco_minimo = max(custo + lucro_minimo_viagem, custo × (1 + margem_minima))`
   - `preco_alvo = max(custo × (1 + margem_alvo), preco_minimo)`
   - `preco_maximo = max(custo × (1 + margem_maxima), preco_alvo)`

### Um único bloco de impostos

Os 23% de `impostos_taxas_seguro` já incluem impostos, taxas **e** seguro. Não existe linha
separada de 0,2% da NF — a planilha original fazia dupla contagem e isso foi corrigido aqui.
O valor da NF **não entra no preço**: serve só para LMG e faixa de GR (`test_valor_nf_nao_altera_o_preco`).

### Piso de lucro absoluto

Quando `custo + 800 > custo × 1,25`, o mínimo puxa o alvo para cima — intencional.
Consequência prática, em carga barata: mínimo, alvo e máximo colapsam no mesmo número
(ex.: 500 kg / 15 m³ / 300 km ⇒ R$ 2.413,73 nos três). **VALIDAR com o dono:** sem banda
de negociação nesses casos, ou o piso de R$ 800 cai, ou a margem máxima passa a ser
`max(custo × 1,30, preco_minimo × 1,05)`.

## Decisões tomadas onde a spec era ambígua

| Ponto | Decisão | Motivo |
|---|---|---|
| Cenário 1 da spec (12.000 kg / 6 m³ / 2.100 km) | resultado é **FRACIONADO** | fração = 12000/20000 = 0,60 < 0,70. A própria spec marcou "conferir". Só vira `DEDICADO` com `corte_dedicado_fracao <= 0,60`. **VALIDAR com o dono.** |
| `preco_maximo` abaixo do alvo | máximo elevado ao alvo | a spec só corrigia o alvo; sem isso, carga barata gera máximo < mínimo |
| Empate entre peso e cubagem | `restricao_dominante = "cubagem"` | segue o `else` da spec |
| km entre faixas (ex.: 100,4) | cai na faixa seguinte (regional) | as faixas do YAML têm vãos entre 100 e 101 |
| `piso_base_km: 6.368` | fica no YAML, **não** entra na fórmula | a fórmula usa CCD/CC por eixo; nenhum passo da spec consome esse valor |
| Cubagem ausente | `peso / densidade_estimada_kg_m3` (300), confiança **BAIXA** | regra do §6.2 da spec, com a densidade em `premissas.yaml` |
| Classificação de mercadoria | matcher determinístico de termos | motor sem IA na semana 1; `verificar_elegibilidade` aceita `classificador=` injetado — o classificador Claude entra na semana 2 sem tocar no motor |

## Itens marcados VALIDAR

- `corte_dedicado_fracao: 0.70` — hipótese, define a virada fracionado→dedicado.
- Cubagem de Carreta Simples (100 m³) e Carreta LS (110 m³).
- Lotação/cubagem de toda a frota: valores conservadores (menor entre planilha e PDF).
- `densidade_estimada_kg_m3: 300` e `confianca_classificador_deterministico: 0.85`.
- `mercadorias_especificas.yaml` — a lista **não** veio da apólice transcrita; foi montada a partir
  de categorias usuais de GR e precisa de revisão item a item com a corretora.
- Banda de preço colapsada em cargas baratas (acima).

## Elegibilidade

Roda antes do cálculo, nesta ordem:

1. `valor_nf > lmg_maximo` ⇒ **BLOQUEIO**.
2. Mercadoria na lista de exclusões ⇒ **RECUSADA** (`EXCLUSAO_APOLICE`).
3. Confiança da classificação < 0,8 ⇒ **REVISAR**.
4. Caso contrário **APROVADA**, com faixa de GR (A–D) e exigências acumuladas
   (faixa + mercadoria específica).

Regra fora do matcher, ainda não automatizada: CT-e emitido como serviço **subcontratado**
(JCN como subcontratada) não tem cobertura da apólice.
