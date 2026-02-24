import base64
import json
import os
from typing import Dict, Literal, List, Any
from sqlalchemy.orm import Session
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai
from app.config import settings
from app.core.logging import logger
from app.models.plantas.configuracao import PlantaConfiguracao

from app.services.base_ocr_service import BaseOCRService

class PlantasService:
    """
    Serviço para análise de planogramas, extração de endereços via OCR e inteligência LLM.
    """

    def __init__(self, db: Session, modelo_llm: str = "gpt-4o"):
        self.db = db
        self.modelo_llm = modelo_llm
        self.ocr_service = BaseOCRService()

        # Inicializar clientes conforme modelo
        if modelo_llm.startswith("gpt"):
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        elif modelo_llm.startswith("claude"):
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif modelo_llm.startswith("gemini"):
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.client = genai.GenerativeModel(modelo_llm)

        # Carregar prompt
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "prompts",
            "analise_share.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.PROMPT_ANALISE = f.read()

    def mapear_enderecos_planta(self, loja_id: str, imagem_bytes: bytes) -> Dict[str, Any]:
        """
        Orquestra a contagem via OCR e o cruzamento com LLM Vision.
        """
        import base64
        logger.info(f"Iniciando mapeamento de plantas V2 com modelo {self.modelo_llm}")

        imagem_base64 = base64.b64encode(imagem_bytes).decode('utf-8')
        
        # 1. Executar OCR Base de Alta Confiança (Filtro Geométrico e Textual Real)
        resultado_ocr = self.ocr_service.detectar_texto(imagem_base64)
        lista_deteccoes = resultado_ocr.get("deteccoes", [])
        dimensoes = resultado_ocr.get("dimensoes", {"width": 1000, "height": 1000})

        # Prepara a string de Evidências Reais para não permitir que o LLM invente nomes
        # Enviamos também os cálculos de coordenadas já prontos para ele apenas "repassar" no JSON
        evidencias_texto = "EVIDÊNCIAS DE TEXTO DETECTADAS (USE APENAS ESTES DADOS):\n"
        id_evidencia = 1
        
        for det in lista_deteccoes:
            bbox = det["bbox"]
            # bbox = [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
            x_center = (bbox[0][0] + bbox[2][0]) / 2.0
            y_center = (bbox[0][1] + bbox[2][1]) / 2.0
            
            x_pct = round(x_center / dimensoes["width"], 4)
            y_pct = round(y_center / dimensoes["height"], 4)
            
            # Adiciona os percentuais no objeto original para uso futuro
            det["x_pct"] = x_pct
            det["y_pct"] = y_pct
            
            evidencias_texto += f"[ID: {id_evidencia}] TEXTO: '{det['texto']}' | x_pct: {x_pct} | y_pct: {y_pct}\n"
            id_evidencia += 1

        prompt_enriquecido = f"{self.PROMPT_ANALISE}\n\n{evidencias_texto}"

        # 2. Acionar LLM para Classificar, Associar e Limpar os Dados
        logger.info(f"Acionando LLM com {len(lista_deteccoes)} blocos de texto nativos...")
        
        if self.modelo_llm.startswith("gpt"):
            resultado_llm = self._analisar_com_openai(imagem_bytes, prompt_personalizado=prompt_enriquecido)
        elif self.modelo_llm.startswith("claude"):
            resultado_llm = self._analisar_com_anthropic(imagem_bytes, prompt_personalizado=prompt_enriquecido)
        elif self.modelo_llm.startswith("gemini"):
            resultado_llm = self._analisar_com_gemini(imagem_bytes, prompt_personalizado=prompt_enriquecido)
        else:
            raise ValueError(f"Modelo não suportado: {self.modelo_llm}")

        # 3. Consolidar Resposta do Contrato V2
        return self._consolidar_relatorio(resultado_llm)

    def _consolidar_relatorio(self, payload_llm: Dict) -> Dict[str, Any]:
        """
        Formata o JSON de saída garantindo as quebras estatísticas obrigatórias do Contrato PMC.
        """
        enderecos_brutos = payload_llm.get("enderecos", [])
        alertas = payload_llm.get("alertas", [])
        
        enderecos_finais = []
        qtd_descartada = 0
        qtd_cadastravel = 0

        for end in enderecos_brutos:
            confidence = end.get("confidence", 0.0)
            
            # Garante float
            if isinstance(confidence, str):
                try: confidence = float(confidence)
                except: confidence = 0.5

            if confidence >= 0.40:
                qtd_cadastravel += 1
                enderecos_finais.append({
                    "codigo": end.get("codigo", ""),
                    "nome": end.get("nome", ""),
                    "categoria_id": end.get("categoria_id"),
                    "tipo_endereco_id": end.get("tipo_endereco_id", 0),
                    "confidence": confidence,
                    "x_pct": end.get("x_pct", 0.0),
                    "y_pct": end.get("y_pct", 0.0),
                    "alertas": end.get("alertas", [])
                })
            else:
                qtd_descartada += 1

        relatorio = {
            "quantidade_detectada": len(enderecos_brutos),
            "quantidade_cadastravel": qtd_cadastravel,
            "quantidade_descartada": qtd_descartada
        }

        return {
            "enderecos": enderecos_finais,
            "alertas": alertas,
            "relatorio": relatorio
        }


    def _analisar_com_openai(self, imagem_bytes: bytes, prompt_personalizado: str = None) -> Dict:
        imagem_base64 = base64.b64encode(imagem_bytes).decode('utf-8')
        prompt = prompt_personalizado if prompt_personalizado else self.PROMPT_ANALISE
        response = self.client.chat.completions.create(
            model=self.modelo_llm,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagem_base64}", "detail": "high"}}
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    def _analisar_com_anthropic(self, imagem_bytes: bytes, prompt_personalizado: str = None) -> Dict:
        imagem_base64 = base64.b64encode(imagem_bytes).decode('utf-8')
        prompt = prompt_personalizado if prompt_personalizado else self.PROMPT_ANALISE
        response = self.client.messages.create(
            model=self.modelo_llm,
            max_tokens=2000,
            temperature=0.1,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": imagem_base64}},
                    {"type": "text", "text": prompt}
                ]
            }]
        )
        res_text = response.content[0].text
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        return json.loads(res_text)

    def _analisar_com_gemini(self, imagem_bytes: bytes, prompt_personalizado: str = None) -> Dict:
        from PIL import Image
        import io
        prompt = prompt_personalizado if prompt_personalizado else self.PROMPT_ANALISE
        imagem = Image.open(io.BytesIO(imagem_bytes))
        response = self.client.generate_content(
            [prompt, imagem],
            generation_config={"temperature": 0.1, "max_output_tokens": 2000}
        )
        res_text = response.text
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        return json.loads(res_text)
