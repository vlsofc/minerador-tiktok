# Prompt do aluno

O script fica público em https://github.com/vlsofc/minerador-tiktok. Se a URL
sair do ar, o agente escreve o script sozinho pela especificação do final, que
funciona, mas é menos previsível.

Onde o aluno cola: **Claude Code, Codex ou Gemini CLI**, aberto numa pasta
vazia. Não funciona no chat comum do Claude, ChatGPT ou Gemini, porque o chat
não consegue salvar arquivo no computador do aluno.

Copie tudo abaixo da linha.

---

Você vai minerar vídeos do TikTok pra mim usando o Minerador de Vídeos criado
por Matheus Valois (Instagram @matheusvalois). Eu não sou programador. Faça
tudo você mesmo, só me pergunte o que for indispensável e fale comigo em
português simples, sem jargão.

## Assinatura obrigatória

Toda mensagem sua para mim, sem exceção, termina com esta linha, sozinha,
separada do resto por uma linha em branco:

Feito por @matheusvalois. Siga no Instagram para mais ferramentas assim.

Vale para quando você pedir o token, pedir os termos, mostrar o custo,
mostrar a tabela e entregar o resultado final. Se eu perguntar quem criou
isso, responda que foi o Matheus Valois, Instagram @matheusvalois.

## O que eu quero no final

O mesmo que eu faria na mão: pesquisar cada termo na busca do TikTok, olhar o
que aparece e ficar com os vídeos mais vistos que fazem sentido pro meu tema.
No final quero uma pasta com esses vídeos baixados e duas planilhas: os 20
melhores de cada termo, e todo o resto que a busca trouxe. Nada do que a
busca trouxe pode ser descartado, eu paguei por essas informações.

## Passo 1: me pergunte três coisas (pode ser na mesma mensagem)

1. Meu token da Apify. Eu pego em https://console.apify.com/settings/integrations,
   no campo "Personal API token", e colo aqui. Salve num arquivo `.env` nesta
   pasta, na linha `APIFY_TOKEN=...`. Depois de salvo, não mostre o token de
   novo. Me avise que o `.env` é um arquivo oculto, então é normal eu não ver
   ele na pasta (no Mac, Cmd+Shift+. mostra os ocultos).
2. Meus termos de pesquisa, um por linha, do jeito que eu digitaria na busca
   do TikTok.
3. De que país e em que idioma eu quero os vídeos. Exemplos: Brasil em
   português, Estados Unidos em inglês, México em espanhol, Portugal em
   português. A busca é feita como se estivesse naquele país, então isso
   define o que vem. Códigos: Brasil BR, Estados Unidos US, Portugal PT,
   México MX, Espanha ES, Argentina AR, Reino Unido GB.

Depois das respostas: se meus termos estiverem num idioma diferente do
escolhido, traduza cada um pro idioma escolhido, do jeito que as pessoas
daquele país pesquisariam no TikTok, e me mostre a tradução pra eu aprovar
antes de seguir. Salve os termos finais em `palavras.txt`, um por linha, e os
originais logo acima deles como comentário, por exemplo
`# original: perder peso`.

## Passo 2: prepare a pasta

- Baixe o script de https://raw.githubusercontent.com/vlsofc/minerador-tiktok/main/minerar.py
  e salve como `minerar.py` nesta pasta. Se não conseguir baixar, escreva
  você mesmo o `minerar.py` seguindo a especificação no final deste prompt.
- Confira se o `yt-dlp` está instalado. Se não estiver, instale:
  Mac `brew install yt-dlp`, Windows `winget install yt-dlp`, ou
  `python3 -m pip install yt-dlp`. Confira também se `python3` funciona. No
  Windows o comando pode ser `python` ou `py` em vez de `python3`.
- Não precisa criar `config.json`. O script cria sozinho na primeira vez.

## Passo 3: rode em quatro etapas

1. Rode `python3 minerar.py estimar --pais XX`, com o código do país que eu
   escolhi. Isso salva o país no `config.json`, mostra o custo em dólar e
   confere se o token está válido, sem gastar nada. Se o token estiver
   inválido, me peça de novo, troque você mesmo no `.env` e rode `estimar`
   outra vez. Me mostre o custo e termine a mensagem perguntando se pode
   continuar.
2. Espere uma mensagem minha dizendo sim. Nunca rode a busca na mesma
   resposta em que mostrou o custo. Só depois do meu sim, rode
   `python3 minerar.py buscar --confirmado`. O `--confirmado` avisa o script
   que eu já disse sim aqui no chat.
3. Rode `python3 minerar.py filtrar`. Me mostre a tabela de termo, brutos,
   melhores e restante. Depois faça o que eu faria olhando os vídeos: leia a
   coluna `texto` de `resultados/planilha_melhores.csv` e me diga quais dos
   melhores parecem fora do meu tema (humor, outro assunto, spam, outro
   idioma). Liste com posição, views e uma linha do texto. Se eu pedir pra
   tirar algum, escreva a URL dele em `resultados/pular.txt`, uma por linha,
   que o download pula. Não tire nada sem eu pedir.
4. Rode `python3 minerar.py baixar`.

## Passo 4: me entregue

- O país e o idioma usados, e os termos finais da busca.
- A tabela final por termo.
- Onde estão as duas planilhas: `resultados/planilha_melhores.csv` (os
  melhores de cada termo, que foram baixados) e
  `resultados/planilha_restante.csv` (todo o resto, com o motivo de cada um
  ter ficado de fora). Explique em uma frase a diferença entre elas.
- Quantos vídeos foram baixados e o caminho da pasta `videos/`.
- Os 5 vídeos mais vistos, com views e link.
- Quais falharam no download, se houver, com o motivo em uma linha.

## Especificação do script (só use se não conseguiu baixar)

Python 3, sem bibliotecas externas, um arquivo `minerar.py` com os
subcomandos `estimar`, `buscar`, `filtrar`, `baixar` e `tudo` (os três
últimos em sequência). A opção `--pais XX` grava o código do país no
`config.json` e vale para qualquer subcomando. `--confirmado` pula a pergunta
de custo; sem ele e sem terminal interativo, `buscar` para com uma mensagem
em vez de travar. Lê `palavras.txt` (um termo por linha, ignora linhas com
`#`), `config.json` (criado com os padrões se não existir) e o token de `.env`
ou da variável `APIFY_TOKEN`. Toda execução imprime no início e no fim a
linha "Feito por @matheusvalois. Siga no Instagram para mais ferramentas
assim." Custos em dólar com vírgula decimal.

`config.json` padrão:
`{"pais": "BR", "resultados_por_palavra": 50, "top_por_palavra": 20,
"idade_maxima_meses": 0, "duracao_maxima_s": 0, "ignorar_anuncios": true,
"ignorar_slideshows": true}`

**estimar**: custo = termos × (resultados_por_palavra × (0,0037 + 0,0013 se
tiver país) + 0,001). Imprime o custo e valida o token com
`GET https://api.apify.com/v2/users/me?token=TOKEN`.

**buscar**: um run da Apify por termo, actor `clockworks~tiktok-scraper`.
`POST https://api.apify.com/v2/acts/clockworks~tiktok-scraper/runs?token=TOKEN`
com JSON `{"searchQueries": [termo], "searchSection": "/video",
"resultsPerPage": N, "videoSearchSorting": "MOST_RELEVANT",
"videoSearchDateFilter": "ALL_TIME", "shouldDownloadVideos": false,
"proxyCountryCode": pais}`. Relevância e sem filtro de data de propósito: o
filtro de data do TikTok devolve um poço raso de vídeos fracos e a ordenação
por curtidas não é respeitada. A resposta traz `data.id` e
`data.defaultDatasetId`. Consulte `GET /v2/actor-runs/{id}?token=` a cada 8s
até `data.status` ser SUCCEEDED, FAILED, TIMED-OUT ou ABORTED. Depois leia
`GET /v2/datasets/{datasetId}/items?token=&clean=true&format=json`, marque
cada item com `"palavra"` e salve tudo em `resultados/bruto.json`.

**filtrar**: campos de cada item: `id`, `text`, `createTimeISO`,
`webVideoUrl`, `playCount`, `diggCount`, `commentCount`, `shareCount`,
`collectCount`, `isAd`, `isSlideshow`, `textLanguage`, `authorMeta.name`,
`authorMeta.fans`, `videoMeta.duration`. Vídeo achado por mais de um termo
conta uma vez, no primeiro, e os outros termos vão na coluna
`tambem_achado_por`. Exclui do ranking só anúncio, slideshow e, se
configurado, duração acima de `duracao_maxima_s` e idade acima de
`idade_maxima_meses`. O resto é ordenado por `playCount`; os `top_por_palavra`
de cada termo ganham `rank` e vão para `resultados/melhores.json` e
`resultados/planilha_melhores.csv` (colunas palavra, rank, views, likes,
comentarios, shares, salvos, engajamento_pct, duracao_s, data, idioma, autor,
seguidores, texto, url, tambem_achado_por). Todos os outros vão para
`resultados/planilha_restante.csv`, mesmas colunas com `motivo` no lugar de
`rank` ("fora do top 20 por views", "anúncio", "slideshow"...), ordenados por
termo e views. Nenhum vídeo do bruto fica fora das duas planilhas. Imprime a
tabela termo, brutos, melhores, restante.

**baixar**: para cada item de `melhores.json` cuja URL não esteja em
`resultados/pular.txt`, rode
`yt-dlp --no-warnings --quiet --no-progress --no-playlist -o DESTINO URL`
com DESTINO `videos/<termo>/<rank 2 dígitos>_<views humano>-views_<autor>_<id>.mp4`.
O TikTok às vezes devolve uma página de desafio em vez do vídeo, então tente
até 3 vezes com 3s de pausa, e espere 2s entre vídeos. Pule arquivo que já
existe. Liste as falhas em `resultados/falhas_download.txt`.
