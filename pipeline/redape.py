"""Baixa do Redape (Dataverse da Embrapa) as exportações de publicações, projetos e soluções tecnológicas.

Cada base é um dataset público com um arquivo por mês ("<prefixo>-AAAA-MM"); não precisa de conta.
Sem argumento, usa o mês mais recente disponível nas três bases. O arquivo só é aceito se o tamanho
bater com o informado pelo Redape; a transferência é retomada se a conexão cair.

Uso:  python pipeline/redape.py            (mês mais recente)
      python pipeline/redape.py 2026-09
Grava em dados/<AAAA-MM>/ e imprime o mês usado na última linha.
"""
import re
import sys
import time
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
URL = "https://www.redape.dados.embrapa.br"
BASES = {
    "publicacoes": ("doi:10.48432/TRBT0S", "publicacoes-da-embrapa"),
    "projetos": ("doi:10.48432/EZDXWF", "projetos-da-embrapa"),
    "solucoes": ("doi:10.48432/ZQE5FV", "solucoes-tecnologicas-da-embrapa"),
}


def arquivos(doi: str, prefixo: str) -> dict:
    """{AAAA-MM: (id, tamanho)} dos arquivos do dataset na versão mais recente."""
    r = requests.get(f"{URL}/api/datasets/:persistentId/", params={"persistentId": doi}, timeout=120)
    r.raise_for_status()
    out = {}
    for f in r.json()["data"]["latestVersion"]["files"]:
        df = f["dataFile"]
        m = re.fullmatch(re.escape(prefixo) + r"-(\d{4}-\d{2})(\.\w+)?", df["filename"])
        if m:
            out[m.group(1)] = (df["id"], int(df.get("originalFileSize") or df["filesize"]))
    return out


def baixar(id_arq: int, tamanho: int, destino: Path, tentativas: int = 8) -> None:
    if destino.exists() and destino.stat().st_size == tamanho:
        print(f"ok (já baixado) {destino.name}")
        return
    parte = destino.with_suffix(".part")
    for i in range(tentativas):
        ja = parte.stat().st_size if parte.exists() else 0
        cab = {"Range": f"bytes={ja}-"} if ja else {}
        try:
            with requests.get(f"{URL}/api/access/datafile/{id_arq}", params={"format": "original"},
                              headers=cab, stream=True, timeout=300) as r:
                r.raise_for_status()
                modo = "ab" if ja and r.status_code == 206 else "wb"
                with open(parte, modo) as fh:
                    for bloco in r.iter_content(1 << 20):
                        fh.write(bloco)
        except requests.RequestException as ex:
            print(f"  tentativa {i + 1} interrompida: {ex}")
            time.sleep(10)
        if parte.exists() and parte.stat().st_size == tamanho:
            parte.replace(destino)
            print(f"baixado {destino.name} ({tamanho / 1e6:.1f} MB)")
            return
        if parte.exists() and parte.stat().st_size > tamanho:
            parte.unlink()
    raise SystemExit(f"Download incompleto de {destino.name}; rode de novo para retomar.")


def main():
    lista = {b: arquivos(*cfg) for b, cfg in BASES.items()}
    comuns = set.intersection(*(set(v) for v in lista.values()))
    mes = sys.argv[1] if len(sys.argv) > 1 else max(comuns)
    if mes not in comuns:
        raise SystemExit(f"Exportação {mes} não está nas três bases. Disponíveis: {sorted(comuns)[-3:]}")
    pasta = RAIZ / "dados" / mes
    pasta.mkdir(parents=True, exist_ok=True)
    for b, (_, prefixo) in BASES.items():
        baixar(*lista[b][mes], pasta / f"{prefixo}-{mes}.csv")
    print(mes)


if __name__ == "__main__":
    main()
