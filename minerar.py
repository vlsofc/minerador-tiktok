#!/usr/bin/env python3
"""
Minerador de vídeos do TikTok.
Criado por Matheus Valois. Instagram: @matheusvalois. Siga para mais ferramentas assim.

Faz o que você faria na mão: pesquisa cada termo no TikTok, pega os vídeos que
aparecem, ordena por views e baixa todos, separando os melhores do restante.

Uso:
  python3 minerar.py estimar   mostra quanto a busca vai custar e confere o token, sem gastar nada
  python3 minerar.py buscar    busca no TikTok via Apify (gasta crédito da Apify)
  python3 minerar.py filtrar   ordena por views e gera as duas planilhas (grátis, pode repetir)
  python3 minerar.py baixar    baixa todos os vídeos com yt-dlp, melhores e restante (grátis)
  python3 minerar.py tudo      os três últimos em sequência

Opções:
  --pais XX                    país de onde a busca é feita (BR, US, PT, MX...). Fica salvo no config.json
  --confirmado                 o usuário já confirmou o custo, não pergunta de novo

Arquivos que você edita:
  palavras.txt   um termo de pesquisa por linha, do jeito que você digitaria no TikTok
  config.json    quantos vídeos buscar por termo, quantos guardar como melhores, país
  .env           APIFY_TOKEN=seu_token

O que sai: a pasta mineracao/, com uma pasta por termo (melhores/ e restante/)
e as duas planilhas. A pasta resultados/ guarda os dados brutos.

Não precisa instalar nenhuma biblioteca Python. Só precisa do yt-dlp para baixar.
"""
import csv
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQ_PALAVRAS = os.path.join(PASTA, "palavras.txt")
ARQ_CONFIG = os.path.join(PASTA, "config.json")
ARQ_ENV = os.path.join(PASTA, ".env")
PASTA_RESULTADOS = os.path.join(PASTA, "resultados")
PASTA_SAIDA = os.path.join(PASTA, "mineracao")
ARQ_BRUTO = os.path.join(PASTA_RESULTADOS, "bruto.json")
ARQ_MELHORES_JSON = os.path.join(PASTA_RESULTADOS, "melhores.json")
ARQ_RESTANTE_JSON = os.path.join(PASTA_RESULTADOS, "restante.json")
ARQ_MELHORES = os.path.join(PASTA_SAIDA, "planilha_melhores.csv")
ARQ_RESTANTE = os.path.join(PASTA_SAIDA, "planilha_restante.csv")

ASSINATURA = "Feito por @matheusvalois. Siga no Instagram para mais ferramentas assim."

API = "https://api.apify.com/v2"
ACTOR = "clockworks~tiktok-scraper"

# Preços do plano gratuito da Apify em 09/2026. Planos pagos são mais baratos.
PRECO_RESULTADO = 0.0037
PRECO_PAIS = 0.0013
PRECO_INICIO_RUN = 0.001

TENTATIVAS_DOWNLOAD = 3
PAUSA_ENTRE_TENTATIVAS_S = 3
PAUSA_ENTRE_VIDEOS_S = 1

# A busca vai por relevância e sem filtro de data de propósito. Testado em 09/2026:
# o filtro de data do TikTok devolve um poço raso de vídeos fracos, e a ordenação
# por curtidas não é respeitada. Relevância sem data traz os vídeos grandes.
ORDENACAO = "MOST_RELEVANT"
PERIODO = "ALL_TIME"

CONFIG_PADRAO = {
    "pais": "BR",
    "resultados_por_palavra": 50,
    "top_por_palavra": 20,
    "idade_maxima_meses": 0,
    "duracao_maxima_s": 0,
}

PAISES_ACEITOS = set("""AF AL DZ AS AD AO AI AG AR AM AU AT AZ BS BH BB BY BE BZ BJ BM BT BO BA BW BR VG BN BG BF BI KH CM CA
CV KY TD CL CO CK CR HR CY CZ CD DK DJ DO EC EG SV EE ET FK FJ FI FR PF GA GE DE GH GI GR GL GD GP GT GN GW GY HN HU IS ID
IQ IE IM IL IT CI JM JP JE KZ KE XK KW LA LV LB LS LR LY LT LU MO MG MW MY MV ML MT MH MQ MR MU MX MD MC MN ME MA MZ MM NA
NR NP NL NZ NI NG MK NO OM PS PA PG PY PE PH PL PT PR QA CG RO RU RW RE KN LC MF PM VC SM SA SN RS SL SG SX SK SB SO ZA KR
ES LK SR SZ SE CH TW TJ TZ TH TG TO TT TN TR TC TV VI UG UA AE GB US UY VE VN WF YE ZM ZW AX""".split())


# ---------------------------------------------------------------- utilidades

def falhar(msg):
    print("\nERRO: " + msg)
    sys.exit(1)


def carregar_config():
    config = dict(CONFIG_PADRAO)
    if not os.path.exists(ARQ_CONFIG):
        with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
            json.dump(CONFIG_PADRAO, f, ensure_ascii=False, indent=2)
        print("Criei o config.json com os valores padrão.\n")
    with open(ARQ_CONFIG, encoding="utf-8") as f:
        try:
            config.update(json.load(f))
        except json.JSONDecodeError as e:
            falhar("config.json inválido: %s" % e)
    if config["pais"] and config["pais"] not in PAISES_ACEITOS:
        falhar("país '%s' não é aceito. Use o código de 2 letras: BR, US, PT, MX, ES, AR, GB..." % config["pais"])
    return config


def salvar_pais(pais):
    if pais not in PAISES_ACEITOS:
        falhar("--pais precisa do código de 2 letras: BR, US, PT, MX, ES, AR, GB...")
    with open(ARQ_CONFIG, encoding="utf-8") as f:
        salvo = json.load(f)
    salvo["pais"] = pais
    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(salvo, f, ensure_ascii=False, indent=2)
    print("País da busca salvo no config.json: %s\n" % pais)


def carregar_palavras():
    if not os.path.exists(ARQ_PALAVRAS):
        falhar("não achei palavras.txt. Crie o arquivo com um termo de pesquisa por linha.")
    with open(ARQ_PALAVRAS, encoding="utf-8") as f:
        palavras = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    if not palavras:
        falhar("palavras.txt está vazio.")
    return palavras


def carregar_token():
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token and os.path.exists(ARQ_ENV):
        with open(ARQ_ENV, encoding="utf-8") as f:
            for linha in f:
                if linha.strip().startswith("APIFY_TOKEN="):
                    token = linha.split("=", 1)[1].strip().strip('"').strip("'")
    if not token:
        falhar("não achei o APIFY_TOKEN. Crie o arquivo .env com a linha APIFY_TOKEN=seu_token\n"
               "Pegue o token em https://console.apify.com/settings/integrations")
    return token


def api(metodo, caminho, token, corpo=None):
    url = "%s%s%stoken=%s" % (API, caminho, "&" if "?" in caminho else "?", token)
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            falhar("token da Apify inválido ou expirado. Confira em https://console.apify.com/settings/integrations "
                   "e corrija a linha APIFY_TOKEN= no arquivo .env")
        if e.code == 402:
            falhar("crédito da Apify insuficiente. Cada busca precisa de pelo menos 0,50 dólar de folga na conta, "
                   "mesmo custando menos. Veja o saldo e adicione crédito em https://console.apify.com/billing\n"
                   "Resposta da Apify: %s" % e.read().decode()[:200])
        falhar("Apify respondeu %s em %s: %s" % (e.code, caminho, e.read().decode()[:300]))
    except urllib.error.URLError as e:
        falhar("não consegui falar com a Apify (%s). Confira sua internet." % e.reason)


def dolar(valor):
    return ("US$ %.2f" % valor).replace(".", ",")


def humano(n):
    n = n or 0
    if n >= 1_000_000:
        return "%.1fM" % (n / 1_000_000)
    if n >= 1_000:
        return "%dK" % (n // 1_000)
    return str(n)


def limpar_nome(s):
    s = re.sub(r"[^\w.-]+", "_", s or "", flags=re.UNICODE)
    return s.strip("._")[:40] or "sem_nome"


def estimar_custo(config, n_palavras):
    por_resultado = PRECO_RESULTADO + (PRECO_PAIS if config["pais"] else 0)
    return n_palavras * (config["resultados_por_palavra"] * por_resultado + PRECO_INICIO_RUN)


# ---------------------------------------------------------------- 1. buscar

def estimar(config):
    palavras = carregar_palavras()
    custo = estimar_custo(config, len(palavras))
    print("Termos (%d): %s" % (len(palavras), ", ".join(palavras)))
    print("Busca feita a partir de: %s" % (config["pais"] or "sem país definido (resultados vêm misturados)"))
    print("Vídeos por termo: %d | melhores por termo: %d" % (config["resultados_por_palavra"], config["top_por_palavra"]))
    print("Custo estimado na Apify (plano gratuito): %s" % dolar(custo))
    token = carregar_token()
    conta = api("GET", "/users/me", token)["data"]
    print("Token da Apify: OK (conta %s)" % (conta.get("username") or conta.get("id")))
    return palavras, token


def buscar(config, confirmado=False):
    palavras, token = estimar(config)
    if not confirmado:
        if not sys.stdin.isatty():
            falhar("rodando sem terminal interativo. Confirme o custo com o usuário e rode de novo com --confirmado")
        resposta = input("Continuar? [s/N] ").strip().lower()
        if resposta not in ("s", "sim", "y", "yes"):
            print("Cancelado.")
            return

    # Um run por termo, assim cada vídeo já sai etiquetado com o termo que o achou.
    runs = {}
    for palavra in palavras:
        entrada = {
            "searchQueries": [palavra],
            "searchSection": "/video",
            "resultsPerPage": config["resultados_por_palavra"],
            "videoSearchSorting": ORDENACAO,
            "videoSearchDateFilter": PERIODO,
            "shouldDownloadVideos": False,
        }
        if config["pais"]:
            entrada["proxyCountryCode"] = config["pais"]
        resp = api("POST", "/acts/%s/runs" % ACTOR, token, entrada)
        runs[palavra] = resp["data"]
        print("  iniciado: %-30s run %s" % (palavra, resp["data"]["id"]))

    print("Aguardando a Apify terminar...")
    pendentes = dict(runs)
    finais = ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED")
    while pendentes:
        time.sleep(8)
        for palavra, run in list(pendentes.items()):
            atual = api("GET", "/actor-runs/%s" % run["id"], token)["data"]
            if atual["status"] in finais:
                runs[palavra] = atual
                del pendentes[palavra]
                print("  %-30s %s" % (palavra, atual["status"]))
        if pendentes:
            print("  ... %d ainda rodando" % len(pendentes))

    itens = []
    for palavra, run in runs.items():
        if run["status"] != "SUCCEEDED":
            print("  AVISO: busca por '%s' terminou com %s, pulando." % (palavra, run["status"]))
            continue
        dados = api("GET", "/datasets/%s/items?clean=true&format=json" % run["defaultDatasetId"], token)
        for item in dados:
            item["palavra"] = palavra
        itens.extend(dados)
        print("  %-30s %d vídeos" % (palavra, len(dados)))

    os.makedirs(PASTA_RESULTADOS, exist_ok=True)
    with open(ARQ_BRUTO, "w", encoding="utf-8") as f:
        json.dump({"buscado_em": time.strftime("%Y-%m-%d %H:%M"), "config": config, "itens": itens},
                  f, ensure_ascii=False, indent=1)
    print("Salvo: %s (%d vídeos brutos)" % (ARQ_BRUTO, len(itens)))


# ---------------------------------------------------------------- 2. filtrar

def normalizar(item):
    autor = item.get("authorMeta") or {}
    video = item.get("videoMeta") or {}
    views = item.get("playCount") or 0
    likes = item.get("diggCount") or 0
    comentarios = item.get("commentCount") or 0
    shares = item.get("shareCount") or 0
    engaj = (likes + comentarios + shares) / views * 100 if views else 0
    return {
        "id": str(item.get("id") or ""),
        "palavra": item.get("palavra") or "",
        "views": views,
        "likes": likes,
        "comentarios": comentarios,
        "shares": shares,
        "salvos": item.get("collectCount") or 0,
        "engajamento_pct": round(engaj, 2),
        "duracao_s": video.get("duration") or 0,
        "data": (item.get("createTimeISO") or "")[:10],
        "idioma": item.get("textLanguage") or "",
        "autor": autor.get("name") or "",
        "seguidores": autor.get("fans") or 0,
        "texto": (item.get("text") or "").replace("\n", " ").strip(),
        "url": item.get("webVideoUrl") or "",
        "anuncio": bool(item.get("isAd")),
        "slideshow": bool(item.get("isSlideshow")),
    }


def escrever_csv(caminho, colunas, linhas):
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, extrasaction="ignore")
        w.writeheader()
        for linha in linhas:
            w.writerow(linha)


def filtrar(config):
    if not os.path.exists(ARQ_BRUTO):
        falhar("não achei resultados/bruto.json. Rode primeiro: python3 minerar.py buscar")
    with open(ARQ_BRUTO, encoding="utf-8") as f:
        brutos = json.load(f)["itens"]

    # Cada termo tem o seu próprio ranking, como se fossem buscas separadas no
    # TikTok. Um vídeo achado por dois termos aparece nos dois, e a coluna
    # tambem_achado_por diz quais outros termos o acharam. O download baixa uma vez.
    achado_por = {}
    for item in brutos:
        vid = str(item.get("id") or "")
        achado_por.setdefault(vid, [])
        if item.get("palavra") not in achado_por[vid]:
            achado_por[vid].append(item.get("palavra"))

    hoje = datetime.date.today()

    def idade_meses(v):
        try:
            return (hoje - datetime.date.fromisoformat(v["data"])).days // 30
        except ValueError:
            return 0

    # Anúncio e carrossel de fotos não entram no ranking dos melhores, mas ficam
    # no restante. O resto é decidido por views.
    def motivo_exclusao(v):
        if v["anuncio"]:
            return "anúncio"
        if v["slideshow"]:
            return "carrossel de fotos, não é vídeo"
        if config["duracao_maxima_s"] and v["duracao_s"] > config["duracao_maxima_s"]:
            return "mais longo que %ds" % config["duracao_maxima_s"]
        if config["idade_maxima_meses"] and idade_meses(v) > config["idade_maxima_meses"]:
            return "mais velho que %d meses" % config["idade_maxima_meses"]
        return ""

    por_palavra = {}
    for item in brutos:
        v = normalizar(item)
        if not v["id"] or not v["url"]:
            continue
        v["tambem_achado_por"] = ", ".join(p for p in achado_por[v["id"]] if p != v["palavra"])
        por_palavra.setdefault(v["palavra"], []).append(v)

    melhores, restante, excluidos = [], [], {}
    top_n = config["top_por_palavra"]
    print("%-30s %7s %9s %10s" % ("termo", "brutos", "melhores", "restante"))
    for palavra, videos in por_palavra.items():
        candidatos, fora = [], []
        for v in videos:
            motivo = motivo_exclusao(v)
            if motivo:
                v["motivo"] = motivo
                excluidos[motivo] = excluidos.get(motivo, 0) + 1
                fora.append(v)
            else:
                candidatos.append(v)
        candidatos.sort(key=lambda x: x["views"], reverse=True)
        fora.sort(key=lambda x: x["views"], reverse=True)
        top = candidatos[:top_n]
        for v in candidatos[top_n:]:
            v["motivo"] = "fora do top %d por views" % top_n
        # posição única por termo: 1..N, melhores primeiro, depois o restante por views
        for i, v in enumerate(top + candidatos[top_n:] + fora, 1):
            v["posicao"] = i
        melhores.extend(top)
        restante.extend(candidatos[top_n:] + fora)
        print("%-30s %7d %9d %10d" % (palavra, len(videos), len(top), len(videos) - len(top)))

    if excluidos:
        print("Fora do ranking dos melhores, mas no restante: " + ", ".join("%s (%d)" % (m, n) for m, n in excluidos.items()))
    repetidos = sum(1 for lista in achado_por.values() if len(lista) > 1)
    if repetidos:
        print("Vídeos achados por mais de um termo: %d (aparecem em cada termo, baixados uma vez)" % repetidos)

    os.makedirs(PASTA_RESULTADOS, exist_ok=True)
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    with open(ARQ_MELHORES_JSON, "w", encoding="utf-8") as f:
        json.dump(melhores, f, ensure_ascii=False, indent=1)
    with open(ARQ_RESTANTE_JSON, "w", encoding="utf-8") as f:
        json.dump(restante, f, ensure_ascii=False, indent=1)
    metricas = ["views", "likes", "comentarios", "shares", "salvos", "engajamento_pct",
                "duracao_s", "data", "idioma", "autor", "seguidores", "texto", "url", "tambem_achado_por"]
    escrever_csv(ARQ_MELHORES, ["palavra", "posicao"] + metricas, melhores)
    escrever_csv(ARQ_RESTANTE, ["palavra", "posicao", "motivo"] + metricas, restante)
    print("Melhores: %d | Restante: %d | planilhas em %s" % (len(melhores), len(restante), os.path.relpath(PASTA_SAIDA, PASTA)))


# ---------------------------------------------------------------- 3. baixar

def baixar(config):
    if not os.path.exists(ARQ_MELHORES_JSON) or not os.path.exists(ARQ_RESTANTE_JSON):
        falhar("não achei os resultados do filtro. Rode primeiro: python3 minerar.py filtrar")
    if shutil.which("yt-dlp"):
        ytdlp = ["yt-dlp"]
    elif subprocess.run([sys.executable, "-m", "yt_dlp", "--version"], capture_output=True).returncode == 0:
        ytdlp = [sys.executable, "-m", "yt_dlp"]
    else:
        falhar("yt-dlp não está instalado.\n  Mac:     brew install yt-dlp\n  Windows: winget install yt-dlp\n"
               "  Qualquer sistema: python3 -m pip install yt-dlp")
    with open(ARQ_MELHORES_JSON, encoding="utf-8") as f:
        melhores = json.load(f)
    with open(ARQ_RESTANTE_JSON, encoding="utf-8") as f:
        restante = json.load(f)

    # Melhores primeiro, para o que mais importa chegar antes. Carrossel de fotos
    # não é vídeo e não é baixado; fica na planilha.
    fila = [(v, "melhores") for v in melhores] + [(v, "restante") for v in restante if not v["slideshow"]]
    fotos = sum(1 for v in restante if v["slideshow"])
    print("Vídeos para baixar: %d (%d melhores + %d restante)" % (len(fila), len(melhores), len(fila) - len(melhores)))
    if fotos:
        print("Carrosséis de fotos (não são vídeo, ficam só na planilha): %d" % fotos)

    # Vídeo no top de mais de um termo é baixado uma vez e aparece na pasta de
    # cada termo por link de arquivo, que não ocupa espaço duas vezes.
    ok, existentes, ligados, falhas = 0, 0, 0, []
    baixado_em = {}
    for n, (v, grupo) in enumerate(fila, 1):
        pasta = os.path.join(PASTA_SAIDA, limpar_nome(v["palavra"]), grupo)
        os.makedirs(pasta, exist_ok=True)
        nome = "%02d_%s-views_%s_%s.mp4" % (v["posicao"], humano(v["views"]), limpar_nome(v["autor"]), v["id"])
        destino = os.path.join(pasta, nome)
        if os.path.exists(destino):
            existentes += 1
            baixado_em.setdefault(v["id"], destino)
            continue
        if v["id"] in baixado_em:
            try:
                os.link(baixado_em[v["id"]], destino)
            except OSError:
                shutil.copy2(baixado_em[v["id"]], destino)
            ligados += 1
            continue
        print("[%d/%d] %s/%s/%s" % (n, len(fila), limpar_nome(v["palavra"]), grupo, nome))
        # O TikTok às vezes devolve uma página de desafio em vez do vídeo. Tentar de novo resolve.
        erro = "erro desconhecido"
        for tentativa in range(1, TENTATIVAS_DOWNLOAD + 1):
            r = subprocess.run(
                ytdlp + ["--no-warnings", "--quiet", "--no-progress", "--no-playlist", "-o", destino, v["url"]],
                capture_output=True, text=True)
            if r.returncode == 0 and os.path.exists(destino):
                ok += 1
                baixado_em[v["id"]] = destino
                break
            linhas = (r.stderr or r.stdout).strip().splitlines()
            erro = linhas[-1] if linhas else erro
            if "blocked" in erro or "not available" in erro.lower() or "private" in erro.lower():
                break  # vídeo apagado, privado ou inexistente: repetir não ajuda
            if tentativa < TENTATIVAS_DOWNLOAD:
                time.sleep(PAUSA_ENTRE_TENTATIVAS_S)
        if not os.path.exists(destino):
            falhas.append((v["url"], erro))
            print("    falhou: %s" % erro[:120])
        time.sleep(PAUSA_ENTRE_VIDEOS_S)

    print("\nBaixados: %d | já existiam: %d | repetidos entre termos (sem baixar de novo): %d | falharam: %d" % (
        ok, existentes, ligados, len(falhas)))
    print("Pasta pronta: %s" % PASTA_SAIDA)
    if falhas:
        with open(os.path.join(PASTA_RESULTADOS, "falhas_download.txt"), "w", encoding="utf-8") as f:
            for url, erro in falhas:
                f.write("%s\t%s\n" % (url, erro))
        print("Lista das falhas em resultados/falhas_download.txt")


# ---------------------------------------------------------------- main

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    confirmado = "--confirmado" in sys.argv or "--sim" in sys.argv
    comando = args[0] if args else ""
    print("Minerador de vídeos do TikTok | " + ASSINATURA + "\n")
    config = carregar_config()
    if "--pais" in sys.argv:
        pos = sys.argv.index("--pais")
        pais = sys.argv[pos + 1].strip().upper() if len(sys.argv) > pos + 1 else ""
        salvar_pais(pais)
        config["pais"] = pais
        args = [a for a in args if a != pais and a != pais.lower()]
        comando = args[0] if args else ""
    if comando == "estimar":
        estimar(config)
    elif comando == "buscar":
        buscar(config, confirmado)
    elif comando == "filtrar":
        filtrar(config)
    elif comando == "baixar":
        baixar(config)
    elif comando == "tudo":
        buscar(config, confirmado)
        filtrar(config)
        baixar(config)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
