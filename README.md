# Minerador de vídeos do TikTok

Criado por Matheus Valois. Instagram: [@matheusvalois](https://instagram.com/matheusvalois).

Busca vídeos no TikTok por palavra-chave via Apify, filtra por views e
duração, e baixa os aprovados com yt-dlp. Sem biblioteca Python externa.

## Para o aluno (sem terminal)

Entregue o `PROMPT-DO-ALUNO.md`. Ele cola no Claude Code, Codex ou Gemini
CLI, responde duas perguntas (token da Apify e palavras) e o agente faz o
resto. O prompt já aponta para o `minerar.py` deste repositório.

## Para quem usa terminal

```
cp .env.exemplo .env          # e cole o token da Apify
nano palavras.txt             # uma palavra-chave por linha
python3 minerar.py estimar    # confere o token e mostra o custo, não gasta nada
python3 minerar.py buscar     # gasta crédito, pede confirmação antes
python3 minerar.py filtrar    # grátis, gera as duas planilhas, pode repetir mexendo no config.json
python3 minerar.py baixar     # grátis, vídeos em videos/<palavra>/
```

`python3 minerar.py tudo --confirmado` roda tudo sem perguntar.

## O que sai do filtro

- `resultados/planilha_melhores.csv`: os `top_por_palavra` mais vistos de cada
  palavra, que são os que o `baixar` baixa.
- `resultados/planilha_restante.csv`: todo o resto do bruto, com a coluna
  `motivo` dizendo por que ficou de fora ("reprovado: anúncio", "aprovado,
  fora do top 20"). Nada é descartado, o aluno pagou por esses dados.
- Vídeo achado por mais de uma palavra aparece uma vez, com as outras
  palavras na coluna `tambem_achado_por`.

## País e idioma

O que define de onde vêm os vídeos é o país da busca (`pais` no
`config.json`, ou `--pais XX` em qualquer comando). A busca é feita como se
estivesse naquele país. Sem isso, termos como "perder peso" trazem uma mistura
de espanhol e inglês. Os termos devem estar no idioma do país escolhido; no
prompt do aluno, o agente traduz e pede aprovação.

O filtro local por `idiomas`/`paises` existe, mas fica desligado por padrão.
Só faz sentido para tirar um ou outro vídeo estrangeiro que ainda apareça.

## Custo

Actor `clockworks/tiktok-scraper`, plano gratuito da Apify em 09/2026:
0,0037 dólar por resultado, mais 0,0013 por filtro de data, mais 0,0013 por
ordenação, mais 0,0013 por país. Com o config padrão, 4 palavras com 50
resultados cada, busca feita do Brasil, dá cerca de 1,52 dólar. O plano gratuito da Apify vem com
5 dólares por mês, então dá pra testar sem pagar.

## O que já foi validado

- Schema de entrada e saída do actor, direto da API da Apify.
- yt-dlp baixa vídeo público do TikTok sem login e sem marca d'água, em
  1080p. Falha de forma intermitente, por isso o script tenta 3 vezes.
- Filtro e download testados com dataset simulado no formato real.

Não validado ainda: uma busca real na Apify. Precisa de token.
