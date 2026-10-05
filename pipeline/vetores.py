"""Vetores de significado (multilingual-e5-base) com cache por hash do texto.

Só documentos novos ou com texto alterado são calculados; os demais reaproveitam o cache.
O cálculo é dividido em partes para rodar em paralelo (GitHub Actions, uma parte por máquina).

Arquivos:
  dados/cache/e5.npy           vetores float16 normalizados (n × 768)
  dados/cache/e5_hash.parquet  hash de cada linha do .npy
  dados/faltam.parquet         textos sem vetor, com o número da parte
  dados/partes/parte_<k>.npz   vetores calculados de uma parte

Uso:
  python pipeline/vetores.py faltam --partes 30    lista o que falta e divide em partes (imprime as partes)
  python pipeline/vetores.py calcular --parte 3    calcula uma parte
  python pipeline/vetores.py juntar                junta cache + partes e descarta o que saiu da base
  python pipeline/vetores.py tudo                  faltam + calcular + juntar numa máquina só
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "dados"
CACHE = DADOS / "cache"
PARTES = DADOS / "partes"
MODELO = "intfloat/multilingual-e5-base"


def ler_cache():
    if not (CACHE / "e5.npy").exists():
        return pd.Series(dtype=str), np.zeros((0, 768), dtype=np.float16)
    return pd.read_parquet(CACHE / "e5_hash.parquet")["hash"], np.load(CACHE / "e5.npy")


def faltam(n_partes: int) -> list[int]:
    base = pd.read_parquet(DADOS / "base.parquet", columns=["hash", "texto_modelo"]).drop_duplicates("hash")
    h, _ = ler_cache()
    f = base[~base.hash.isin(set(h))].copy()
    # partes equilibradas pelo tamanho do texto (o custo cresce com o comprimento)
    f = f.assign(tam=f.texto_modelo.str.len()).sort_values("tam", ascending=False)
    n = max(1, min(n_partes, len(f) // 200 + 1)) if len(f) else 0
    f["parte"] = np.arange(len(f)) % n if n else []
    f.drop(columns="tam").to_parquet(DADOS / "faltam.parquet", index=False)
    print(f"base {len(base)} | no cache {len(base) - len(f)} | faltam {len(f)} em {n} partes")
    return list(range(n))


def calcular(parte: int) -> None:
    from sentence_transformers import SentenceTransformer

    f = pd.read_parquet(DADOS / "faltam.parquet")
    f = f[f.parte == parte]
    m = SentenceTransformer(MODELO)
    m.max_seq_length = 512
    E = m.encode(f.texto_modelo.tolist(), normalize_embeddings=True, batch_size=32, show_progress_bar=True)
    PARTES.mkdir(parents=True, exist_ok=True)
    np.savez(PARTES / f"parte_{parte}.npz", hash=f.hash.to_numpy(), E=E.astype(np.float16))
    print(f"parte {parte}: {len(f)} vetores")


def juntar() -> None:
    h, E = ler_cache()
    hs, Es = [h.to_numpy()], [E]
    for p in sorted(PARTES.glob("parte_*.npz")):
        z = np.load(p, allow_pickle=True)
        hs.append(z["hash"].astype(str))
        Es.append(z["E"])
    H, E = np.concatenate(hs), np.concatenate(Es)
    atuais = set(pd.read_parquet(DADOS / "base.parquet", columns=["hash"]).hash)
    _, primeira = np.unique(H, return_index=True)
    manter = np.array([i for i in sorted(primeira) if H[i] in atuais], dtype=int)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "e5.npy", E[manter].astype(np.float16))
    pd.DataFrame({"hash": H[manter]}).to_parquet(CACHE / "e5_hash.parquet", index=False)
    print(f"cache: {len(manter)} vetores (cobre {len(set(H[manter]) & atuais)} de {len(atuais)} textos da base)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("acao", choices=["faltam", "calcular", "juntar", "tudo"])
    ap.add_argument("--partes", type=int, default=30)
    ap.add_argument("--parte", type=int, default=0)
    a = ap.parse_args()
    if a.acao == "faltam":
        print("PARTES=" + json.dumps(faltam(a.partes)))
    elif a.acao == "calcular":
        calcular(a.parte)
    elif a.acao == "juntar":
        juntar()
    else:
        for k in faltam(1):
            calcular(k)
        juntar()
