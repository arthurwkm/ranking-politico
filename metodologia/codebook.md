# Livro de regras (codebook) v3 — posições absolutas

Objetivo: estimar a prática parlamentar pelo **conteúdo das alternativas votadas**, sem exigir equilíbrio entre esquerda e direita. Fundamentação e limites: [referências](referencias.md). A [v2](v2/codebook.md) e seus CSVs foram arquivados; as 335 votações ainda precisam de classificação v3.

## Unidade e regra central

Para cada votação, classifique em cada eixo **p**, o estado de coisas que o Sim aprova, e **q**, o status quo ou alternativa efetiva mantida pelo Não. Ambos em **−10..+10**. Não classifique o tamanho da mudança, nem faça `q = −p` automaticamente. Uma reforma entre duas alternativas de esquerda pode ter p e q negativos; uma proposta moderada pode substituir uma alternativa extrema.

Considere o efeito concreto do texto, **nunca o autor, partido, governo, orientação da bancada ou placar**. Trocar o autor não pode mudar a classificação. As posições partidárias nas referências não são alvos a reproduzir. PCO/PSTU são referências do extremo do survey histórico, não uma regra para atribuir posições a seus projetos ou afirmar sua representação atual.

- Projeto, substitutivo, subemenda substitutiva, PEC em turno, MP: Sim aprova exatamente o texto submetido.
- “Rejeitado”: Sim continua favorável ao texto; o resultado coletivo não inverte p e q.
- Emenda do Senado: identificar tanto o conteúdo da emenda como o texto que subsiste sem ela.
- Procedimento (ex.: quebra de interstício), homenagem, indicação, crédito de rotina ou acordo técnico sem efeito nos eixos: pares 0/0.
- Informação insuficiente sobre **qualquer uma das alternativas**: deixe **ambos os campos do eixo vazios**; justifique “informação insuficiente: ...”. Não presuma q=0. Não conhecer não equivale a centrismo.
- Eixo inaplicável: ambos vazios ou ambos 0. Alternativas iguais, mesmo não nulas, não identificam posição nesse eixo.

## Esquerda × direita (`ed`)

Bobbio orienta a dimensão igualdade/hierarquia. Economia, direitos e costumes, segurança, ambiente e terra compõem o eixo; explique a dimensão predominante. Estado/mercado é uma dimensão, não sinônimo universal de esquerda/direita. Os exemplos abaixo são **âncoras operacionais do projeto**, não notas atribuídas por Bobbio, Mudde ou pelos surveys a projetos reais.

| Posição da alternativa | Âncoras concretas |
|---|---|
| −10 a −7 | Ruptura econômica abrangente: abolição da propriedade privada dos meios de produção (−10); reforma agrária ampla por expropriação que reorganize estruturalmente a propriedade (−8). Desapropriação constitucional pontual não basta. |
| >−7 a −4 | Redistribuição estrutural dentro de economia plural: forte progressividade tributária, expansão universal de serviços; fim da escala 6×1 com proteção salarial (âncora −4, conforme texto e alcance). |
| >−4 a <0 | Reformas igualitárias graduais: igualdade civil LGBT/casamento igualitário (−3), ampliação parcial de direitos trabalhistas (−2), proteção ambiental e inclusão social incrementais. Direitos LGBT não são extrema-esquerda. |
| 0 | Alternativa substantivamente neutra/equilibrada neste eixo; não é o valor padrão do status quo. |
| >0 a <4 | Reformas graduais de mercado e conservadorismo limitado por direitos iguais: desregulação parcial, redução ampla mas limitada de tributos, privatização pontual (ex.: +3). |
| +4 a <7 | Reorganização ampla pró-mercado ou conservadora: privatização de vários setores, flexibilização trabalhista extensa, punitivismo abrangente. |
| +7 a +10 | Polo de mercado/hierarquia: vender todas as estatais (+8); abolir o casamento igualitário (+8); supressão abrangente de direitos civis LGBT (+9). Restrição parcial exige avaliar alcance, podendo ficar aquém do extremo. |

**Redução massiva de salários de políticos**, exemplo solicitado: tamanho do corte isolado não demonstra extrema-esquerda. Uma equiparação estrutural ao salário dos trabalhadores como parte de um programa de eliminação de privilégios pode ancorar −7; um corte orçamentário isolado pode ser neutro. Evite classificar indignação contra políticos como ideologia. Anistia, foro ou blindagem de parlamentares continuam 0/0, tratados no autobenefício; a nota de atuação permanece separada.

Subsídio tributário setorial não equivale a liberalização geral; avalie distribuição e alternativa. Reforma agrária legal, demarcação e proteção ambiental não são extremas por definição. Garantismo tende à esquerda e punitivismo à direita neste recorte, mas classifique o texto, não palavras-chave.

## Democracia, radicalidade e extremidade

Em Mudde, **extrema** rejeita a própria democracia; **radical** aceita democracia eleitoral, podendo rejeitar direitos de minorias, Estado de direito e separação de poderes. Não confundir as duas coisas. Aplicamos simetricamente o marcador institucional: supressão de eleições competitivas, pluralismo ou oposição em nome de igualdade revolucionária ou de hierarquia nacional/religiosa pode ancorar, respectivamente, ed −9/−10 ou +9/+10 e aut +9/+10. Autoritarismo sem conteúdo distributivo/cultural identificável não determina sozinho o sinal de ed: deixe esse eixo vazio.

O rótulo “extrema” **do site é uma faixa espacial**, que também inclui rupturas econômicas e de direitos; não certifica extremismo antidemocrático no sentido estrito de Mudde. Estatização, privatização ou salário parlamentar isoladamente não demonstram rejeição da democracia. Registre na justificativa quando houver ruptura institucional. Nenhum bônus partidário ou ajuste para igualar os dois lados é permitido.

## Autoridade (`aut`): − libertário / + autoritário

Classifique o regime de liberdade/coerção resultante em cada alternativa, independentemente de ed:

| Posição | Âncora operacional |
|---|---|
| −10 a <−5 | Limitações muito amplas ao poder coercitivo estatal, forte autonomia individual (ex.: −8). Não significa ausência de direitos ou de proteção pública. |
| −5 a <0 | Garantias de privacidade, expressão, devido processo e decisões sobre o corpo; descriminalização delimitada (ex.: −3). |
| 0 a <5 | Regulação coercitiva limitada, fiscalização e sanções com garantias (ex.: +2). Zero é neutro. |
| +5 a +10 | Restrição abrangente de direitos, vigilância e punitivismo fortes (+6); censura e repressão da oposição (+8); abolição de eleições competitivas/Estado de direito (+10). |

Criminalizar homofobia pode combinar ed negativo (igualdade) com aut positivo (poder penal). Criminalizar aborto pode combinar ambos positivos; não confunda “bom” com libertário. Políticas econômicas não pontuam automaticamente em autoridade.

## Saída e concordância

CSV: `casa,id,ed_p,ed_q,aut_p,aut_q,justificativa`, uma linha por candidata, na mesma ordem.

- Valores numéricos finitos em −10..+10, com ponto decimal; preferir inteiros quando a evidência não sustentar precisão maior.
- Justificativa curta em português (~200 caracteres), indicando efeito de Sim, alternativa de Não e dimensão; incluir fonte oficial quando precisar buscar além da candidata. Sem juízos de valor.
- Fontes: ementa, texto, ementa detalhada e palavras-chave do CSV, Câmara/Senado e suas APIs. Conhecimento prévio orienta busca, mas não substitui informação verificável sobre p e q. Não usar opinião de imprensa como critério.
- Duas classificações concordam no eixo se p tem mesmo sinal (−/0/+) e `|p_a−p_b|≤3` e `|q_a−q_b|≤3`: médias de p e q. Dois pares vazios permanecem vazios; vazio contra preenchido diverge, inclusive 0/0.
- Divergência requer desempate naquele eixo; sem resolução, par vazio, nunca zero inventado. O outro eixo mantém seu consenso. Kappa usa sinal de p apenas nos pares conhecidos; ausência não vira categoria zero.

## Estimativa parlamentar e faixas

Modelo unidimensional inspirado em Optimal Classification, **com alternativas fixadas pelo codebook**, não uma implementação do estimador original: cada par distinto define corte `m=(p+q)/2`. Sim exige o lado de p; Não/Obstrução, o lado de q. Abstenções e ausências não contam. Testamos −10..+10 em grade 0,1 e minimizamos o peso das violações. Indiferença exatamente no corte viola ambas as escolhas estritas, evitando um encaixe artificial de votos contraditórios.

Peso único: `bonus_minoria()` (maioria=1; minoria cresce até 3). Consensos entram; não se equilibram sinais nem se normaliza a posição pela magnitude/soma das pautas. Exigem-se ao menos 5 votos informativos por eixo.

Empate em intervalo ótimo: seu meio, arredondado à grade (equidistância favorece zero, depois esquerda). Se houver intervalos desconexos, escolher o mais largo, depois centro mais próximo de zero, depois esquerda; nunca usar um meio fora do conjunto ótimo. Se tocar −10/+10, usar o corte respeitado mais extremo menos/mais 0,5, limitado à alternativa apoiada e ao intervalo ótimo. Assim uma sequência de p=−4,q=0 resulta em −2,5, não −10. p=−10,q=−6 permite −8,5. Apoiar uma proposta extrema **permite**, mas não garante extremidade: depende da alternativa e dos demais votos.

Cortes de ed inspirados na transformação `2s−10` do survey, adaptados a seis faixas:

| Faixa | Intervalo |
|---|---|
| Extrema-esquerda | [−10, −7] |
| Esquerda | (−7, −4] |
| Centro-esquerda | (−4, 0) |
| Centro-direita | [0, 4) |
| Direita | [4, 7) |
| Extrema-direita | [7, 10] |

O centro próprio do estudo é absorvido nas faixas centrais; zero entra em centro-direita apenas para manter seis categorias. Autoridade mantém [−10,−5), [−5,0), [0,5), [5,10], por convenção, totalizando 24 subquadrantes. Nenhum estudo citado calibra essas quatro faixas de autoridade.

Limites: posições dependem da qualidade de p/q, agenda observada, coerência espacial e escolha de desempate; não medem convicção pessoal. Consistência com pautas moderadas não prova extremismo. Maioria/minoria é peso de evidência, não âncora de conteúdo. Só publicar resultados v3 depois da classificação e de um novo build; os JSONs v2 não são comparáveis diretamente.
