"""Baixa dados oficiais (Câmara + Senado) e gera data.json para o site.

Uso: python3 build.py [ano]   (padrão: ano atual)
"""
import bisect, csv, http.client, io, json, os, sys, time, unicodedata, urllib.request, zipfile
from collections import defaultdict
from datetime import date, datetime

ANO = int(sys.argv[1]) if len(sys.argv) > 1 else date.today().year
PESOS = {"presenca": 0.4, "votacoes": 0.4, "proposicoes": 0.2}
CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2"
CAMARA_ARQ = "https://dadosabertos.camara.leg.br/arquivos"
SENADO = "https://legis.senado.leg.br/dadosabertos"
# Códigos de voto do Senado que indicam presença no plenário / voto registrado
SEN_VOTOU = {"Sim", "Não", "Abstenção", "Votou", "Presidente (art. 51 RISF)"}
SEN_PRESENTE = SEN_VOTOU | {"P-NRV", "Obstrução"}
ULTIMOS = 15  # quantos gastos / votações recentes mostrar no detalhe

# Votações em que o parlamentar legisla em benefício próprio ou da classe política.
# Lista curada à mão (palavras-chave geram falsos positivos): só a votação principal
# de cada pauta, onde "Sim" = a favor do texto. Votar "Sim" desconta pontos da nota.
PENALIDADE_AUTOBENEFICIO = 20  # pontos descontados se votou "Sim" em todas
AUTOBENEFICIO_CAMARA = {  # idVotacao -> pauta
    "2352476-149": "PEC 9/2023 (1º turno) – anistia a partidos que descumpriram cotas de raça e gênero",
    "2352476-168": "PEC 9/2023 (2º turno) – anistia a partidos que descumpriram cotas de raça e gênero",
    "2387067-33": "PLP 192/2023 – reduz prazos de inelegibilidade da Lei da Ficha Limpa",
    "2383019-54": "PLP 177/2023 – aumenta o número de deputados de 513 para 531",
    "2383019-91": "PLP 177/2023 (emendas do Senado) – aumenta o número de deputados",
    "2270800-135": "PEC 3/2021 (1º turno) – PEC da Blindagem: exige aval do Congresso para processar parlamentares",
    "2270800-160": "PEC 3/2021 (2º turno) – PEC da Blindagem: exige aval do Congresso para processar parlamentares",
    "2565441-32": "PL 4822/2025 – limita multas e descontos do Fundo Partidário dos partidos",
}
AUTOBENEFICIO_SENADO = {  # codigoSessaoVotacao -> (data, pauta)
    "6873": ("2024-08-14", "PEC 9/2023 (1º turno) – anistia a partidos que descumpriram cotas de raça e gênero"),
    "6874": ("2024-08-14", "PEC 9/2023 (2º turno) – anistia a partidos que descumpriram cotas de raça e gênero"),
    "6951": ("2025-06-25", "PLP 177/2023 – aumenta o número de deputados de 513 para 531"),
    "7007": ("2025-09-02", "PLP 192/2023 – reduz prazos de inelegibilidade da Lei da Ficha Limpa"),
}


# Posição política pelos votos (ver metodologia/codebook.md). Proposta, alternativa e parlamentares ficam em −10..+10.
CLASSIFICACAO = "metodologia/classificacao.csv"
CANDIDATAS = "metodologia/votacoes_candidatas.csv"
# Votar com a minoria vale mais: peso 1 com a maioria, crescendo até MAX_BONUS_MINORIA quando quase ninguém votou junto.
MAX_BONUS_MINORIA = 3
MIN_VOTOS_EIXO = 5  # abaixo disso o eixo fica "dados insuficientes"
VOTO_VALOR = {"Sim": 1, "Não": -1, "Obstrução": -1}  # obstruir é tática para derrubar o texto
ED_NOMES = ("Esquerda", "Centro-esquerda", "Centro-direita", "Direita")
EXTREMO = 7  # a partir daqui, "Extrema-esquerda" / "Extrema-direita"
AUT_NOMES = ("libertária", "moderadamente libertária", "moderadamente autoritária", "autoritária")


def baixar(url, tentativas=3, accept="*/*"):
    """Baixa o corpo inteiro; repete se a conexão cair ou vier menor que o Content-Length."""
    req = urllib.request.Request(url, headers={"Accept": accept})
    for t in range(tentativas):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                corpo = r.read()
                esperado = r.headers.get("Content-Length")
            if esperado and len(corpo) != int(esperado):
                raise http.client.IncompleteRead(corpo)
            return corpo
        except (OSError, http.client.HTTPException):
            if t == tentativas - 1:
                raise
            time.sleep(2 ** t)


def get_json(url):
    return json.loads(baixar(url, accept="application/json"))


def get_csv(path):
    print("baixando", path, file=sys.stderr)
    return csv.DictReader(io.StringIO(baixar(f"{CAMARA_ARQ}/{path}").decode("utf-8-sig")), delimiter=";")


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper().strip()


def posicoes_pauta(r):
    """Lê os pares v3; vazio é desconhecido, zero é uma posição válida."""
    out = {}
    for e in ("ed", "aut"):
        p, q = (r[e + sufixo] for sufixo in ("_p", "_q"))
        if (p in ("", None)) != (q in ("", None)):
            raise ValueError(f"{e}: proposta e alternativa devem ser preenchidas juntas")
        for sufixo, v in (("_p", p), ("_q", q)):
            v = None if v in ("", None) else float(v)
            if v is not None and not -10 <= v <= 10:
                raise ValueError(f"{e}: posição fora de −10..+10")
            out[e + sufixo] = v
    return out


def carregar_classificacao(casa):
    """Votações v3 com alternativas distintas; sem equilibrar sinais ou excluir consenso."""
    cand = {(r["casa"], r["id"]): r for r in csv.DictReader(open(CANDIDATAS, encoding="utf-8"))}
    out = {}
    for r in csv.DictReader(open(CLASSIFICACAO, encoding="utf-8")):
        valores = posicoes_pauta(r)
        if r["casa"] == casa and any(valores[e + "_p"] != valores[e + "_q"] for e in ("ed", "aut")):
            c = cand[(r["casa"], r["id"])]
            out[r["id"]] = {"data": c["data"], "proposicao": c["proposicao"], "descricao": c["descricao"],
                            **valores, "justificativa": r["justificativa"],
                            "sim": int(c["sim"]), "nao": int(c["nao"])}
    return out


def bonus_minoria(v):
    """1 se votou com a maioria; até MAX_BONUS_MINORIA se o lado dele teve quase nenhum voto."""
    if "sim" not in v or v["sim"] + v["nao"] == 0:
        return 1
    lado = (v["sim"] if VOTO_VALOR[v["voto"]] > 0 else v["nao"]) / (v["sim"] + v["nao"])
    return 1 if lado >= 0.5 else round(1 + (MAX_BONUS_MINORIA - 1) * (1 - 2 * lado), 2)


def faixa(x):
    return min(int((x + 10) / 5), 3)  # [-10,-5) [-5,0) [0,5) [5,10]


def nome_ed(x):
    if abs(x) >= EXTREMO:
        return "Extrema-esquerda" if x < 0 else "Extrema-direita"
    return ED_NOMES[0 if x <= -4 else 1 if x < 0 else 2 if x < 4 else 3]


def posicao(votos):
    """Classificação espacial por eixo, em grade de 0,1, com cortes fixos (p+q)/2.

    Minimiza violações ponderadas apenas por bonus_minoria: sem equilíbrio por sinal
    nem exclusão de consenso. Não/Obstrução escolhem q; outros votos não contam.
    No corte, a indiferença viola ambos os lados (não explica uma escolha estrita).
    Empates: meio do intervalo ótimo; se houver intervalos separados, maior largura,
    depois centro mais próximo de zero, depois o da esquerda. Nunca atravessa uma
    região não ótima. Na ponta, usa o corte respeitado mais extremo ±0,5, limitado
    à alternativa apoiada e ao intervalo ótimo. Arredonda para a grade mais próxima.
    """
    res = {}
    for e in ("ed", "aut"):
        vs = []
        for v in votos:
            p, q = v[e + "_p"], v[e + "_q"]
            if p is None or q is None or p == q or v["voto"] not in VOTO_VALOR:
                continue
            lado = (1 if p > q else -1) * VOTO_VALOR[v["voto"]]
            vs.append(((p + q) / 2, lado, round(100 * bonus_minoria(v)), p if v["voto"] == "Sim" else q))
        res[e], res["n_" + e] = None, len(vs)
        if len(vs) < MIN_VOTOS_EIXO:
            continue
        perdas = [sum(w for m, lado, w, _ in vs if (i / 10 - m) * lado <= 1e-9) for i in range(-100, 101)]
        minimo = min(perdas)
        otimos = [i - 100 for i, perda in enumerate(perdas) if perda == minimo]
        intervalos = []
        for i in otimos:
            if not intervalos or i > intervalos[-1][1] + 1:
                intervalos.append([i, i])
            else:
                intervalos[-1][1] = i
        lo, hi = min(intervalos, key=lambda par: (par[0] - par[1], abs(sum(par)), par[0]))
        alvo = (lo + hi) / 20
        if lo == -100:
            cortes = [(m, alternativa) for m, lado, _, alternativa in vs if lado < 0 and lo / 10 < m]
            if cortes:
                m, alternativa = min(cortes)
                alvo = max(m - 0.5, alternativa)
        elif hi == 100:
            cortes = [(m, alternativa) for m, lado, _, alternativa in vs if lado > 0 and hi / 10 > m]
            if cortes:
                m, alternativa = max(cortes)
                alvo = min(m + 0.5, alternativa)
        res[e] = min(range(lo, hi + 1), key=lambda i: (round(abs(i / 10 - alvo), 10), abs(i), i)) / 10
    # sem votos suficientes em autoridade (ex.: Senado), o nome usa só o eixo esquerda × direita
    res["posicao_nome"] = ("Dados insuficientes" if res["ed"] is None else nome_ed(res["ed"]) if res["aut"] is None
                           else f"{nome_ed(res['ed'])} {AUT_NOMES[faixa(res['aut'])]}")
    return res


def resumo_gastos(gastos):
    """gastos: lista de (data ISO, categoria, fornecedor, valor, url)."""
    cats = defaultdict(float)
    for g in gastos:
        cats[g[1]] += g[3]
    return {
        "total": round(sum(cats.values()), 2),
        "categorias": sorted(([c, round(v, 2)] for c, v in cats.items()), key=lambda x: -x[1]),
        "ultimos": [dict(zip(("data", "categoria", "fornecedor", "valor", "url"), g))
                    for g in sorted(gastos, key=lambda g: g[0], reverse=True)[:ULTIMOS]],
    }


def deputados_federais():
    deps = get_json(f"{CAMARA_API}/deputados?itens=1000")["dados"]

    sessoes = {e["id"] for e in get_csv(f"eventos/csv/eventos-{ANO}.csv")
               if e["descricaoTipo"] == "Sessão Deliberativa"
               and e["localCamara.nome"] == "Plenário da Câmara dos Deputados"
               and e["situacao"].startswith("Encerrada")}
    presencas = defaultdict(set)
    for p in get_csv(f"eventosPresencaDeputados/csv/eventosPresencaDeputados-{ANO}.csv"):
        if p["idEvento"] in sessoes:
            presencas[p["idDeputado"]].add(p["idEvento"])
    sessoes = set().union(*presencas.values())  # descarta sessões do Congresso sem lista de presença

    plen = {v["id"]: v["descricao"] for v in get_csv(f"votacoes/csv/votacoes-{ANO}.csv") if v["siglaOrgao"] == "PLEN"}
    prop_votacao = {}
    for v in get_csv(f"votacoesProposicoes/csv/votacoesProposicoes-{ANO}.csv"):
        prop_votacao.setdefault(v["idVotacao"], (v["proposicao_titulo"], v["proposicao_ementa"]))
    votacoes_nominais, votos, historico = set(), defaultdict(int), defaultdict(list)
    for v in get_csv(f"votacoesVotos/csv/votacoesVotos-{ANO}.csv"):
        if v["idVotacao"] in plen:
            votacoes_nominais.add(v["idVotacao"])
            votos[v["deputado_id"]] += 1
            titulo, ementa = prop_votacao.get(v["idVotacao"], ("", ""))
            historico[v["deputado_id"]].append({"id": v["idVotacao"], "data": v["dataHoraVoto"][:10], "proposicao": titulo, "ementa": ementa,
                                                "descricao": plen[v["idVotacao"]], "voto": v["voto"]})

    props = defaultdict(set)
    for a in get_csv(f"proposicoesAutores/csv/proposicoesAutores-{ANO}.csv"):
        if a["idDeputadoAutor"]:
            props[a["idDeputadoAutor"]].add(a["idProposicao"])

    print("baixando cota parlamentar da Câmara", file=sys.stderr)
    gastos = defaultdict(list)
    z = zipfile.ZipFile(io.BytesIO(baixar(f"https://www.camara.leg.br/cotas/Ano-{ANO}.csv.zip")))
    for g in csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8-sig"), delimiter=";"):
        if g["ideCadastro"]:
            gastos[g["ideCadastro"]].append((g["datEmissao"][:10], g["txtDescricao"].strip(" .") or "Sem categoria informada", g["txtFornecedor"],
                                             float(g["vlrLiquido"] or 0), g["urlDocumento"]))

    print("baixando votos das pautas classificadas da Câmara", file=sys.stderr)
    votos_class = defaultdict(list)
    for id_vot, info in carregar_classificacao("Câmara").items():
        for v in get_json(f"{CAMARA_API}/votacoes/{id_vot}/votos")["dados"]:
            voto = {**info, "voto": v["tipoVoto"]}
            votos_class[str(v["deputado_"]["id"])].append({**voto, "bonus": bonus_minoria(voto) if voto["voto"] in VOTO_VALOR else 1})

    autobeneficio = defaultdict(list)
    for id_vot, pauta in AUTOBENEFICIO_CAMARA.items():
        for v in get_json(f"{CAMARA_API}/votacoes/{id_vot}/votos")["dados"]:
            autobeneficio[str(v["deputado_"]["id"])].append(
                {"pauta": pauta, "data": v["dataRegistroVoto"][:10], "voto": v["tipoVoto"]})

    # ponytail: suplentes que assumiram no meio do ano são comparados ao ano inteiro;
    # usar períodos de exercício (/deputados/{id}/historico) se isso distorcer demais.
    out = []
    for d in deps:
        i = str(d["id"])
        out.append({
            "id": i, "nome": d["nome"], "partido": d["siglaPartido"], "uf": d["siglaUf"],
            "foto": d["urlFoto"],
            "url": f"https://www.camara.leg.br/deputados/{i}",
            "presencas": len(presencas[i]), "sessoes": len(sessoes),
            "votos": votos[i], "votacoes": len(votacoes_nominais),
            "proposicoes": len(props[i]),
            "autobeneficio_sim": sum(a["voto"] == "Sim" for a in autobeneficio[i]),
            "autobeneficio_total": len(AUTOBENEFICIO_CAMARA),
            **posicao(votos_class[i]),
            "_det": {
                "votos_classificados": sorted(votos_class[i], key=lambda v: v["data"], reverse=True),
                "gastos": resumo_gastos(gastos[i]),
                "ultimas_votacoes": sorted(historico[i], key=lambda v: v["data"], reverse=True)[:ULTIMOS],
                "autobeneficio": autobeneficio[i],
            },
        })
    return out


def senadores():
    lista = get_json(f"{SENADO}/senador/lista/atual.json")["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]
    print("baixando votações do Senado", file=sys.stderr)
    votacoes = get_json(f"{SENADO}/votacao?dataInicio={ANO}-01-01&dataFim={ANO}-12-31")

    sessoes, presentes = defaultdict(set), defaultdict(set)
    total_vot, votos, historico = defaultdict(int), defaultdict(int), defaultdict(list)
    for v in votacoes:
        for x in v["votos"]:
            cod = str(x["codigoParlamentar"])
            historico[cod].append({"id": str(v["codigoSessaoVotacao"]), "data": v["dataSessao"], "proposicao": v.get("identificacao") or "",
                                   "ementa": v.get("ementa") or "", "descricao": v.get("descricaoVotacao") or "",
                                   "voto": x["descricaoVotoParlamentar"] or x["siglaVotoParlamentar"]})
            sessoes[cod].add(v["codigoSessao"])
            total_vot[cod] += 1
            if x["siglaVotoParlamentar"] in SEN_PRESENTE:
                presentes[cod].add(v["codigoSessao"])
            if x["siglaVotoParlamentar"] in SEN_VOTOU:
                votos[cod] += 1

    autobeneficio = defaultdict(list)
    for codigo, (dia, pauta) in AUTOBENEFICIO_SENADO.items():
        # o filtro por código é ignorado pela API; busca o dia e filtra aqui
        for v in get_json(f"{SENADO}/votacao?dataInicio={dia}&dataFim={dia}"):
            if str(v["codigoSessaoVotacao"]) == codigo:
                for x in v["votos"]:
                    autobeneficio[str(x["codigoParlamentar"])].append(
                        {"pauta": pauta, "data": dia, "voto": x["siglaVotoParlamentar"]})

    classif = carregar_classificacao("Senado")
    votos_class = defaultdict(list)
    for ano in sorted({c["data"][:4] for c in classif.values()}):
        for v in get_json(f"{SENADO}/votacao?dataInicio={ano}-01-01&dataFim={ano}-12-31"):
            info = classif.get(str(v["codigoSessaoVotacao"]))
            for x in v["votos"] if info else []:
                voto = {**info, "voto": x["siglaVotoParlamentar"]}
                votos_class[str(x["codigoParlamentar"])].append({**voto, "bonus": bonus_minoria(voto) if voto["voto"] in VOTO_VALOR else 1})

    print("baixando cota parlamentar do Senado", file=sys.stderr)
    gastos = defaultdict(list)  # chave: nome normalizado (o CSV do Senado não traz o código)
    linhas = io.StringIO(baixar(f"https://www.senado.leg.br/transparencia/LAI/verba/despesa_ceaps_{ANO}.csv").decode("latin-1"))
    next(linhas)  # "ULTIMA ATUALIZACAO"
    for g in csv.DictReader(linhas, delimiter=";"):
        d, m, a = g["DATA"].split("/") if g["DATA"].count("/") == 2 else ("01", g["MES"], g["ANO"])
        gastos[norm(g["SENADOR"])].append((f"{a}-{int(m):02d}-{int(d):02d}", g["TIPO_DESPESA"].strip(" .") or "Sem categoria informada",
                                           g["FORNECEDOR"], float(g["VALOR_REEMBOLSADO"].replace(".", "").replace(",", ".")), ""))

    out = []
    for p in lista:
        i = p["IdentificacaoParlamentar"]
        cod = i["CodigoParlamentar"]
        props = get_json(f"{SENADO}/processo?codigoParlamentarAutor={cod}&ano={ANO}")
        completo = set(norm(i["NomeCompletoParlamentar"]).split())
        nome_gasto = next((n for n in gastos if n == norm(i["NomeParlamentar"]) or set(n.split()) <= completo), None)
        out.append({
            "id": cod, "nome": i["NomeParlamentar"], "partido": i.get("SiglaPartidoParlamentar", ""),
            "uf": i.get("UfParlamentar", ""), "foto": i["UrlFotoParlamentar"].replace("http://", "https://"),
            "url": i["UrlPaginaParlamentar"],
            # ponytail: presença no Senado = estar presente em sessões com votação nominal;
            # o Senado não publica lista de presença por sessão em formato aberto.
            "presencas": len(presentes[cod]), "sessoes": len(sessoes[cod]),
            "votos": votos[cod], "votacoes": total_vot[cod],
            "proposicoes": len(props),
            "autobeneficio_sim": sum(a["voto"] == "Sim" for a in autobeneficio[cod]),
            "autobeneficio_total": len(AUTOBENEFICIO_SENADO),
            **posicao(votos_class[cod]),
            "_det": {
                "votos_classificados": sorted(votos_class[cod], key=lambda v: v["data"], reverse=True),
                "gastos": resumo_gastos(gastos.get(nome_gasto, [])),
                "ultimas_votacoes": sorted(historico[cod], key=lambda v: v["data"], reverse=True)[:ULTIMOS],
                "autobeneficio": autobeneficio[cod],
            },
        })
    return out


def pontuar(politicos):
    sem_dados = [p for p in politicos if not p["sessoes"] or not p["votacoes"]]
    ativos = [p for p in politicos if p["sessoes"] and p["votacoes"]]
    props = sorted(p["proposicoes"] for p in ativos)
    for p in ativos:
        p["taxa_presenca"] = p["presencas"] / p["sessoes"]
        p["taxa_votacoes"] = p["votos"] / p["votacoes"]
        # percentil: fração dos colegas de cargo com menos proposições (resiste a outliers)
        p["indice_proposicoes"] = bisect.bisect_left(props, p["proposicoes"]) / max(len(props) - 1, 1)
        p["penalidade"] = round(PENALIDADE_AUTOBENEFICIO * p["autobeneficio_sim"] / max(p["autobeneficio_total"], 1), 1)
        p["nota"] = round(max(0, 100 * (PESOS["presenca"] * p["taxa_presenca"]
                                        + PESOS["votacoes"] * p["taxa_votacoes"]
                                        + PESOS["proposicoes"] * p["indice_proposicoes"]) - p["penalidade"]), 1)
    ativos.sort(key=lambda p: -p["nota"])
    for pos, p in enumerate(ativos, 1):
        p["posicao"] = pos
    for p in sem_dados:
        p.update(taxa_presenca=None, taxa_votacoes=None, indice_proposicoes=None, penalidade=None, nota=None, posicao=None)
    return ativos + sem_dados


def escrever_pautas():
    """pautas.json: todas as votações candidatas com a classificação final, mais as de autobenefício."""
    cl = {(r["casa"], r["id"]): r for r in csv.DictReader(open(CLASSIFICACAO, encoding="utf-8"))}
    pautas = []
    for c in csv.DictReader(open(CANDIDATAS, encoding="utf-8")):
        r = cl[(c["casa"], c["id"])]
        url = (f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={c['id_proposicao']}" if c["casa"] == "Câmara"
               else f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{c['id_proposicao']}")
        pautas.append({k: c[k] for k in ("casa", "id", "data", "proposicao", "ementa", "descricao")}
                      | {"sim": int(c["sim"]), "nao": int(c["nao"]), **posicoes_pauta(r),
                         "origem": r["origem"], "justificativa": r["justificativa"], "url": url})
    auto = ([{"casa": "Câmara", "pauta": p, "url": f"{CAMARA_API}/votacoes/{i}"} for i, p in AUTOBENEFICIO_CAMARA.items()]
            + [{"casa": "Senado", "pauta": p, "data": d, "url": f"{SENADO}/votacao?dataInicio={d}&dataFim={d}"}
               for d, p in AUTOBENEFICIO_SENADO.values()])
    with open("pautas.json", "w", encoding="utf-8") as f:
        json.dump({"versao_metodologia": 3, "pautas": sorted(pautas, key=lambda p: p["data"], reverse=True), "autobeneficio": auto}, f, ensure_ascii=False)


def _teste():
    base = dict(sessoes=10, votacoes=10, autobeneficio_sim=0, autobeneficio_total=4)
    r = pontuar([dict(base, presencas=10, votos=10, proposicoes=50), dict(base, presencas=5, votos=5, proposicoes=0),
                 dict(base, presencas=10, votos=10, proposicoes=50, autobeneficio_sim=2),
                 dict(base, sessoes=0, votacoes=0, presencas=0, votos=0, proposicoes=0)])
    assert [p["nota"] for p in r] == [90.0, 80.0, 40.0, None], r  # empate em proposições = percentil 0.5
    assert r[0]["posicao"] == 1 and r[3]["posicao"] is None
    v = lambda p, q, voto="Sim", **kw: dict(ed_p=p, ed_q=q, aut_p=None, aut_q=None, voto=voto, **kw)
    moderados = [v(-4, 0)] * 5
    assert posicao(moderados)["ed"] == -2.5
    assert posicao(moderados)["posicao_nome"] == "Centro-esquerda"
    assert posicao([v(-10, -6)] * 5)["ed"] == -8.5
    assert posicao([v(10, 6)] * 5)["ed"] == 8.5
    assert posicao([v(-4, 0, "Não")] * 5)["ed"] == -1.5
    assert posicao([v(-4, 0, "Obstrução")] * 5)["ed"] == -1.5
    assert posicao(moderados[:4])["ed"] is None
    assert posicao([v(0, 0), v(None, None), v(-4, 0, "Abstenção")] * 5)["n_ed"] == 0
    # Intervalo limitado por dois cortes: meio −1, sem atingir as pontas.
    assert posicao([v(-4, 4)] * 3 + [v(0, -4)] * 3)["ed"] == -1
    # Dois intervalos ótimos separados: não escolher o corte 0, que viola ambos.
    assert posicao([v(-2, 2)] * 3 + [v(2, -2)] * 3)["ed"] == -0.5
    # Dois votos minoritários superam três majoritários no sentido oposto.
    maioria = [v(2, -2, sim=400, nao=10)] * 3
    minoria = [v(2, -2, "Não", sim=400, nao=10)] * 2
    assert posicao(maioria + [v(2, -2, "Não")] * 2)["ed"] == 0.5
    assert posicao(maioria + minoria)["ed"] == -0.5
    assert bonus_minoria(maioria[0]) == 1 and bonus_minoria(minoria[0]) == 2.9
    # Margem não ultrapassa alternativas muito próximas nem a escala.
    assert posicao([v(-2, -1.8)] * 5)["ed"] == -2
    assert posicao([v(10, 9.8)] * 5)["ed"] == 10
    aut = [dict(v(-4, 0), aut_p=8, aut_q=4)] * 5
    assert posicao(aut)["posicao_nome"] == "Centro-esquerda autoritária"
    assert [nome_ed(x) for x in (-7, -6.9, -4, -3.9, 0, 3.9, 4, 6.9, 7)] == [
        "Extrema-esquerda", "Esquerda", "Esquerda", "Centro-esquerda", "Centro-direita",
        "Centro-direita", "Direita", "Direita", "Extrema-direita"]
    assert [faixa(x) for x in (-10, -5.1, -5, -0.1, 0, 4.9, 5, 10)] == [0, 0, 1, 1, 2, 2, 3, 3]
    assert posicoes_pauta(dict(ed_p="", ed_q="", aut_p="0", aut_q="2"))["ed_p"] is None
    for p, q in (("nan", "0"), ("11", "0"), ("", "0")):
        try:
            posicoes_pauta(dict(ed_p=p, ed_q=q, aut_p="", aut_q=""))
        except ValueError:
            pass
        else:
            raise AssertionError((p, q))


if __name__ == "__main__":
    _teste()
    if not os.path.exists(CLASSIFICACAO):
        sys.exit("Classificação v3 pendente: gere metodologia/classificacao.csv antes do build.")
    cargos = {
        "Senador": pontuar(senadores()),
        "Deputado Federal": pontuar(deputados_federais()),
        # ponytail: deputados estaduais e vereadores não têm fonte oficial unificada;
        # adicionar uma função por casa (ex.: ALESP, Câmara de SP) quando escolher quais cobrir.
    }
    categorias = {c: defaultdict(float) for c in cargos}
    os.makedirs("detalhes", exist_ok=True)
    for cargo, ps in cargos.items():
        for p in ps:
            det = p.pop("_det")
            p["gasto_total"] = det["gastos"]["total"]
            for cat, v in det["gastos"]["categorias"]:
                categorias[cargo][cat] += v
            with open(f"detalhes/{norm(cargo).replace(' ', '-').lower()}-{p['id']}.json", "w", encoding="utf-8") as f:
                json.dump(det, f, ensure_ascii=False)
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({"ano": ANO, "pesos": PESOS, "penalidade_autobeneficio": PENALIDADE_AUTOBENEFICIO,
                   "min_votos_eixo": MIN_VOTOS_EIXO, "versao_metodologia": 3, "max_bonus_minoria": MAX_BONUS_MINORIA,
                   "categorias_gastos": {c: sorted(([k, round(v, 2)] for k, v in cs.items()), key=lambda x: -x[1])
                                         for c, cs in categorias.items()}, "gerado_em": datetime.now().isoformat(timespec="minutes"),
                   "cargos": cargos}, f, ensure_ascii=False)
    escrever_pautas()
    print({c: len(v) for c, v in cargos.items()}, file=sys.stderr)

