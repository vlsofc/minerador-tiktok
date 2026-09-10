# Minerador de vídeos do TikTok

Criado por Matheus Valois. Instagram: [@matheusvalois](https://instagram.com/matheusvalois).

Faz o que você faria na mão: pesquisa cada termo na busca do TikTok, pega o
que aparece, ordena por views, separa os melhores de cada termo e baixa. A
busca é feita pela Apify, o download pelo yt-dlp. Sem biblioteca Python
externa.

## Para o aluno (sem terminal)

Entregue o `PROMPT-DO-ALUNO.md`. Ele cola no Claude Code, Codex ou Gemini
CLI, responde três perguntas (token da Apify, termos, país e idioma) e o
agente faz o resto. O prompt já aponta para o `minerar.py` deste repositório.

## Para quem usa terminal

```
cp .env.exemplo .env                 # e cole o token da Apify
nano palavras.txt                    # um termo por linha, como você digitaria no TikTok
python3 minerar.py estimar --pais BR # confere o token e mostra o custo, não gasta nada
python3 minerar.py buscar            # gasta crédito, pede confirmação antes
python3 minerar.py filtrar           # grátis, gera as duas planilhas, pode repetir
python3 minerar.py baixar            # grátis, vídeos em videos/<termo>/
```

`python3 minerar.py tudo --confirmado` roda tudo sem perguntar.

## O que sai

- `resultados/planilha_melhores.csv`: os `top_por_palavra` mais vistos de cada
  termo, com posição. São os que o `baixar` baixa.
- `resultados/planilha_restante.csv`: todo o resto do bruto, com a coluna
  `motivo` ("fora do top 20 por views", "anúncio", "slideshow"). Nada é
  descartado, o aluno pagou por esses dados.
- Cada termo tem o seu próprio top, como buscas separadas no TikTok. Vídeo
  achado por mais de um termo aparece em cada um, com os outros termos na
  coluna `tambem_achado_por`. É baixado uma vez e aparece na pasta de cada
  termo por link de arquivo, sem ocupar espaço duas vezes.
- `resultados/pular.txt` (opcional): URLs que o download deve pular. É onde o
  agente anota os vídeos fora do tema que o aluno mandou tirar.

## config.json

| chave | padrão | o que faz |
|---|---|---|
| `pais` | BR | país de onde a busca é feita; `--pais XX` grava aqui |
| `resultados_por_palavra` | 50 | quantos vídeos buscar por termo |
| `top_por_palavra` | 20 | quantos guardar como melhores por termo |
| `idade_maxima_meses` | 0 | 0 desliga; acima disso vai pro restante |
| `duracao_maxima_s` | 0 | 0 desliga; acima disso vai pro restante |
| `ignorar_anuncios` | true | anúncio vai pro restante |
| `ignorar_slideshows` | true | carrossel de fotos vai pro restante |

## Por que a busca vai por relevância e sem filtro de data

Testado em 09/2026 com dinheiro de verdade. A busca do TikTok com "últimos 6
meses" e "mais curtidos" devolve um poço raso, cerca de 50 vídeos fracos com
mediana de 4 mil views, e a ordenação por curtidas nem é respeitada. A mesma
busca por relevância e sem filtro de data traz mediana de 190 mil views, com
12 de 20 acima de 100 mil, metade com menos de 4 meses, e sai mais barata.
Isso está fixo no script, não é configurável.

## País e idioma

O que define de onde vêm os vídeos é o país da busca. Sem ele, termos como
"perder peso" trazem uma mistura de espanhol e inglês. Os termos devem estar
no idioma do país escolhido; no prompt do aluno, o agente traduz e pede
aprovação.

## Custo

Actor `clockworks/tiktok-scraper`, plano gratuito da Apify em 09/2026:
0,0037 dólar por resultado, mais 0,0013 pelo país, mais 0,001 por termo. Com
o padrão, 3 termos com 50 resultados cada dá 0,75 dólar; 4 termos dá 1,00. O
plano gratuito da Apify vem com 5 dólares por mês, então dá pra testar sem
pagar.
