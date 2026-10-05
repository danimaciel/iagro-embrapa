"""Monta a base do iAgro Embrapa a partir das exportações do Redape.

Lê dados/<AAAA-MM>/{publicacoes,projetos,solucoes-tecnologicas}-da-embrapa-<AAAA-MM>.csv e grava
dados/base.parquet: um documento por linha (obra, projeto ou solução tecnológica), com o texto que o
modelo recebe e o hash desse texto (chave do cache de vetores).

Obras: a mesma publicação depositada por várias unidades vira uma obra só, com a lista de unidades
(mesmo critério do Observatório de P&D: título normalizado + ano + sobreposição de autores ≥ 50%;
títulos genéricos, com menos de 4 palavras ou 25 letras, não são agrupados).

Uso:  python pipeline/base.py 2026-09
"""
import hashlib
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
MODELO = "intfloat/multilingual-e5-base"
PREFIXO = "passage: "  # e5: "passage: " nos documentos e "query: " nas perguntas
MAX_TOKENS = 512


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_titulo(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", sem_acento(str(t).lower()))).strip()


def chave_autores(a) -> set:
    if not isinstance(a, str):
        return set()
    out = set()
    for x in a.split(";"):
        sob, _, ini = x.partition(",")
        sob = norm_titulo(sob)
        if sob:
            out.add(f"{sob} {norm_titulo(ini)[:1]}")
    return out


def limpo(t) -> str:
    return re.sub(r"\s+", " ", str(t)).strip() if isinstance(t, str) else ""


def agrupar_obras(pub: pd.DataFrame) -> pd.Series:
    """Devolve, para cada publicação (índice de pub), o ID da obra (menor ID do grupo)."""
    pai = {i: i for i in pub.index}

    def raiz(i):
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i

    tn = pub["Título"].map(norm_titulo)
    eleg = (tn.str.count(" ") >= 3) & (tn.str.len() >= 25)
    cand = pub[eleg].assign(tn=tn[eleg])
    cand = cand[cand.duplicated(["tn", "Ano de publicação"], keep=False)]
    for _, g in cand.groupby(["tn", "Ano de publicação"]):
        idx, aut = list(g.index), [chave_autores(a) for a in g["Autores"]]
        for x in range(len(idx)):
            for y in range(x + 1, len(idx)):
                a, b = aut[x], aut[y]
                sob = 1 if not a or not b else len(a & b) / min(len(a), len(b))
                if sob >= 0.5:
                    pai[raiz(idx[x])] = raiz(idx[y])
    grupo = pd.Series({i: raiz(i) for i in pub.index})
    menor = pub.groupby(grupo)["ID"].apply(lambda s: min(s, key=int))
    return grupo.map(menor)


def ler(dir_mes: Path, nome: str, mes: str) -> pd.DataFrame:
    return pd.read_csv(dir_mes / f"{nome}-da-embrapa-{mes}.csv", dtype=str)


def montar(mes: str) -> pd.DataFrame:
    d = RAIZ / "dados" / mes
    linhas = []

    pub = ler(d, "publicacoes", mes)
    pub["obra"] = agrupar_obras(pub)
    pub["tam"] = pub["Resumo"].fillna("").str.len()
    pub["idn"] = pub["ID"].astype(int)
    unid = pub.dropna(subset=["Unidade"]).groupby("obra")["Unidade"].agg(lambda s: sorted(set(s)))
    nreg = pub.groupby("obra").size()
    # representante: a publicação com o resumo mais longo (empate: menor ID)
    rep = pub.sort_values(["tam", "idn"], ascending=[False, True]).drop_duplicates("obra")
    for r in rep.to_dict("records"):
        linhas.append({
            "codigo": f"PUB {r['obra']}", "tipo": "PUB", "titulo": limpo(r["Título"]), "resumo": limpo(r["Resumo"]),
            "ano": limpo(r["Ano de publicação"]), "detalhe": limpo(r["Tipo de publicação"]),
            "unidades": unid.get(r["obra"], []), "autores": limpo(r["Autores"]), "palavras": limpo(r["Palavras-chave"]),
            "link": limpo(r["Página da publicação no Portal Embrapa"]), "onde": "", "bioma": "",
            "registros": int(nreg[r["obra"]]),
        })

    for _, r in ler(d, "projetos", mes).iterrows():
        linhas.append({
            "codigo": f"PRJ {r['ID']}", "tipo": "PRJ", "titulo": limpo(r["Título"]), "resumo": limpo(r["Resumo"]),
            "ano": limpo(r["mês/ano de início"])[-4:],
            "detalhe": f"{limpo(r['Situação'])}; {limpo(r['mês/ano de início'])} a {limpo(r['mês/ano de finalização'])}",
            "unidades": [limpo(r["Unidade líder"])] if isinstance(r["Unidade líder"], str) else [],
            "autores": "", "palavras": limpo(r["Palavras-chave"]),
            "link": limpo(r["Página do projeto no Portal Embrapa"]), "onde": "", "bioma": "", "registros": 1,
        })

    for _, r in ler(d, "solucoes-tecnologicas", mes).iterrows():
        linhas.append({
            "codigo": f"TEC {r['ID']}", "tipo": "TEC", "titulo": limpo(r["Nome"]), "resumo": limpo(r["Descrição"]),
            "ano": limpo(r["Ano de lançamento"]), "detalhe": " - ".join(x for x in (limpo(r["Tipo"]), limpo(r["Subtipo"])) if x),
            "unidades": [limpo(r["Unidade responsável"])] if isinstance(r["Unidade responsável"], str) else [],
            "autores": "", "palavras": limpo(r["Palavras-chave"]),
            "link": limpo(r["Página da tecnologia no Portal Embrapa"]), "onde": limpo(r["Onde encontrar"]),
            "bioma": limpo(r["Bioma"]), "registros": 1,
        })

    b = pd.DataFrame(linhas)
    # Texto que o modelo recebe: título + resumo + palavras-chave (sem unidade, pessoas ou links)
    corpo = b.titulo.str.rstrip(".") + ". " + b.resumo + (" Palavras-chave: " + b.palavras).where(b.palavras != "", "")
    b["texto_modelo"] = PREFIXO + corpo.str.replace(r"\s+", " ", regex=True).str.strip()
    b["hash"] = [hashlib.sha1(f"{MODELO}|{MAX_TOKENS}|{t}".encode("utf-8")).hexdigest() for t in b.texto_modelo]
    return b


if __name__ == "__main__":
    mes = sys.argv[1] if len(sys.argv) > 1 else "2026-09"
    b = montar(mes)
    b.to_parquet(RAIZ / "dados" / "base.parquet", index=False)
    print(f"{mes}: {len(b)} documentos | {b.tipo.value_counts().to_dict()} | "
          f"obras com mais de uma unidade: {(b.unidades.map(len) > 1).sum()}")
