# dig.D Vídeo — marca

## Nome

**dig.D Vídeo.** Sempre `dig.D` (minúsculo, ponto, D maiúsculo) + `Vídeo` com acento.
No logo o "vídeo" aparece em minúsculo; em texto corrido é `dig.D Vídeo`.

Errado: `DigD Video`, `DIGD VÍDEO`, `dig.d video`, `Dig.D Vídeo`.

## O que é, em uma frase

Editor de vídeo curto: você sobe o vídeo, ele tira os silêncios, você escreve "corta" em cima
do trecho que sai, escolhe a legenda e aprova a versão final.

Tagline: **Você marca o que sai. Ele corta, legenda e espera o seu sim.**

## Por que é da dig.D e não é a dig.D

- **Da casa:** mesma paleta (azul, rosa, amarelo), mesmo ponto rosa da grafia `dig.D`, mesma
  fonte de corpo (DM Sans), mesmo fundo escuro que a tela já usa.
- **Próprio:** a agência ancorou no rosa sobre o fundo escuro. O dig.D Vídeo ancora no **azul**,
  que é a cor dele. Onde a agência tem a fita rosa, ele tem o `.D` com play.

## Logo

| Arquivo | Uso |
|---|---|
| `logo.svg` | Principal, empilhado. Capa, tela de boas-vindas, documento. Fundo claro. |
| `logo-negativo.svg` | O mesmo, sobre fundo escuro. |
| `logo-horizontal.svg` | Cabeçalho de README, barra do topo, rodapé. Fundo claro. |
| `logo-horizontal-negativo.svg` | O mesmo, sobre fundo escuro (é o da tela do editor). |
| `icone.svg` | Só o símbolo, de 24px pra cima: avatar, atalho, instalador. |
| `favicon.svg` | Aba do navegador (16 e 32px). Sem o ponto rosa, que some nesse tamanho. |

**O símbolo:** quadrado azul de canto arredondado; dentro, um `D` branco com um play vazado
e, à esquerda, o ponto rosa. Lê-se `.D ▶`: a assinatura da dig.D virando botão de tocar.

O wordmark é DM Sans convertida em curva, então o SVG abre certo sem a fonte instalada.

- Área livre em volta: metade da altura do ícone.
- Tamanho mínimo: ícone 16px (usar `favicon.svg`), logo horizontal 120px de largura.

## Paleta

| Cor | Hex | Onde manda |
|---|---|---|
| Azul | `#064794` | Cor do produto. Campo do ícone, botão primário, trecho selecionado na linha do tempo, link em fundo claro. |
| Rosa | `#EA2871` | A ação que decide: Aprovar, Renderizar, Aplicar o que marquei. Uma por tela. E o ponto do `.D`. |
| Amarelo | `#FFD413` | Agulha da linha do tempo, foco do teclado, badge de status ("Esperando o seu sim"). |
| Cosmic | `#0A1024` | Fundo da tela do editor. |
| Creme | `#F4F1E9` | Texto sobre o cosmic. |
| Tinta | `#15141B` | Texto sobre fundo claro e sobre amarelo. |

Nas peças de marca (README, capa, instalador) vale a proporção 60/30/10: azul, rosa, amarelo.
Na tela do editor quem ocupa área é o cosmic; as três cores entram como sinal, nessa ordem de peso.

Contrastes que definem as regras:

- Branco sobre azul: 9,0:1. É por isso que o botão comum é azul.
- Branco sobre rosa: 4,2:1. Só passa em texto grande (19px bold ou mais); botão rosa é grande.
- Azul sobre cosmic: 2,1:1. **Azul nunca é texto no escuro.** Link no escuro é creme sublinhado.
- Rosa em texto pequeno no escuro usa `#FF8FBA` (8,9:1), não `#EA2871`.

Variáveis prontas em `tokens.css`.

## Tipografia

| Função | Fonte | Pesos |
|---|---|---|
| Interface e títulos | DM Sans | 400, 500, 700, 800 |
| Timecode, duração, tamanho de arquivo | DM Mono | 400, 500 |

As duas são Google Fonts, licença OFL: baixa em fonts.google.com e instala, ou usa o
`@import` do `tokens.css`. A dig.D usa Anton nos posts; o dig.D Vídeo não usa. Ferramenta de
trabalho não grita.

## Tom de voz

Fala como quem está do lado, operando junto. A própria tela já faz isso e é a referência:

- "Aplicar o que marquei" — não "Processar edições"
- "Esperando o seu sim" — não "Pendente de aprovação"
- "A gente está preparando seu vídeo" — não "Processando… aguarde"
- "Nunca" como título de uma lista de travas — não "Restrições"

Regras:

- Verbo no botão, dizendo o que acontece: "Gerar capa", "Acrescentar faixa".
- Erro diz o que houve e o que fazer: "Não achei fala nesse vídeo. Confere se ele tem som e sobe de novo."
- "A gente" e "você". Nada de "o usuário".
- Número real ou nenhum número.

Palavras que não entram: revolucionar, transformar, mágica, incrível, poderoso, com um clique,
potencializar, IA que faz tudo.

## O que não fazer

- **Não** pôr o play branco sobre campo rosa ou vermelho. Vira cópia de plataforma de vídeo conhecida.
  O campo do ícone é sempre azul.
- **Não** trocar a cor do ponto. O ponto é rosa em qualquer fundo.
- **Não** usar o ícone azul sobre fundo `#064794` ou outro azul médio. No escuro, só sobre o cosmic.
- **Não** aplicar gradiente, sombra, brilho ou contorno no logo.
- **Não** escrever texto em amarelo sobre fundo claro.
- **Não** usar Anton, fonte manuscrita ou itálico no nome.
- **Não** inventar número de usuário, depoimento, parceria ou prêmio em nenhuma peça.
- **Não** tirar ou esconder o crédito do edvid. A interface nasceu do edvid (fillrochaa/edvid,
  MIT, © 2026 Creator Factory); a marca é da dig.D, o aviso de copyright fica no `LICENSE`.
