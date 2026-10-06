"""Gera os dados da página de busca (site/dados/) a partir da base e do cache de vetores.

  site/dados/indice.json    título, ano, tipo e unidades de cada documento (o que a busca precisa)
  site/dados/bits.bin       vetor de cada documento em 1 bit por dimensão (96 bytes), já centrado
  site/dados/vet/NN.bin     vetor completo de cada documento em int8 (768 bytes), em arquivos de 32.768 linhas
  site/dados/info.json      totais, unidades, média dos vetores (para centrar a pergunta), data da exportação
  site/dados/det/NNNN.json  detalhes (resumo, link, autores...) em blocos de 256, baixados só quando aparecem

Busca em dois passos: os bits (18 MB, baixados inteiros) selecionam os 120 candidatos mais próximos; a página
lê só as linhas desses candidatos nos arquivos vet/ (requisições de trecho, HTTP Range) e os reordena com o
vetor completo. Nos testes, o resultado é igual ao de usar o vetor completo em tudo (ver docs/METODO.md).

Uso:  python pipeline/site_dados.py 2026-10
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "dados"
SAIDA = RAIZ / "site" / "dados"
BLOCO = 256
LINHAS_VET = 32768  # vetores int8 em arquivos de 24 MB; a página lê só as linhas dos candidatos
TIPOS = ["PUB", "TEC", "PRJ"]
MESES = "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split()


def main(mes: str) -> None:
    b = pd.read_parquet(DADOS / "base.parquet")
    h = pd.read_parquet(DADOS / "cache" / "e5_hash.parquet")["hash"]
    E = np.load(DADOS / "cache" / "e5.npy")
    pos = pd.Series(np.arange(len(h)), index=h.to_numpy())
    b = b[b.hash.isin(pos.index)].copy()

    b["u0"] = b.unidades.map(lambda u: u[0] if len(u) else "~")
    b["anon"] = pd.to_numeric(b.ano, errors="coerce").fillna(0).astype(int)
    b = b.sort_values(["u0", "tipo", "anon"], ascending=[True, True, False]).reset_index(drop=True)

    V = E[pos[b.hash].to_numpy()].astype(np.float32)
    mu = V.mean(0)
    bits = np.packbits(V - mu > 0, axis=1)  # n × 96 bytes, bit mais significativo primeiro
    escala = float(np.abs(V).max())
    v8 = np.round(V / escala * 127).astype(np.int8)  # vetor completo, para reordenar os candidatos

    unidades = sorted({u for us in b.unidades for u in us})
    iu = {u: i for i, u in enumerate(unidades)}

    if SAIDA.exists():
        shutil.rmtree(SAIDA)
    (SAIDA / "det").mkdir(parents=True)
    (SAIDA / "vet").mkdir()
    bits.tofile(SAIDA / "bits.bin")
    for k in range(0, len(v8), LINHAS_VET):
        v8[k:k + LINHAS_VET].tofile(SAIDA / "vet" / f"{k // LINHAS_VET:02d}.bin")
    indice = {
        "t": b.titulo.tolist(),
        "a": b.anon.tolist(),
        "k": [TIPOS.index(t) for t in b.tipo],
        "u": [[iu[u] for u in us] if len(us) != 1 else iu[us[0]] for us in b.unidades],
    }
    (SAIDA / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    for k in range(0, len(b), BLOCO):
        blo = []
        for r in b.iloc[k:k + BLOCO].itertuples():
            d = {"c": r.codigo, "r": r.resumo, "l": r.link, "d": r.detalhe}
            if r.autores:
                d["au"] = r.autores if len(r.autores) <= 160 else r.autores[:160].rsplit(";", 1)[0] + "; et al."
            if r.onde:
                d["o"] = r.onde
            if r.bioma:
                d["b"] = r.bioma
            if r.registros > 1:
                d["n"] = int(r.registros)
            blo.append(d)
        (SAIDA / "det" / f"{k // BLOCO:04d}.json").write_text(
            json.dumps(blo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    pubs = b[b.tipo == "PUB"]
    anos = pubs.anon[(pubs.anon >= 1970) & (pubs.anon <= int(mes[:4]))]
    cont_u = pd.Series([u for us in b.unidades for u in us]).value_counts()
    info = {
        "exportacao": f"{MESES[int(mes[5:]) - 1]} de {mes[:4]}", "mes": mes,
        "n": len(b), "dim": int(V.shape[1]), "bloco": BLOCO, "linhas_vet": LINHAS_VET, "escala": escala,
        "publicacoes": int((b.tipo == "PUB").sum()), "solucoes": int((b.tipo == "TEC").sum()),
        "projetos": int((b.tipo == "PRJ").sum()),
        "ano_min": int(anos.min()), "ano_max": int(anos.max()),
        "por_ano": {int(a): int(n) for a, n in anos.value_counts().sort_index().items()},
        "unidades": [{"nome": u, "n": int(cont_u.get(u, 0))} for u in unidades],
        "media": [round(float(x), 6) for x in mu],
    }
    (SAIDA / "info.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    tam = sum(f.stat().st_size for f in SAIDA.rglob("*") if f.is_file()) / 1e6
    print(f"{len(b)} documentos | {len(unidades)} unidades | bits {bits.nbytes / 1e6:.1f} MB | "
          f"índice {(SAIDA / 'indice.json').stat().st_size / 1e6:.1f} MB | total {tam:.0f} MB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2026-09")
