# Guia de implantação (para a TI)

A página é **estática**: um `index.html` e uma pasta `dados/`. Não há servidor de aplicação, banco de dados
nem coleta de dados de quem usa. A busca roda no navegador.

## 1. Hospedar a página

1. Gerar os dados (ver seção 3) ou baixar o artefato da última execução do fluxo no GitHub Actions.
2. Copiar a pasta `site/` (com `site/dados/`) para qualquer servidor web (nginx, Apache, IIS, ou o servidor
   do Portal).
3. Recomendado no servidor: compressão gzip/brotli para `.json` (o índice cai de cerca de 20 MB para cerca
   de 6 MB) e cache longo para `dados/`.

Tamanho atual: `bits.bin` cerca de 18 MB, `indice.json` cerca de 20 MB, `vet/` 142 MB em 6 arquivos (lidos só em trechos;
o servidor precisa aceitar requisições HTTP Range, como fazem nginx, Apache e IIS por padrão), `det/` cerca de 200 MB em cerca de
700 arquivos pequenos (só os blocos dos resultados exibidos são baixados).

## 2. Retirar dependências externas (se a política exigir)

Hoje a página busca três coisas fora do servidor:

| O quê | De onde | Como trazer para dentro |
|---|---|---|
| Biblioteca transformers.js 3.8.1 | cdn.jsdelivr.net | Copiar `transformers.min.js` (e os arquivos `.wasm` do onnxruntime-web) para `site/lib/` e trocar o `import(...)` no `index.html` |
| Modelo `Xenova/multilingual-e5-base` (versão q8, cerca de 110 MB) | huggingface.co | Copiar a pasta do modelo para `site/modelos/Xenova/multilingual-e5-base/` e, no `index.html`, usar `env.allowRemoteModels = false; env.localModelPath = "modelos/";` |
| Fontes Fraunces e Inter | fonts.googleapis.com | Servir os arquivos de fonte localmente ou trocar por fontes do sistema |

## 3. Atualização mensal

Um script Python agendado (cron, Agendador de Tarefas ou a ferramenta de integração contínua da casa):

```
python pipeline/redape.py                 # baixa a exportação mais recente (API pública do Redape, sem conta)
python pipeline/base.py AAAA-MM
python pipeline/vetores.py tudo           # só calcula o que mudou desde o mês anterior
python pipeline/site_dados.py AAAA-MM
# copiar site/ para o servidor web
```

- Requisitos: Python 3.12, `pipeline/requirements-base.txt` e `pipeline/requirements-vetores.txt`
  (PyTorch para CPU basta; não precisa de placa de vídeo).
- Guardar `dados/cache/` entre execuções: é o que faz o mês seguinte calcular só os documentos novos.
- Primeira execução: cerca de 17 horas num processador comum para os 182 mil documentos (ou cerca de 1 hora
  dividindo em partes paralelas, como faz `.github/workflows/atualizar.yml`). Meses seguintes: minutos.

## 4. Pontos institucionais

- **Acessibilidade (eMAG/WCAG):** a página tem rótulos, contraste e funciona no celular, mas precisa de auditoria formal.
- **Identidade visual:** a demonstração não usa a marca oficial; aplicar a identidade da Embrapa é decisão da Comunicação.
- **LGPD:** a página não coleta dados. Autores aparecem como já constam nas páginas públicas do Portal.
  A base de pessoas (AutorPessoalEmbrapa.xls) não é usada.

## 5. Se quiserem respostas escritas (agente)

A versão com agente conversacional (Google ADK + modelo aberto via Ollama) está em
[danimaciel/iagro](https://github.com/danimaciel/iagro). Ela precisa de um servidor com placa de vídeo
(16 a 24 GB de memória de vídeo bastam para o modelo de 7B) e de uma API entre a página e o modelo.
