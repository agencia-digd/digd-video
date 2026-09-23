# De onde veio esta interface

O editor de linha do tempo — régua, agulha, faixas, forma de onda — nasceu do
**edvid** (`fillrochaa/edvid`), licenciado MIT, © 2026 Creator Factory. A cópia
da licença está em `LICENSE-edvid` e **fica aqui**: a MIT exige que o aviso de
copyright acompanhe o código, e acompanha.

O que a MIT permite, e é o que foi feito: modificar e adaptar. Esta pasta é a
versão do **dig.D Vídeo** — marca da dig.D, e livre pra evoluir. O `edvid`
continua sendo o motor de corte e render, instalado à parte (ver README na raiz);
o que mudou de dono foi só a interface.

Por que copiar em vez de continuar sobrescrevendo por CSS: a documentação do
edvid trata o app de preview como imutável, e uma folha injetada só consegue
mudar o que é cor e posição. Pra mudar comportamento — que é o plano — o
arquivo precisa ser nosso.
