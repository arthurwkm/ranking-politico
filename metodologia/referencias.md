# Referências usadas no codebook v3

Consulta: 10/10/2026. Estudos de partidos orientam a escala; não classificam automaticamente propostas ou parlamentares.

- **Bobbio, Norberto. _Direita e esquerda_ (1994)**: a atitude perante a igualdade distingue esquerda/direita; liberdade/autoritarismo é outra dimensão. Fundamenta os dois eixos, não números para projetos. [Editora Wiley/Polity](https://www.wiley-vch.de/en?isbn=9780745615615&option=com_eshop&title=Left+and+Right&view=product); [edição inglesa, University of Chicago Press/BiblioVault](https://www.bibliovault.org/BV.book.epl?ISBN=9780226062464).
- **Mudde, Cas. Entrevista à E-International Relations**, sobre _The Far Right Today_ (2019): extrema-direita rejeita soberania popular/regra da maioria; direita radical aceita democracia eleitoral, mas rejeita elementos liberais (minorias, Estado de direito, separação de poderes). Portanto, radical não significa respeito integral ao Estado de direito. [Entrevista, fonte direta](https://www.e-ir.org/p/interview-cas-mudde); [entrevista à CEU, 2023](https://revdem.ceu.edu/2023/12/08/cas-mudde-interview/). Aplicar o critério institucional também à esquerda é uma opção simétrica deste projeto; uma posição econômica distante do centro não prova antidemocracia.

## Bolognesi, Ribeiro & Codato (2023)

[_Uma Nova Classificação Ideológica dos Partidos Políticos Brasileiros_, Dados 66(2), DOI 10.1590/dados.2023.66.2.303](https://www.scielo.br/j/dados/a/zzyM3gzHD4P45WWdytXjZWg/?lang=pt). Survey de especialistas de **2018**; médias da Tabela 1, escala **0–10**:

| Partido | Média | Partido | Média | Partido | Média |
|---|---:|---|---:|---|---:|
| PSTU | 0,51 | PCO | 0,61 | PCB | 0,91 |
| PSOL | 1,28 | PCdoB | 1,92 | PT | 2,97 |
| PDT | 3,92 | PSB | 4,05 | Rede | 4,77 |
| PPS | 4,92 | PV | 5,29 | PTB | 6,10 |
| Avante | 6,32 | SDD | 6,50 | PMN | 6,88 |
| PMB | 6,90 | PHS | 6,96 | MDB | 7,01 |
| PSD | 7,09 | PSDB | 7,11 | Podemos | 7,24 |
| PPL | 7,27 | PRTB | 7,45 | Pros | 7,47 |
| PRP | 7,59 | PRB | 7,78 | PR | 7,78 |
| PTC | 7,86 | DC | 8,11 | PSL | 8,11 |
| Novo | 8,13 | Progressistas | 8,20 | PSC | 8,33 |
| Patriota | 8,55 | DEM | 8,57 | | |

Faixas publicadas: extrema-esquerda 0–1,5; esquerda 1,51–3; centro-esquerda 3,01–4,49; centro 4,5–5,5; centro-direita 5,51–7; direita 7,01–8,5; extrema-direita 8,51–10. São posições históricas de siglas, não diagnósticos individuais nem estimativas atuais.

## Power & Zucco / Brazilian Legislative Surveys (BLS)

[_Estimating Ideology of Brazilian Legislative Parties, 1990–2005_ (2009), LARR 44(1), 218–246](https://www.cambridge.org/core/journals/latin-american-research-review/article/estimating-ideology-of-brazilian-legislative-parties-19902005-a-research-communication/1776C66E2346AA28D9EA33D0AB2797EE): mais de 850 parlamentares, escala **1 (esquerda)–10 (direita)**, reescalonamento para diferenças entre respondentes e períodos. [BLS, ondas 1–8, 1990–2017](https://doi.org/10.7910/DVN/ARYBJI). Não consegui verificar nesta consulta uma tabela numérica partidária diretamente no artigo/dataset (PDF e dataset não abriram), nem cortes categóricos próprios. Não transcrevo números de fontes secundárias como se fossem estimativas verificadas do BLS. Uso a referência para distinguir percepção partidária de conteúdo de uma votação.

## Decisão do projeto

A transformação `x = 2s − 10` inspira os cortes **±4 e ±7**. Para manter seis faixas e 24 subquadrantes, absorvemos o centro nas duas faixas centrais, divididas em zero; adotamos limites simétricos inclusivos em |x|=4 e 7. Isso **adapta**, não reproduz, as sete categorias do survey. Autoridade mantém cortes −5, 0, +5, uma convenção do projeto sem calibração numérica nesses estudos. Os exemplos e números de propostas no codebook são âncoras operacionais propostas aqui, não resultados dos surveys.
