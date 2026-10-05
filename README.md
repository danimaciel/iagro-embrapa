# iAgro Embrapa

**Página:** https://danimaciel.github.io/iagro-embrapa/

Demonstração de como os acervos da Embrapa (BDPA, Infoteca, Portal) podem ser reposicionados:
em vez de acertar as palavras do título, a pessoa pergunta do seu jeito e chega à publicação, solução
tecnológica ou projeto certo, de qualquer unidade. Feita com dados públicos do Redape; não é um serviço
oficial da Embrapa.

- **Busca por significado no navegador.** O modelo aberto multilingual-e5-base transforma a pergunta em vetor
  no próprio navegador, que é comparado aos vetores de cerca de 182 mil documentos, combinado com busca por
  palavras do título (BM25). Nenhuma pergunta vai para servidor.
- **Atualização automática.** Todo mês o GitHub Actions baixa a exportação nova do Redape, calcula vetores só
  do que mudou e republica a página.
- **Custo zero.** Página estática, modelo aberto, processamento no GitHub Actions (gratuito em repositório público).

Piloto de uma unidade, com o agente conversacional: [danimaciel/iagro](https://github.com/danimaciel/iagro)
(Embrapa Territorial).

## Como funciona

```
Redape (3 exportações mensais, CSV)
  └─ pipeline/redape.py       baixa a exportação mais recente
  └─ pipeline/base.py         obras (publicação repetida entre unidades vira uma só), projetos, soluções
  └─ pipeline/vetores.py      vetores e5 só dos textos novos (cache por hash; partes em paralelo)
  └─ pipeline/site_dados.py   índice (títulos, anos, tipos, unidades) + vetores em 1 bit + detalhes em blocos
site/index.html               página (HTML + JavaScript, sem servidor)
.github/workflows/atualizar.yml   orquestra tudo, todo dia 12, e publica no GitHub Pages
```

O repositório guarda só código. Os dados do Redape, a base e os vetores são gerados pelo fluxo; o cache de
vetores fica como anexo da release `cache-vetores`.

## Rodar no próprio computador

```
pip install -r pipeline/requirements-base.txt -r pipeline/requirements-vetores.txt
python pipeline/redape.py                 # baixa a exportação mais recente para dados/AAAA-MM
python pipeline/base.py 2026-10
python pipeline/vetores.py tudo           # ~17 h no processador para a base inteira; o fluxo faz em ~1 h
python pipeline/site_dados.py 2026-10
python -m http.server 8000 --directory site
```

Para levar para a infraestrutura da Embrapa, ver [docs/IMPLANTACAO.md](docs/IMPLANTACAO.md).
Método e testes: [docs/METODO.md](docs/METODO.md).
