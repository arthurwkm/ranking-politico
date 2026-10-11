# Livro de regras (codebook) — classificação das votações

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
- "Aprovada/Rejeitada a Emenda do Senado nº X": Sim = acatar aquela emenda do Senado. Se não for possível saber o
  conteúdo da emenda, use 0 nos dois eixos.
- Senado, "Votação nominal do Projeto ...": Sim = aprovar o texto.

## Eixo econômico (`eco`): Estado × mercado

| Nota | Efeito do Sim |
|---|---|
| **−1** | Amplia claramente o papel do Estado na economia: cria ou expande gasto social, transferência de renda, tributação progressiva, estatal, controle de preços, regulação de mercado, direitos trabalhistas, piso salarial |
| **−0,5** | Mesmo sentido, com efeito pequeno, parcial ou setorial |
| **0** | Sem efeito econômico relevante, efeito misto/equilibrado, ou impossível determinar |
| **+0,5** | Sentido de mercado, efeito pequeno, parcial ou setorial |
| **+1** | Reduz claramente o papel do Estado: corta tributos ou gastos, privatiza, desregula, flexibiliza regras trabalhistas, abre o mercado, cria regra de ajuste fiscal |

Observações:
- Isenção ou benefício tributário **para um setor específico** é subsídio estatal direcionado, não liberalização
  geral: em regra, −0,5 ou 0. Redução ampla de carga tributária é +.
- Crédito orçamentário de rotina, acordo internacional técnico, indicação de autoridade e homenagem são 0.

## Eixo de autoridade (`aut`): poder do Estado sobre o indivíduo

| Nota | Efeito do Sim |
|---|---|
| **+1** | Amplia claramente o poder do Estado sobre o indivíduo: penas maiores, novos crimes, menos garantias processuais, mais vigilância ou coleta de dados, restrição de expressão, protesto, imprensa, associação, privacidade ou decisões sobre o próprio corpo, poder de polícia |
| **+0,5** | Mesmo sentido, com efeito pequeno ou restrito |
| **0** | Sem efeito sobre liberdades individuais, efeito misto ou indeterminado |
| **−0,5** | Sentido libertário, com efeito pequeno ou restrito |
| **−1** | Amplia claramente liberdades e garantias individuais: descriminaliza, reduz penas, reforça o devido processo, protege dados e privacidade, limita a vigilância ou o poder de polícia, amplia a liberdade de expressão |

Observações:
- Proteção de um grupo contra violência de terceiros (ex.: Lei Maria da Penha) normalmente usa o direito penal:
  é +0,5 ou +1 no eixo de autoridade, independentemente de quão justa a medida pareça. **Não confunda "bom" com
  "libertário".**
- Regras sobre armas: mais restrição ao porte/posse é +, flexibilização é −.
- Anistia, foro ou blindagem **de parlamentares** não é liberdade individual do cidadão: use 0 neste eixo
  (o tema já é tratado na lista de autobenefício).

## Formato da saída

CSV com cabeçalho `casa,id,eco,aut,justificativa`, uma linha por votação de `votacoes_candidatas.csv`,
na mesma ordem.

- `eco` e `aut` ∈ {-1, -0.5, 0, 0.5, 1}.
- `justificativa`: uma frase objetiva em português (máx. ~200 caracteres) descrevendo o efeito do texto que
  justifica as notas. Sem adjetivos de valor ("bom", "ruim", "absurdo").
- Se não tiver informação suficiente, use 0 e escreva "informação insuficiente: ..." na justificativa.

## Fontes permitidas

Ementa, ementa detalhada e palavras-chave do CSV, seu conhecimento sobre a proposição e as páginas oficiais
(camara.leg.br, senado.leg.br e as APIs de dados abertos). Não use opinião de imprensa para decidir a direção.
