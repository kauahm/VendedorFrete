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
   - `preco_maximo = max(custo × (1 + margem_maxima), preco_minimo × (1 + folga_maximo_sobre_minimo))`

### Um único bloco de impostos

Os 23% de `impostos_taxas_seguro` já incluem impostos, taxas **e** seguro. Não existe linha
separada de 0,2% da NF — a planilha original fazia dupla contagem e isso foi corrigido aqui.
O valor da NF **não entra no preço**: serve só para LMG e faixa de GR (`test_valor_nf_nao_altera_o_preco`).

### Piso de lucro absoluto

Quando `custo + 800 > custo × 1,25`, o mínimo puxa o alvo para cima — intencional.

Em carga barata o alvo colapsa no mínimo, mas o **máximo não**: `folga_maximo_sobre_minimo`
(5%) garante banda de negociação acima do piso. Ex.: 500 kg / 15 m³ / 300 km ⇒
mínimo R$ 2.413,73 · alvo R$ 2.413,73 · máximo R$ 2.534,42. Em carga cara a folga não
morde e valem as margens de 20/25/30% (ex.: custo R$ 20.000 ⇒ 24.000 / 25.000 / 26.000).

## Decisões tomadas onde a spec era ambígua

| Ponto | Decisão | Motivo |
|---|---|---|
| Cenário 1 da spec (12.000 kg / 6 m³ / 2.100 km) | resultado é **FRACIONADO** | fração = 12000/20000 = 0,60 < 0,70. **Confirmado pelo dono:** o corte fica em 0,70 e o `esperado` da spec é que estava sob suspeita ("conferir"). |
| `preco_maximo` abaixo do alvo | `max(custo × 1,30, mínimo × 1,05)` | **decisão do dono.** A spec só corrigia o alvo; sem isso, carga barata gerava máximo < mínimo e banda de negociação zero |
| Empate entre peso e cubagem | `restricao_dominante = "cubagem"` | segue o `else` da spec |
| km entre faixas (ex.: 100,4) | cai na faixa seguinte (regional) | as faixas do YAML têm vãos entre 100 e 101 |
| `piso_base_km: 6.368` | fica no YAML, **não** entra na fórmula | a fórmula usa CCD/CC por eixo; nenhum passo da spec consome esse valor |
| Cubagem ausente | `peso / densidade_estimada_kg_m3` (300), confiança **BAIXA** | regra do §6.2 da spec, com a densidade em `premissas.yaml` |
| Classificação de mercadoria | matcher determinístico de termos | motor sem IA na semana 1; `verificar_elegibilidade` aceita `classificador=` injetado — o classificador Claude entra na semana 2 sem tocar no motor |
| Lista de mercadorias específicas | **desligada** por `mercadorias_especificas_validadas: false` | lista NÃO-VALIDADA; enquanto isso não alimenta elegibilidade, só gera aviso |

## `mercadorias_especificas.yaml` — NÃO-VALIDADO

A lista **não** veio da apólice transcrita: foi montada a partir de categorias usuais de
gerenciamento de risco e aguarda revisão item a item com a corretora. Até lá ela **não pode
alimentar decisão de elegibilidade**, e o código garante isso:

`premissas.yaml` traz `mercadorias_especificas_validadas: false`. Com o flag desligado, um
match na lista:

- **não** classifica a mercadoria como `ESPECIFICA` (segue `NAO_ESPECIFICA`);
- **não** acrescenta exigências de GR (só valem as da faixa por valor de NF);
- **não** muda o status da elegibilidade;
- gera um aviso — `"Possível mercadoria específica (…), porém a lista ainda não foi validada
  com a corretora: confirmar o GR manualmente"` — que o painel mostra junto dos alertas.

As **exclusões da apólice** (`exclusoes.yaml`) são validadas e seguem recusando normalmente:
o flag cobre só a lista de específicas. Depois da revisão com a corretora, virar o flag para
`true` reativa classificação e exigências (`test_mercadoria_especifica_traz_exigencias_quando_a_lista_for_validada`
já cobre esse caminho).

## Itens ainda marcados VALIDAR

- Cubagem de Carreta Simples (100 m³) e Carreta LS (110 m³).
- Lotação/cubagem de toda a frota: valores conservadores (menor entre planilha e PDF).
- `densidade_estimada_kg_m3: 300` e `confianca_classificador_deterministico: 0.85`.
- `mercadorias_especificas.yaml` (acima).

Decididos pelo dono, fora de dúvida: `corte_dedicado_fracao: 0.70` e a fórmula do preço máximo.

## Elegibilidade

Roda antes do cálculo, nesta ordem:

1. `valor_nf > lmg_maximo` ⇒ **BLOQUEIO**.
2. Mercadoria na lista de exclusões ⇒ **RECUSADA** (`EXCLUSAO_APOLICE`).
3. Confiança da classificação < 0,8 ⇒ **REVISAR**.
4. Caso contrário **APROVADA**, com faixa de GR (A–D) e exigências acumuladas
   (faixa + mercadoria específica, esta última só quando a lista estiver validada).

Regra fora do matcher, ainda não automatizada: CT-e emitido como serviço **subcontratado**
(JCN como subcontratada) não tem cobertura da apólice.
