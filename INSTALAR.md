# Instalar o dig.D Vídeo

Passo a passo, do repositório clonado até a tela aberta no navegador. Cada passo termina com um jeito
de conferir que deu certo. Depois de instalar, siga pro [COMO-USAR.md](COMO-USAR.md).

**Onde foi testado:** Linux, Ubuntu 24.04, Python 3.12, Node 20, ffmpeg do apt. macOS e Windows
**não foram testados**; os scripts são bash, então no Windows só via WSL (também não testado).

**O que não foi testado, e é o tropeço mais provável:** a instalação do WhisperX pelo
`scripts/instalar-edvid.sh`. No teste de instalação limpa, a dig.D apontou um Python com WhisperX
que já existia na máquina em vez de baixar tudo de novo — o passo 4 do instalador (`uv sync` ou
`pip install`) **nunca foi executado de ponta a ponta**. Também não foi testado o download dos
modelos na primeira transcrição (já estavam em cache). Se algo quebrar, é provável que seja aí; veja
[Solução de problemas](#solução-de-problemas).

---

## Pré-requisitos

| Programa | Versão | Pra quê | Como conferir |
|---|---|---|---|
| **ffmpeg** e **ffprobe** | a do apt do Ubuntu 24.04 foi a testada; versão mínima não verificada | todo corte e render | `ffmpeg -version` e `ffprobe -version` |
| **Python** | **3.10 a 3.13** (o edvid não aceita 3.14) | a API e o WhisperX | `python3 -V` |
| **Node.js** e **npm** | **18 ou mais novo** (o instalador recusa menos) | o Remotion, que desenha legenda e título | `node -v` e `npm -v` |
| **git** | qualquer recente | baixar o edvid | `git --version` |
| **uv** | recomendado, versão não fixada | instala o ambiente do WhisperX com as versões travadas no `uv.lock` do edvid | `uv --version` — [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| **WhisperX** | vem pelo instalador: **3.8.6**, com torch **2.8.0**, se instalado com `uv` | transcrição local, sem chave de API | depois do passo 3 |
| Claude Code *(opcional)* | — | IA que sugere o corte | `claude --version`, logado |

No Ubuntu:

```bash
sudo apt install ffmpeg git python3-venv nodejs npm
```

Confira se o Node do apt é 18+ (`node -v`). Se não for, instale por
[nodesource](https://github.com/nodesource/distributions) ou `nvm`.

**Espaço e memória** (medidos pela dig.D): ~2,4 GB do ambiente Python com WhisperX, ~510 MB do
Remotion com o Chrome headless, ~5,3 GB de modelos baixados na primeira transcrição, mais os vídeos.
O render de um vídeo de 22 s usou ~6 GB de RAM; 8 GB livres dão conta de um vídeo por vez.

**Internet:** necessária na instalação (GitHub, npm, PyPI, Mixkit) e na **primeira transcrição**
(os modelos do WhisperX vêm do Hugging Face). Pra português não precisa de token do Hugging Face.

---

## 1. Baixar o repositório

```bash
git clone https://github.com/agencia-digd/digd-video.git
cd digd-video
```

**Confira:** `ls` mostra `api/`, `edvid-extras/`, `scripts/`, `README.md`, `.env.exemplo`
(esse com `ls -a`).

Todos os comandos daqui pra frente rodam **de dentro desta pasta**.

## 2. Ambiente Python da API

A API é leve (FastAPI + Uvicorn). Ela fica num ambiente separado do WhisperX.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**Confira:**

```bash
.venv/bin/python -c "import fastapi, uvicorn, multipart; print('ok')"
```

deve imprimir `ok`.

## 3. Instalar o edvid (motor de corte, transcrição e render)

```bash
scripts/instalar-edvid.sh
```

É o passo demorado (baixa uns 3 GB). Pode rodar de novo quantas vezes quiser: o que já está feito é
pulado. Ele faz, em ordem, e imprime cada etapa:

1. **`[1/5] edvid em …/vendor/edvid`** — clona [fillrochaa/edvid](https://github.com/fillrochaa/edvid)
   em `vendor/edvid` e fixa no commit `d8e6389` (o testado).
2. **`[2/5] patch do dig.D Vídeo`** — aplica `edvid-extras/patches/digd-video.patch` (cartão de
   fechamento, enquadramento da tela dividida, correção do `render.py`) e copia `encode_social.py` e
   `pick_bed.py` pro `helpers/` do edvid. Na segunda vez, diz "já aplicado".
3. **`[3/5] trilhas`** — baixa as 6 trilhas da Mixkit direto do site deles. Se uma falhar, diz
   "NÃO baixou" e segue; aquele clima sai sem trilha.
4. **`[4/5] Python do edvid (WhisperX)`** — com `uv`: `uv sync` em `vendor/edvid` (versões travadas
   no `uv.lock`). Sem `uv`: cria `vendor/edvid/.venv` e faz `pip install -e` (versões **não**
   travadas — pega a mais nova de cada pacote). Se já existe um `.venv` que importa `whisperx`, diz
   "já instalado".
5. **`[5/5] Remotion`** — `npm install` no template `vendor/edvid/assets/shortform` e
   `npx remotion browser ensure`, que baixa o Chrome headless usado no render.

Opções, se quiser pular uma parte:

```bash
scripts/instalar-edvid.sh --sem-python    # pula o WhisperX — nenhum vídeo passa da 1ª etapa
scripts/instalar-edvid.sh --sem-node      # pula o Remotion — sem legenda nem estilo
scripts/instalar-edvid.sh --sem-trilhas   # não baixa as trilhas — vídeos sem música
```

Se o seu edvid já está em outro lugar, defina `VIDEOS_EDVID` antes de rodar; o script aplica o patch
nele.

**Confira:** a última linha é

```
Pronto. edvid em …/vendor/edvid (commit d8e6389 + patch do dig.D Vídeo).
```

e estes três comandos respondem sem erro:

```bash
vendor/edvid/.venv/bin/python -c "import whisperx; print('whisperx ok')"
ls vendor/edvid/assets/shortform/node_modules/remotion >/dev/null && echo "remotion ok"
ls vendor/edvid/assets/music/beds/     # 6 arquivos .mp3, se não usou --sem-trilhas
```

## 4. Configurar (opcional)

**Nada é obrigatório** se você seguiu os passos acima e vai usar só na própria máquina. Pra mudar
algo:

```bash
cp .env.exemplo .env
```

e tire o `#` da frente da linha que quiser usar. O `.env` fica na raiz do pacote e é lido pela API e
pelo `scripts/rodar.sh`. Formato: `CHAVE=valor`, uma por linha, `#` comenta, aspas em volta do valor
são removidas, **sem `export` na frente**. Variável exportada no shell (ou num serviço systemd) vence
o `.env`. O `.env` já está no `.gitignore`.

| Variável | Obrigatória? | Padrão | O que faz |
|---|---|---|---|
| `VIDEOS_HOST` | não | `127.0.0.1` | Onde o servidor escuta. `127.0.0.1` = só esta máquina. Qualquer outro valor (ex.: `0.0.0.0`) exige `VIDEOS_TOKEN`, senão o `rodar.sh` recusa subir. |
| `VIDEOS_PORTA` | não | `8742` | Porta. |
| `VIDEOS_TOKEN` | **sim, se `VIDEOS_HOST` não for local** | vazio | Token de acesso. Vazio = API aberta pra quem alcançar a porta. Ver [abaixo](#videos_token-a-porta-de-entrada). |
| `VIDEOS_TAM_MAX_MB` | não | `500` | Maior upload aceito, em MB. **Tem que ser número inteiro**: `1.5` ou `500MB` impedem o servidor de subir. |
| `VIDEOS_ORIGENS` | não | vazio | Só se um painel seu, em **outro domínio**, chama a API. Lista separada por vírgula. Liga o CORS pra essas origens. |
| `VIDEOS_VOLTAR_URL` | não | vazio | Mostra um link "←" no topo do editor apontando pra esse endereço. Vazio = sem link. |
| `VIDEOS_RAIZ` | não | `./dados` | Onde ficam os vídeos (`dados/videos/<id>/`). |
| `VIDEOS_REFERENCIAS` | não | `$VIDEOS_RAIZ/referencias` | Capas de referência e famílias de arte (só servem com gerador de imagem). |
| `VIDEOS_EDVID` | não | `./vendor/edvid` | Onde está o edvid. Mude só se instalou em outro lugar. |
| `VIDEOS_REMOTION` | não | `$VIDEOS_EDVID/assets/shortform` | Template do Remotion; precisa ter `node_modules`. |
| `VIDEOS_PYTHON` | não | `$VIDEOS_EDVID/.venv/bin/python` | O Python que tem o WhisperX. Útil se você instalou o WhisperX por conta própria. Se o padrão não existe e esta variável está vazia, usa o Python do servidor — que **não** tem WhisperX, e a transcrição falha. |
| `VIDEOS_IDIOMA` | não | `pt` | Idioma da fala, pra transcrição. |
| `VIDEOS_CLAUDE_BIN` | não | o `claude` do PATH | Caminho do Claude Code, pra IA de corte. **Se o `claude` estiver no PATH, a IA liga sozinha.** Pra desligar mesmo tendo o Claude Code, aponte pra um caminho que não existe (ex.: `/desligado`) — conferido no código, não rodando. |
| `VIDEOS_IA_MODELO` | não | `claude-sonnet-5` | Modelo que o Claude Code usa pra sugerir o corte. |
| `VIDEOS_GERADOR_IMAGEM` | não | vazio | Script gerador de imagem (contrato no [README](README.md#gerador-de-imagem-opcional)). Vazio = capa e tela dividida desligadas. Precisa ser executável (`chmod +x`). |
| `VIDEOS_ASSINATURA_CAPA` | não | vazio | Assinatura pequena na capa, ex.: `@seuperfil`. |

**Confira:** depois do passo 5, `curl http://127.0.0.1:8742/api/recursos` mostra o que ficou ligado
(ver abaixo).

## 5. Subir o servidor

```bash
scripts/rodar.sh
```

Ele usa o Python de `.venv/` (o do passo 2) e sobe o Uvicorn em primeiro plano. Pra parar:
**Ctrl+C**.

**Confira:**

1. O terminal mostra `dig.D Vídeo em http://127.0.0.1:8742/editor` e, logo depois, as linhas do
   Uvicorn terminando em `Application startup complete.`
2. Em outro terminal:

   ```bash
   curl http://127.0.0.1:8742/api/saude
   ```

   responde `{"ok":true,"processador":true,"na_fila":0}`.
3. E:

   ```bash
   curl http://127.0.0.1:8742/api/recursos
   ```

   responde algo como
   `{"capa":false,"arte":false,"motivo_imagem":"Capa e arte de tela dividida estão desligadas: …","ia":true,"voltar":null}`.
   `capa`/`arte` = gerador de imagem ligado; `ia` = Claude Code encontrado. (Com `VIDEOS_TOKEN`
   definido, esta rota pede o token: acrescente `-H 'Authorization: Bearer SEU_TOKEN'`.)
4. Abra `http://127.0.0.1:8742/editor` no navegador: aparece o logo e a aba **Fila**.

Daqui, siga o [COMO-USAR.md](COMO-USAR.md#do-zero-ao-primeiro-vídeo-pronto).

Pra deixar rodando como serviço no Linux, há um exemplo de unidade systemd no
[README](README.md#rodando).

---

## VIDEOS_TOKEN: a porta de entrada

**Sem `VIDEOS_TOKEN`, a API não pede senha nenhuma.** Quem alcançar a porta vê, baixa e **apaga**
todos os vídeos. O que protege a instalação padrão é só escutar em `127.0.0.1` — o que deixa de
proteger no momento em que você:

- muda `VIDEOS_HOST` (o `rodar.sh` recusa subir sem token, mas rodar o Uvicorn na mão não recusa);
- põe um proxy (nginx, Caddy) ou um túnel (Cloudflare Tunnel, ngrok) apontando pra `127.0.0.1:8742`
  — pro servidor, o acesso ainda vem "da própria máquina", e **ele não tem como saber** que do outro
  lado é a internet.

Então: se o editor vai ser acessado de qualquer lugar além desta máquina, **defina o token**.

**Gerar e configurar:**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copie a saída pro `.env`:

```
VIDEOS_TOKEN=cole-aqui-o-que-saiu
```

e reinicie o `scripts/rodar.sh`.

**Entrar pela primeira vez:** com o token definido, toda rota pede o token — a API, o editor e os
arquivos de vídeo. Abrir `/editor` sem ele mostra: "Este editor pede o token de acesso. Abra
`/entrar?token=SEU_TOKEN` uma vez neste navegador." Então abra, uma vez em cada navegador:

```
http://SEU_HOST:8742/entrar?token=SEU_TOKEN
```

O servidor confere o token, grava um cookie (`dv_token`, válido por **30 dias**, inacessível ao
JavaScript da página) e te manda pro `/editor`. Depois de 30 dias, ou em outro navegador, repita.
Token errado responde `{"detail":"token errado"}`.

**Por script** (curl, outro sistema): mande o cabeçalho `Authorization: Bearer SEU_TOKEN`.

**Livres sem token:** só `/api/saude` (monitoramento; não expõe vídeo) e o próprio `/entrar`.

**Cuidados:**

- O token vai na URL do `/entrar` e fica no histórico do navegador. Em computador compartilhado,
  apague essa entrada do histórico.
- Em HTTP puro o token e o cookie trafegam sem criptografia. Na internet, ponha atrás de HTTPS
  (Caddy, nginx, Cloudflare Tunnel). Em HTTPS o cookie é gravado como `Secure`.
- Trocar o `VIDEOS_TOKEN` derruba todos os cookies antigos: cada navegador precisa passar pelo
  `/entrar` de novo.

---

## Solução de problemas

### Na instalação

**`Falta instalar: …`** — o `instalar-edvid.sh` não achou um dos programas (`git`, `ffmpeg`,
`ffprobe`, `python3`, `node`, `npm`). Instale o que ele listou e rode de novo.

**`O Remotion pede Node 18 ou mais novo; este é o vX`** — atualize o Node (nodesource ou `nvm`).

**`O edvid pede Python 3.10 a 3.13 e este é o Python 3.14…`** — só acontece **sem** `uv`. Instale o
`uv` e rode o script de novo: o `uv` baixa um Python compatível sozinho.

**`Não consegui pôr o edvid no commit d8e6389`** — alguém mexeu em `vendor/edvid`. Se não tem nada
seu lá, apague a pasta `vendor/edvid` e rode de novo.

**Falha no `[2/5] patch`** (`git apply` reclamando que o patch não se aplica) — o edvid não está no
commit certo ou foi modificado. Mesma saída: apague `vendor/edvid` e rode de novo.

**Falha no `[4/5] Python do edvid (WhisperX)`** — **este é o passo que nunca foi testado pelo
script**. O erro vem do `uv` ou do `pip`, não do nosso código. O que dá pra fazer:

1. Instale o `uv` se ainda não tem e rode de novo. Com `uv` as versões são as travadas
   (whisperx 3.8.6, torch 2.8.0); sem `uv`, o `pip` pega as mais novas, que **ninguém testou** com o
   edvid.
2. Confira espaço em disco: o ambiente ocupa ~2,4 GB e o download é maior que isso durante a
   instalação.
3. Se ainda assim falhar, instale o WhisperX por conta própria num Python 3.10–3.13 e aponte
   `VIDEOS_PYTHON` pra ele. Esse Python precisa conseguir `import whisperx`; **não verifiquei** o que
   mais o `transcribe.py` do edvid importa além disso. Rode o instalador com `--sem-python` pra ele
   não tentar de novo.

**Falha no `[5/5] Remotion`** — `npm install` precisa de internet até o registro do npm. O
`remotion browser ensure` baixa um Chrome headless; num Linux mínimo (servidor, container) esse
Chrome pode precisar de bibliotecas do sistema. **Não verifiquei** quais.

### Ao subir o servidor

**`Recusei subir em 0.0.0.0 sem VIDEOS_TOKEN…`** — é de propósito. Defina `VIDEOS_TOKEN` no `.env`
ou volte `VIDEOS_HOST` pra `127.0.0.1`.

**`No module named uvicorn`** (ou `fastapi`) — o `rodar.sh` não achou `.venv/bin/python` e caiu no
`python3` do sistema. Faça o [passo 2](#2-ambiente-python-da-api) dentro da pasta do pacote.

**`[Errno 98] Address already in use`** (ou mensagem parecida do Uvicorn) — a porta 8742 está
ocupada, provavelmente por outra cópia do próprio servidor. Pare a outra ou mude `VIDEOS_PORTA`.

**`ValueError: invalid literal for int()`** ao subir — `VIDEOS_TAM_MAX_MB` com valor que não é
número inteiro.

### No navegador

**"Este editor pede o token de acesso"** — você tem `VIDEOS_TOKEN` definido. Abra
`/entrar?token=SEU_TOKEN` uma vez. Se o cookie tiver expirado (30 dias) ou o token mudou, repita.

**"Não consegui falar com o servidor de vídeo. Fico tentando."** no alto da página — o servidor caiu
ou foi reiniciado. A tela tenta de novo sozinha.

**O editor abre sem vídeo, ou aparece "escolha um vídeo na Fila primeiro"** — o vídeo aberto é
lembrado num cookie que dura 1 dia. Volte pra aba **Fila** e clique **Abrir no editor** de novo.

**`formato não aceito. Use: …`** — a extensão do arquivo não está na lista (`.avi .m4v .mkv .mov
.mp4 .webm`). Renomear não resolve se o conteúdo não for vídeo; converta com ffmpeg.

**`vídeo maior que 500 MB`** — aumente `VIDEOS_TAM_MAX_MB` ou comprima o vídeo. Atrás de nginx, o
limite do próprio nginx (`client_max_body_size`, 1 MB por padrão) chega antes e o erro vem dele.

**A tela aparece com letra diferente das prévias** — o editor carrega fontes do Google Fonts. Sem
internet no navegador, as prévias de legenda usam fonte substituta. O render não depende disso.

### Vídeo com "Deu erro"

A etiqueta **Deu erro** vem com a última linha do que falhou. As que o código produz:

| Mensagem (começo) | O que é | O que fazer |
|---|---|---|
| `a transcrição falhou: …` | O WhisperX não rodou. No primeiro vídeo, pode ser o download dos modelos (internet, disco). | Rode `vendor/edvid/.venv/bin/python -c "import whisperx"`. Se falhar, volte ao [passo 3](#3-instalar-o-edvid-motor-de-corte-transcrição-e-render). Se passar, confira internet e espaço (~5,3 GB de modelos). |
| `speech_regions falhou: …` | O detector de fala do edvid falhou; ele usa o ffmpeg. | Confira `ffmpeg -version` e se o arquivo abre num player. |
| `não achei fala nenhuma no vídeo.` | Nenhum trecho com voz + palavra transcrita. | Vídeo sem fala, áudio mudo, ou idioma diferente de `VIDEOS_IDIOMA`. |
| `a IA não respondeu: …` | O Claude Code existe mas falhou (não logado, sem acesso ao modelo). | Rode `claude` uma vez e faça login, ou desligue a IA (`VIDEOS_CLAUDE_BIN=/desligado`). Depois apague e mande o vídeo de novo. |
| `a IA respondeu fora do formato: …` / `não entendi a resposta da IA: …` | A resposta do Claude não veio em JSON. | Mande de novo; se repetir, desligue a IA. |
| `o render falhou.` | O render do corte (edvid `render.py`, ffmpeg) falhou. | Veja o terminal do servidor; confira ffmpeg. |
| `o template do Remotion não está instalado em … (falta node_modules)` | Faltou o passo 5 do instalador. | `scripts/instalar-edvid.sh` (sem `--sem-node`). |
| `o render do Remotion falhou: …` | Remotion/Chrome headless falhou no render de estilo. | Veja a mensagem; confira Node 18+ e se o Chrome foi baixado (`[5/5]`). |
| `… o arquivo saiu corrompido …` / `… não terminou de escrever.` | O render terminou sem erro mas o arquivo não presta — geralmente falta de memória ou disco. | Confira RAM livre (~6 GB) e disco. |
| `passou de 1 hora processando e foi parado` | Uma etapa passou do limite (no código, 90 min). | Vídeo muito longo pra máquina. Corte em partes. |
| `o serviço reiniciou no meio. Dá pra mandar de novo.` | O servidor foi reiniciado com o vídeo no meio do processamento. | Apague e mande de novo. |
| `não achei o vídeo final.` | **Pôr 1s na frente do vídeo** (capa) antes de existir um render com legenda. | Renderize um estilo primeiro. |
| `Capa e arte de tela dividida estão desligadas…` | Gerador de imagem não configurado. | Normal. Ver [COMO-USAR.md](COMO-USAR.md#gerador-de-imagem-capa-e-tela-dividida). |

Pra ver o erro completo (a tela mostra só a última linha), olhe o terminal onde o `rodar.sh` está
rodando. **Não verifiquei** se todo o texto do erro chega ao terminal: a API guarda a saída dos
scripts e só grava a última linha no `estado.json`.

Como recuperar um vídeo com erro está em [COMO-USAR.md → Quando um vídeo dá
erro](COMO-USAR.md#quando-um-vídeo-dá-erro).
