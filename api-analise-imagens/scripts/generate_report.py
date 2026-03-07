#!/usr/bin/env python3
"""
Gera relatório HTML a partir do JSON de resultados da auditoria PDV.

Uso:
    python3 scripts/generate_report.py /tmp/resultados_pdv_v2.json -o /tmp/report_pdv.html
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


STATUS_LABEL = {
    "aprovado": "APROVADO",
    "aprovado_com_ressalvas": "COM RESSALVAS",
    "reprovado": "REPROVADO",
}

STATUS_COLOR = {
    "aprovado": "#16a34a",
    "aprovado_com_ressalvas": "#d97706",
    "reprovado": "#dc2626",
}

STATUS_BG = {
    "aprovado": "#dcfce7",
    "aprovado_com_ressalvas": "#fef3c7",
    "reprovado": "#fee2e2",
}


def nota_color(nota):
    if nota is None:
        return "#6b7280"
    if nota >= 8:
        return "#16a34a"
    if nota >= 5:
        return "#d97706"
    return "#dc2626"


def build_card(i: int, entry: dict) -> str:
    url = entry["url"]
    nome = url.split("/")[-1]
    res = entry.get("resultado", {})

    if "_erro" in res:
        erro_msg = res["_erro"]
        if "429" in erro_msg:
            detalhe = "Rate limit OpenAI (429) — reprocessar após alguns instantes."
        elif "Timeout" in erro_msg:
            detalhe = "Timeout ao aguardar resultado do worker."
        else:
            detalhe = erro_msg[:200]
        return f"""
<div class="card card-erro" data-status="erro" data-tipo="ERRO">
  <div class="card-header erro-header">
    <span class="seq">#{i:02d}</span>
    <span class="nome">{nome}</span>
    <span class="badge-erro">ERRO</span>
  </div>
  <div class="card-body erro-body">
    <div class="thumb-col">
      <img src="{url}" alt="{nome}" loading="lazy" onerror="this.style.display='none'">
    </div>
    <div class="info-col">
      <p class="erro-msg">{detalhe}</p>
    </div>
  </div>
</div>"""

    nota = res.get("nota")
    status = res.get("status", "")
    tipo = res.get("tipo_ativo", "—")
    marca = res.get("marca") or "—"
    preco = res.get("preço") or "—"
    vis = "✓" if res.get("visualizacao_ok") else "✗"
    parecer = res.get("parecer", "")
    problemas = res.get("problemas", [])
    recomendacao = res.get("recomendacao", "")

    s_label = STATUS_LABEL.get(status, status.upper())
    s_color = STATUS_COLOR.get(status, "#6b7280")
    s_bg = STATUS_BG.get(status, "#f3f4f6")
    n_color = nota_color(nota)

    problemas_html = ""
    if problemas:
        itens = "".join(f'<li>{p}</li>' for p in problemas)
        problemas_html = f'<div class="problemas"><strong>Problemas:</strong><ul>{itens}</ul></div>'

    rec_html = ""
    if recomendacao:
        rec_html = f'<div class="recomendacao"><strong>Recomendação:</strong> {recomendacao}</div>'

    return f"""
<div class="card" data-status="{status}" data-tipo="{tipo}">
  <div class="card-header" style="border-left: 4px solid {s_color};">
    <span class="seq">#{i:02d}</span>
    <span class="nome">{nome}</span>
    <span class="badge" style="background:{s_bg}; color:{s_color};">{s_label}</span>
  </div>
  <div class="card-body">
    <div class="thumb-col">
      <img src="{url}" alt="{nome}" loading="lazy" onerror="this.style.display='none'">
    </div>
    <div class="info-col">
      <div class="nota-row">
        <span class="nota" style="color:{n_color}; border-color:{n_color};">{nota if nota is not None else '—'}</span>
        <div class="meta-grid">
          <div><span class="label">Tipo</span><span class="value">{tipo}</span></div>
          <div><span class="label">Marca</span><span class="value">{marca}</span></div>
          <div><span class="label">Preço</span><span class="value">{preco}</span></div>
          <div><span class="label">Visib.</span><span class="value">{vis}</span></div>
        </div>
      </div>
      <div class="parecer">{parecer}</div>
      {problemas_html}
      {rec_html}
    </div>
  </div>
</div>"""


def build_html(dados: list, gerado_em: str) -> str:
    total = len(dados)
    aprovados = sum(1 for d in dados if d.get("resultado", {}).get("status") == "aprovado")
    ressalvas = sum(1 for d in dados if d.get("resultado", {}).get("status") == "aprovado_com_ressalvas")
    reprovados = sum(1 for d in dados if d.get("resultado", {}).get("status") == "reprovado")
    erros = sum(1 for d in dados if "_erro" in d.get("resultado", {}))
    notas = [d["resultado"]["nota"] for d in dados if "nota" in d.get("resultado", {}) and isinstance(d["resultado"].get("nota"), (int, float))]
    media = f"{sum(notas)/len(notas):.1f}" if notas else "—"

    tipos_count: dict = {}
    for d in dados:
        t = d.get("resultado", {}).get("tipo_ativo", "—")
        tipos_count[t] = tipos_count.get(t, 0) + 1

    tipos_html = "".join(
        f'<span class="tipo-chip" data-tipo="{t}" onclick="filtrarTipo(\'{t}\')">{t} <b>{c}</b></span>'
        for t, c in sorted(tipos_count.items(), key=lambda x: -x[1]) if t != "—"
    )

    cards_html = "\n".join(build_card(i + 1, d) for i, d in enumerate(dados))

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Relatório Auditoria PDV — {gerado_em}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f1f5f9; color: #1e293b; }}
  header {{ background: #1e293b; color: #fff; padding: 24px 32px; }}
  header h1 {{ font-size: 22px; font-weight: 700; letter-spacing: -0.3px; }}
  header p {{ margin-top: 4px; font-size: 13px; color: #94a3b8; }}

  .summary {{ display: flex; gap: 16px; padding: 20px 32px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-wrap: wrap; align-items: center; }}
  .stat {{ display: flex; flex-direction: column; align-items: center; min-width: 80px; }}
  .stat .num {{ font-size: 28px; font-weight: 800; line-height: 1; }}
  .stat .lbl {{ font-size: 11px; color: #64748b; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .stat-sep {{ width: 1px; height: 40px; background: #e2e8f0; }}
  .stat-green .num {{ color: #16a34a; }}
  .stat-yellow .num {{ color: #d97706; }}
  .stat-red .num {{ color: #dc2626; }}
  .stat-gray .num {{ color: #6b7280; }}
  .stat-blue .num {{ color: #2563eb; }}

  .controls {{ padding: 16px 32px; background: #fff; border-bottom: 1px solid #e2e8f0; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
  .controls label {{ font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; }}
  .filter-btn {{ padding: 5px 14px; border: 1px solid #e2e8f0; border-radius: 20px; font-size: 13px; cursor: pointer; background: #f8fafc; transition: all .15s; }}
  .filter-btn:hover, .filter-btn.active {{ background: #1e293b; color: #fff; border-color: #1e293b; }}
  .tipo-chip {{ padding: 4px 10px; border: 1px solid #e2e8f0; border-radius: 20px; font-size: 12px; cursor: pointer; background: #f8fafc; transition: all .15s; }}
  .tipo-chip:hover, .tipo-chip.active {{ background: #2563eb; color: #fff; border-color: #2563eb; }}
  .tipo-chip b {{ font-weight: 700; }}

  main {{ padding: 24px 32px; display: flex; flex-direction: column; gap: 16px; max-width: 1100px; margin: 0 auto; }}

  .card {{ background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.07); transition: box-shadow .2s; }}
  .card:hover {{ box-shadow: 0 4px 16px rgba(0,0,0,.12); }}
  .card-header {{ display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: #f8fafc; border-bottom: 1px solid #f1f5f9; }}
  .seq {{ font-size: 12px; color: #94a3b8; font-weight: 600; min-width: 30px; }}
  .nome {{ flex: 1; font-size: 13px; font-family: monospace; color: #475569; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .badge {{ padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; letter-spacing: 0.4px; white-space: nowrap; }}
  .badge-erro {{ padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; background: #fee2e2; color: #dc2626; }}

  .card-body {{ display: flex; gap: 0; }}
  .thumb-col {{ width: 220px; min-width: 220px; background: #0f172a; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
  .thumb-col img {{ width: 100%; height: 180px; object-fit: cover; display: block; }}
  .info-col {{ flex: 1; padding: 16px 20px; display: flex; flex-direction: column; gap: 10px; }}

  .nota-row {{ display: flex; gap: 16px; align-items: flex-start; }}
  .nota {{ width: 64px; height: 64px; border-radius: 50%; border: 3px solid; display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: 800; flex-shrink: 0; }}
  .meta-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px 20px; }}
  .meta-grid .label {{ font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.4px; }}
  .meta-grid .value {{ font-size: 13px; font-weight: 600; color: #1e293b; margin-left: 4px; }}

  .parecer {{ font-size: 13px; color: #475569; line-height: 1.6; border-left: 3px solid #e2e8f0; padding-left: 10px; }}
  .problemas {{ font-size: 13px; }}
  .problemas strong {{ color: #dc2626; }}
  .problemas ul {{ margin-top: 4px; padding-left: 18px; color: #b91c1c; }}
  .problemas li {{ margin-bottom: 2px; }}
  .recomendacao {{ font-size: 12px; color: #64748b; font-style: italic; }}

  .erro-header {{ background: #fef2f2; }}
  .erro-body .thumb-col {{ background: #1f2937; }}
  .erro-body .info-col {{ justify-content: center; }}
  .erro-msg {{ font-size: 13px; color: #dc2626; }}

  .hidden {{ display: none !important; }}

  @media (max-width: 680px) {{
    .card-body {{ flex-direction: column; }}
    .thumb-col {{ width: 100%; min-width: unset; }}
    .thumb-col img {{ height: 200px; }}
    main {{ padding: 16px; }}
    header, .summary, .controls {{ padding: 16px; }}
  }}
</style>
</head>
<body>

<header>
  <h1>Relatório Auditoria PDV</h1>
  <p>Gerado em {gerado_em} &nbsp;·&nbsp; {total} fotos analisadas</p>
</header>

<div class="summary">
  <div class="stat stat-green"><span class="num">{aprovados}</span><span class="lbl">Aprovados</span></div>
  <div class="stat-sep"></div>
  <div class="stat stat-yellow"><span class="num">{ressalvas}</span><span class="lbl">Ressalvas</span></div>
  <div class="stat-sep"></div>
  <div class="stat stat-red"><span class="num">{reprovados}</span><span class="lbl">Reprovados</span></div>
  <div class="stat-sep"></div>
  <div class="stat stat-gray"><span class="num">{erros}</span><span class="lbl">Erros</span></div>
  <div class="stat-sep"></div>
  <div class="stat stat-blue"><span class="num">{media}</span><span class="lbl">Nota Média</span></div>
</div>

<div class="controls">
  <label>Status:</label>
  <button class="filter-btn active" onclick="filtrarStatus('todos')">Todos</button>
  <button class="filter-btn" onclick="filtrarStatus('aprovado')">Aprovados</button>
  <button class="filter-btn" onclick="filtrarStatus('aprovado_com_ressalvas')">Com Ressalvas</button>
  <button class="filter-btn" onclick="filtrarStatus('reprovado')">Reprovados</button>
  <button class="filter-btn" onclick="filtrarStatus('erro')">Erros</button>
  &nbsp;
  <label>Tipo:</label>
  {tipos_html}
  <button class="filter-btn" onclick="filtrarTipo('todos')" id="btn-tipo-todos">Todos os tipos</button>
</div>

<main>
{cards_html}
</main>

<script>
  let statusAtual = 'todos';
  let tipoAtual = 'todos';

  function aplicarFiltros() {{
    document.querySelectorAll('.card').forEach(card => {{
      const s = card.dataset.status;
      const t = card.dataset.tipo;
      const matchStatus = statusAtual === 'todos' || s === statusAtual;
      const matchTipo = tipoAtual === 'todos' || t === tipoAtual;
      card.classList.toggle('hidden', !(matchStatus && matchTipo));
    }});
  }}

  function filtrarStatus(status) {{
    statusAtual = status;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    aplicarFiltros();
  }}

  function filtrarTipo(tipo) {{
    tipoAtual = tipo;
    document.querySelectorAll('.tipo-chip').forEach(b => b.classList.remove('active'));
    document.getElementById('btn-tipo-todos').classList.remove('active');
    if (tipo === 'todos') {{
      document.getElementById('btn-tipo-todos').classList.add('active');
    }} else {{
      event.target.classList.add('active');
    }}
    aplicarFiltros();
  }}
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", help="Arquivo JSON de resultados")
    parser.add_argument("-o", "--output", default="/tmp/report_pdv.html")
    args = parser.parse_args()

    with open(args.json_file, encoding="utf-8") as f:
        dados = json.load(f)

    gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")
    html = build_html(dados, gerado_em)

    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    print(f"Relatório gerado: {out.resolve()}")


if __name__ == "__main__":
    main()
