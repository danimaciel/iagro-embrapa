# Método e testes

## Base

- Fonte: exportações mensais públicas do Redape (publicações doi:10.48432/TRBT0S, projetos doi:10.48432/EZDXWF,
  soluções tecnológicas doi:10.48432/ZQE5FV).
- **Obras:** publicação depositada por mais de uma unidade (mesmo título normalizado e ano, com pelo menos 50% dos
  autores em comum) vira um documento só, com todas as unidades. Títulos genéricos (menos de 4 palavras ou
  25 letras) não são agrupados. Mesmo critério do Observatório de P&D da Embrapa. Exportação de setembro de 2026:
  178.767 registros, 177.409 obras.
- Texto de cada documento: título + resumo (ou descrição) + palavras-chave. Não inclui unidade, pessoas nem links.

## Vetores

- Modelo `intfloat/multilingual-e5-base` (aberto, licença MIT), prefixo `passage: ` nos documentos e
  `query: ` nas perguntas, como recomendam os autores do modelo.
- Cache por hash do texto: só documentos novos ou alterados são recalculados.

## Por que 1 bit por dimensão

Com 182 mil documentos × 768 dimensões, os vetores completos passam de 130 MB (int8) — pesado demais para o
navegador. Testes com 35 perguntas comparando o ranking comprimido ao ranking com vetores completos:

| Compressão | Tamanho | Sobreposição dos 10 primeiros com o ranking centrado | Observação |
|---|---|---|---|
| PCA para 128/192/256 dimensões, int8 | 23 a 47 MB | 0,37 a 0,45 | perde muito |
| **Sinal do vetor centrado (1 bit)** | **17 MB** | **0,59** | escolhido |
| 2 bits por dimensão (quartis) | 35 MB | 0,59 | sem ganho sobre 1 bit |

No gabarito da Embrapa Territorial (23 perguntas com resposta, busca filtrada pela unidade), 1 bit levou um
documento esperado aos 4 primeiros em 22 de 23 perguntas (vetores completos centrados: 19 de 23).

A pergunta não é comprimida: o vetor dela (centrado na média dos documentos) é comparado aos bits de cada documento.

## Busca

Busca híbrida: significado (acima) + BM25 nos títulos, com fusão pela posição de cada documento nas duas listas
(Reciprocal Rank Fusion, k = 60). O filtro de unidade é aplicado antes do ranking.

O aviso de "relação fraca" da versão da Territorial foi retirado: na base inteira a semelhança do primeiro
resultado é igual para perguntas com e sem resposta (0,894 × 0,895), então não serve como sinal.
