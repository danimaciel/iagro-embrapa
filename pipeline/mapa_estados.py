"""Gera site/estados.json: contorno simplificado de cada estado em caminho SVG, para o mapa da página.

Fonte: malha de UFs do IBGE (API de malhas v3, qualidade mínima). Rodar só quando a malha mudar:
  python pipeline/mapa_estados.py
Projeção simples (longitude × cos da latitude média), suficiente para um mapa de contagens por estado.
"""
import json
import math
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
URL = ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
       "?formato=application/vnd.geo%2Bjson&qualidade=minima&intrarregiao=UF")
SIGLA = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI",
         "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
         "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}
NOME = {"RO": "Rondônia", "AC": "Acre", "AM": "Amazonas", "RR": "Roraima", "PA": "Pará", "AP": "Amapá",
        "TO": "Tocantins", "MA": "Maranhão", "PI": "Piauí", "CE": "Ceará", "RN": "Rio Grande do Norte",
        "PB": "Paraíba", "PE": "Pernambuco", "AL": "Alagoas", "SE": "Sergipe", "BA": "Bahia", "MG": "Minas Gerais",
        "ES": "Espírito Santo", "RJ": "Rio de Janeiro", "SP": "São Paulo", "PR": "Paraná", "SC": "Santa Catarina",
        "RS": "Rio Grande do Sul", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso", "GO": "Goiás", "DF": "Distrito Federal"}


def main():
    local = RAIZ / "dados" / "enriquecimento" / "br_uf.geojson"
    geo = json.loads(local.read_text(encoding="utf-8")) if local.exists() else requests.get(URL, timeout=120).json()
    k = math.cos(math.radians(-15))
    W, H = 1000, 1000
    todos = [(x, y) for f in geo["features"] for poly in
             ([f["geometry"]["coordinates"]] if f["geometry"]["type"] == "Polygon" else f["geometry"]["coordinates"])
             for anel in poly for x, y in anel]
    xs, ys = [x * k for x, _ in todos], [y for _, y in todos]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    esc = min(W / (x1 - x0), H / (y1 - y0))
    px = lambda x: round((x * k - x0) * esc, 1)
    py = lambda y: round((y1 - y) * esc, 1)
    saida = {"largura": round((x1 - x0) * esc), "altura": round((y1 - y0) * esc), "estados": {}}
    for f in geo["features"]:
        uf = SIGLA[str(f["properties"]["codarea"])]
        polys = [f["geometry"]["coordinates"]] if f["geometry"]["type"] == "Polygon" else f["geometry"]["coordinates"]
        d = []
        for poly in polys:
            for anel in poly:
                pts, ult = [], None
                for x, y in anel:
                    p = (px(x), py(y))
                    if p != ult:
                        pts.append(p)
                        ult = p
                if len(pts) > 2:
                    d.append("M" + "L".join(f"{a},{b}" for a, b in pts) + "Z")
        saida["estados"][uf] = {"nome": NOME[uf], "d": "".join(d)}
    arq = RAIZ / "site" / "estados.json"
    arq.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(saida['estados'])} estados, {arq.stat().st_size / 1e3:.0f} KB")


if __name__ == "__main__":
    main()
