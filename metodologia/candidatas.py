"""Passo 1: gera votacoes_candidatas.csv com as votações nominais principais (texto-base) de 2023 até hoje.

Uso: python3 metodologia/candidatas.py
"""
import csv, os, re, sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from build import CAMARA_API, SENADO, get_csv, get_json

ANOS = range(2023, date.today().year + 1)
SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "votacoes_candidatas.csv")
# Votação do texto principal na Câmara. Fora: requerimentos, destaques ("Mantido o texto"),
# emendas avulsas e redação final, cujo "Sim" não diz o que estava em jogo.
PRINCIPAL_CD = re.compile(r"turno|^(Aprovad|Rejeitad)[ao]s? (o|a|os|as) (Projeto|Substitutivo|Subemenda Substitutiva|"
                          r"Medida Provisória|Proposta|Emenda Aglutinativa|Emendas? do Senado)", re.I)
SO_APROVADO = re.compile(r"^(Aprovad|Rejeitad)[ao]\.?$", re.I)
TIPOS = {"PL", "PLP", "PEC", "MPV", "PDL", "PLV", "PLN", "PRC", "PDC"}
PRINCIPAL_SF = re.compile(r"Votação nominal (do|da) (Projeto|Proposta|Medida|PL|PEC|PLP|PDL|Substitutivo|Emendas? da Câmara)", re.I)


def camara(ano):
    plen = {v["id"]: v for v in get_csv(f"votacoes/csv/votacoes-{ano}.csv")
            if v["siglaOrgao"] == "PLEN" and int(v["votosSim"] or 0) + int(v["votosNao"] or 0) > 0}
    props = {}
    for p in get_csv(f"votacoesProposicoes/csv/votacoesProposicoes-{ano}.csv"):
        if p["idVotacao"] in plen and p["proposicao_siglaTipo"] in TIPOS:
            props.setdefault(p["idVotacao"], p)
    for i, v in plen.items():
        p = props.get(i)
        desc = v["descricao"].strip()
        if p and (PRINCIPAL_CD.search(desc) or SO_APROVADO.match(desc)):
            yield {"casa": "Câmara", "id": i, "data": v["data"], "proposicao": p["proposicao_titulo"],
                   "id_proposicao": p["proposicao_id"], "ementa": p["proposicao_ementa"], "descricao": desc,
                   "sim": v["votosSim"], "nao": v["votosNao"]}


def senado(ano):
    for v in get_json(f"{SENADO}/votacao?dataInicio={ano}-01-01&dataFim={ano}-12-31"):
        votos = [x["siglaVotoParlamentar"] for x in v["votos"]]
        sim, nao = votos.count("Sim"), votos.count("Não")
        if sim + nao and PRINCIPAL_SF.search(v["descricaoVotacao"] or ""):
            yield {"casa": "Senado", "id": str(v["codigoSessaoVotacao"]), "data": v["dataSessao"],
                   "proposicao": v["identificacao"], "id_proposicao": str(v["codigoMateria"]),
                   "ementa": v.get("ementa") or "", "descricao": v["descricaoVotacao"], "sim": sim, "nao": nao}


if __name__ == "__main__":
    linhas = [r for a in ANOS for r in (*camara(a), *senado(a))]
    # Ementa detalhada e palavras-chave ajudam a entender ementas genéricas ("Altera a Lei nº ...").
    detalhes = {}
    for r in linhas:
        if r["casa"] == "Câmara" and r["id_proposicao"] not in detalhes:
            d = get_json(f"{CAMARA_API}/proposicoes/{r['id_proposicao']}")["dados"]
            detalhes[r["id_proposicao"]] = " | ".join(x for x in (d.get("ementaDetalhada"), d.get("keywords")) if x)
        r["detalhe"] = detalhes.get(r["id_proposicao"], "")
        r["pct_maioria"] = round(max(int(r["sim"]), int(r["nao"])) / (int(r["sim"]) + int(r["nao"])), 3)
    linhas.sort(key=lambda r: (r["casa"], r["data"], r["id"]))
    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    print(len(linhas), "votações ->", SAIDA, file=sys.stderr)
