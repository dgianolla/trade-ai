#!/usr/bin/env python3
"""
Teste rápido com URLs reais de produção.

Submete as fotos à API local, aguarda o processamento e exibe os
resultados formatados com nota, status, tipo_ativo, problemas e parecer.

Uso:
    python3 scripts/test_urls.py
    python3 scripts/test_urls.py --api-key SUA_KEY --base-url http://localhost:8000
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

# ---------------------------------------------------------------------------
# URLs de teste
# ---------------------------------------------------------------------------
URLS = [
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304115743.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304115857.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304115958.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304120036.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304120119.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304120157.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304120342.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304120437.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304120528.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304120606.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304120744.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304120840.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64088/319/868735_20260304145803.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64089/325/1229198_20260304150131.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304143010.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304143108.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304143250.jpeg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64063/8687/918394_20260304143339.jpeg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64090/8687/1298485_20260304152156.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64090/8687/1298485_20260304152238.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64090/8687/1298486_20260304152021.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64090/8687/1298486_20260304152054.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64090/8687/1298487_20260304152400.jpg",
    "https://d2xsprysh7aash.cloudfront.net/Catalogo/64090/8687/1298487_20260304152442.jpg",
]


# ---------------------------------------------------------------------------
# Helpers HTTP (sem dependências externas)
# ---------------------------------------------------------------------------

def _request(method: str, url: str, headers: dict, body: bytes | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def submeter(base_url: str, api_key: str, imagem_url: str) -> str | None:
    status, resp = _request(
        "POST",
        f"{base_url}/api/v1/analise-fotos/auditar-pdv",
        {"X-API-Key": api_key, "Content-Type": "application/json"},
        json.dumps({"imagem_url": imagem_url}).encode(),
    )
    if status == 202:
        return resp.get("processamento_id")
    print(f"    Erro ao submeter ({status}): {resp}")
    return None


def consultar(base_url: str, api_key: str, proc_id: str) -> dict | None:
    status, resp = _request(
        "GET",
        f"{base_url}/api/v1/analise-fotos/auditorias/{proc_id}",
        {"X-API-Key": api_key},
    )
    if status == 200:
        return resp
    return None


def aguardar_resultado(
    base_url: str, api_key: str, proc_id: str,
    timeout: int = 120, intervalo: int = 3,
) -> dict | None:
    inicio = time.time()
    while time.time() - inicio < timeout:
        resp = consultar(base_url, api_key, proc_id)
        if resp is None:
            time.sleep(intervalo)
            continue

        # Formato n8n: lista com {"output": {...}}
        if isinstance(resp, list) and resp:
            return resp[0].get("output")

        # Formato padrão: dict com status
        if isinstance(resp, dict):
            status_proc = resp.get("status", "")
            if status_proc == "concluido":
                resultado = resp.get("resultado", {})
                return resultado.get("auditoria") if resultado else None
            if status_proc in ("erro", "falhou"):
                return {"_erro": resp.get("erro_mensagem", "Erro desconhecido")}
            # ainda processando — aguarda
        time.sleep(intervalo)

    return {"_erro": f"Timeout após {timeout}s"}


# ---------------------------------------------------------------------------
# Formatação do resultado
# ---------------------------------------------------------------------------

STATUS_ICON = {
    "aprovado": "✓",
    "aprovado_com_ressalvas": "~",
    "reprovado": "✗",
}

NOTA_COR = {
    range(8, 11): "APROVADO   ",
    range(5, 8):  "RESSALVAS  ",
    range(0, 5):  "REPROVADO  ",
}


def cor_nota(nota) -> str:
    if nota is None:
        return "?"
    for r, label in NOTA_COR.items():
        if nota in r:
            return label
    return "?"


def imprimir_resultado(i: int, url: str, resultado: dict) -> None:
    nome_foto = url.split("/")[-1]

    if "_erro" in resultado:
        print(f"\n  [{i:02d}] {nome_foto}")
        print(f"       ERRO: {resultado['_erro']}")
        return

    nota = resultado.get("nota", "?")
    status = resultado.get("status", "?")
    tipo = resultado.get("tipo_ativo", "?")
    marca = resultado.get("marca") or "-"
    preco = resultado.get("preço") or resultado.get("preco") or "-"
    confianca = resultado.get("confianca_avaliacao", "?")
    vis_ok = "✓" if resultado.get("visualizacao_ok") else "✗"
    icon = STATUS_ICON.get(status, "?")
    problemas = resultado.get("problemas", [])
    parecer = resultado.get("parecer", "")
    limitacoes = resultado.get("limitacoes_foto", [])
    penalidades = resultado.get("penalidades_aplicadas", [])
    criterio = resultado.get("criterio_eliminatorio")

    print(f"\n  [{i:02d}] {nome_foto}")
    print(f"       Nota     : {nota}/10  {icon} {status.upper()}")
    print(f"       Tipo     : {tipo}")
    print(f"       Marca    : {marca}   Preço: {preco}   Vis: {vis_ok}   Confiança: {confianca}")
    if parecer:
        # quebra longa em múltiplas linhas
        palavras = parecer.split()
        linha = "       Parecer  : "
        for p in palavras:
            if len(linha) + len(p) > 100:
                print(linha)
                linha = "                  " + p + " "
            else:
                linha += p + " "
        if linha.strip():
            print(linha)
    if criterio:
        print(f"       Eliminat.: {criterio}")
    if problemas:
        print(f"       Problemas: {'; '.join(problemas)}")
    if penalidades:
        print(f"       Penalid. : {'; '.join(penalidades)}")
    if limitacoes:
        print(f"       Limitaç. : {'; '.join(limitacoes)}")


# ---------------------------------------------------------------------------
# Resumo final
# ---------------------------------------------------------------------------

def imprimir_resumo(resultados: list[dict]) -> None:
    total = len(resultados)
    aprovados = sum(1 for r in resultados if r.get("status") == "aprovado")
    ressalvas = sum(1 for r in resultados if r.get("status") == "aprovado_com_ressalvas")
    reprovados = sum(1 for r in resultados if r.get("status") == "reprovado")
    erros = sum(1 for r in resultados if "_erro" in r)
    notas = [r["nota"] for r in resultados if "nota" in r and isinstance(r.get("nota"), (int, float))]
    media = sum(notas) / len(notas) if notas else 0

    tipos = {}
    for r in resultados:
        t = r.get("tipo_ativo", "?")
        tipos[t] = tipos.get(t, 0) + 1

    print("\n" + "=" * 70)
    print("  RESUMO GERAL")
    print("=" * 70)
    print(f"  Total analisado : {total - erros}/{total}")
    print(f"  Aprovados       : {aprovados}  ({aprovados/total*100:.0f}%)")
    print(f"  Com ressalvas   : {ressalvas}  ({ressalvas/total*100:.0f}%)")
    print(f"  Reprovados      : {reprovados}  ({reprovados/total*100:.0f}%)")
    print(f"  Erros/Timeout   : {erros}")
    print(f"  Nota média      : {media:.1f}/10")
    print()
    print("  Tipos de ativo identificados:")
    for tipo, cnt in sorted(tipos.items(), key=lambda x: -x[1]):
        print(f"    {cnt:>3}x  {tipo}")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Teste com URLs reais de produção")
    parser.add_argument("--api-key", default="dev_api_key_123")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout por imagem em segundos")
    parser.add_argument("--output", default=None, help="Salvar resultados em JSON")
    args = parser.parse_args()

    print(f"\n{'=' * 70}")
    print(f"  TESTE DE URLs — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  API : {args.base_url}")
    print(f"  Fotos: {len(URLS)}")
    print(f"{'=' * 70}")

    # Fase 1 — submeter todas as URLs
    print("\n  Submetendo imagens...")
    jobs: list[tuple[str, str | None]] = []
    for url in URLS:
        nome = url.split("/")[-1]
        sys.stdout.write(f"    → {nome:<45} ")
        sys.stdout.flush()
        proc_id = submeter(args.base_url, args.api_key, url)
        if proc_id:
            print(f"OK  ({proc_id[:8]}...)")
            jobs.append((url, proc_id))
        else:
            print("FALHOU")
            jobs.append((url, None))

    # Fase 2 — aguardar e coletar resultados
    print(f"\n  Aguardando processamento (timeout={args.timeout}s por foto)...")
    resultados_por_url: dict[str, dict] = {}

    for url, proc_id in jobs:
        nome = url.split("/")[-1]
        if proc_id is None:
            resultados_por_url[url] = {"_erro": "Falha ao submeter"}
            continue
        sys.stdout.write(f"    ← {nome:<45} ")
        sys.stdout.flush()
        resultado = aguardar_resultado(args.base_url, args.api_key, proc_id, args.timeout)
        if resultado:
            if "_erro" in resultado:
                print(f"ERRO: {resultado['_erro'][:40]}")
            else:
                nota = resultado.get("nota", "?")
                status = resultado.get("status", "?")
                print(f"nota={nota}  {status}")
            resultados_por_url[url] = resultado
        else:
            print("SEM RESULTADO")
            resultados_por_url[url] = {"_erro": "Sem resultado após polling"}

    # Fase 3 — exibir detalhes
    print("\n" + "=" * 70)
    print("  RESULTADOS DETALHADOS")
    print("=" * 70)
    for i, url in enumerate(URLS, 1):
        resultado = resultados_por_url.get(url, {"_erro": "Não processado"})
        imprimir_resultado(i, url, resultado)

    # Fase 4 — resumo
    imprimir_resumo(list(resultados_por_url.values()))

    # Salvar JSON
    if args.output:
        saida = [
            {"url": url, "resultado": resultados_por_url.get(url)}
            for url in URLS
        ]
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(saida, f, ensure_ascii=False, indent=2)
        print(f"\n  Resultados salvos em: {args.output}\n")


if __name__ == "__main__":
    main()
