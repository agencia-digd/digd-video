<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="marca/logo-horizontal-negativo.svg">
    <img src="marca/logo-horizontal.svg" alt="dig.D Vídeo" height="64">
  </picture>
</p>

<h3 align="center">Você marca o que sai. Ele corta, legenda e espera o seu sim.</h3>

<p align="center">
  Editor de vídeo curto que roda no navegador: tira os silêncios sozinho, corta os trechos em que
  você escreveu "corta", aplica o estilo de legenda e só entrega depois que você aprova.
</p>

<p align="center">
  Feito pela <a href="https://digd.com.br">dig.D</a> · licença e créditos em <a href="LICENSE">LICENSE</a>
</p>

---

**Primeira vez aqui?**

- **[INSTALAR.md](INSTALAR.md)** — passo a passo da instalação, com como conferir cada passo,
  configuração campo a campo, o `VIDEOS_TOKEN` e solução de problemas.
- **[COMO-USAR.md](COMO-USAR.md)** — do upload ao vídeo legendado baixado, o que cada aba faz, os
  dois portões de aprovação, os estilos de legenda e a edição por nota.

---

## O que ele faz

Você sobe um vídeo falado (vertical, gravado no celular) e o dig.D Vídeo:

1. **Tira os silêncios.** Pausa curta de respiração fica; buraco de 1,2 s pra cima sai. O volume dos trechos baixos é emparelhado.
2. **Lê o que você falou** (WhisperX, roda na sua máquina, sem chave de API) e divide em blocos de fala.
3. **Sugere o que cortar** — tomada repetida, gaguejo, frase abandonada. *Opcional*: precisa do Claude Code instalado. A sugestão só vale depois que você aprova.
4. **Deixa você marcar na linha do tempo.** Selecione um trecho, escreva "corta" (ou "tira", "remove" — erro de digitação passa) e aperte *Aplicar o que marquei*.
5. **Aplica o estilo**: legenda palavra por palavra (6 estilos), título nos primeiros segundos, zoom nos cortes, clarão na emenda, trilha de fundo e um cartão final de chamada ("digita QUERO aqui embaixo 👇"). Tudo desenhado em vetor pelo Remotion, não queimado com ffmpeg.
6. **Espera o seu sim.** Nada vira "pronto" sem você aprovar o corte e depois o vídeo final.

Opcionais, se você plugar um gerador de imagem: **capa** do Reel no estilo de uma capa de referência, colada 1 s na frente do vídeo, e **tela dividida** com arte gerada em cima e o seu rosto embaixo.

## O que vem neste repositório e o que não vem

| | |
|---|---|
| **Vem** | A API (`api/`), a tela do editor (`api/editor-ui/`), o patch e os dois scripts que o dig.D Vídeo acrescenta ao edvid (`edvid-extras/`), os scripts de instalação e execução, a marca. |
| **Não vem: o edvid** | É o motor de corte, transcrição e render. É de terceiro — [fillrochaa/edvid](https://github.com/fillrochaa/edvid), licença MIT, © 2026 Creator Factory — e entra como **dependência**: o `scripts/instalar-edvid.sh` baixa do GitHub dele, no commit testado, e aplica o nosso patch por cima. |
| **Não vem: as trilhas** | São da [Mixkit](https://mixkit.co/license/#musicFree) (uso comercial livre, mas não pode redistribuir o MP3). O instalador baixa direto da Mixkit, na sua máquina. |
| **Não vem: publicar no Instagram** | A versão original publica o Reel direto no Instagram, mas isso depende de um app aprovado na Meta e de tokens da conta de quem opera. Fora desse contexto não funciona, e um token de rede social esquecido num servidor é risco. O dig.D Vídeo entrega o arquivo final pra baixar; você posta como quiser. |
| **Não vem: gerador de imagem** | Capa e tela dividida usam um gerador de imagem externo. Sem ele, essas duas funções ficam desligadas e a tela avisa — o resto funciona igual. Veja [Gerador de imagem](#gerador-de-imagem-opcional). |

## O que instalar antes

Testado em Linux (Ubuntu 24.04). Foi escrito pra rodar em macOS também, mas macOS e Windows não foram testados (veja [o que foi testado](#o-que-foi-testado-e-o-que-não-foi)).

| Programa | Pra quê | Como conferir |
|---|---|---|
| **ffmpeg** (com ffprobe) | Todo corte e render | `ffmpeg -version` |
| **Python 3.10 a 3.13** | A API e o WhisperX (o edvid não aceita 3.14) | `python3 -V` |
| **Node.js 18+** e npm | O Remotion, que desenha legenda e título | `node -v` |
| **git** | Baixar o edvid | `git --version` |
| **uv** (recomendado) | Instala o ambiente do edvid do jeito que o autor dele recomenda | `uv --version` — [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| Claude Code *(opcional)* | A IA que sugere o que cortar | `claude --version`, logado na sua conta |

No Ubuntu: `sudo apt install ffmpeg git python3-venv nodejs npm` (confira se o Node do seu apt é 18+; se não for, use o [nodesource](https://github.com/nodesource/distributions) ou o `nvm`).

**Espaço e memória, medidos:**

- Disco: ~2,4 GB do ambiente Python com WhisperX, ~510 MB do Remotion (pacotes + o Chrome headless que ele usa pra renderizar), e **~5,3 GB de modelos** que o WhisperX baixa na primeira transcrição (Whisper large-v3 + o modelo de alinhamento do português). Some os vídeos.
- Memória: durante o render de um vídeo de 22 s, o uso subiu ~6 GB. Uma máquina com 8 GB de RAM livre dá conta de um vídeo por vez — e a fila roda um de cada vez de propósito.
- Tempo, numa VPS de 8 núcleos sem GPU: transcrever e cortar um vídeo de 27 s levou ~1,5 min; o render com legenda levou ~3 min.

## Instalação

Resumo abaixo. O passo a passo com verificação e a solução de problemas estão no
[INSTALAR.md](INSTALAR.md).

```bash
# 1. Baixe este repositório e entre na pasta
git clone <endereço-deste-repositório> dig-d-video
cd dig-d-video

# 2. Ambiente Python da API (leve: FastAPI + Uvicorn)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. O edvid, o patch do dig.D Vídeo, as trilhas, o WhisperX e o Remotion
scripts/instalar-edvid.sh
```

O passo 3 é o demorado (baixa uns 3 GB). Ele pode ser rodado de novo sem estragar nada: o que já está feito é pulado. Ele faz, em ordem:

1. clona o edvid em `vendor/edvid` e fixa no commit `d8e6389` (o testado);
2. aplica `edvid-extras/patches/digd-video.patch` e copia `encode_social.py` e `pick_bed.py` pro `helpers/` do edvid;
3. baixa as 6 trilhas da Mixkit (`--sem-trilhas` pula; o vídeo sai sem música);
4. cria o ambiente Python do edvid com o WhisperX (`uv sync`, ou `venv` + `pip` se você não tem o uv);
5. roda `npm install` no template do Remotion e baixa o Chrome headless que ele usa pra renderizar (sem isso, cada render baixaria o navegador de novo).

Se o seu edvid já está instalado em outro lugar, aponte `VIDEOS_EDVID` pra ele antes de rodar o script — mas o patch precisa ser aplicado nele (o script faz isso).

## Configuração

Tudo é por variável de ambiente, e **nada é obrigatório** se você seguiu a instalação acima. Pra mudar algo, copie o exemplo:

```bash
cp .env.exemplo .env
```

| Variável | Padrão | O que é |
|---|---|---|
| `VIDEOS_HOST` / `VIDEOS_PORTA` | `127.0.0.1` / `8742` | Onde o servidor escuta |
| `VIDEOS_TOKEN` | *(vazio)* | Token de acesso. **Obrigatório se abrir pra rede** — veja [Segurança](#segurança) |
| `VIDEOS_RAIZ` | `./dados` | Onde ficam os vídeos e o estado de cada um |
| `VIDEOS_REFERENCIAS` | `$VIDEOS_RAIZ/referencias` | Capas de referência e famílias de arte |
| `VIDEOS_EDVID` | `./vendor/edvid` | Onde está o edvid |
| `VIDEOS_REMOTION` | `$VIDEOS_EDVID/assets/shortform` | Template do Remotion (com `node_modules`) |
| `VIDEOS_PYTHON` | `$VIDEOS_EDVID/.venv/bin/python` | O Python que tem o WhisperX |
| `VIDEOS_IDIOMA` | `pt` | Idioma da fala |
| `VIDEOS_TAM_MAX_MB` | `500` | Maior upload aceito |
| `VIDEOS_CLAUDE_BIN` | o `claude` do PATH | Claude Code, pra sugestão de corte. Sem ele, a sugestão fica desligada |
| `VIDEOS_IA_MODELO` | `claude-sonnet-5` | Modelo que o Claude Code usa pra sugerir |
| `VIDEOS_GERADOR_IMAGEM` | *(vazio)* | Script gerador de imagem. Sem ele, capa e arte ficam desligadas |
| `VIDEOS_ASSINATURA_CAPA` | *(vazio)* | Assinatura pequena na capa, ex. `@seuperfil` |
| `VIDEOS_ORIGENS` | *(vazio)* | Só se um painel seu, em outro domínio, chamar a API |
| `VIDEOS_VOLTAR_URL` | *(vazio)* | Mostra um link "←" no topo do editor, pro seu painel |

## Rodando

```bash
scripts/rodar.sh
```

Abra **http://127.0.0.1:8742/editor**. Suba um vídeo na aba *Fila* e acompanhe: ele passa por "lendo o que você falou", "montando o corte" e para em *O que cortar*, esperando você aprovar.

Pra deixar rodando como serviço no Linux, um `systemd` simples basta:

```ini
# /etc/systemd/system/dig-d-video.service
[Unit]
Description=dig.D Vídeo
After=network-online.target

[Service]
WorkingDirectory=/caminho/para/dig-d-video
ExecStart=/caminho/para/dig-d-video/scripts/rodar.sh
Restart=on-failure
User=seu-usuario
# ffmpeg e render comem CPU inteira; nice alto deixa o resto da máquina respirar.
Nice=10

[Install]
WantedBy=multi-user.target
```

## Segurança

- Por padrão o servidor escuta **só em 127.0.0.1** — só a própria máquina acessa.
- Pra acessar de outro computador, defina `VIDEOS_TOKEN` e `VIDEOS_HOST=0.0.0.0`. O `rodar.sh` **recusa** subir aberto na rede sem token. Com token, toda rota exige: abra uma vez `http://SEU_HOST:8742/entrar?token=SEU_TOKEN` no navegador e ele vira um cookie que dura 30 dias. Pra chamar a API por script: cabeçalho `Authorization: Bearer SEU_TOKEN`.
- Gere o token com `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` e guarde só no `.env` (que o `.gitignore` já ignora).
- Na internet aberta, ponha atrás de HTTPS (Caddy, nginx, Cloudflare Tunnel). Em HTTP, o token trafega sem criptografia.
- O `/api/saude` responde sem token, de propósito (monitoramento). Ele não expõe vídeo nenhum.

## Gerador de imagem (opcional)

Capa e arte da tela dividida chamam um programa seu, apontado em `VIDEOS_GERADOR_IMAGEM`. O contrato é:

```
seu-gerador "<prompt em texto>" <arquivo-de-saida.png> [imagem-de-referencia ...]
```

- Recebe o prompt, o caminho do PNG a escrever e zero ou mais imagens de referência (pra capa: um quadro do vídeo com o rosto + a capa de referência do estilo; pra arte: as imagens da família escolhida).
- Tem que sair com código 0 **e** deixar o PNG escrito. Qualquer outra coisa vira erro legível na Fila.
- Precisa ser executável (`chmod +x`).

Um wrapper de 20 linhas em cima de qualquer API de imagem que aceite referência (OpenAI, Google, Replicate…) resolve. Este repositório não traz um, porque todo gerador bom pede chave paga — e chave não entra em repositório.

As **referências de estilo** ficam em `dados/referencias/`:

- Capa: `dados/referencias/<familia>.png` — uma capa aprovada por família. A própria tela cria: em *Capas*, "Usar como referência".
- Arte: `dados/referencias/arte/<familia>/*.png` — algumas imagens da mesma série. Crie a pasta e ponha as imagens.
- `exemplos/split.exemplo.json` mostra o formato do plano da tela dividida, com a explicação de como medir o enquadramento do rosto.

## IA que sugere o corte (opcional)

Se o `claude` (Claude Code) estiver instalado e logado, depois da transcrição ele lê os blocos de fala e sugere quais tirar — com o motivo de cada um, mostrado na tela. Ele só **propõe**: nada sai sem você aprovar, e se ele quiser tirar mais da metade das falas a sugestão é descartada por desconfiança. Sem o Claude Code, o passo não falha: a tela diz que a IA está desligada e o corte de silêncio segue normal.

Cada sugestão é uma chamada ao Claude, na sua conta.

## Onde ficam as coisas

```
dados/videos/<id>/
  entrada.mp4          o que você subiu (nunca é apagado sozinho)
  corte.mp4            sem os silêncios (e sem o que você marcou)
  final-<estilo>.mp4   um por estilo de legenda renderizado
  final-com-capa.mp4   com a capa 1 s na frente
  estado.json          em que etapa está
  falas.json, edl.json transcrição em blocos e a lista de cortes
```

Nada é apagado sem você apertar *Apagar*. Backup é copiar a pasta `dados/`.

## Limitações conhecidas

- **Legenda atrás do cartão final.** Se a fala vai até o último segundo, a última linha da legenda karaokê pode aparecer por trás do cartão de fechamento. O cartão foi pensado pra vídeos que terminam com a chamada antes dele. Contorno: deixe o cartão vazio nesses vídeos, ou termine de falar uns 3 s antes do fim.
- **O texto de um bloco pode perder as últimas palavras** na aba de edição por texto quando o alinhamento do WhisperX escorrega na borda. O corte é pelo áudio, então o vídeo não perde a fala — só a transcrição mostrada.
- **Aba Visual** mostra a linha do tempo do corte, mas não as faixas de legenda do render final (a pasta de trabalho do Remotion é apagada depois de cada render pra economizar ~300 MB por vídeo). O vídeo final se assiste em *Prontos*.
- **Cor personalizada, música com IA e observações** da aba Estilo ficam guardadas, mas o render não as aplica.
- **Um vídeo por vez.** De propósito: corte e render comem a CPU inteira.

## O que foi testado e o que não foi

Testado de verdade, numa instalação limpa desta pasta (Ubuntu 24.04, Python 3.12, Node 20, ffmpeg do apt), com um vídeo de 27 s com três falas em português separadas por silêncio:

- `scripts/instalar-edvid.sh`: clone do edvid no commit fixado, patch aplicado (o resultado é idêntico, byte a byte, ao edvid modificado que roda em produção, exceto dois comentários), helpers copiados, as 6 trilhas baixadas da Mixkit, `npm install` do Remotion e o Chrome headless dele (conferido que a cópia de trabalho do render enxerga o navegador sem baixar de novo). Rodado três vezes: as seguintes pulam o que já está feito.
- `pip install -r requirements.txt` num venv novo.
- `scripts/rodar.sh`, com token: sem token → 401; token errado → 401; `/entrar?token=` grava o cookie; com cookie ou `Authorization: Bearer` → 200.
- Upload → transcrição → blocos de fala → corte (27 s → 22,5 s).
- IA desligada: o fluxo segue, a tela recebe o aviso. IA ligada (`sugerir.py` com o Claude Code): sugeriu tirar só a tomada abortada.
- Render da Fase 2: legenda karaokê, título, trilha (conferida no áudio), clarão, zoom e cartão final — conferidos olhando os quadros.
- Aprovação do corte e do final; nota "corts essa parte" na linha do tempo → a fala saiu (22,5 s → 16 s); nota que não é corte é ignorada.
- Colar a capa 1 s na frente (com uma imagem de teste) → vídeo 1 s mais longo. Apagar o vídeo.
- Capa e arte sem gerador → a API responde 503 com a mensagem, e a tela desliga os dois botões.
- Editor em `http://` sem HTTPS: o cookie do vídeo aberto é gravado (em HTTPS ele vira `SameSite=None; Secure`, pra funcionar embutido em outro domínio).

**Não testado:**

- **A instalação do WhisperX pelo script.** No teste, usei um ambiente Python com WhisperX que já existia na máquina (`VIDEOS_PYTHON`) em vez de baixar 2,4 GB de novo. O passo 4 do instalador (`uv sync` / `pip install -e`) não foi executado.
- **O download dos modelos** do WhisperX na primeira transcrição (já estavam em cache).
- **Geração de capa e de arte com um gerador de imagem real.** Só o caminho "gerador desligado" foi testado. O caminho ligado é o mesmo código que roda em produção, mas não com um gerador que não seja o da dig.D.
- **macOS e Windows.** O `rodar.sh` e o instalador são bash; no Windows, só via WSL (não testado).
- **Clicar na tela.** A tela foi aberta num Chrome headless (abas Fila e Capas): o logo aparece, o aviso de gerador desligado aparece no lugar certo e os dois botões ficam desabilitados. As rotas que a tela chama foram testadas uma a uma (estado, forma de onda, miniaturas, vídeo com Range, salvar, aplicar). Mas ninguém arrastou a agulha, marcou um trecho com o mouse ou subiu um vídeo pelo botão — isso foi feito pela API, não pela tela.
- Rodar atrás de um proxy HTTPS.

## Créditos e licença

- **dig.D Vídeo** — © 2026 Daniela Okada, licença MIT. Veja [`LICENSE`](LICENSE).
- **edvid** — © 2026 Creator Factory ([fillrochaa/edvid](https://github.com/fillrochaa/edvid)), licença MIT. É uma dependência instalada à parte. A tela do editor (`api/editor-ui/`) nasceu do app de pré-visualização do edvid e foi modificada; o aviso original está em [`api/editor-ui/LICENSE-edvid`](api/editor-ui/LICENSE-edvid). O patch em `edvid-extras/` modifica arquivos do edvid, sob a mesma licença.
- **Trilhas** — [Mixkit](https://mixkit.co), Mixkit Stock Music Free License, baixadas na instalação. Créditos de cada faixa em `edvid-extras/music/catalog.json`.
- **Marca** — logo, ícone e cores em [`marca/`](marca/BRAND.md).
