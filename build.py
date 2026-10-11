"""Baixa dados oficiais (Câmara + Senado) e gera data.json para o site.

Uso: python3 build.py [ano]   (padrão: ano atual)
"""
import bisect, csv, http.client, io, json, os, sys, time, unicodedata, urllib.request, zipfile
from collections import defaultdict
from datetime import date, datetime

ANO = int(sys.argv[1]) if len(sys.argv) > 1 else date.today().year
# Critérios sem dado para alguém (ex.: o Senado não publica presença em comissões) saem da conta e os pesos restantes
# são reescalados para somar 100%.
PESOS = {"presenca": 0.35, "votacoes": 0.35, "comissoes": 0.1, "leis": 0.1, "relatorias": 0.1}
INICIO_LEGISLATURA = "2023-02-01"  # leis e relatorias contam a legislatura inteira (são raras demais num ano só)
TIPOS_PROJETO = {"PL", "PLS", "PLC", "PLP", "PLN", "PLV", "PEC", "PDL", "PDS", "MPV", "PRS", "PRC"}
CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2"
CAMARA_ARQ = "https://dadosabertos.camara.leg.br/arquivos"
SENADO = "https://legis.senado.leg.br/dadosabertos"
# Códigos de voto do Senado que indicam presença no plenário / voto registrado
SEN_VOTOU = {"Sim", "Não", "Abstenção", "Votou", "Presidente (art. 51 RISF)"}
SEN_PRESENTE = SEN_VOTOU | {"P-NRV", "Obstrução"}
csv.field_size_limit(10 ** 8)  # ementas longas nos CSVs de proposições
ULTIMOS = 15  # quantos gastos / votações recentes mostrar no detalhe

# Votações em que o parlamentar legisla em benefício próprio ou da classe política.
# Lista curada à mão (palavras-chave geram falsos positivos): só a votação principal
# de cada pauta, onde "Sim" = a favor do texto. Votar "Sim" desconta pontos da nota.
PENALIDADE_AUTOBENEFICIO = 20  # pontos descontados se votou "Sim" em todas
AUTOBENEFICIO_CAMARA = {  # idVotacao -> pauta
    "2352476-149": "PEC 9/2023 (1º turno) – anistia a partidos que descumpriram cotas de raça e gênero",
    "2352476-168": "PEC 9/2023 (2º turno) – anistia a partidos que descumpriram cotas de raça e gênero",
    "2387067-33": "PLP 192/2023 – reduz prazos de inelegibilidade da Lei da Ficha Limpa",
    "2270800-135": "PEC 3/2021 (1º turno) – PEC da Blindagem: exige aval do Congresso para processar parlamentares",
    "2270800-160": "PEC 3/2021 (2º turno) – PEC da Blindagem: exige aval do Congresso para processar parlamentares",
    "2565441-32": "PL 4822/2025 – limita multas e descontos do Fundo Partidário dos partidos",
}
AUTOBENEFICIO_SENADO = {  # codigoSessaoVotacao -> (data, pauta)
    "6873": ("2024-08-14", "PEC 9/2023 (1º turno) – anistia a partidos que descumpriram cotas de raça e gênero"),
    "6874": ("2024-08-14", "PEC 9/2023 (2º turno) – anistia a partidos que descumpriram cotas de raça e gênero"),
    "7007": ("2025-09-02", "PLP 192/2023 – reduz prazos de inelegibilidade da Lei da Ficha Limpa"),
}


# Posição política pelos votos (ver metodologia/codebook.md). Proposta, alternativa e parlamentares ficam em −10..+10.
CLASSIFICACAO = "metodologia/classificacao.csv"
CANDIDATAS = "metodologia/votacoes_candidatas.csv"
# Votar com a minoria vale mais: peso 1 com a maioria, crescendo até MAX_BONUS_MINORIA quando quase ninguém votou junto.
MAX_BONUS_MINORIA = 3
# Votações com >= 90% de votos iguais ficam fora: não diferenciam ninguém e, com os pesos equilibrados por sentido,
# os consensos de um lado só (ex.: as poucas pautas libertárias, aprovadas por 464 × 3) puxariam todos para lá.
LIMITE_CONSENSO = {"ed": 0.9, "aut": 0.9}
# Calibração da escala esquerda × direita: os votos dão a ORDEM; a posição absoluta vem da pesquisa com especialistas
# de Bolognesi, Ribeiro & Codato (2023, survey de 2018), convertida de 0..10 para −10..+10 (x = 2s − 10).
# Partidos atuais sem nota própria no survey: PL usa a do PSL (partido de Bolsonaro em 2018; decisão do usuário),
# União = média de DEM e PSL (fusão), PRD = média de PTB e Patriota (fusão), Republicanos = PRB, Cidadania = PPS.
ANCORAS_ED = {"PSOL": -7.44, "PCdoB": -6.16, "PT": -4.06, "PDT": -2.16, "PSB": -1.9, "REDE": -0.46, "Cidadania": -0.16,
              "PV": 0.58, "AVANTE": 2.64, "SOLIDARIEDADE": 3.0, "MDB": 4.02, "PSD": 4.18, "PSDB": 4.22, "PODE": 4.48,
              "PRD": 4.65, "REPUBLICANOS": 5.56, "PL": 6.22, "NOVO": 6.26, "PP": 6.4, "UNIÃO": 6.68}
MIN_VOTOS_EIXO = 5  # abaixo disso o eixo fica "dados insuficientes"
VOTO_VALOR = {"Sim": 1, "Não": -1, "Obstrução": -1}  # obstruir é tática para derrubar o texto
ED_NOMES = ("Esquerda", "Centro-esquerda", "Centro-direita", "Direita")
EXTREMO = 7  # a partir daqui, "Extrema-esquerda" / "Extrema-direita"
AUT_NOMES = ("libertária", "moderadamente libertária", "moderadamente autoritária", "autoritária")


def baixar(url, tentativas=8, accept="*/*"):
    """Baixa o corpo inteiro; se a conexão cair no meio, retoma do ponto de parada (Range)."""
    corpo, total = b"", None
    for t in range(tentativas):
        cab = {"Accept": accept, **({"Range": f"bytes={len(corpo)}-"} if corpo else {})}
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=600) as r:
                if corpo and r.status != 206:
                    corpo = b""  # servidor ignorou o Range: recomeça
                total = total or (int(r.headers["Content-Length"]) + len(corpo) if r.headers.get("Content-Length") else None)
                try:
                    corpo += r.read()
                except http.client.IncompleteRead as e:
                    corpo += e.partial
            if total is None or len(corpo) == total:
                return corpo
        except (OSError, http.client.HTTPException):
            if t == tentativas - 1:
                raise
        time.sleep(2 ** min(t, 4))
    raise http.client.IncompleteRead(corpo, total and total - len(corpo))


def get_json(url):
    return json.loads(baixar(url, accept="application/json"))


def get_csv(path):
    print("baixando", path, file=sys.stderr)
    return csv.DictReader(io.StringIO(baixar(f"{CAMARA_ARQ}/{path}").decode("utf-8-sig")), delimiter=";")


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper().strip()


# Marcador de democracia (Mudde, The Far Right Today): o que separa extrema de radical é a relação com a democracia.
# Anistiar/abrandar a punição de ataques à ordem democrática (8 de janeiro) recebe posição de extrema-direita no eixo
# esquerda × direita; os classificadores deixaram esse eixo vazio. A PEC da Blindagem não entra aqui: teve apoio de
# vários partidos e já é penalizada como autobenefício.
DEMOCRACIA = {  # (casa, id) -> (ed_p, ed_q, motivo)
    ("Câmara", "2358548-89"): (8, 0, "anistia a participantes dos atos de 8 de janeiro contra a ordem democrática"),
    ("Senado", "7041"): (8, 0, "reduz penas de condenados pelos atos de 8 de janeiro contra a ordem democrática"),
}


def classificacao_final(r):
    """Posições da pauta com o marcador de democracia aplicado, e a justificativa correspondente."""
    valores, just = posicoes_pauta(r), r["justificativa"]
    if (r["casa"], r["id"]) in DEMOCRACIA:
        p, q, motivo = DEMOCRACIA[(r["casa"], r["id"])]
        valores.update(ed_p=p, ed_q=q)
        just = f"{just} Marcador de democracia: {motivo}."
    return valores, just


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
    """Votações v3 com alternativas distintas, com pesos w_ed/w_aut (equilíbrio por sentido e corte de consenso)."""
    cand = {(r["casa"], r["id"]): r for r in csv.DictReader(open(CANDIDATAS, encoding="utf-8"))}
    out = {}
    for r in csv.DictReader(open(CLASSIFICACAO, encoding="utf-8")):
        valores, just = classificacao_final(r)
        if r["casa"] == casa and any(valores[e + "_p"] != valores[e + "_q"] for e in ("ed", "aut")):
            c = cand[(r["casa"], r["id"])]
            out[r["id"]] = {"data": c["data"], "proposicao": c["proposicao"], "descricao": c["descricao"],
                            **valores, "justificativa": just,
                            "sim": int(c["sim"]), "nao": int(c["nao"]), "pct_maioria": float(c["pct_maioria"])}
    for e in ("ed", "aut"):
        # d = p − q: quanto e para que lado o "Sim" move em relação ao status quo
        conta = [i for i in out.values() if i[e + "_p"] is not None and i[e + "_p"] != i[e + "_q"]
                 and i["pct_maioria"] < LIMITE_CONSENSO[e]]
        soma = {s: sum(abs(i[e + "_p"] - i[e + "_q"]) for i in conta if (i[e + "_p"] > i[e + "_q"]) == s) for s in (True, False)}
        for i in out.values():
            i["w_" + e] = 1 / soma[i[e + "_p"] > i[e + "_q"]] if i in conta else 0
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
    """Posição relativa pelos votos, Σ w·m·d·v / Σ w·m·|d|, em −10..+10 (antes da calibração).

    d = p − q da pauta; v = +1 Sim, −1 Não/Obstrução; m = bonus_minoria(); w equilibra os dois sentidos do eixo
    (quem vota "Sim" em tudo fica no centro) e é 0 nas pautas fora do cálculo (consenso no eixo esquerda × direita).
    """
    res = {}
    for e in ("ed", "aut"):
        vs = [((v[e + "_p"] - v[e + "_q"]) * v.get("w_" + e, 1) * bonus_minoria(v), VOTO_VALOR[v["voto"]])
              for v in votos if v[e + "_p"] is not None and v[e + "_p"] != v[e + "_q"] and v.get("w_" + e, 1)
              and v["voto"] in VOTO_VALOR]
        res[e] = round(10 * sum(d * x for d, x in vs) / sum(abs(d) for d, _ in vs), 1) if len(vs) >= MIN_VOTOS_EIXO else None
        res["n_" + e] = len(vs)
    return res


def nomear(p):
    p["posicao_nome"] = ("Dados insuficientes" if p["ed"] is None else nome_ed(p["ed"]) if p["aut"] is None
                         else f"{nome_ed(p['ed'])} {AUT_NOMES[faixa(p['aut'])]}")


def calibrar(politicos):
    """Leva a pontuação relativa de esquerda × direita à escala da pesquisa com especialistas.

    Pontos de apoio: (mediana da pontuação do partido, posição do partido em ANCORAS_ED), para partidos com >= 3
    parlamentares. As posições são ajustadas para crescer junto com a pontuação (regressão isotônica, peso = tamanho)
    e cada parlamentar é interpolado linearmente entre os pontos vizinhos; fora das pontas, segue a inclinação do
    último trecho. Preserva a ordem dada pelos votos; a pesquisa define só a escala.
    """
    por_partido = defaultdict(list)
    for p in politicos:
        if p["ed"] is not None and p["partido"] in ANCORAS_ED:
            por_partido[p["partido"]].append(p["ed"])
    pts = sorted((sorted(v)[len(v) // 2], ANCORAS_ED[k], len(v)) for k, v in por_partido.items() if len(v) >= 3)
    blocos = []  # regressão isotônica (pool adjacent violators): [soma s·w, soma x·w, peso]
    for s0, x, w in pts:
        blocos.append([s0 * w, x * w, w])
        while len(blocos) > 1 and blocos[-2][1] / blocos[-2][2] >= blocos[-1][1] / blocos[-1][2]:
            b = blocos.pop()
            blocos[-1] = [blocos[-1][i] + b[i] for i in range(3)]
    apoio = [(sw / w, xw / w) for sw, xw, w in blocos]

    def mapa(s0):
        if len(apoio) < 2:
            return s0
        i = max(1, min(len(apoio) - 1, next((k for k, (sk, _) in enumerate(apoio) if sk >= s0), len(apoio) - 1)))
        (s1, x1), (s2, x2) = apoio[i - 1], apoio[i]
        return x1 + (x2 - x1) * (s0 - s1) / (s2 - s1) if s2 != s1 else x1

    for p in politicos:
        p["ed_votos"] = p["ed"]
        if p["ed"] is not None:
            p["ed"] = round(max(-10, min(10, mapa(p["ed"]))), 1)
        nomear(p)
    return [[round(sk, 2), round(xk, 2)] for sk, xk in apoio]


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

    eventos = list(get_csv(f"eventos/csv/eventos-{ANO}.csv"))
    sessoes = {e["id"] for e in eventos
               if e["descricaoTipo"] == "Sessão Deliberativa"
               and e["localCamara.nome"] == "Plenário da Câmara dos Deputados"
               and e["situacao"].startswith("Encerrada")}
    reunioes = {e["id"]: e["dataHoraInicio"][:10] for e in eventos
                if e["descricaoTipo"] in ("Reunião Deliberativa", "Audiência Pública e Deliberação")
                and e["situacao"].startswith("Encerrada")}
    presencas, presencas_com = defaultdict(set), defaultdict(set)
    for p in get_csv(f"eventosPresencaDeputados/csv/eventosPresencaDeputados-{ANO}.csv"):
        if p["idEvento"] in sessoes:
            presencas[p["idDeputado"]].add(p["idEvento"])
        elif p["idEvento"] in reunioes:
            presencas_com[p["idDeputado"]].add(p["idEvento"])
    sessoes = set().union(*presencas.values())  # descarta sessões do Congresso sem lista de presença

    # Comissões: reuniões deliberativas dos órgãos em que o deputado era membro (titular ou cargo, não suplente) na data.
    com_lista = set().union(*presencas_com.values())  # só reuniões com lista de presença publicada
    reunioes_orgao = defaultdict(set)
    for x in get_csv(f"eventosOrgaos/csv/eventosOrgaos-{ANO}.csv"):
        if x["idEvento"] in com_lista:
            reunioes_orgao[x["idOrgao"]].add(x["idEvento"])
    devidas = defaultdict(set)
    for m in get_csv("orgaosDeputados/csv/orgaosDeputados-L57.csv"):
        if m["cargo"] != "Suplente":
            dep = m["uriDeputado"].rsplit("/", 1)[1]
            devidas[dep] |= {e for e in reunioes_orgao.get(m["uriOrgao"].rsplit("/", 1)[1], ())
                             if m["dataInicio"] <= reunioes[e] and (not m["dataFim"] or reunioes[e] <= m["dataFim"])}

    # Leis: proposições da legislatura que viraram norma jurídica, com o deputado como primeiro autor.
    # ponytail: relatoria = relator atual (último status) de proposições da legislatura; a Câmara não publica o
    # histórico de designações em arquivo aberto (só nas tramitações, uma chamada por proposição).
    normas, relatorias = {}, defaultdict(set)
    anos_leg = range(int(INICIO_LEGISLATURA[:4]), ANO + 1)
    for ano in anos_leg:
        for p in get_csv(f"proposicoes/csv/proposicoes-{ano}.csv"):
            if p["siglaTipo"] in TIPOS_PROJETO:
                if p["ultimoStatus_descricaoSituacao"] == "Transformado em Norma Jurídica":
                    normas[p["id"]] = {"proposicao": f"{p['siglaTipo']} {p['numero']}/{p['ano']}", "ementa": p["ementa"],
                                       "url": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={p['id']}"}
                if p["ultimoStatus_uriRelator"]:
                    relatorias[p["ultimoStatus_uriRelator"].rsplit("/", 1)[1]].add(p["id"])
    leis = defaultdict(list)
    for ano in anos_leg:
        for a in get_csv(f"proposicoesAutores/csv/proposicoesAutores-{ano}.csv"):
            if a["idProposicao"] in normas and a["ordemAssinatura"] == "1" and a["idDeputadoAutor"]:
                leis[a["idDeputadoAutor"]].append(normas[a["idProposicao"]])

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
            "presencas_comissao": len(presencas_com[i] & devidas[i]), "reunioes_comissao": len(devidas[i]),
            "leis": len(leis[i]), "relatorias": len(relatorias[i]),
            "autobeneficio_sim": sum(a["voto"] == "Sim" for a in autobeneficio[i]),
            "autobeneficio_total": len(AUTOBENEFICIO_CAMARA),
            **posicao(votos_class[i]),
            "_det": {
                "votos_classificados": sorted(votos_class[i], key=lambda v: v["data"], reverse=True),
                "gastos": resumo_gastos(gastos[i]),
                "ultimas_votacoes": sorted(historico[i], key=lambda v: v["data"], reverse=True)[:ULTIMOS],
                "autobeneficio": autobeneficio[i],
                "leis": leis[i],
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

    print("baixando relatorias do Senado", file=sys.stderr)
    relatorias = defaultdict(set)
    for ano in range(int(INICIO_LEGISLATURA[:4]), ANO + 1):
        for r in get_json(f"{SENADO}/processo/relatoria?dataInicio={ano}-01-01&dataFim={ano}-12-31"):
            if (r["descricaoTipoRelator"] == "Relator" and r["dataDesignacao"] >= INICIO_LEGISLATURA
                    and r["identificacaoProcesso"].split()[0] in TIPOS_PROJETO):
                relatorias[str(r["codigoParlamentar"])].add(r["idProcesso"])

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
        completo = set(norm(i["NomeCompletoParlamentar"]).split())
        # Leis: processos da legislatura que viraram norma jurídica, com o senador como primeiro autor.
        leis = [{"proposicao": x["identificacao"], "ementa": x.get("ementa") or "",
                 "url": f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{x['codigoMateria']}"}
                for x in get_json(f"{SENADO}/processo?codigoParlamentarAutor={cod}")
                if x["dataApresentacao"] >= INICIO_LEGISLATURA and x["identificacao"].split()[0] in TIPOS_PROJETO
                and (x.get("situacaoAtual") or "").startswith("TRANSFORMADA EM NORMA JURÍDICA")
                and norm(i["NomeParlamentar"]) in norm(x.get("autoria") or "").split(",")[0]]
        nome_gasto = next((n for n in gastos if n == norm(i["NomeParlamentar"]) or set(n.split()) <= completo), None)
        out.append({
            "id": cod, "nome": i["NomeParlamentar"], "partido": i.get("SiglaPartidoParlamentar", ""),
            "uf": i.get("UfParlamentar", ""), "foto": i["UrlFotoParlamentar"].replace("http://", "https://"),
            "url": i["UrlPaginaParlamentar"],
            # ponytail: presença no Senado = estar presente em sessões com votação nominal;
            # o Senado não publica lista de presença por sessão em formato aberto.
            "presencas": len(presentes[cod]), "sessoes": len(sessoes[cod]),
            "votos": votos[cod], "votacoes": total_vot[cod],
            # o Senado não publica presença por reunião de comissão em formato aberto (só atas em PDF)
            "presencas_comissao": None, "reunioes_comissao": None,
            "leis": len(leis), "relatorias": len(relatorias[cod]),
            "autobeneficio_sim": sum(a["voto"] == "Sim" for a in autobeneficio[cod]),
            "autobeneficio_total": len(AUTOBENEFICIO_SENADO),
            **posicao(votos_class[cod]),
            "_det": {
                "votos_classificados": sorted(votos_class[cod], key=lambda v: v["data"], reverse=True),
                "gastos": resumo_gastos(gastos.get(nome_gasto, [])),
                "ultimas_votacoes": sorted(historico[cod], key=lambda v: v["data"], reverse=True)[:ULTIMOS],
                "autobeneficio": autobeneficio[cod],
                "leis": leis,
            },
        })
    return out


def pontuar(politicos):
    sem_dados = [p for p in politicos if not p["sessoes"] or not p["votacoes"]]
    ativos = [p for p in politicos if p["sessoes"] and p["votacoes"]]
    # leis e relatorias: percentil entre os colegas de cargo (fração com menos; resiste a outliers como o presidente da casa)
    ordem = {k: sorted(p[k] for p in ativos) for k in ("leis", "relatorias")}
    for p in ativos:
        p["taxa_presenca"] = p["presencas"] / p["sessoes"]
        p["taxa_votacoes"] = p["votos"] / p["votacoes"]
        p["taxa_comissoes"] = p["presencas_comissao"] / p["reunioes_comissao"] if p["reunioes_comissao"] else None
        for k, o in ordem.items():
            p["indice_" + k] = bisect.bisect_left(o, p[k]) / max(len(o) - 1, 1)
        indices = {"presenca": p["taxa_presenca"], "votacoes": p["taxa_votacoes"], "comissoes": p["taxa_comissoes"],
                   "leis": p["indice_leis"], "relatorias": p["indice_relatorias"]}
        usados = {k: v for k, v in indices.items() if v is not None}
        p["penalidade"] = round(PENALIDADE_AUTOBENEFICIO * p["autobeneficio_sim"] / max(p["autobeneficio_total"], 1), 1)
        p["nota"] = round(max(0, 100 * sum(PESOS[k] * v for k, v in usados.items()) / sum(PESOS[k] for k in usados)
                              - p["penalidade"]), 1)
    ativos.sort(key=lambda p: -p["nota"])
    for pos, p in enumerate(ativos, 1):
        p["posicao"] = pos
    for p in sem_dados:
        p.update(taxa_presenca=None, taxa_votacoes=None, taxa_comissoes=None, indice_leis=None, indice_relatorias=None,
                 penalidade=None, nota=None, posicao=None)
    return ativos + sem_dados


def escrever_pautas():
    """pautas.json: todas as votações candidatas com a classificação final, mais as de autobenefício."""
    cl = {(r["casa"], r["id"]): r for r in csv.DictReader(open(CLASSIFICACAO, encoding="utf-8"))}
    pautas = []
    for c in csv.DictReader(open(CANDIDATAS, encoding="utf-8")):
        r = cl[(c["casa"], c["id"])]
        valores, just = classificacao_final(r)
        url = (f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={c['id_proposicao']}" if c["casa"] == "Câmara"
               else f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{c['id_proposicao']}")
        pautas.append({k: c[k] for k in ("casa", "id", "data", "proposicao", "ementa", "descricao")}
                      | {"sim": int(c["sim"]), "nao": int(c["nao"]), **valores,
                         "origem": "marcador de democracia" if (c["casa"], c["id"]) in DEMOCRACIA else r["origem"],
                         "justificativa": just, "url": url})
    auto = ([{"casa": "Câmara", "pauta": p, "url": f"{CAMARA_API}/votacoes/{i}"} for i, p in AUTOBENEFICIO_CAMARA.items()]
            + [{"casa": "Senado", "pauta": p, "data": d, "url": f"{SENADO}/votacao?dataInicio={d}&dataFim={d}"}
               for d, p in AUTOBENEFICIO_SENADO.values()])
    with open("pautas.json", "w", encoding="utf-8") as f:
        json.dump({"versao_metodologia": 3, "pautas": sorted(pautas, key=lambda p: p["data"], reverse=True), "autobeneficio": auto}, f, ensure_ascii=False)


def _teste():
    base = dict(sessoes=10, votacoes=10, autobeneficio_sim=0, autobeneficio_total=4,
                presencas_comissao=None, reunioes_comissao=None, leis=0, relatorias=0)
    r = pontuar([dict(base, presencas=10, votos=10, leis=3, relatorias=9), dict(base, presencas=5, votos=5, leis=1, relatorias=9),
                 dict(base, presencas=10, votos=10, autobeneficio_sim=2, relatorias=1),
                 dict(base, sessoes=0, votacoes=0, presencas=0, votos=0)])
    # sem comissões: pesos 35/35/10/10 de 90. Leis: percentis 1, 0,5, 0; relatorias: 0,5, 0,5, 0
    assert [p["nota"] for p in r] == [round(100 * (0.7 + 0.1 + 0.05) / 0.9, 1), round(100 * 0.7 / 0.9 - 10, 1),
                                     round(100 * (0.35 + 0.05 + 0.05) / 0.9, 1), None], r
    assert r[0]["posicao"] == 1 and r[3]["posicao"] is None and r[1]["indice_relatorias"] == 0
    c = pontuar([dict(base, presencas=10, votos=10, presencas_comissao=1, reunioes_comissao=4)])[0]
    assert c["taxa_comissoes"] == 0.25 and c["nota"] == round(100 * (0.7 + 0.025), 1), c
    v = lambda p, q, voto="Sim", **kw: dict(ed_p=p, ed_q=q, aut_p=None, aut_q=None, voto=voto, **kw)
    assert posicao([v(-4, 0)] * 5)["ed"] == -10 and posicao([v(-4, 0, "Não")] * 5)["ed"] == 10
    assert posicao([v(-4, 0)] * 4)["ed"] is None
    assert posicao([v(0, 0), v(None, None), v(-4, 0, "Abstenção")] * 5)["n_ed"] == 0
    # voto minoritário pesa mais: 1 contra a maioria (m≈2,9) vs 4 com a maioria no sentido oposto
    vm = [v(2, 0, sim=400, nao=10)] * 4 + [v(2, 0, "Não", sim=400, nao=10)]
    assert posicao(vm)["ed"] == round(10 * (4 - 2.9) / (4 + 2.9), 1)
    # pesos equilibrados: "Sim" em tudo = centro, mesmo com mais pautas de um lado
    tudo = [dict(v(2, 0), w_ed=1 / 6)] * 3 + [dict(v(-2, 0), w_ed=1 / 4)] * 2
    assert posicao(tudo)["ed"] == 0
    # calibração: mantém a ordem e leva as medianas dos partidos às âncoras
    ps = [{"partido": k, "ed": s0, "aut": None} for k, s0 in (("PT", -8), ("PSOL", -9), ("PL", 7), ("MDB", 1))] * 3
    calibrar(ps)
    assert ps[1]["ed"] < ps[0]["ed"] < ps[3]["ed"] < ps[2]["ed"], ps
    assert ps[2]["posicao_nome"] in ("Direita", "Extrema-direita"), ps
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
    }
    # ponytail: deputados estaduais e vereadores não têm fonte oficial unificada;
    # adicionar uma função por casa (ex.: ALESP, Câmara de SP) quando escolher quais cobrir.
    calibracao = {c: calibrar(ps) for c, ps in cargos.items()}
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
        json.dump({"ano": ANO, "pesos": PESOS, "inicio_legislatura": INICIO_LEGISLATURA, "penalidade_autobeneficio": PENALIDADE_AUTOBENEFICIO,
                   "min_votos_eixo": MIN_VOTOS_EIXO, "versao_metodologia": 3, "max_bonus_minoria": MAX_BONUS_MINORIA,
                   "limite_consenso": LIMITE_CONSENSO, "ancoras_ed": ANCORAS_ED, "calibracao": calibracao,
                   "categorias_gastos": {c: sorted(([k, round(v, 2)] for k, v in cs.items()), key=lambda x: -x[1])
                                         for c, cs in categorias.items()}, "gerado_em": datetime.now().isoformat(timespec="minutes"),
                   "cargos": cargos}, f, ensure_ascii=False)
    escrever_pautas()
    print({c: len(v) for c, v in cargos.items()}, file=sys.stderr)

