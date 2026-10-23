# iAgro Embrapa: instruções para o Claude

Busca por significado em toda a produção da Embrapa (publicações, soluções tecnológicas e projetos de todas as
unidades), no navegador e sem servidor. Página: https://danimaciel.github.io/iagro-embrapa/ · repo público
danimaciel/iagro-embrapa.

**Comece lendo `estado.md`** e atualize-o ao fim de cada sessão.

## Família iAgro

Irmãos: `../IAGRO` (piloto Territorial e agente local) e `../iagro-conversa` (conversa/RAG da Territorial,
que abre esta página pelo link "Ver no mapa"). Visão geral em `../iagro-conversa/CLAUDE.md`. Produtos e
localização vêm do Observatório de Pesquisa da Embrapa (release pública `enriquecimento-AAAA-MM` em
danimaciel/observatorio_embrapa); regras mudam lá.

## Como funciona

- `pipeline/`: redape.py → base.py (obras: publicação repetida entre unidades vira uma só) → vetores.py
  (e5 `passage:`, cache por hash) → site_dados.py (bits de 1 bit centrados, índice, vetores int8, detalhes em
  blocos, filtros de produto/estado/bioma) e mapa_estados.py (`site/estados.json`). Detalhes em `README.md`,
  `docs/METODO.md`; guia para a TI em `docs/IMPLANTACAO.md`.
- Busca v2: só significado, em dois passos (bits escolhem 120 candidatos; vetores int8 lidos por HTTP Range
  reordenam). O GitHub Pages responde 206, mas não aceita vários trechos numa requisição.
- Endereço com filtros: `#q=…&u=<nome da unidade>&p=<produto_id>&e=<UF>&b=<bioma>` (usado pelo Conversa).
- `.github/workflows/atualizar.yml`: dia 12 de cada mês (ou manual) refaz tudo; cache de vetores e
  `site-dados.tar.gz` na release `cache-vetores`. `pagina.yml`: push em `site/**` publica em 1–2 min.

## Regras da usuária

- Demonstração com dados públicos; não é serviço oficial e não usa a marca oficial da Embrapa.
- Sem custo: Pages + Actions gratuitos, modelos abertos.
- Números sempre com fonte e etapa (exportação do Redape, arquivo do pipeline), nunca de memória.
- Documentar sempre (`.md` + `.docx` para outras pessoas; gerador em
  `../observatorio de P&D Embrapa/documentacao/ferramentas/md2docx.js`).
- Português do Brasil em textos, código e commits. Publicar (push) depois do OK da usuária.
