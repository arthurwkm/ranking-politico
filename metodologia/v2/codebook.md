# Livro de regras (codebook) v2 — classificação das votações

Objetivo: medir **a prática** de cada parlamentar pelos votos, não a convicção pessoal.
Cada votação de `votacoes_candidatas.csv` recebe uma nota em dois eixos, que descreve
**o efeito de votar "Sim"** naquela votação.

## Regra central

Classifique **o efeito concreto do texto** sobre a realidade, em relação à situação atual.
Nunca considere quem propôs, qual partido ou governo apoia, nem a repercussão na mídia.
Se você trocar o autor do projeto e sua classificação mudar, ela está errada.

## O que o "Sim" aprova

- "Aprovado o Projeto / Substitutivo / Subemenda Substitutiva / PEC (turno) / Medida Provisória": Sim = aprovar o texto.
- "Rejeitado(a) ...": o Sim continua sendo a favor do texto votado; foi a maioria que votou Não.
- "Aprovada/Rejeitada a Emenda do Senado nº X": Sim = acatar aquela emenda. Se não der para saber o conteúdo, use 0.
- Senado, "Votação nominal do Projeto ...": Sim = aprovar o texto.
- Requerimentos (ex.: quebra de interstício) são procedimentais: 0 nos dois eixos.

## Escala (os dois eixos)

| Nota | Intensidade |
|---|---|
| **±3** | Pauta **emblemática** da divisão: tema que define, no debate brasileiro, de que lado alguém está (ex.: aborto, armas, privatização ampla, reforma trabalhista ou previdenciária, marco temporal, criminalização de drogas, direitos LGBT, cotas raciais) |
| **±2** | Efeito claro e relevante na direção do eixo |
| **±1** | Efeito leve, parcial ou setorial |
| **0** | Sem efeito no eixo, efeito misto/equilibrado, ou impossível determinar |

Use ±3 com parcimônia: só quando o tema é central na divisão do eixo, não quando o projeto é apenas grande.

## Eixo esquerda × direita (`ed`): − esquerda / + direita

Combina as três dimensões que definem esquerda e direita no Brasil. Uma pauta pode tocar mais de uma;
dê a nota pelo efeito predominante.

| Dimensão | Esquerda (−) | Direita (+) |
|---|---|---|
| **Economia** | mais Estado: gasto social, transferência de renda, tributação progressiva, estatais, controle de preços, regulação, direitos trabalhistas, piso salarial | mais mercado: corte de tributos ou gastos, privatização, desregulação, flexibilização trabalhista, ajuste fiscal, abertura comercial |
| **Direitos e costumes** | amplia direitos de mulheres, população LGBT+, negros, indígenas e outras minorias; aborto legal; ações afirmativas; Estado laico; educação sexual/de gênero | preserva ou reforça valores tradicionais e religiosos; restringe aborto; restringe pautas de gênero/LGBT+; contra ações afirmativas; ensino domiciliar e "escola sem partido" |
| **Segurança e penal** | abordagem social e garantista; desencarceramento; controle de armas; controle da atividade policial | punitivismo: penas maiores, menos progressão, redução da maioridade penal; flexibilização de armas; ampliação de excludente de ilicitude |
| **Meio ambiente e terra** | proteção ambiental, demarcação indígena e quilombola, reforma agrária | flexibilização ambiental e de licenciamento, marco temporal, proteção reforçada da propriedade contra ocupações |

Observações:
- Benefício tributário **para um setor específico** é subsídio estatal direcionado, não liberalização geral:
  em regra −1 ou 0. Redução ampla de carga tributária é +.
- Crédito orçamentário de rotina, acordo internacional técnico, indicação de autoridade e homenagem são 0.
- Pautas consensuais sem conteúdo ideológico (ex.: campanha de conscientização sobre uma doença) são 0.

## Eixo de autoridade (`aut`): − libertário / + autoritário

Mede **o poder do Estado sobre o indivíduo**, independentemente de esquerda ou direita.

| Autoritário (+) | Libertário (−) |
|---|---|
| penas maiores, novos crimes, menos garantias processuais, mais vigilância ou coleta de dados, poder de polícia, censura ou restrição de expressão, protesto, imprensa, associação, privacidade ou decisões sobre o próprio corpo | descriminalização, redução de penas, reforço do devido processo, proteção de dados e privacidade, limite à vigilância e ao poder de polícia, ampliação da liberdade de expressão e das escolhas individuais |

Observações:
- Uma pauta pode pontuar nos dois eixos. Ex.: aumentar penas costuma ser `ed` + (punitivismo) **e** `aut` +.
  Criminalizar o aborto é `ed` + (costumes) **e** `aut` + (restringe decisão sobre o próprio corpo).
- Proteção de um grupo usando o direito penal (ex.: Lei Maria da Penha, criminalizar a homofobia) é
  `ed` − (direitos de minorias) **e** `aut` + (amplia o poder punitivo). **Não confunda "bom" com "libertário".**
- Anistia, foro ou blindagem **de parlamentares** não é liberdade do cidadão: use 0 nos dois eixos
  (o tema já é tratado na lista de autobenefício).

## Formato da saída

CSV com cabeçalho `casa,id,ed,aut,justificativa`, uma linha por votação de `votacoes_candidatas.csv`,
na mesma ordem.

- `ed` e `aut` ∈ {-3, -2, -1, 0, 1, 2, 3} (inteiros).
- `justificativa`: uma frase objetiva em português (máx. ~200 caracteres) descrevendo o efeito do texto
  e a dimensão usada (economia, costumes, segurança, meio ambiente). Sem adjetivos de valor ("bom", "ruim").
- Se não tiver informação suficiente, use 0 e escreva "informação insuficiente: ..." na justificativa.

## Fontes permitidas

Ementa, ementa detalhada e palavras-chave do CSV, seu conhecimento sobre a proposição e as páginas oficiais
(camara.leg.br, senado.leg.br e as APIs de dados abertos). Não use opinião de imprensa para decidir a direção.
