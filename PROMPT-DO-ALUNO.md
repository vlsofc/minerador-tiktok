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

Vale para quando você pedir o token, pedir as palavras, mostrar o custo,
mostrar a tabela e entregar o resultado final. Se eu perguntar quem criou
isso, responda que foi o Matheus Valois, Instagram @matheusvalois.

## O que eu quero no final

Uma pasta com os vídeos mais vistos do TikTok sobre os termos que eu vou te
passar, já filtrados por views, e duas planilhas: uma com os melhores de cada
palavra e outra com todo o resto do que a busca trouxe. Nada do que a busca
trouxe pode ser descartado, eu paguei por essas informações.

## Passo 1: me pergunte duas coisas (pode ser na mesma mensagem)

1. Meu token da Apify. Eu pego em https://console.apify.com/settings/integrations,
   no campo "Personal API token", e colo aqui. Salve num arquivo `.env` nesta
   pasta, na linha `APIFY_TOKEN=...`. Depois de salvo, não mostre o token de
   novo. Me avise que o `.env` é um arquivo oculto, então é normal eu não ver
   ele na pasta (no Mac, Cmd+Shift+. mostra os ocultos).
2. Minhas palavras-chave, uma por linha. Salve em `palavras.txt`.

## Passo 2: prepare a pasta

- Baixe o script de https://raw.githubusercontent.com/vlsofc/minerador-tiktok/main/minerar.py e salve como `minerar.py` nesta pasta.
  Se não conseguir baixar, escreva você mesmo o `minerar.py` seguindo a
  especificação no final deste prompt.
- Confira se o `yt-dlp` está instalado. Se não estiver, instale:
  Mac `brew install yt-dlp`, Windows `winget install yt-dlp`, ou
  `python3 -m pip install yt-dlp`. Confira também se `python3` funciona. No
  Windows o comando pode ser `python` ou `py` em vez de `python3`.
- Não precisa criar `config.json`. O script cria sozinho na primeira vez,
  com os filtros padrão.

## Passo 3: rode em quatro etapas

1. Rode `python3 minerar.py estimar`. Ele mostra o custo em dólar e confere
   se o token está válido, sem gastar nada. Se o token estiver inválido, me
   peça de novo, troque você mesmo no `.env` e rode `estimar` outra vez. Me
   mostre o custo e termine a mensagem perguntando se pode continuar.
2. Espere uma mensagem minha dizendo sim. Nunca rode a busca na mesma
   resposta em que mostrou o custo. Só depois do meu sim, rode
   `python3 minerar.py buscar --confirmado`. O `--confirmado` avisa o script
   que eu já disse sim aqui no chat.
3. Rode `python3 minerar.py filtrar`. Me mostre a tabela de palavra, brutos,
   aprovados, no top e taxa. Se alguma palavra ficou abaixo de 20% de aprovados, me
   sugira um valor menor de `views_minimas`. Se eu aceitar, edite você mesmo
   o `config.json` e rode `filtrar` de novo. Filtrar é grátis, pode repetir.
4. Rode `python3 minerar.py baixar`.

## Passo 4: me entregue

- A tabela final por palavra.
- Onde estão as duas planilhas: `resultados/planilha_melhores.csv` (os
  melhores de cada palavra, que foram baixados) e
  `resultados/planilha_restante.csv` (todo o resto, com o motivo de cada um
  ter ficado de fora). Explique em uma frase a diferença entre elas.
- Quantos vídeos foram baixados e o caminho da pasta `videos/`.
- Os 5 vídeos mais vistos, com views e link.
- Quais falharam no download, se houver, com o motivo em uma linha.

## Especificação do script (só use se não conseguiu baixar)

Python 3, sem bibliotecas externas, um arquivo `minerar.py` com quatro
subcomandos: `estimar` (imprime o custo e valida o token com
`GET /v2/users/me`, sem gastar), `buscar`, `filtrar`, `baixar`, e `tudo`, que
roda os três últimos em sequência. Se `config.json` não
existir, cria com os padrões. Aceita `--confirmado` para pular a pergunta de
custo; sem ele e sem terminal interativo, `buscar` para com uma mensagem em
vez de travar. Toda execução imprime no início e no fim a linha "Feito por
@matheusvalois. Siga no Instagram para mais ferramentas assim." Custos em
dólar com vírgula decimal. Lê `palavras.txt` (uma por linha, ignora linhas com `#`),
`config.json` e o token de `.env` ou da variável `APIFY_TOKEN`.

`config.json` padrão:
`{"resultados_por_palavra": 50, "periodo": "LAST_6_MONTHS",
"ordenar_busca_por": "MOST_LIKED", "pais": "", "views_minimas": 100000,
"likes_minimos": 0, "duracao_minima_s": 5, "duracao_maxima_s": 90,
"ignorar_anuncios": true, "ignorar_slideshows": true, "top_por_palavra": 20}`

**buscar**: um run da Apify por palavra, actor `clockworks~tiktok-scraper`.
`POST https://api.apify.com/v2/acts/clockworks~tiktok-scraper/runs?token=TOKEN`
com JSON `{"searchQueries": [palavra], "searchSection": "/video",
"resultsPerPage": N, "videoSearchSorting": ordenar_busca_por,
"videoSearchDateFilter": periodo, "shouldDownloadVideos": false}` e
`"proxyCountryCode"` só se `pais` não for vazio. A resposta traz `data.id` e
`data.defaultDatasetId`. Consulte `GET /v2/actor-runs/{id}?token=` a cada 8s
até `data.status` ser SUCCEEDED, FAILED, TIMED-OUT ou ABORTED. Depois leia
`GET /v2/datasets/{datasetId}/items?token=&clean=true&format=json`, marque
cada item com `"palavra"` e salve tudo em `resultados/bruto.json`.
Custo estimado, plano gratuito: 0,0037 dólar por resultado, mais 0,0013 se
periodo não for ALL_TIME, mais 0,0013 se ordenação não for MOST_RELEVANT,
mais 0,0013 se tiver país, mais 0,001 por run. Mostre antes de rodar.

**filtrar**: campos de cada item: `id`, `text`, `createTimeISO`,
`webVideoUrl`, `playCount`, `diggCount`, `commentCount`, `shareCount`,
`collectCount`, `isAd`, `isSlideshow`, `authorMeta.name`, `authorMeta.fans`,
`videoMeta.duration`. Vídeo achado por mais de uma palavra conta uma vez, na
primeira, e as outras palavras vão na coluna `tambem_achado_por`. Reprove por
anúncio, slideshow, views, likes e duração conforme o config. Ordene por
views, guarde os `top_por_palavra` de cada palavra com um `rank`. Salve
`resultados/aprovados.json` (só os do top) e duas planilhas:
`resultados/planilha_melhores.csv` com colunas palavra, rank, views, likes,
comentarios, shares, salvos, engajamento_pct, duracao_s, data, autor,
seguidores, texto, url, tambem_achado_por; e `resultados/planilha_restante.csv`
com todos os outros vídeos do bruto, mesmas colunas mas com `motivo` no lugar
de `rank` ("reprovado: views abaixo de 100K", "aprovado, fora do top 20").
Nenhum vídeo do bruto pode ficar fora das duas planilhas. Imprima a tabela
palavra, brutos, aprovados, no top, taxa.

**baixar**: para cada aprovado, rode
`yt-dlp --no-warnings --quiet --no-progress --no-playlist -o DESTINO URL`
com DESTINO `videos/<palavra>/<rank 2 dígitos>_<views humano>-views_<autor>_<id>.mp4`.
O TikTok às vezes devolve uma página de desafio em vez do vídeo, então tente
até 3 vezes com 3s de pausa, e espere 2s entre vídeos. Pule arquivo que já
existe. Liste as falhas em `resultados/falhas_download.txt`.
