# Minerador de vídeos do TikTok

Criado por Matheus Valois. Instagram: [@matheusvalois](https://instagram.com/matheusvalois).

Faz o que você faria na mão: pesquisa cada termo na busca do TikTok e baixa
todos os vídeos que aparecem, uma pasta por termo, numerados do mais visto ao
menos visto. A busca é feita pela Apify, o download pelo yt-dlp. Sem
biblioteca Python externa.

## Para o aluno (sem terminal)

Envie o `prompt-para-enviar.txt`. O aluno cola no Claude Code, Codex ou
Gemini CLI, responde três perguntas (token da Apify, termos, país e idioma),
diz "sim" pro custo, e no fim a pasta `mineracao` abre na tela dele. O prompt
já aponta para o `minerar.py` deste repositório. `PROMPT-DO-ALUNO.md` é o
mesmo texto com notas para o professor.

## Para quem usa terminal

```
cp .env.exemplo .env                 # e cole o token da Apify
nano palavras.txt                    # um termo por linha, como você digitaria no TikTok
python3 minerar.py estimar --pais BR # confere o token e mostra o custo, não gasta nada
python3 minerar.py buscar            # gasta crédito, pede confirmação antes
python3 minerar.py organizar         # grátis, ordena por views e gera a planilha
python3 minerar.py baixar            # grátis, baixa tudo em mineracao/
```

`python3 minerar.py tudo --confirmado` roda tudo sem perguntar.

## O que sai: a pasta `mineracao/`

```
mineracao/
  planilha.csv                 todos os vídeos, com views, likes, duração, autor, texto, link
  perder_barriga/
    01_2.9M-views_autor_id.mp4
    02_2.1M-views_autor_id.mp4
    ...
  secar_barriga/
    ...
```

- Nada é filtrado nem descartado: o aluno pagou por todos os vídeos, então
  todos são baixados. Carrossel de fotos não é baixado porque não é vídeo,
  mas fica na planilha, assim como a marcação de anúncio.
- Cada termo é uma busca separada. Vídeo achado por mais de um termo aparece
  em cada pasta, com os outros termos na coluna `tambem_achado_por`, e é
  baixado uma vez, aparecendo nas outras pastas por link de arquivo, sem
  ocupar espaço duas vezes.
- O script não julga conteúdo. Quem sabe pra que serve o b-roll é o aluno.
- `resultados/` guarda o bruto da Apify e os arquivos internos.

## config.json

| chave | padrão | o que faz |
|---|---|---|
| `pais` | BR | país de onde a busca é feita; `--pais XX` grava aqui |
| `resultados_por_palavra` | 50 | quantos vídeos buscar por termo |

## Por que a busca vai por relevância e sem filtro de data

Testado em 09/2026 com dinheiro de verdade. A busca do TikTok com "últimos 6
meses" e "mais curtidos" devolve um poço raso, cerca de 50 vídeos fracos com
mediana de 4 mil views, e a ordenação por curtidas nem é respeitada. A mesma
busca por relevância e sem filtro de data traz mediana de 190 mil views, com
12 de 20 acima de 100 mil, metade com menos de 4 meses, e sai mais barata.
Isso está fixo no script, não é configurável. A API do actor não tem filtro
por views; os números vêm na resposta e vão pra planilha.

## País e idioma

O que define de onde vêm os vídeos é o país da busca. O robô da Apify
pesquisa de fora do Brasil e anônimo; o proxy faz a busca sair do país
escolhido, como sai do celular do aluno. Sem ele, termos que existem em
português e espanhol, como "perder peso", trazem metade em espanhol. Os
termos devem estar no idioma do país escolhido; no prompt do aluno, o agente
traduz e pede aprovação.

## Custo

Actor `clockworks/tiktok-scraper`, plano gratuito da Apify em 09/2026:
0,0037 dólar por resultado, mais 0,0013 pelo país, mais 0,001 por termo. Com
o padrão, 3 termos com 50 resultados cada dá 0,75 dólar. O plano gratuito
vem com 5 dólares por mês, mas cada busca precisa de 0,50 de folga na conta,
então dá pra umas 6 minerações por mês sem pagar.
