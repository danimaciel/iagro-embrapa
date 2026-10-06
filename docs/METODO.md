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

## Busca (versão 2, 06/10/2026)

Em dois passos, só por significado:
1. A pergunta (vetor completo, centrado na média) é comparada aos bits de todos os documentos (filtrados pela
   unidade escolhida) e seleciona os 120 mais próximos.
2. A página lê, por requisições de trecho (HTTP Range), só as linhas desses 120 documentos nos arquivos de vetores
   completos em int8 (`dados/vet/`, 142 MB no total, nunca baixados inteiros) e os reordena pelo cosseno.

A busca por palavras do título (BM25) só é usada enquanto o modelo de significado carrega.

**Por que a mudança.** A versão 1 combinava significado (só os bits) e palavras do título com peso igual (RRF).
Na análise de 06/10, as palavras do título puxavam para o topo títulos curtos sem resumo e títulos sem relação
("plantas que ajudam a recuperar solo cansado" trazia "Extrativismo ou plantio: recuperar o tempo perdido").
Gabarito da Territorial (23 perguntas), documento esperado em 1º lugar / entre os 4 primeiros:

| Variante | Filtro Territorial | Toda a Embrapa |
|---|---|---|
| v1: bits + palavras do título (RRF, pesos iguais) | 14 / 22 | 8 / 15 |
| bits + palavras com peso 0,3 | 18 / 22 | 12 / 15 |
| só bits | 16 / 23 | 12 / 17 |
| **v2: bits → 120 candidatos → vetor completo int8** | **21 / 23** | **15 / 19** |
| vetor completo em todos (teto) | 22 / 23 | 15 / 19 |

Reordenar 50 candidatos já dá o mesmo resultado que 300; 120 é folga. Somar as palavras do título à v2 piora
(peso 0,3: 18 e 11 em 1º lugar).

## Resultado na página publicada (exportação de outubro de 2026)

Base: 185.407 documentos de 44 unidades (180.949 publicações, 1.266 soluções, 3.192 projetos). Índice de 20 MB e
vetores de 18 MB; a página fica pronta em cerca de 30 segundos numa conexão comum (mais o modelo, cerca de 110 MB,
só na primeira visita).

Gabarito da Embrapa Territorial (23 perguntas com resposta), testado na própria página publicada em 05/10/2026:

| Modo | Documento esperado em 1º | Entre os 4 primeiros | Entre os 20 primeiros |
|---|---|---|---|
| Filtro "Embrapa Territorial" | 15 | 20 | 22 |
| Toda a Embrapa | 8 | 14 | 19 |

Na Embrapa toda, documentos de outras unidades concorrem — e muitas vezes também respondem (por exemplo, aquicultura
traz a Embrapa Pesca e Aquicultura). Perguntas gerais testadas trazem as unidades esperadas (lagarta-do-cartucho:
Milho e Sorgo e Clima Temperado; mudas de açaí: Amapá, Acre e Roraima; cultivares de feijão: Arroz e Feijão e Meio-Norte).

Os números acima são da versão 1 (ver "Busca"). Versão 2, testada na página publicada em 06/10/2026:

| Modo | 1º lugar | Entre os 4 primeiros | Entre os 20 primeiros |
|---|---|---|---|
| Filtro "Embrapa Territorial" | 20 | 23 | 23 |
| Toda a Embrapa | 13 | 17 | 21 |

Um pouco abaixo da simulação em Python (21 e 15 em 1º lugar) porque o navegador usa a versão comprimida (q8) do
modelo para a pergunta. Tempo de busca na página publicada: cerca de 0,5 a 2 segundos, incluindo a leitura dos
vetores dos 120 candidatos. Exemplo de ganho: "como diminuir o calor que as vacas sentem no verão" trazia em 1º
"perda de água por cocção de carne"; agora traz sombra para vacas em sistemas silvipastoris e estresse térmico
em vacas leiteiras.

A barra de proximidade mostra o cosseno entre pergunta e documento, de 0,80 (vazia) a 0,90 (cheia). Ela compara
os resultados entre si; não indica se a base responde à pergunta (perguntas fora do tema também chegam a 0,86).

O aviso de "relação fraca" da versão da Territorial foi retirado: na base inteira a semelhança do primeiro
resultado é igual para perguntas com e sem resposta (0,894 × 0,895), então não serve como sinal.
