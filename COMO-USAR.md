# Como usar o dig.D Vídeo

O dig.D Vídeo pega um vídeo falado, tira os silêncios e deixa você marcar na linha do tempo o que
mais deve sair. Depois aplica legenda palavra por palavra, título, trilha e um cartão final, e só
considera o vídeo pronto quando você aprova.

Ainda não instalou? Comece pelo [INSTALAR.md](INSTALAR.md). Este guia supõe o servidor rodando e a
tela aberta em **http://127.0.0.1:8742/editor**.

---

## Antes de gravar

Ele foi feito pra um tipo de vídeo: **uma pessoa falando pra câmera, na vertical, gravado no
celular, em português** (o idioma muda com `VIDEOS_IDIOMA`). Vídeo sem fala, só com música, não
passa da primeira etapa: o corte se guia pela voz.

Formatos aceitos: `.mp4`, `.mov`, `.m4v`, `.webm`, `.mkv`, `.avi`, até **500 MB** (muda com
`VIDEOS_TAM_MAX_MB`). O resto está em [Limites](#limites).

---

## Do zero ao primeiro vídeo pronto

O caminho completo, na ordem. São 9 passos; os que não são obrigatórios estão marcados.

### 1. Mandar o vídeo

Na aba **Fila**, no quadro *Mandar um vídeo*, clique em **Escolher vídeo** e escolha o arquivo.

**Confira:** aparece *Enviando…* no alto da página enquanto o arquivo sobe (não tem barra de
progresso). Quando termina, o vídeo aparece na lista **Na fila**, com a pílula *Na fila* ou
*Montando*.

### 2. Esperar o corte

Não precisa fazer nada. O card vai mudando de frase sozinho (a tela confere a cada 4 segundos):

1. *lendo o que você falou* — a transcrição. Na **primeira vez** demora bem mais: ele baixa uns
   5 GB de modelos.
2. *a IA está escolhendo os cortes* — só se a IA de corte estiver ligada (ver
   [Opcionais](#o-que-é-opcional-e-como-fica-desligado)).
3. *montando o corte* — monta e renderiza o vídeo sem os silêncios.

Um vídeo de 27 s levou ~1,5 min nessa etapa numa máquina de 8 núcleos sem GPU.

**Confira:** o vídeo sai da lista *Na fila* e aparece embaixo, em **Escolher um vídeo para editar**,
com a duração antes e depois — por exemplo `0:27.00 → 0:22.50 · 17% fora`.

Se aparecer a pílula **Deu erro**, a mensagem está no card. Veja a
[solução de problemas](INSTALAR.md#solução-de-problemas).

### 3. Abrir no editor

No card do vídeo, clique em **Abrir no editor**.

**Confira:** a tela troca pra aba **O que cortar**. No topo aparece o nome do arquivo e a frase
*"Veja o corte e diga se pode seguir."*. Há um quadro com o resumo do corte e os botões
**Aprovar**, **Recusar** e **Baixar corte**. Embaixo, o player (*Seu vídeo*) e a linha do tempo
(*Suas marcações*), com as faixas MARCAÇÕES, VÍDEO e ÁUDIO.

### 4. Assistir o corte

Dê play (botão ou tecla **espaço**) e assista inteiro. É aqui que você decide se sai mais alguma
coisa. Leia o que o quadro diz: se a IA estiver ligada, ele resume o que ela propôs tirar.

### 5. Marcar o que mais sai *(opcional)*

Se tem uma frase repetida, um gaguejo, um trecho que você não quer:

1. Pare o vídeo no começo do trecho e aperte **M** (ou o botão **Marcar trecho**).
   Aparece *"Início marcado — avance até o fim do trecho e marque o fim"*.
2. Vá até o fim do trecho e aperte **M** de novo (o botão agora diz **Finalizar trecho**).
3. Abre uma caixinha. Escreva **corta** e clique **salvar marcação**.
4. Repita pra **todos** os trechos antes de salvar. Salvar de novo antes de aplicar substitui o
   que foi salvo antes: o primeiro lote se perde.
5. No topo, clique **Salvar ajustes**. Aparece *"✓ Salvo. Agora é só aplicar."*
6. **Recarregue a página (F5).** Pelo código, o botão **Aplicar o que marquei** só aparece depois
   de recarregar. Não conferi clicando; se o botão já estiver lá, siga.
7. Clique **Aplicar o que marquei** e confirme.

**Confira:** a tela volta pra **Fila** e o vídeo aparece com *aplicando o que você marcou*. Quando
termina, ele volta pro passo 3, com o corte novo esperando o seu sim.

Só a palavra do começo da nota importa, e só pedido de corte funciona. Detalhes em
[Edição por nota](#edição-por-nota).

### 6. Aprovar o corte

Clique **Aprovar** no quadro da aba *O que cortar*.

**Confira:** o quadro some e a frase do topo muda pra *"Corte aprovado. Escolha o estilo quando
quiser."*

### 7. Escolher o estilo

Clique na aba **Estilo**. De cima pra baixo:

1. **Tipo de edição** — deixe **Limpa** (a primeira). As outras duas são tela dividida e dependem
   do gerador de imagem.
2. **Estilo do título** — clique no card do visual que você quer. O último, *Nenhum*, é sem título.
3. **Estilo de legenda** — cada card mostra a legenda de verdade, animada. Clique no que quiser.
   Os estilos estão descritos em [Estilos de legenda](#estilos-de-legenda).
4. **Elementos da edição** — liga e desliga os efeitos (zoom, câmera no rosto, clarão).
5. No quadro **Texto da headline**: escreva o título (uma linha por linha, até três). Sem texto, o
   vídeo começa direto na fala. Ajuste tamanho do título, altura e tamanho da legenda.
6. **Cartão de fechamento** *(opcional)*: escreva a palavra que a pessoa deve digitar, ex. `QUERO`.
   Aparece uma prévia: *digita **QUERO** aqui embaixo 👇*. Vazio = sem cartão.
7. **Trilha sonora da biblioteca**: vem ligada. Escolha o clima em **Trilha**.

**Confira:** logo acima do botão **Aplicar e renderizar** aparece *Vídeo aberto: seu-arquivo.mp4* e
um resumo, por exemplo *"Legenda: Karaokê · tamanho 1.45. Headline: … Trilha: Acolhedora.
Fechamento: QUERO."* Leia: é exatamente o que vai ser renderizado.

### 8. Renderizar

Clique **Aplicar e renderizar**.

Não confunda com o botão lá embaixo, **Guardar escolhas avançadas**: ele só guarda as escolhas, não
gera vídeo nenhum.

**Confira:** a tela vai pra **Fila** e o card mostra *escrevendo as legendas*. É a parte demorada:
ele transcreve o corte de novo (pra legenda bater com a boca) e desenha tudo. Um vídeo de 22 s
levou ~3 min. Quando termina, a frase do topo vira *"O vídeo com legenda está pronto pra você
aprovar."*

### 9. Assistir, aprovar e baixar

Clique na aba **Prontos**. O vídeo está em **Esperando o seu sim**, com player.

1. Assista.
2. Clique **Aprovar** (ou **Recusar**, se quiser mudar o estilo — ver
   [portões](#os-dois-portões-de-aprovação)).
3. Clique **Baixar**.

**Confira:** o vídeo passa pra lista **Aprovados**, e o navegador baixa um arquivo chamado
`<nome-do-seu-vídeo>-legendado.mp4`, na vertical, 1080×1920.

Pronto. Postar é com você: o dig.D Vídeo não publica em rede social.

---

## As abas

| Aba | Pra quê | Quando usar |
|---|---|---|
| **Fila** | Mandar vídeo, ver o que está processando, abrir ou apagar um vídeo | Sempre começa aqui. Todo processamento aparece aqui |
| **O que cortar** | Assistir o corte, marcar o que mais sai, aprovar o corte | Depois que o corte fica pronto, e toda vez que você refaz o corte |
| **Estilo** | Escolher legenda, título, efeitos, trilha, cartão final; renderizar | Depois de aprovar o corte. Pode voltar quantas vezes quiser |
| **Visual** | Assistir o vídeo legendado dentro do editor, com a linha do tempo | Só liga depois do primeiro render |
| **Prontos** | Aprovar o vídeo final, baixar, ver todas as versões | Depois de renderizar |
| **Capas** | Gerar capa e colar 1 s na frente do vídeo | Só com gerador de imagem ligado |

Detalhes que valem saber:

- **Fila** tem duas listas: **Na fila** (esperando, processando ou com erro) e **Escolher um vídeo
  para editar** (os prontos). O botão **Apagar** fica nas duas; ele apaga o vídeo e **todas** as
  versões, depois de pedir confirmação, e fica desligado enquanto o vídeo processa.
- A fila roda **um vídeo por vez**. O segundo espera com *Esperando a vez*.
- **O que cortar** e **Visual** mostram o vídeo que você abriu. Pra trocar de vídeo, volte na Fila
  e clique **Abrir no editor** em outro. Se você tiver ajustes não salvos, ele pergunta antes.
- **Estilo** guarda as suas escolhas neste navegador, por vídeo. Voltar à aba mostra o que você
  escolheu da última vez.
- **Prontos** tem três listas: **Esperando o seu sim** (o portão final), **Aprovados**, e **Cortes
  e versões** — o corte sem legenda e cada estilo que você já renderizou, cada um com player e
  **Baixar**.
- **Visual** toca o vídeo legendado, mas a linha do tempo não mostra as faixas de legenda do render
  final. Pra assistir e decidir, use **Prontos**.

### Atalhos (nas abas O que cortar e Visual)

São os da janela **Ajuda** (botão *Ajuda* ou tecla **?**):

| Tecla / gesto | Faz |
|---|---|
| **espaço** | reproduz ou pausa |
| **←** **→** | um quadro pra trás/frente; com **shift**, 1 segundo |
| **M** | marca o início do trecho; de novo, o fim, e abre a nota |
| **Esc** | cancela um início marcado; fecha a Ajuda |
| **delete** | tira (ou devolve) o trecho de vídeo selecionado |
| arrastar a borda de um trecho | ajusta onde ele começa ou termina |
| clique duplo num trecho | desfaz o ajuste dele |
| pinça no trackpad / barra **Ampliar** | amplia a linha do tempo; **Ajustar** volta a caber na tela |

Na caixinha da nota: **Ctrl+Enter** (ou **Cmd+Enter**) salva, **Esc** fecha.

---

## Os dois portões de aprovação

Nada vira "pronto" sem você dizer sim duas vezes: uma pro **corte** (o que sai do vídeo) e uma pro
**final** (como ele ficou com legenda). Existem porque são decisões diferentes: corrigir o corte
depois de legendar joga o render fora, então vale acertar o corte primeiro.

### Portão 1: o corte

Aparece quando o corte fica pronto, e de novo toda vez que você aplica marcações. Fica em dois
lugares: no quadro da aba **O que cortar** (com o vídeo aberto) e no card do corte em **Prontos →
Cortes e versões**.

- **Aprovar:** o vídeo passa pra *"Corte aprovado. Escolha o estilo quando quiser."*
- **Recusar:** **nada muda no vídeo e nada é apagado.** Recusar também **não desfaz** o que a IA
  tirou: a sugestão dela já está aplicada no corte que você está vendo. Você cai na aba *O que
  cortar* pra marcar o que não gostou. O vídeo continua esperando o seu sim; o corte só muda quando você marca, salva e
  **Aplicar o que marquei**. Aí o portão aparece de novo com o corte novo.

O portão é pra você, não uma tranca: o botão **Aplicar e renderizar** não espera o sim do corte.
Se você renderizar antes de aprovar, o vídeo vai direto pro portão final.

### Portão 2: o final

Aparece em **Prontos → Esperando o seu sim** depois de cada render.

- **Aprovar:** o vídeo vai pra **Aprovados** (*"Aprovado e guardado."*). É uma marcação pra você
  saber o que está pronto pra postar; o arquivo continua baixável em qualquer lista.
- **Recusar:** você cai na aba **Estilo**. O vídeo volta pra *"Corte aprovado"*, e a versão
  recusada **não é apagada** — continua em *Cortes e versões*. Mude o que quiser e renderize de novo.

Aprovar também não tranca: renderizar outro estilo depois põe o vídeo de volta no portão final.

### Versões

- Renderizar um estilo de legenda **diferente** guarda uma versão nova; as antigas ficam.
- Renderizar o **mesmo** estilo de novo substitui a versão dele.
- **Aplicar o que marquei** (refazer o corte) **apaga todas as versões com legenda**, porque elas
  eram do corte antigo. A tela avisa e pede confirmação antes.

---

## Estilos de legenda

Os cards da aba Estilo não têm nome escrito: cada um mostra a legenda de verdade. A ordem é esta, e
o nome aparece no resumo acima do botão de render depois que você escolhe.

| # | Nome | Como é | Pra quê |
|---|---|---|---|
| 1 | **Karaokê** | até 3 palavras por vez, branca, grossa; cada palavra sobe e aparece no tempo da fala | o padrão; a mais legível no celular |
| 2 | **Empilhado** | linhas empilhadas alternando três tipos de letra (itálico grosso, fina pequena, serifada itálica), entrando com desfoque | vídeo mais "editado", de estética |
| 3 | **Disperso** | linhas soltas e deslocadas de 3 a 4 palavras; a palavra mais longa da frase (se tiver mais de 6 letras) ganha linha própria e fica maior | dar ênfase a uma palavra-chave |
| 4 | **Simples** | sem animação, sem serifa, até 3 palavras por vez | limpo, sem movimento |
| 5 | **Serifada** | sem animação, com serifa, até 3 palavras por vez | tom mais sóbrio ou editorial |
| 6 | **Clássica** | sem animação, letra menor, até duas linhas com a frase inteira | cara de legenda de filme; quando o texto importa mais que o efeito |
| 7 | *Nenhum* | — | o render **não aceita**: o botão fica desligado |

As três sem animação quebram linha pela largura do texto, não só pela contagem de palavras.

### O resto da aba Estilo

- **Estilo do título** — *Contorno*, *Cartão*, *Realce*, *Misto* ou *Nenhum*. O título aparece nos
  **primeiros 4 segundos**, e só se você escrever o texto em *Texto da headline*.
- **Elementos da edição:**
  - *Câmera acompanha a pessoa* — o enquadramento segue o rosto no terço de cima. Vem desligado.
  - *Aproximação automática* — o quadro avança devagar. Vem ligado.
  - *Aproxima e afasta nos cortes* — alterna o enquadramento a cada emenda. Vem ligado.
  - *Clarão na transição* — um flash começando dois quadros antes de cada corte. Vem desligado.
  - *Trilha sonora com IA* — **não faz nada neste pacote** (fica guardado, o render ignora).
- **Altura da legenda** — de *Padrão* até *Acima da cabeça*.
- **Tamanho da legenda** — *Padrão*, *Maior*, *Bem maior* (vem marcado; no celular legenda pequena
  some) e *Gigante*.
- **Cartão de fechamento** — ocupa os **últimos 3 segundos**. A palavra tem até 20 caracteres; os
  textos de antes e depois (padrão *digita* / *aqui embaixo*), até 30. Com cartão, a legenda some um
  pouco antes dele, pra não aparecer por trás.
- **Trilha** — seis climas: *Acolhedora*, *Com energia*, *Tensa*, *De chamada*, *Séria*,
  *Tecnológica*. São trilhas da Mixkit baixadas na instalação. Se a instalação pulou as trilhas, o
  vídeo sai sem música e sem erro.
- **Cor de destaque** e **Observações** — ficam guardadas, mas **o render não aplica**.

---

## Edição por nota

É o jeito de tirar pedaços do vídeo escrevendo em cima deles, sem precisar achar o quadro exato.

### Como funciona

1. Na aba **O que cortar**, marque um trecho com **M** (início) e **M** (fim).
2. Escreva a nota. Se a **primeira palavra** começa com um destes pedaços, é um pedido de corte:

   | Começo | Exemplos que funcionam |
   |---|---|
   | `cort` | corta, corte, cortar, *corts* (erro de digitação passa) |
   | `tir` | tira, tirar, tira isso |
   | `remov` | remove, remover |
   | `apag` | apaga, apagar |
   | `sai` | sai, sai isso |
   | `fora` | fora |

   Maiúscula e acento não importam.
3. **Salvar ajustes** e **Aplicar o que marquei**. O pedaço marcado sai do vídeo; se ele atravessa
   uma emenda, sai dos dois lados.

### O que dá

- Tirar vários trechos de uma vez: marque todos, salve uma vez, aplique uma vez.
- Tirar só um pedaço de uma frase: o corte é no tempo que você marcou, não na frase inteira.
- Junto com as notas, dá pra ajustar o corte à mão na faixa VÍDEO: arrastar a borda de um trecho,
  selecionar um trecho e apertar **delete** pra tirá-lo inteiro, ou clique duplo pra desfazer.

### O que não dá

- **Só corte funciona.** A caixinha sugere coisas como *"insere a marca do cliente"* ou *"abaixa a
  música"*, mas **nenhuma nota que não seja de corte faz nada** — e a tela **não avisa** que ignorou.
  Se você escreveu uma nota e nada mudou, é isso.
- **Frase de negação não funciona:** *"não corta"*, *"pode cortar aqui"*, *"quero tirar"* começam com
  outra palavra e são ignoradas. Comece pela palavra de corte.
- **Cuidado com o falso positivo:** o que importa é o começo da primeira palavra. *"Saiba mais"*,
  *"cortina"* ou *"fora de foco, mas deixa"* **cortam** o trecho.
- Nota não devolve o que já saiu. Pra recuperar um pedaço, o caminho é arrastar a borda do trecho
  pra fora na faixa VÍDEO (li isso no código; não testei).
- Se no mesmo salvamento você tirar um trecho inteiro com **delete** e também escrever notas, as
  notas podem cair alguns décimos de segundo fora do lugar. Faça uma coisa, aplique, depois a outra.
- Aplicar apaga as versões com legenda desse vídeo (a tela pede confirmação).

---

## O que é opcional e como fica desligado

Numa instalação nova, sem configurar nada, três coisas estão desligadas. **Não é defeito:** o resto
funciona igual.

### IA que sugere o corte

Liga sozinha se o **Claude Code** (`claude`) estiver instalado. Ela lê o que você falou e escolhe
tirar tomada repetida, gaguejo e frase abandonada. **O que ela escolhe já sai do corte** que você
vê no portão 1; o quadro da aba *O que cortar* resume o que ela fez. Se não gostar, recusar não
devolve a fala — puxe de volta arrastando a borda do trecho na faixa VÍDEO (li isso no código; não
testei). Se ela quiser tirar mais da metade das falas, o sistema descarta a escolha e avisa. Cada sugestão é
uma chamada ao Claude, na sua conta.

**Desligada, você vê:** no quadro da aba *O que cortar*, a frase *"A IA de corte está desligada
nesta instalação (Claude Code não encontrado). Tirei só os silêncios; marque você o que mais sai."*
O vídeo não passa pela etapa *a IA está escolhendo os cortes*.

**Atenção:** se o Claude Code está instalado mas não consegue responder (não logado, por exemplo),
o vídeo inteiro vai pra erro com *a IA não respondeu*. Como resolver está no
[INSTALAR.md](INSTALAR.md#vídeo-com-deu-erro).

### Gerador de imagem (capa e tela dividida)

As duas próximas funções usam o mesmo gerador de imagem, que você mesmo fornece. Sem ele, as duas
ficam desligadas.

#### Capa

Desenha uma capa com o seu rosto (um quadro do vídeo) no estilo de uma capa de referência, e cola
1 s dela na frente do vídeo. Precisa de um programa gerador de imagem seu, apontado em
`VIDEOS_GERADOR_IMAGEM` — contrato no [README](README.md#gerador-de-imagem-opcional).

**Desligada, você vê:** na aba **Capas**, o botão **Gerar capa** apagado e, embaixo dele, *"Capa e
arte de tela dividida estão desligadas: nenhum gerador de imagem configurado
(VIDEOS_GERADOR_IMAGEM). O resto do editor funciona normalmente."* As listas dizem *Nenhuma capa
ainda* e *Ainda não há referência*.

Com o gerador ligado: escreva a frase em até 4 linhas (a 1ª sai pequena, a 2ª grande, a 3ª é a
ponte, a 4ª vem grifada), escolha a família e **Gerar capa**. Cada capa pronta tem **Baixar**,
**Usar como referência** (vira o estilo das próximas), **Pôr 1s na frente do vídeo** e **Apagar**.
O vídeo com capa aparece em *Prontos* com a pílula *★ com a capa na frente*. Esse caminho não foi
testado com um gerador que não seja o da dig.D.

#### Tela dividida

Arte gerada em cima (ou embaixo) e o seu rosto na outra metade, em trechos que você escolhe. Usa o
mesmo gerador da capa, mais imagens de referência em `dados/referencias/arte/<família>/`.

**Desligada, você vê:** na aba **Estilo**, ao escolher *Tela dividida* ou *Tela dividida 2* em
*Tipo de edição*, aparece o quadro *Faixas de tela dividida* com o botão **Gerar novas artes e
salvar faixas** apagado e a mesma frase sobre o gerador. Se você renderizar assim, o vídeo sai
normal, em tela cheia.

Com o gerador ligado, cada faixa pede início e fim (em segundos do corte), o que desenhar e a
posição; e o quadro pede o **enquadramento medido** do rosto em JSON. Como medir está em
`exemplos/split.exemplo.json`.

---

## Limites

| | |
|---|---|
| **Formatos** | `.mp4`, `.mov`, `.m4v`, `.webm`, `.mkv`, `.avi` (pela extensão do arquivo) |
| **Tamanho** | 500 MB por vídeo (`VIDEOS_TAM_MAX_MB`) |
| **Idioma** | português (`VIDEOS_IDIOMA`) |
| **Saída** | MP4 vertical 1080×1920 |
| **Um por vez** | a fila processa um vídeo de cada vez, de propósito |
| **Tempo** | medido numa máquina de 8 núcleos sem GPU: vídeo de 27 s → ~1,5 min pro corte, ~3 min pro render com legenda. A tela diz "um vídeo de 1 minuto leva uns 2" pro corte; não verifiquei |
| **Primeira vez** | a primeira transcrição baixa ~5,3 GB de modelos e demora bem mais |
| **Teto por etapa** | 90 min. Passou disso, o vídeo vai pra erro |
| **Memória** | o render de 22 s usou ~6 GB de RAM |
| **Título** | até 3 linhas |
| **Cartão final** | palavra até 20 caracteres; últimos 3 s do vídeo |

Não verifiquei o que acontece com vídeo **horizontal**: o editor se adapta na tela, mas a saída é
vertical.

---

## Limitações conhecidas

- **Pausas de até 3 segundos ficam.** Na versão atual, o corte automático mantém a pausa entre uma
  fala e outra até 3 s, e encurta pra 3 s as que passam disso. O começo do vídeo, antes da primeira
  fala, também fica; o silêncio depois da última fala sai. (O card da Fila fala em cortar silêncio
  de 1,2 s pra cima — não é o que acontece hoje.) Pra tirar mais, use as notas de corte.
- **Uma fala curta que a IA mandou tirar pode continuar no vídeo**, se estiver entre pausas curtas.
  É exatamente o que o portão do corte está ali pra pegar: assista antes de aprovar, e se ela ficou,
  marque com **corta**.
- **Nota que não é corte é ignorada sem aviso** (ver [Edição por nota](#o-que-não-dá)).
- **Capa colada pode ficar velha.** Se você cola a capa e depois renderiza outro estilo ou refaz o
  corte, o card de *Prontos* continua tocando (e baixando) a versão com a capa antiga. Cole a capa
  de novo depois do último render.
- **Não há "tentar de novo".** Veja [Quando um vídeo dá erro](#quando-um-vídeo-dá-erro).
- **Salvar marcações duas vezes antes de aplicar perde o primeiro lote.** Marque tudo, salve uma
  vez, aplique.
- **O botão Aplicar o que marquei pode só aparecer depois de recarregar a página** (F5) — pela
  leitura do código; não conferi clicando.
- **O texto de um bloco pode perder as últimas palavras** na transcrição quando o alinhamento
  escorrega na borda. O corte é pelo áudio, então o vídeo não perde a fala.
- **Cor de destaque, Trilha sonora com IA e Observações** ficam guardadas mas não entram no render.

---

## Quando um vídeo dá erro

O card do vídeo mostra a pílula **Deu erro** e a última linha do que falhou. O que cada mensagem
quer dizer está na tabela do [INSTALAR.md](INSTALAR.md#vídeo-com-deu-erro).

A tela não tem botão de "tentar de novo". Depende de onde o erro aconteceu:

- **Na primeira etapa** (lendo o que você falou, IA, montando o corte): o vídeo fica na lista *Na
  fila* com o erro. Conserte a causa, clique **Apagar** e mande o arquivo de novo. Apagar leva o
  original junto — tenha o arquivo aí.
- **No render com legenda, na capa ou numa aplicação de marcações:** o vídeo também fica marcado
  com erro e **some** da lista *Escolher um vídeo para editar*, porque ela só mostra vídeo pronto.
  Pela tela, não há como abrir esse vídeo de novo nem renderizar outra vez. Na prática: apague e
  mande de novo. (Pela API ainda dá pra pedir outro render — `POST /api/videos/<id>/legendar` —,
  mas isso é pra quem quer mexer por linha de comando.)
- **"o serviço reiniciou no meio"**: o servidor caiu ou foi reiniciado com o vídeo processando.
  Mesma saída: apague e mande de novo.

---

## Onde ficam os arquivos

Tudo em `dados/videos/<id>/` — o original que você subiu, o corte, uma versão por estilo, a versão
com capa. A lista completa está no [README](README.md#onde-ficam-as-coisas). Nada é apagado sem você
apertar **Apagar**. Backup é copiar a pasta `dados/`.
