"""Compara classificações v3 independentes A e B, por eixo.

python3 metodologia/consolidar.py divergencias  -> divergencias.csv para desempate
python3 metodologia/consolidar.py               -> classificacao.csv final

Concordância: mesmo sinal de p e diferenças de p e q ≤ 3; usa as médias.
Divergência sem desempate: par vazio. Kappa mede o sinal de p conhecido.
"""
import csv, os, sys
from collections import Counter

DIR = os.path.dirname(os.path.abspath(__file__))
EIXOS = ("ed", "aut")
CAMPOS = [e + s for e in EIXOS for s in ("_p", "_q")]


def ler(nome):
    caminho = os.path.join(DIR, nome)
    if not os.path.exists(caminho):
        return {}
    return {(r["casa"], r["id"]): r for r in csv.DictReader(open(caminho, encoding="utf-8"))}


def sinal(x):
    return (x > 0) - (x < 0)


def par(r, e):
    p, q = (r.get(e + s, "") for s in ("_p", "_q"))
    if p == q == "":
        return None
    if p == "" or q == "":
        raise ValueError(f"{e}: proposta e alternativa devem ser preenchidas juntas")
    p, q = float(p), float(q)
    if not (-10 <= p <= 10 and -10 <= q <= 10):
        raise ValueError(f"{e}: posição fora de −10..+10")
    return p, q


def concordam(a, b):
    if a is None or b is None:
        return a == b
    return sinal(a[0]) == sinal(b[0]) and all(abs(x - y) <= 3 for x, y in zip(a, b))


def kappa(pares):
    """Kappa de Cohen sobre o sinal de p (−, 0, +), excluindo informação ausente."""
    n = len(pares)
    if not n:
        return None
    obs = sum(a == b for a, b in pares) / n
    ca, cb = Counter(a for a, _ in pares), Counter(b for _, b in pares)
    esp = sum(ca[k] * cb[k] for k in (-1, 0, 1)) / n ** 2
    return (obs - esp) / (1 - esp) if esp < 1 else 1.0


def consolidar(a, b, desempate):
    if a.keys() != b.keys():
        raise ValueError("A e B não cobrem as mesmas votações")
    final, stats = [], {e: [] for e in EIXOS}
    for chave, ra in a.items():
        rb, rd = b[chave], desempate.get(chave, {})
        linha = {"casa": chave[0], "id": chave[1], "justificativa": ra["justificativa"], "origem": "consenso"}
        for e in EIXOS:
            va, vb = par(ra, e), par(rb, e)
            if va is not None and vb is not None:
                stats[e].append((sinal(va[0]), sinal(vb[0])))
            if concordam(va, vb):
                valor = tuple((x + y) / 2 for x, y in zip(va, vb)) if va is not None else None
            else:
                valor = par(rd, e)
                origem = "desempate" if valor is not None else "divergência sem desempate"
                if linha["origem"] != "divergência sem desempate":
                    linha["origem"] = origem
                if rd.get("justificativa"):
                    linha["justificativa"] += f"; {e}: {rd['justificativa']}"
                if valor is None:
                    linha["justificativa"] += f"; {e}: informação insuficiente (divergência sem desempate)"
            linha[e + "_p"], linha[e + "_q"] = valor if valor is not None else ("", "")
        final.append(linha)
    return final, stats


def _teste():
    r = lambda p, q, ap="", aq="": dict(ed_p=p, ed_q=q, aut_p=ap, aut_q=aq, justificativa="x")
    a = {("C", "1"): r(-2, 0, 1, 0), ("C", "2"): r(-4, 1), ("C", "3"): r("", "")}
    b = {("C", "1"): r(-5, 3, 2, 0), ("C", "2"): r(-4, 5), ("C", "3"): r(0, 0)}
    f, s = consolidar(a, b, {("C", "2"): r(-3, 2)})
    assert (f[0]["ed_p"], f[0]["ed_q"], f[0]["aut_p"]) == (-3.5, 1.5, 1.5)
    assert (f[1]["ed_p"], f[1]["ed_q"], f[1]["origem"]) == (-3, 2, "desempate")
    assert f[2]["ed_p"] == f[2]["ed_q"] == "" and f[2]["origem"] == "divergência sem desempate"
    assert not concordam((-1, 0), (1, 0))
    assert not concordam((-1, 0), (-4.1, 0))
    assert concordam(None, None) and not concordam(None, (0, 0))
    assert kappa([(1, 1), (0, 0), (-1, -1)]) == 1 and kappa([]) is None
    assert s["ed"] == [(-1, -1), (-1, -1)]
    for p, q in (("", 0), (11, 0), ("nan", 0)):
        try:
            par(r(p, q), "ed")
        except ValueError:
            pass
        else:
            raise AssertionError((p, q))


if __name__ == "__main__":
    _teste()
    a, b = ler("classificacao_a.csv"), ler("classificacao_b.csv")
    assert a and a.keys() == b.keys(), "A e B devem existir e cobrir as mesmas votações"
    for r in [*a.values(), *b.values()]:
        assert all(c in r for c in CAMPOS), "Formato v3 obrigatório"
        for e in EIXOS:
            par(r, e)
    if sys.argv[1:] == ["divergencias"]:
        cand = ler("votacoes_candidatas.csv")
        div = [{**cand[k], "eixos_em_disputa": " ".join(e for e in EIXOS if not concordam(par(a[k], e), par(b[k], e))),
                **{c + "_" + fonte: r[k][c] for fonte, r in (("a", a), ("b", b)) for c in CAMPOS},
                "just_a": a[k]["justificativa"], "just_b": b[k]["justificativa"]}
               for k in a if any(not concordam(par(a[k], e), par(b[k], e)) for e in EIXOS)]
        with open(os.path.join(DIR, "divergencias.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(div[0]) if div else ["casa", "id"])
            w.writeheader()
            w.writerows(div)
        print(len(div), "divergências -> divergencias.csv")
        sys.exit()
    final, stats = consolidar(a, b, ler("desempate.csv"))
    with open(os.path.join(DIR, "classificacao.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["casa", "id", *CAMPOS, "origem", "justificativa"])
        w.writeheader()
        w.writerows(final)
    for e in EIXOS:
        n = sum(concordam(par(a[k], e), par(b[k], e)) for k in a)
        k = kappa(stats[e])
        print(f"{e}: concordância {n / len(a):.0%}, kappa do sinal de p {k if k is not None else 'indisponível'}")
    print(Counter(l["origem"] for l in final))
