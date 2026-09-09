#!/usr/bin/env python3
"""
Minerador de vídeos do TikTok.
Criado por Matheus Valois. Instagram: @matheusvalois. Siga para mais ferramentas assim.

Uso:
  python3 minerar.py estimar   mostra quanto a busca vai custar, sem gastar nada
  python3 minerar.py buscar    busca no TikTok via Apify (gasta crédito da Apify)
  python3 minerar.py filtrar   filtra e gera as duas planilhas (grátis, pode repetir à vontade)
  python3 minerar.py baixar    baixa os vídeos aprovados com yt-dlp (grátis)
  python3 minerar.py tudo      os três passos em sequência

Opções:
  --pais XX                    país de onde a busca é feita (BR, US, PT, MX...). Fica salvo no config.json
  --confirmado                 o usuário já confirmou o custo, não pergunta de novo

Arquivos que você edita:
  palavras.txt   uma palavra-chave por linha
  config.json    filtros (views mínimas, período, quantos por palavra...)
  .env           APIFY_TOKEN=seu_token

Não precisa instalar nenhuma biblioteca Python. Só precisa do yt-dlp para baixar.
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQ_PALAVRAS = os.path.join(PASTA, "palavras.txt")
ARQ_CONFIG = os.path.join(PASTA, "config.json")
ARQ_ENV = os.path.join(PASTA, ".env")
PASTA_RESULTADOS = os.path.join(PASTA, "resultados")
PASTA_VIDEOS = os.path.join(PASTA, "videos")
ARQ_BRUTO = os.path.join(PASTA_RESULTADOS, "bruto.json")
ARQ_APROVADOS = os.path.join(PASTA_RESULTADOS, "aprovados.json")
ARQ_MELHORES = os.path.join(PASTA_RESULTADOS, "planilha_melhores.csv")
ARQ_RESTANTE = os.path.join(PASTA_RESULTADOS, "planilha_restante.csv")

ASSINATURA = "Feito por @matheusvalois. Siga no Instagram para mais ferramentas assim."

API = "https://api.apify.com/v2"
ACTOR = "clockworks~tiktok-scraper"

# Preços do plano gratuito da Apify em 09/2026. Planos pagos são mais baratos.
PRECO_RESULTADO = 0.0037
PRECO_FILTRO = 0.0013
PRECO_INICIO_RUN = 0.001

TENTATIVAS_DOWNLOAD = 3
PAUSA_ENTRE_TENTATIVAS_S = 3
PAUSA_ENTRE_VIDEOS_S = 2

CONFIG_PADRAO = {
    "resultados_por_palavra": 50,
    "periodo": "LAST_6_MONTHS",
    "ordenar_busca_por": "MOST_LIKED",
    "pais": "BR",
    "idiomas": [],
    "paises": [],
    "views_minimas": 100000,
    "likes_minimos": 0,
    "duracao_minima_s": 5,
    "duracao_maxima_s": 90,
    "ignorar_anuncios": True,
    "ignorar_slideshows": True,
    "top_por_palavra": 20,
}

PAISES_ACEITOS = set("""AF AL DZ AS AD AO AI AG AR AM AU AT AZ BS BH BB BY BE BZ BJ BM BT BO BA BW BR VG BN BG BF BI KH CM CA
CV KY TD CL CO CK CR HR CY CZ CD DK DJ DO EC EG SV EE ET FK FJ FI FR PF GA GE DE GH GI GR GL GD GP GT GN GW GY HN HU IS ID
IQ IE IM IL IT CI JM JP JE KZ KE XK KW LA LV LB LS LR LY LT LU MO MG MW MY MV ML MT MH MQ MR MU MX MD MC MN ME MA MZ MM NA
NR NP NL NZ NI NG MK NO OM PS PA PG PY PE PH PL PT PR QA CG RO RU RW RE KN LC MF PM VC SM SA SN RS SL SG SX SK SB SO ZA KR
ES LK SR SZ SE CH TW TJ TZ TH TG TO TT TN TR TC TV VI UG UA AE GB US UY VE VN WF YE ZM ZW AX""".split())

PERIODOS = ["ALL_TIME", "PAST_24_HOURS", "PAST_WEEK", "PAST_MONTH", "LAST_3_MONTHS", "LAST_6_MONTHS"]
ORDENACOES = ["MOST_RELEVANT", "MOST_LIKED", "LATEST"]


# ---------------------------------------------------------------- utilidades

def falhar(msg):
    print("\nERRO: " + msg)
    sys.exit(1)


def carregar_config():
    config = dict(CONFIG_PADRAO)
    if not os.path.exists(ARQ_CONFIG):
        with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
            json.dump(CONFIG_PADRAO, f, ensure_ascii=False, indent=2)
        print("Criei o config.json com os filtros padrão. Edite ele se quiser mudar views mínimas, período etc.\n")
    with open(ARQ_CONFIG, encoding="utf-8") as f:
        try:
            config.update(json.load(f))
        except json.JSONDecodeError as e:
            falhar("config.json inválido: %s" % e)
    if config["pais"] and config["pais"] not in PAISES_ACEITOS:
        falhar("país '%s' não é aceito. Use o código de 2 letras: BR, US, PT, MX, ES, AR, GB..." % config["pais"])
    if config["periodo"] not in PERIODOS:
        falhar("periodo inválido no config.json. Use um destes: %s" % ", ".join(PERIODOS))
    if config["ordenar_busca_por"] not in ORDENACOES:
        falhar("ordenar_busca_por inválido no config.json. Use um destes: %s" % ", ".join(ORDENACOES))
    return config


def carregar_palavras():
    if not os.path.exists(ARQ_PALAVRAS):
        falhar("não achei palavras.txt. Crie o arquivo com uma palavra-chave por linha.")
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
    por_resultado = PRECO_RESULTADO
    if config["periodo"] != "ALL_TIME":
        por_resultado += PRECO_FILTRO
    if config["ordenar_busca_por"] != "MOST_RELEVANT":
        por_resultado += PRECO_FILTRO
    if config["pais"]:
        por_resultado += PRECO_FILTRO
    total = n_palavras * (config["resultados_por_palavra"] * por_resultado + PRECO_INICIO_RUN)
    return total


# ---------------------------------------------------------------- 1. buscar

def estimar(config):
    palavras = carregar_palavras()
    custo = estimar_custo(config, len(palavras))
    print("Palavras-chave (%d): %s" % (len(palavras), ", ".join(palavras)))
    print("Busca feita a partir de: %s" % (config["pais"] or "sem país definido (resultados vêm misturados)"))
    print("Resultados por palavra: %d | período: %s | ordenação: %s" % (
        config["resultados_por_palavra"], config["periodo"], config["ordenar_busca_por"]))
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

    # Um run por palavra, assim cada vídeo já sai etiquetado com a palavra que o achou.
    runs = {}
    for palavra in palavras:
        entrada = {
            "searchQueries": [palavra],
            "searchSection": "/video",
            "resultsPerPage": config["resultados_por_palavra"],
            "videoSearchSorting": config["ordenar_busca_por"],
            "videoSearchDateFilter": config["periodo"],
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
        "pais": item.get("locationCreated") or "",
        "autor": autor.get("name") or "",
        "seguidores": autor.get("fans") or 0,
        "texto": (item.get("text") or "").replace("\n", " ").strip(),
        "url": item.get("webVideoUrl") or "",
        "anuncio": bool(item.get("isAd")),
        "slideshow": bool(item.get("isSlideshow")),
    }


def filtrar(config):
    if not os.path.exists(ARQ_BRUTO):
        falhar("não achei resultados/bruto.json. Rode primeiro: python3 minerar.py buscar")
    with open(ARQ_BRUTO, encoding="utf-8") as f:
        brutos = json.load(f)["itens"]

    # Mesmo vídeo pode aparecer em mais de uma palavra. Fica na primeira,
    # e as outras palavras que também o acharam vão numa coluna.
    vistos = {}
    for item in brutos:
        v = normalizar(item)
        if not v["id"] or not v["url"]:
            continue
        if v["id"] in vistos:
            outras = vistos[v["id"]]["tambem_achado_por"]
            if v["palavra"] not in outras:
                outras.append(v["palavra"])
            continue
        v["tambem_achado_por"] = []
        vistos[v["id"]] = v

    idiomas, paises = config.get("idiomas") or [], config.get("paises") or []

    def motivo_reprovacao(v):
        # Passa se o texto está num idioma aceito OU o vídeo foi criado num país aceito.
        if (idiomas or paises) and not (v["idioma"] in idiomas or v["pais"] in paises):
            return "idioma %s / país %s" % (v["idioma"] or "?", v["pais"] or "?")
        if config["ignorar_anuncios"] and v["anuncio"]:
            return "anúncio"
        if config["ignorar_slideshows"] and v["slideshow"]:
            return "slideshow"
        if v["views"] < config["views_minimas"]:
            return "views abaixo de %s" % humano(config["views_minimas"])
        if v["likes"] < config["likes_minimos"]:
            return "likes abaixo de %s" % humano(config["likes_minimos"])
        if v["duracao_s"] < config["duracao_minima_s"]:
            return "mais curto que %ds" % config["duracao_minima_s"]
        if v["duracao_s"] > config["duracao_maxima_s"]:
            return "mais longo que %ds" % config["duracao_maxima_s"]
        return ""

    por_palavra = {}
    for v in vistos.values():
        grupo = por_palavra.setdefault(v["palavra"], {"aprovados": [], "reprovados": []})
        motivo = motivo_reprovacao(v)
        if motivo:
            v["motivo"] = "reprovado: " + motivo
            grupo["reprovados"].append(v)
        else:
            grupo["aprovados"].append(v)

    melhores, restante, motivos = [], [], {}
    print("%-30s %7s %9s %8s %6s" % ("palavra", "brutos", "aprovados", "no top", "taxa"))
    for palavra, grupo in por_palavra.items():
        aprovados = sorted(grupo["aprovados"], key=lambda x: x["views"], reverse=True)
        top = aprovados[: config["top_por_palavra"]]
        for i, v in enumerate(top, 1):
            v["rank"] = i
        melhores.extend(top)
        for v in aprovados[config["top_por_palavra"]:]:
            v["motivo"] = "aprovado, fora do top %d" % config["top_por_palavra"]
            restante.append(v)
        for v in sorted(grupo["reprovados"], key=lambda x: x["views"], reverse=True):
            resumo = "idioma/país fora do filtro" if v["motivo"].startswith("reprovado: idioma") else v["motivo"]
            motivos[resumo] = motivos.get(resumo, 0) + 1
            restante.append(v)
        brutos_palavra = len(aprovados) + len(grupo["reprovados"])
        taxa = len(aprovados) / brutos_palavra * 100 if brutos_palavra else 0
        print("%-30s %7d %9d %8d %5.0f%%" % (palavra, brutos_palavra, len(aprovados), len(top), taxa))

    if motivos:
        print("Reprovados por motivo: " + ", ".join("%s (%d)" % (m.replace("reprovado: ", ""), n) for m, n in motivos.items()))
    duplicados = len(brutos) - len(vistos)
    if duplicados:
        print("Vídeos achados por mais de uma palavra: %d (contados uma vez, coluna tambem_achado_por)" % duplicados)

    os.makedirs(PASTA_RESULTADOS, exist_ok=True)
    for v in list(melhores) + restante:
        v["tambem_achado_por"] = ", ".join(v["tambem_achado_por"])
    with open(ARQ_APROVADOS, "w", encoding="utf-8") as f:
        json.dump(melhores, f, ensure_ascii=False, indent=1)
    metricas = ["views", "likes", "comentarios", "shares", "salvos", "engajamento_pct",
                "duracao_s", "data", "idioma", "pais", "autor", "seguidores", "texto", "url", "tambem_achado_por"]
    escrever_csv(ARQ_MELHORES, ["palavra", "rank"] + metricas, melhores)
    escrever_csv(ARQ_RESTANTE, ["palavra", "motivo"] + metricas, restante)
    print("Melhores: %d vídeos em %s" % (len(melhores), os.path.relpath(ARQ_MELHORES, PASTA)))
    print("Restante: %d vídeos em %s (nada é descartado, você pagou por eles)" % (len(restante), os.path.relpath(ARQ_RESTANTE, PASTA)))


def escrever_csv(caminho, colunas, linhas):
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, extrasaction="ignore")
        w.writeheader()
        for linha in linhas:
            w.writerow(linha)


# ---------------------------------------------------------------- 3. baixar

def baixar(config):
    if not os.path.exists(ARQ_APROVADOS):
        falhar("não achei resultados/aprovados.json. Rode primeiro: python3 minerar.py filtrar")
    if shutil.which("yt-dlp"):
        ytdlp = ["yt-dlp"]
    elif subprocess.run([sys.executable, "-m", "yt_dlp", "--version"], capture_output=True).returncode == 0:
        ytdlp = [sys.executable, "-m", "yt_dlp"]
    else:
        falhar("yt-dlp não está instalado.\n  Mac:     brew install yt-dlp\n  Windows: winget install yt-dlp\n"
               "  Qualquer sistema: python3 -m pip install yt-dlp")
    with open(ARQ_APROVADOS, encoding="utf-8") as f:
        aprovados = json.load(f)

    ok, pulados, falhas = 0, 0, []
    for n, v in enumerate(aprovados, 1):
        pasta = os.path.join(PASTA_VIDEOS, limpar_nome(v["palavra"]))
        os.makedirs(pasta, exist_ok=True)
        nome = "%02d_%s-views_%s_%s.mp4" % (v.get("rank", n), humano(v["views"]), limpar_nome(v["autor"]), v["id"])
        destino = os.path.join(pasta, nome)
        if os.path.exists(destino):
            pulados += 1
            continue
        print("[%d/%d] %s" % (n, len(aprovados), nome))
        # O TikTok às vezes devolve uma página de desafio em vez do vídeo. Tentar de novo resolve.
        erro = "erro desconhecido"
        for tentativa in range(1, TENTATIVAS_DOWNLOAD + 1):
            r = subprocess.run(
                ytdlp + ["--no-warnings", "--quiet", "--no-progress", "--no-playlist", "-o", destino, v["url"]],
                capture_output=True, text=True)
            if r.returncode == 0 and os.path.exists(destino):
                ok += 1
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

    print("Baixados: %d | já existiam: %d | falharam: %d | pasta: %s" % (ok, pulados, len(falhas), PASTA_VIDEOS))
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
        if pais not in PAISES_ACEITOS:
            falhar("--pais precisa do código de 2 letras: BR, US, PT, MX, ES, AR, GB...")
        config["pais"] = pais
        salvo = json.load(open(ARQ_CONFIG, encoding="utf-8"))
        salvo["pais"] = pais
        with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
            json.dump(salvo, f, ensure_ascii=False, indent=2)
        print("País da busca salvo no config.json: %s\n" % pais)
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
    print("\n" + ASSINATURA)


if __name__ == "__main__":
    main()
