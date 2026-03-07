#!/usr/bin/env python3
"""
QA Evaluation Script — Agente de Análise de Fotos de PDV

Executa os 56 cenários de teste distribuídos em 6 dimensões e gera
um report estruturado com taxa de aprovação, critical fails e
recomendações de melhoria no prompt.

Uso:
    python scripts/qa_eval_agent.py --photos-dir ./fotos_teste --modelo gpt-4o-mini
    python scripts/qa_eval_agent.py --photos-dir ./fotos_teste --modelo claude-3-5-sonnet
    python scripts/qa_eval_agent.py --list-scenarios          # lista cenários sem executar
    python scripts/qa_eval_agent.py --scenario C01 --foto ./foto.jpg  # cenário avulso
"""

import argparse
import json
import math
import os
import sys
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Adiciona o diretório pai ao path para importar o serviço
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Tipos de validação
# ---------------------------------------------------------------------------

ALLOWED_TIPOS_ATIVO = {
    # Físicos
    "PONTA GÔNDOLA", "ILHA", "ILHA OURO", "ORELHA DE PONTA GÔNDOLA",
    "DISPLAY DE CHÃO", "RÁDIO INDOOR", "TELA DESCANSO PDV (CHECKOUT)",
    "SELF CHECKOUTS", "ESPAÇO NO CHECK STAND", "TV INDOOR",
    # Gráficos
    "ADESIVO DE CHECKOUT", "ADESIVO DE CHÃO", "PDV IMPRESSO (FAIXA GÔNDOLA)",
    "TIRA STRIP", "WOBBLER", "STOPPER", "PLACA DE CARRINHO", "PLACA DE CESTINHA",
    "BANNER AÉREO LOJA", "BANNER ESTACIONAMENTO", "LONA ESTACIONAMENTO GRADIL",
    "TAPETE ENTRADA DA LOJA", "WALK IN COOLER", "ADESIVO DE ELEVADOR",
    # Perecível
    "ADESIVO DE PORTAS DE GELADEIRA", "ESPAÇO GELADEIRA",
    "PONTA GÔNDOLA REFRIGERADA(PORTA)", "ILHA DE CONGELADOS",
    "PONTA DE ILHA DE CONGELADOS",
    # Extras
    "DEGUSTAÇÃO AGENDADA (ESPAÇO)", "CARROS DE ENTREGA", "RAMPA DE ACESSO (ESPAÇO)",
    "AÇÃO FÍSICA", "CANTINHO DO CHURRASCO", "LAMA", "BANNER EXTERNO LOJA", "TOTEM LED",
    # Encarte
    "ITEM TABLÓIDE", "BOX TABLÓIDE",
    # Especial
    "nao_identificado",
}

STATUS_VALIDOS = {"aprovado", "aprovado_com_ressalvas", "reprovado"}
CONFIANCA_VALIDAS = {"alta", "media", "baixa"}
CHAVES_OBRIGATORIAS = [
    "nota", "nota_posicionamento", "nota_visibilidade", "nota_integridade",
    "nota_conteudo", "status", "tipo_ativo", "marca", "visualizacao_ok",
    "parecer", "problemas", "penalidades_aplicadas", "criterio_eliminatorio",
    "recomendacao", "preço", "confianca_avaliacao", "limitacoes_foto",
]


# ---------------------------------------------------------------------------
# Definição dos cenários
# ---------------------------------------------------------------------------

@dataclass
class Cenario:
    id: str
    dimensao: str               # D1..D6
    descricao: str
    foto_esperada: str          # nome sugerido para o arquivo de foto
    validacoes: List[str]       # lista de chaves de validação a executar
    # Expectativas concretas (None = não verificar)
    tipo_ativo_esperado: Optional[str] = None
    preco_esperado: Optional[Any] = None          # str | None | "QUALQUER"
    problemas_esperados: Optional[List[str]] = None   # lista parcial obrigatória
    zero_problemas_esperado: bool = False          # True = problemas deve ser []
    status_esperado: Optional[str] = None
    nota_minima: Optional[int] = None
    nota_maxima: Optional[int] = None
    confianca_esperada: Optional[str] = None
    limitacoes_nao_vazias: bool = False           # limitacoes_foto deve ter ≥ 1 item
    is_critical: bool = False                     # falha aqui é blocker


CENARIOS: List[Cenario] = [
    # -----------------------------------------------------------------------
    # DIMENSÃO 1 — CLASSIFICAÇÃO DE ATIVOS
    # -----------------------------------------------------------------------
    Cenario(
        id="C01", dimensao="D1",
        descricao="Ponta de gôndola clássica — estrutura 3D com prateleiras no fim do corredor",
        foto_esperada="C01_ponta_gondola.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "tipo_ativo"],
        tipo_ativo_esperado="PONTA GÔNDOLA",
    ),
    Cenario(
        id="C02", dimensao="D1",
        descricao="Orelha de ponta de gôndola — cartaz/painel na lateral da gôndola",
        foto_esperada="C02_orelha_ponta_gondola.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "tipo_ativo"],
        tipo_ativo_esperado="ORELHA DE PONTA GÔNDOLA",
    ),
    Cenario(
        id="C03", dimensao="D1",
        descricao="Adesivo na esteira do caixa",
        foto_esperada="C03_adesivo_checkout.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "tipo_ativo"],
        tipo_ativo_esperado="ADESIVO DE CHECKOUT",
    ),
    Cenario(
        id="C04", dimensao="D1",
        descricao="Ilha de produtos sobre pallet no corredor",
        foto_esperada="C04_ilha.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "tipo_ativo"],
        tipo_ativo_esperado="ILHA",
    ),
    Cenario(
        id="C05", dimensao="D1",
        descricao="Wobbler suspenso na borda da prateleira",
        foto_esperada="C05_wobbler.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "tipo_ativo"],
        tipo_ativo_esperado="WOBBLER",
    ),
    Cenario(
        id="C06", dimensao="D1",
        descricao="Stopper perpendicular projetando-se da gôndola",
        foto_esperada="C06_stopper.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "tipo_ativo"],
        tipo_ativo_esperado="STOPPER",
    ),
    Cenario(
        id="C07", dimensao="D1",
        descricao="Faixa contínua impressa na frente das prateleiras",
        foto_esperada="C07_faixa_gondola.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "tipo_ativo"],
        tipo_ativo_esperado="PDV IMPRESSO (FAIXA GÔNDOLA)",
    ),
    Cenario(
        id="C08", dimensao="D1",
        descricao="Foto ambígua — corredor sem material promocional visível",
        foto_esperada="C08_sem_ativo.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "tipo_ativo"],
        tipo_ativo_esperado="nao_identificado",
    ),
    Cenario(
        id="C09", dimensao="D1",
        descricao="Adesivo de chão — aplicado no piso da loja",
        foto_esperada="C09_adesivo_chao.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "tipo_ativo"],
        tipo_ativo_esperado="ADESIVO DE CHÃO",
    ),
    Cenario(
        id="C10", dimensao="D1",
        descricao="Display de chão com produtos — estrutura independente",
        foto_esperada="C10_display_chao.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "tipo_ativo"],
        tipo_ativo_esperado="DISPLAY DE CHÃO",
    ),

    # -----------------------------------------------------------------------
    # DIMENSÃO 2 — EXTRAÇÃO DE PREÇO
    # -----------------------------------------------------------------------
    Cenario(
        id="P01", dimensao="D2",
        descricao='Preço claro "R$ 7,99" visível no ativo',
        foto_esperada="P01_preco_claro.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "preco_exato"],
        preco_esperado="R$ 7,99",
    ),
    Cenario(
        id="P02", dimensao="D2",
        descricao='Preço promocional combo "2x R$ 5,00"',
        foto_esperada="P02_preco_combo.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "preco_exato"],
        preco_esperado="2x R$ 5,00",
    ),
    Cenario(
        id="P03", dimensao="D2",
        descricao="Preço parcialmente coberto — dígito invisível",
        foto_esperada="P03_preco_parcial.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "preco_null"],
        preco_esperado=None,
        is_critical=True,
    ),
    Cenario(
        id="P04", dimensao="D2",
        descricao="Sem preço no ativo — não existe",
        foto_esperada="P04_sem_preco.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "preco_null"],
        preco_esperado=None,
        is_critical=True,
    ),
    Cenario(
        id="P05", dimensao="D2",
        descricao="Preço em etiqueta ao lado, fora do ativo principal",
        foto_esperada="P05_preco_fora.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "preco_null"],
        preco_esperado=None,
        is_critical=True,
    ),
    Cenario(
        id="P06", dimensao="D2",
        descricao='"De R$ 12,99 por R$ 9,99" — captura promoção completa',
        foto_esperada="P06_preco_de_por.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "preco_exato"],
        preco_esperado="De R$ 12,99 por R$ 9,99",
    ),
    Cenario(
        id="P07", dimensao="D2",
        descricao="Preço desfocado e ilegível",
        foto_esperada="P07_preco_desfocado.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "preco_null"],
        preco_esperado=None,
        is_critical=True,
    ),
    Cenario(
        id="P08", dimensao="D2",
        descricao='Preço em formato irregular "997" — sem símbolo R$',
        foto_esperada="P08_preco_irregular.jpg",
        validacoes=["json_valido", "chaves_obrigatorias"],
        preco_esperado="QUALQUER",  # depende do contexto, não é critical fail
    ),

    # -----------------------------------------------------------------------
    # DIMENSÃO 3 — DETECÇÃO DE PROBLEMAS
    # -----------------------------------------------------------------------
    Cenario(
        id="D01", dimensao="D3",
        descricao="Ativo perfeito, foto nítida — zero problemas esperados",
        foto_esperada="D01_ativo_perfeito.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "zero_problemas"],
        zero_problemas_esperado=True,
        is_critical=True,
    ),
    Cenario(
        id="D02", dimensao="D3",
        descricao="Ativo com rasgo grande e evidente",
        foto_esperada="D02_rasgo.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "problemas_detectados"],
        problemas_esperados=["rasgo"],
    ),
    Cenario(
        id="D03", dimensao="D3",
        descricao="Artefatos de compressão JPEG pesada — não há problemas reais",
        foto_esperada="D03_jpeg_compressao.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "zero_problemas"],
        zero_problemas_esperado=True,
        is_critical=True,
    ),
    Cenario(
        id="D04", dimensao="D3",
        descricao="Ativo com descolamento >50% — severidade Alta",
        foto_esperada="D04_descolamento.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "problemas_detectados"],
        problemas_esperados=["descolamento"],
    ),
    Cenario(
        id="D05", dimensao="D3",
        descricao="Foto escura mas ativo íntegro — zero problemas no ativo",
        foto_esperada="D05_foto_escura.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "zero_problemas"],
        zero_problemas_esperado=True,
        is_critical=True,
    ),
    Cenario(
        id="D06", dimensao="D3",
        descricao="Ativo amassado + sujo + torto — múltiplos problemas",
        foto_esperada="D06_multiplos_problemas.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "multiplos_problemas"],
        problemas_esperados=["amassado", "sujeira", "torto"],
    ),
    Cenario(
        id="D07", dimensao="D3",
        descricao="Sombra projetada sobre o ativo — não é sujeira",
        foto_esperada="D07_sombra.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "zero_problemas"],
        zero_problemas_esperado=True,
        is_critical=True,
    ),
    Cenario(
        id="D08", dimensao="D3",
        descricao="Ativo com desbotamento leve — gravidade Baixa",
        foto_esperada="D08_desbotamento.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "problemas_detectados"],
        problemas_esperados=["desbotamento"],
    ),

    # -----------------------------------------------------------------------
    # DIMENSÃO 4 — CONSISTÊNCIA DO JSON
    # -----------------------------------------------------------------------
    Cenario(
        id="L01", dimensao="D4",
        descricao="Notas dos pilares = 10, 8, 8, 10 → nota_final deve ser 9",
        foto_esperada="L01_notas_altas.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "consistencia_matematica",
                    "status_coerente", "tipo_ativo_permitido"],
        is_critical=True,
    ),
    Cenario(
        id="L02", dimensao="D4",
        descricao="Preço errado na foto → nota ≤ 4, status reprovado, criterio_eliminatorio preenchido",
        foto_esperada="L02_preco_errado.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "consistencia_matematica",
                    "status_coerente", "criterio_eliminatorio_presente"],
        nota_maxima=4,
        status_esperado="reprovado",
        is_critical=True,
    ),
    Cenario(
        id="L03", dimensao="D4",
        descricao="Ativo ilegível → nota ≤ 3, status reprovado",
        foto_esperada="L03_ilegivel.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "consistencia_matematica",
                    "status_coerente", "criterio_eliminatorio_presente"],
        nota_maxima=3,
        status_esperado="reprovado",
        is_critical=True,
    ),
    Cenario(
        id="L04", dimensao="D4",
        descricao="Nota calculada = 6, sem critério eliminatório → aprovado_com_ressalvas",
        foto_esperada="L04_ressalvas.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "consistencia_matematica", "status_coerente"],
        nota_minima=5,
        nota_maxima=7,
        status_esperado="aprovado_com_ressalvas",
    ),
    Cenario(
        id="L05", dimensao="D4",
        descricao="Nota = 8 → status aprovado",
        foto_esperada="L05_aprovado.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "consistencia_matematica", "status_coerente"],
        nota_minima=8,
        status_esperado="aprovado",
    ),
    Cenario(
        id="L06", dimensao="D4",
        descricao="Penalidade Média (-1) aplicada — nota decresce exatamente 1 ponto",
        foto_esperada="L06_penalidade.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "consistencia_matematica",
                    "penalidades_coerentes"],
        is_critical=True,
    ),
    Cenario(
        id="L07", dimensao="D4",
        descricao="Dois critérios eliminatórios simultâneos — usa menor nota máxima",
        foto_esperada="L07_dois_eliminatorios.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "criterio_eliminatorio_presente"],
        status_esperado="reprovado",
        is_critical=True,
    ),
    Cenario(
        id="L08", dimensao="D4",
        descricao="visualizacao_ok: false mas nota_visibilidade: 10 — inconsistência esperada",
        foto_esperada="L08_inconsistencia.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "visualizacao_vs_nota"],
        is_critical=True,
    ),

    # -----------------------------------------------------------------------
    # DIMENSÃO 5 — ROBUSTEZ COM FOTOS DIFÍCEIS
    # -----------------------------------------------------------------------
    Cenario(
        id="E01", dimensao="D5",
        descricao="Foto extremamente escura",
        foto_esperada="E01_escura.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "confianca_baixa",
                    "limitacoes_nao_vazias"],
        confianca_esperada="baixa",
        limitacoes_nao_vazias=True,
        is_critical=True,
    ),
    Cenario(
        id="E02", dimensao="D5",
        descricao="Ativo cortado pela metade na foto",
        foto_esperada="E02_cortado.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "limitacoes_nao_vazias"],
        limitacoes_nao_vazias=True,
    ),
    Cenario(
        id="E03", dimensao="D5",
        descricao="3+ ativos na mesma foto — avalia apenas o proeminente",
        foto_esperada="E03_multiplos_ativos.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "tipo_ativo_permitido"],
    ),
    Cenario(
        id="E04", dimensao="D5",
        descricao="Ângulo muito oblíquo — sinaliza mas não penaliza o ativo",
        foto_esperada="E04_angulo_obliquo.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "limitacoes_nao_vazias"],
        limitacoes_nao_vazias=True,
    ),
    Cenario(
        id="E05", dimensao="D5",
        descricao="Reflexo forte de flash sobre o ativo",
        foto_esperada="E05_reflexo.jpg",
        validacoes=["json_valido", "chaves_obrigatorias"],
    ),
    Cenario(
        id="E06", dimensao="D5",
        descricao="Foto de altíssima resolução (4K+) — sem micro-defeitos inventados",
        foto_esperada="E06_4k.jpg",
        validacoes=["json_valido", "chaves_obrigatorias"],
    ),
    Cenario(
        id="E07", dimensao="D5",
        descricao="Dedo/mão cobrindo parte do ativo",
        foto_esperada="E07_dedo.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "limitacoes_nao_vazias"],
        limitacoes_nao_vazias=True,
    ),
    Cenario(
        id="E08", dimensao="D5",
        descricao="Foto sem ativo algum — corredor vazio",
        foto_esperada="E08_sem_ativo.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "criterio_eliminatorio_presente"],
        status_esperado="reprovado",
        nota_maxima=0,
        is_critical=True,
    ),
    Cenario(
        id="E09", dimensao="D5",
        descricao="Foto borrada por movimento",
        foto_esperada="E09_borrada.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "confianca_baixa"],
        confianca_esperada="baixa",
    ),
    Cenario(
        id="E10", dimensao="D5",
        descricao="Foto com marca d'água ou timestamp — avalia o ativo normalmente",
        foto_esperada="E10_marca_dagua.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "tipo_ativo_permitido"],
    ),

    # -----------------------------------------------------------------------
    # DIMENSÃO 6 — REGRAS ESPECÍFICAS POR TIPO DE ATIVO
    # -----------------------------------------------------------------------
    Cenario(
        id="R01", dimensao="D6",
        descricao="Ponta gôndola com 90% ocupação, bloco de marca, header — deve aprovar",
        foto_esperada="R01_pg_ok.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "status_coerente"],
        tipo_ativo_esperado="PONTA GÔNDOLA",
        zero_problemas_esperado=False,
        nota_minima=7,
    ),
    Cenario(
        id="R02", dimensao="D6",
        descricao="Ponta gôndola com 40% de ocupação — penalidade Alta",
        foto_esperada="R02_pg_sub_ocupacao.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "problemas_detectados",
                    "penalidade_alta_presente"],
        tipo_ativo_esperado="PONTA GÔNDOLA",
        problemas_esperados=["ocupação"],
    ),
    Cenario(
        id="R03", dimensao="D6",
        descricao="Ponta gôndola sem header/cartaz de comunicação",
        foto_esperada="R03_pg_sem_comunicacao.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "problemas_detectados"],
        tipo_ativo_esperado="PONTA GÔNDOLA",
        problemas_esperados=["comunicação", "header"],
    ),
    Cenario(
        id="R04", dimensao="D6",
        descricao="Ponta gôndola com mix caótico de categorias",
        foto_esperada="R04_pg_mix_caotico.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "problemas_detectados"],
        tipo_ativo_esperado="PONTA GÔNDOLA",
        problemas_esperados=["categorias", "mistura"],
    ),
    Cenario(
        id="R05", dimensao="D6",
        descricao="Wobbler dobrado — problema de fixação e forma",
        foto_esperada="R05_wobbler_dobrado.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "problemas_detectados"],
        tipo_ativo_esperado="WOBBLER",
        problemas_esperados=["dobrado", "dobra"],
    ),
    Cenario(
        id="R06", dimensao="D6",
        descricao="Faixa de gôndola com gaps entre segmentos",
        foto_esperada="R06_faixa_gaps.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "problemas_detectados"],
        tipo_ativo_esperado="PDV IMPRESSO (FAIXA GÔNDOLA)",
        problemas_esperados=["gap", "alinhamento"],
    ),
    Cenario(
        id="R07", dimensao="D6",
        descricao="Adesivo de chão com bolhas",
        foto_esperada="R07_adesivo_bolhas.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "problemas_detectados"],
        tipo_ativo_esperado="ADESIVO DE CHÃO",
        problemas_esperados=["bolha"],
    ),
    Cenario(
        id="R08", dimensao="D6",
        descricao="Banner com ondulação visível",
        foto_esperada="R08_banner_ondulacao.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "problemas_detectados"],
        problemas_esperados=["ondulação", "ondulacao"],
    ),
    Cenario(
        id="R09", dimensao="D6",
        descricao="Cartaz de preço sem preço legível — penaliza conteúdo",
        foto_esperada="R09_cartaz_sem_preco.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "preco_null"],
        preco_esperado=None,
        is_critical=True,
    ),
    Cenario(
        id="R10", dimensao="D6",
        descricao="Display de chão com peça faltando — montagem incompleta",
        foto_esperada="R10_display_incompleto.jpg",
        validacoes=["json_valido", "chaves_obrigatorias", "problemas_detectados"],
        tipo_ativo_esperado="DISPLAY DE CHÃO",
        problemas_esperados=["peça", "peca", "faltando", "incompleto"],
    ),
]


# ---------------------------------------------------------------------------
# Motor de validação
# ---------------------------------------------------------------------------

@dataclass
class ResultadoCenario:
    cenario_id: str
    dimensao: str
    descricao: str
    foto_usada: Optional[str]
    pass_: bool
    critical_fail: bool = False
    erros: List[str] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)
    json_bruto: Optional[Dict] = None
    excecao: Optional[str] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["pass"] = d.pop("pass_")
        return d


def _nota_esperada_dos_pilares(resp: Dict) -> int:
    """Recalcula nota esperada a partir dos 4 pilares (sem penalidades)."""
    pilares = [
        resp.get("nota_posicionamento", 0),
        resp.get("nota_visibilidade", 0),
        resp.get("nota_integridade", 0),
        resp.get("nota_conteudo", 0),
    ]
    return round(sum(pilares) / 4)


def _extrair_desconto_total(resp: Dict) -> float:
    """Soma penalidades aplicadas a partir do campo penalidades_aplicadas."""
    total = 0.0
    for p in resp.get("penalidades_aplicadas", []):
        # Tenta extrair número do padrão "(-X)" ou "(-X.X)"
        import re
        match = re.search(r"\(-(\d+(?:\.\d+)?)\)", p)
        if match:
            total += float(match.group(1))
    return total


def validar_cenario(cenario: Cenario, resp: Dict) -> List[str]:
    """
    Executa as validações configuradas para o cenário.
    Retorna lista de strings de erros (vazia = pass).
    """
    erros = []
    validacoes = set(cenario.validacoes)

    # --- json_valido (implícito — chegou até aqui = JSON foi parseado)
    # --- chaves_obrigatorias
    if "chaves_obrigatorias" in validacoes:
        faltantes = [k for k in CHAVES_OBRIGATORIAS if k not in resp]
        if faltantes:
            erros.append(f"Chaves faltantes: {faltantes}")

    # --- tipo_ativo_permitido (sempre aplicado implicitamente)
    tipo = resp.get("tipo_ativo", "")
    if tipo not in ALLOWED_TIPOS_ATIVO:
        erros.append(f"tipo_ativo '{tipo}' fora da lista permitida")

    # --- tipo_ativo (match exato)
    if "tipo_ativo" in validacoes and cenario.tipo_ativo_esperado:
        if tipo != cenario.tipo_ativo_esperado:
            erros.append(
                f"tipo_ativo: esperado '{cenario.tipo_ativo_esperado}', "
                f"obtido '{tipo}'"
            )

    # --- preco_null
    if "preco_null" in validacoes and cenario.preco_esperado is None:
        if resp.get("preço") is not None:
            erros.append(
                f"preço: esperado null, obtido '{resp.get('preço')}' "
                f"[ALUCINAÇÃO DE PREÇO - critical fail]"
            )

    # --- preco_exato
    if "preco_exato" in validacoes and cenario.preco_esperado not in (None, "QUALQUER"):
        if resp.get("preço") != cenario.preco_esperado:
            erros.append(
                f"preço: esperado '{cenario.preco_esperado}', "
                f"obtido '{resp.get('preço')}'"
            )

    # --- zero_problemas
    if "zero_problemas" in validacoes and cenario.zero_problemas_esperado:
        problemas = resp.get("problemas", [])
        if problemas:
            erros.append(
                f"Falso positivo: problemas reportados indevidamente: {problemas}"
            )

    # --- problemas_detectados (verifica que ao menos uma keyword aparece)
    if "problemas_detectados" in validacoes and cenario.problemas_esperados:
        problemas = " ".join(resp.get("problemas", [])).lower()
        encontrou = any(kw.lower() in problemas for kw in cenario.problemas_esperados)
        if not encontrou:
            erros.append(
                f"Problema esperado não detectado. Keywords: {cenario.problemas_esperados}. "
                f"Problemas reportados: {resp.get('problemas', [])}"
            )

    # --- multiplos_problemas
    if "multiplos_problemas" in validacoes and cenario.problemas_esperados:
        problemas_texto = " ".join(resp.get("problemas", [])).lower()
        nao_encontrados = [
            kw for kw in cenario.problemas_esperados
            if kw.lower() not in problemas_texto
        ]
        if nao_encontrados:
            erros.append(
                f"Problemas não detectados: {nao_encontrados}. "
                f"Reportados: {resp.get('problemas', [])}"
            )

    # --- status_coerente
    if "status_coerente" in validacoes:
        nota = resp.get("nota", -1)
        status = resp.get("status", "")
        if status not in STATUS_VALIDOS:
            erros.append(f"status inválido: '{status}'")
        elif 8 <= nota <= 10 and status != "aprovado":
            erros.append(f"nota={nota} deveria ser 'aprovado', obtido '{status}'")
        elif 5 <= nota <= 7 and status != "aprovado_com_ressalvas":
            erros.append(
                f"nota={nota} deveria ser 'aprovado_com_ressalvas', obtido '{status}'"
            )
        elif 0 <= nota <= 4 and status != "reprovado":
            erros.append(f"nota={nota} deveria ser 'reprovado', obtido '{status}'")

        if cenario.status_esperado and status != cenario.status_esperado:
            erros.append(
                f"status_esperado='{cenario.status_esperado}', obtido='{status}'"
            )

    # --- nota_minima / nota_maxima
    nota = resp.get("nota", -1)
    if cenario.nota_minima is not None and nota < cenario.nota_minima:
        erros.append(f"nota={nota} abaixo do mínimo esperado {cenario.nota_minima}")
    if cenario.nota_maxima is not None and nota > cenario.nota_maxima:
        erros.append(
            f"nota={nota} acima do máximo esperado {cenario.nota_maxima} "
            f"(critério eliminatório pode não ter sido aplicado)"
        )

    # --- consistencia_matematica
    if "consistencia_matematica" in validacoes:
        nota_pilares = _nota_esperada_dos_pilares(resp)
        desconto = _extrair_desconto_total(resp)
        nota_esperada_final = max(0, nota_pilares - int(desconto))
        nota_real = resp.get("nota", -1)
        # Tolerância de ±1 pois penalidades podem ter casas decimais
        if abs(nota_real - nota_esperada_final) > 1:
            erros.append(
                f"Inconsistência matemática: pilares={nota_pilares}, "
                f"desconto={desconto}, esperado≈{nota_esperada_final}, "
                f"obtido={nota_real}"
            )

    # --- criterio_eliminatorio_presente
    if "criterio_eliminatorio_presente" in validacoes:
        ce = resp.get("criterio_eliminatorio")
        if not ce:
            erros.append("criterio_eliminatorio deveria estar preenchido mas está null/vazio")
        status = resp.get("status", "")
        if ce and status != "reprovado":
            erros.append(
                f"criterio_eliminatorio preenchido mas status='{status}' "
                f"(deveria ser 'reprovado')"
            )

    # --- penalidades_coerentes
    if "penalidades_coerentes" in validacoes:
        pens = resp.get("penalidades_aplicadas", [])
        problemas = resp.get("problemas", [])
        if pens and not problemas:
            erros.append("penalidades_aplicadas preenchidas mas problemas=[]")
        if problemas and not pens:
            erros.append("problemas reportados mas penalidades_aplicadas=[]")

    # --- penalidade_alta_presente
    if "penalidade_alta_presente" in validacoes:
        pens = " ".join(resp.get("penalidades_aplicadas", [])).lower()
        if "alta" not in pens:
            erros.append(
                f"Penalidade 'Alta' esperada mas não encontrada: "
                f"{resp.get('penalidades_aplicadas', [])}"
            )

    # --- visualizacao_vs_nota
    if "visualizacao_vs_nota" in validacoes:
        vis_ok = resp.get("visualizacao_ok")
        nota_vis = resp.get("nota_visibilidade", -1)
        if vis_ok is False and nota_vis >= 8:
            erros.append(
                f"Inconsistência: visualizacao_ok=false mas nota_visibilidade={nota_vis}"
            )
        if vis_ok is True and nota_vis <= 3:
            erros.append(
                f"Inconsistência: visualizacao_ok=true mas nota_visibilidade={nota_vis}"
            )

    # --- confianca_baixa
    if "confianca_baixa" in validacoes and cenario.confianca_esperada == "baixa":
        c = resp.get("confianca_avaliacao", "")
        if c not in ("baixa", "media"):
            erros.append(
                f"confianca_avaliacao: esperado 'baixa' (ou 'media'), obtido '{c}'"
            )

    # --- limitacoes_nao_vazias
    if "limitacoes_nao_vazias" in validacoes and cenario.limitacoes_nao_vazias:
        lim = resp.get("limitacoes_foto", [])
        if not lim:
            erros.append("limitacoes_foto deveria ter ≥1 item mas está vazia")

    # --- tipo_ativo_permitido
    if "tipo_ativo_permitido" in validacoes:
        if tipo not in ALLOWED_TIPOS_ATIVO:
            erros.append(f"tipo_ativo '{tipo}' não está na lista permitida")

    return erros


# ---------------------------------------------------------------------------
# Executor principal
# ---------------------------------------------------------------------------

def carregar_foto(foto_path: Path) -> Optional[bytes]:
    if foto_path.exists():
        return foto_path.read_bytes()
    return None


def executar_cenario(
    cenario: Cenario,
    service: Any,
    photos_dir: Path,
) -> ResultadoCenario:
    foto_path = photos_dir / cenario.foto_esperada
    foto_bytes = carregar_foto(foto_path)

    if foto_bytes is None:
        return ResultadoCenario(
            cenario_id=cenario.id,
            dimensao=cenario.dimensao,
            descricao=cenario.descricao,
            foto_usada=None,
            pass_=False,
            erros=[f"Foto não encontrada: {foto_path}"],
            avisos=["Cenário pulado por falta de foto"],
        )

    try:
        resp = service.auditar_ativo_pdv(foto_bytes)
        erros = validar_cenario(cenario, resp)
        is_critical_fail = cenario.is_critical and bool(erros)
        return ResultadoCenario(
            cenario_id=cenario.id,
            dimensao=cenario.dimensao,
            descricao=cenario.descricao,
            foto_usada=str(foto_path),
            pass_=len(erros) == 0,
            critical_fail=is_critical_fail,
            erros=erros,
            json_bruto=resp,
        )
    except Exception as exc:
        return ResultadoCenario(
            cenario_id=cenario.id,
            dimensao=cenario.dimensao,
            descricao=cenario.descricao,
            foto_usada=str(foto_path),
            pass_=False,
            critical_fail=cenario.is_critical,
            erros=[f"Exceção durante execução: {exc}"],
            excecao=traceback.format_exc(),
        )


# ---------------------------------------------------------------------------
# Geração de report
# ---------------------------------------------------------------------------

DIMENSAO_NOMES = {
    "D1": "classificacao_ativos",
    "D2": "extracao_preco",
    "D3": "deteccao_problemas",
    "D4": "consistencia_json",
    "D5": "robustez_fotos",
    "D6": "regras_especificas",
}

METAS = {
    "D1": 0.90,
    "D2": 0.90,  # mas 100% nos null cases
    "D3": 1.00,  # 100% nos cenários clean
    "D4": 1.00,
    "D5": 1.00,
    "D6": 0.85,
}

BLOCKERS = {"D2", "D3", "D4", "D5"}  # critical dims


def gerar_report(resultados: List[ResultadoCenario]) -> Dict:
    # Cenários com foto disponível (excluindo pulados)
    executados = [r for r in resultados if r.foto_usada is not None]
    aprovados = [r for r in executados if r.pass_]
    reprovados = [r for r in executados if not r.pass_]
    critical_fails = [r for r in executados if r.critical_fail]

    por_dimensao = {}
    for dim_code, dim_nome in DIMENSAO_NOMES.items():
        dim_res = [r for r in executados if r.dimensao == dim_code]
        dim_pass = [r for r in dim_res if r.pass_]
        dim_fail = [r for r in dim_res if not r.pass_]
        taxa = len(dim_pass) / len(dim_res) if dim_res else 0
        meta = METAS[dim_code]
        atingiu = taxa >= meta

        extra = {}
        if dim_code == "D2":
            null_cenarios = {"P03", "P04", "P05", "P07"}
            null_res = [r for r in dim_res if r.cenario_id in null_cenarios]
            null_pass = [r for r in null_res if r.pass_]
            extra["null_cases_taxa"] = f"{len(null_pass)}/{len(null_res)}"
            extra["null_cases_meta"] = "100%"
            extra["null_cases_ok"] = len(null_pass) == len(null_res)
            extra["critical_fails"] = len([r for r in dim_res if r.critical_fail])

        if dim_code == "D3":
            clean_cenarios = {"D01", "D03", "D05", "D07"}
            clean_res = [r for r in dim_res if r.cenario_id in clean_cenarios]
            clean_pass = [r for r in clean_res if r.pass_]
            extra["falsos_positivos"] = len(clean_cenarios) - len(clean_pass)

        if dim_code == "D5":
            extra["jsons_invalidos"] = len([r for r in dim_fail if r.excecao])

        por_dimensao[dim_nome] = {
            "dimensao_code": dim_code,
            "total": len(dim_res),
            "pass": len(dim_pass),
            "fail": len(dim_fail),
            "taxa": f"{taxa:.0%}",
            "meta": f"{meta:.0%}",
            "atingiu_meta": atingiu,
            "is_blocker": dim_code in BLOCKERS,
            **extra,
        }

    # Veredicto final
    blockers_falhando = [
        dim_code for dim_code in BLOCKERS
        if not por_dimensao[DIMENSAO_NOMES[dim_code]]["atingiu_meta"]
    ]
    nao_blockers_falhando = [
        dim_code for dim_code in (set(DIMENSAO_NOMES) - BLOCKERS)
        if not por_dimensao[DIMENSAO_NOMES[dim_code]]["atingiu_meta"]
    ]

    if blockers_falhando or critical_fails:
        veredicto = "REPROVADO"
    elif nao_blockers_falhando:
        veredicto = "APROVADO COM RESSALVAS"
    else:
        veredicto = "APROVADO"

    # Padrões de erros recorrentes
    todos_erros = []
    for r in reprovados:
        todos_erros.extend(r.erros)

    from collections import Counter
    palavras_chave = [
        "tipo_ativo", "preço", "null", "alucinação", "inconsistência",
        "penalidade", "status", "nota", "problema", "limitacoes", "chaves",
    ]
    padroes = {}
    for kw in palavras_chave:
        cnt = sum(1 for e in todos_erros if kw.lower() in e.lower())
        if cnt > 0:
            padroes[kw] = cnt

    problemas_recorrentes = [
        f"{kw}: {cnt} ocorrência(s)"
        for kw, cnt in sorted(padroes.items(), key=lambda x: -x[1])
    ]

    # Cenários pulados
    pulados = [r for r in resultados if r.foto_usada is None]

    return {
        "gerado_em": datetime.now().isoformat(),
        "resumo_geral": {
            "total_cenarios": len(CENARIOS),
            "executados": len(executados),
            "pulados_sem_foto": len(pulados),
            "aprovados": len(aprovados),
            "reprovados": len(reprovados),
            "taxa_aprovacao": f"{len(aprovados)/len(executados):.0%}" if executados else "N/A",
            "critical_fails": len(critical_fails),
            "veredicto_final": veredicto,
        },
        "por_dimensao": por_dimensao,
        "critical_fails": [
            {
                "cenario_id": r.cenario_id,
                "descricao": r.descricao,
                "erros": r.erros,
            }
            for r in critical_fails
        ],
        "cenarios_reprovados": [
            {
                "cenario_id": r.cenario_id,
                "dimensao": r.dimensao,
                "descricao": r.descricao,
                "erros": r.erros,
                "is_critical": r.critical_fail,
            }
            for r in reprovados
        ],
        "cenarios_pulados": [
            {"cenario_id": r.cenario_id, "motivo": r.erros[0] if r.erros else "?"}
            for r in pulados
        ],
        "problemas_recorrentes": problemas_recorrentes,
        "recomendacoes_prompt": _gerar_recomendacoes(reprovados),
    }


def _gerar_recomendacoes(reprovados: List[ResultadoCenario]) -> List[str]:
    recomendacoes = []
    ids = {r.cenario_id for r in reprovados}

    if ids & {"C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10"}:
        recomendacoes.append(
            "Reforçar dicas de disambiguação na Seção 1.1 com exemplos fotográficos "
            "por tipo de ativo (wobblers vs stoppers, ilhas vs displays, etc.)"
        )
    if ids & {"P03", "P04", "P05", "P07"}:
        recomendacoes.append(
            "Adicionar exemplos negativos explícitos na Seção 9 (Preço) sobre "
            "quando NÃO extrair preço — incluir caso de preço parcialmente coberto "
            "e preço fora do ativo principal."
        )
    if ids & {"D01", "D03", "D05", "D07"}:
        recomendacoes.append(
            "Ampliar Seção 2 (Regra de Evidência Visual) com exemplos visuais de "
            "artefatos JPEG, sombras e variações de iluminação que NÃO devem ser "
            "reportados como problemas."
        )
    if ids & {"L01", "L02", "L03", "L06", "L07", "L08"}:
        recomendacoes.append(
            "Incluir na Seção 4 um exemplo passo-a-passo do cálculo completo: "
            "pilares → média → penalidades → travas eliminatórias → nota_final."
        )
    if ids & {"E01", "E02", "E07", "E08", "E09"}:
        recomendacoes.append(
            "Fortalecer Seção 8 (Qualidade da Foto) com critérios claros para "
            "definir quando confianca_avaliacao deve ser 'baixa' vs 'media'."
        )
    if ids & {"R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10"}:
        recomendacoes.append(
            "Expandir Seção 7 (Regras por Tipo) com checklist detalhado por ativo — "
            "especialmente para PONTA GÔNDOLA (ocupação mínima 70%, bloqueio de marca, "
            "comunicação obrigatória) e WOBBLER/STOPPER (fixação e orientação)."
        )

    if not recomendacoes:
        recomendacoes.append("Nenhuma recomendação crítica identificada — prompt está bem calibrado.")

    return recomendacoes


# ---------------------------------------------------------------------------
# Saída por terminal
# ---------------------------------------------------------------------------

def imprimir_report(report: Dict, verbose: bool = False) -> None:
    r = report["resumo_geral"]
    print("\n" + "=" * 70)
    print("  REPORT DE QUALIDADE — AGENTE DE ANÁLISE PDV")
    print("=" * 70)
    print(f"  Gerado em : {report['gerado_em']}")
    print(f"  Veredicto : {r['veredicto_final']}")
    print(f"  Executados: {r['executados']}/{r['total_cenarios']} cenários")
    print(f"  Aprovados : {r['aprovados']} ({r['taxa_aprovacao']})")
    print(f"  Critical  : {r['critical_fails']} falhas críticas")
    if r["pulados_sem_foto"] > 0:
        print(f"  Pulados   : {r['pulados_sem_foto']} (foto não encontrada)")

    print("\n  Por dimensão:")
    print(f"  {'DIM':<28} {'PASS/TOTAL':>12} {'TAXA':>8} {'META':>8} {'META?':>7} {'BLOCKER?':>9}")
    print("  " + "-" * 70)
    for nome, dim in report["por_dimensao"].items():
        ok = "✓" if dim["atingiu_meta"] else "✗"
        bl = "SIM" if dim["is_blocker"] else "-"
        print(
            f"  {nome:<28} {dim['pass']:>5}/{dim['total']:<6} "
            f"{dim['taxa']:>8} {dim['meta']:>8} {ok:>7} {bl:>9}"
        )

    if report["critical_fails"]:
        print("\n  CRITICAL FAILS:")
        for cf in report["critical_fails"]:
            print(f"    [{cf['cenario_id']}] {cf['descricao']}")
            for e in cf["erros"]:
                print(f"      → {e}")

    if report["problemas_recorrentes"]:
        print("\n  Padrões de erro recorrentes:")
        for p in report["problemas_recorrentes"]:
            print(f"    • {p}")

    if report["recomendacoes_prompt"]:
        print("\n  Recomendações para o prompt:")
        for i, rec in enumerate(report["recomendacoes_prompt"], 1):
            print(f"    {i}. {rec}")

    if verbose and report["cenarios_reprovados"]:
        print("\n  Detalhes dos cenários reprovados:")
        for cr in report["cenarios_reprovados"]:
            flag = "[CRITICAL] " if cr["is_critical"] else ""
            print(f"    {flag}[{cr['cenario_id']}] {cr['descricao']}")
            for e in cr["erros"]:
                print(f"      → {e}")

    print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="QA Evaluation — Agente de Análise PDV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--photos-dir", "-p",
        type=Path,
        default=Path("fotos_teste"),
        help="Diretório com as fotos de teste (default: ./fotos_teste)",
    )
    parser.add_argument(
        "--modelo", "-m",
        default="gpt-4o-mini",
        help="Modelo LLM: gpt-4o-mini | gpt-4o | claude-3-5-sonnet | gemini-pro-vision",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Arquivo JSON de saída do report (opcional)",
    )
    parser.add_argument(
        "--output-raw", "-r",
        type=Path,
        default=None,
        help="Arquivo JSON com respostas brutas do agente (opcional)",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="Lista todos os cenários e sai sem executar",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Executa apenas o cenário especificado (ex.: C01)",
    )
    parser.add_argument(
        "--foto",
        type=Path,
        default=None,
        help="Foto a usar no --scenario avulso",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Imprime detalhes de todos os cenários reprovados",
    )
    parser.add_argument(
        "--dimensao", "-d",
        type=str,
        default=None,
        help="Filtra por dimensão: D1..D6",
    )
    args = parser.parse_args()

    # --list-scenarios
    if args.list_scenarios:
        print(f"\n{'ID':<6} {'DIM':<4} {'CRÍTICO':<8} {'FOTO ESPERADA':<35} DESCRIÇÃO")
        print("-" * 110)
        for c in CENARIOS:
            critico = "★" if c.is_critical else ""
            print(
                f"{c.id:<6} {c.dimensao:<4} {critico:<8} "
                f"{c.foto_esperada:<35} {c.descricao}"
            )
        print(f"\nTotal: {len(CENARIOS)} cenários\n")
        return

    # Filtro por cenário único
    cenarios_alvo = CENARIOS
    if args.scenario:
        cenarios_alvo = [c for c in CENARIOS if c.id == args.scenario]
        if not cenarios_alvo:
            print(f"Erro: cenário '{args.scenario}' não encontrado.")
            sys.exit(1)
        # Override da foto se passada via --foto
        if args.foto:
            cenarios_alvo[0].foto_esperada = args.foto.name
            args.photos_dir = args.foto.parent

    # Filtro por dimensão
    if args.dimensao:
        cenarios_alvo = [c for c in cenarios_alvo if c.dimensao == args.dimensao.upper()]
        if not cenarios_alvo:
            print(f"Nenhum cenário encontrado para dimensão '{args.dimensao}'.")
            sys.exit(1)

    print(f"\nInicializando serviço com modelo: {args.modelo}")
    try:
        from app.api.v1.analise_fotos.services import AnalisePDVService
        service = AnalisePDVService(modelo_llm=args.modelo)
    except Exception as exc:
        print(f"Erro ao inicializar serviço: {exc}")
        sys.exit(1)

    print(f"Diretório de fotos: {args.photos_dir.resolve()}")
    print(f"Executando {len(cenarios_alvo)} cenário(s)...\n")

    resultados: List[ResultadoCenario] = []
    raw_responses: Dict[str, Any] = {}

    for cenario in cenarios_alvo:
        sys.stdout.write(f"  [{cenario.id}] {cenario.descricao[:55]:<55} ")
        sys.stdout.flush()
        resultado = executar_cenario(cenario, service, args.photos_dir)
        resultados.append(resultado)

        if resultado.foto_usada is None:
            print("SKIP (sem foto)")
        elif resultado.pass_:
            print("PASS")
        else:
            flag = " [CRITICAL]" if resultado.critical_fail else ""
            print(f"FAIL{flag}")
            for e in resultado.erros[:2]:
                print(f"       → {e}")

        if resultado.json_bruto:
            raw_responses[cenario.id] = resultado.json_bruto

    report = gerar_report(resultados)
    imprimir_report(report, verbose=args.verbose)

    # Salvar report JSON
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"Report salvo em: {args.output}")

    # Salvar respostas brutas
    if args.output_raw:
        args.output_raw.write_text(json.dumps(raw_responses, ensure_ascii=False, indent=2))
        print(f"Respostas brutas salvas em: {args.output_raw}")

    # Exit code
    veredicto = report["resumo_geral"]["veredicto_final"]
    sys.exit(0 if veredicto == "APROVADO" else 1)


if __name__ == "__main__":
    main()
