import base64
import json
import os
from typing import Dict, Literal
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai
from app.config import settings
from app.core.logging import logger

class AnalisePDVService:
    """
    Serviço para análise de materiais promocionais de PDV usando LLMs com visão.
    """

    def __init__(self, modelo_llm: str = "gpt-4o"):
        """
        Inicializa o serviço com o modelo de LLM especificado.

        Args:
            modelo_llm: 'gpt-4o' | 'claude-3-5-sonnet' | 'gemini-pro-vision'
        """
        self.modelo_llm = modelo_llm

        # Inicializar clientes conforme modelo
        if modelo_llm.startswith("gpt"):
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        elif modelo_llm.startswith("claude"):
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif modelo_llm.startswith("gemini"):
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.client = genai.GenerativeModel(modelo_llm)

        # Carregar prompt do arquivo
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "prompts",
            "auditoria_pdv.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.PROMPT_AUDITORIA = f.read()

    def auditar_ativo_pdv(self, imagem_bytes: bytes) -> Dict:
        """
        Analisa imagem de ativo de PDV e retorna auditoria estruturada.

        Args:
            imagem_bytes: Bytes da imagem

        Returns:
            Dict com resultado da auditoria conforme schema
        """
        logger.info(f"Iniciando auditoria com modelo {self.modelo_llm}")

        # Chamar LLM apropriado
        if self.modelo_llm.startswith("gpt"):
            resultado = self._auditar_com_openai(imagem_bytes)
        elif self.modelo_llm.startswith("claude"):
            resultado = self._auditar_com_anthropic(imagem_bytes)
        elif self.modelo_llm.startswith("gemini"):
            resultado = self._auditar_com_gemini(imagem_bytes)
        else:
            raise ValueError(f"Modelo não suportado: {self.modelo_llm}")

        # Validar e retornar
        return self._validar_resultado(resultado)

    def _auditar_com_openai(self, imagem_bytes: bytes) -> Dict:
        """Auditoria usando GPT-4 Vision."""

        # Converter imagem para base64
        imagem_base64 = base64.b64encode(imagem_bytes).decode('utf-8')

        response = self.client.chat.completions.create(
            model=self.modelo_llm,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.PROMPT_AUDITORIA
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{imagem_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0.1,  # Baixa temperatura para consistência
            response_format={"type": "json_object"}  # Forçar JSON
        )

        resultado_json = response.choices[0].message.content
        return json.loads(resultado_json)

    def _auditar_com_anthropic(self, imagem_bytes: bytes) -> Dict:
        """Auditoria usando Claude 3.5 Sonnet."""

        # Converter imagem para base64
        imagem_base64 = base64.b64encode(imagem_bytes).decode('utf-8')

        response = self.client.messages.create(
            model=self.modelo_llm,
            max_tokens=2000,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": imagem_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": self.PROMPT_AUDITORIA
                        }
                    ]
                }
            ]
        )

        resultado_texto = response.content[0].text

        # Extrair JSON (Claude pode retornar texto + JSON)
        if "```json" in resultado_texto:
            resultado_texto = resultado_texto.split("```json")[1].split("```")[0].strip()

        return json.loads(resultado_texto)

    def _auditar_com_gemini(self, imagem_bytes: bytes) -> Dict:
        """Auditoria usando Gemini Pro Vision."""

        from PIL import Image
        import io

        # Converter bytes para PIL Image
        imagem = Image.open(io.BytesIO(imagem_bytes))

        response = self.client.generate_content(
            [self.PROMPT_AUDITORIA, imagem],
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 2000
            }
        )

        resultado_texto = response.text

        # Extrair JSON
        if "```json" in resultado_texto:
            resultado_texto = resultado_texto.split("```json")[1].split("```")[0].strip()

        return json.loads(resultado_texto)

    def _validar_resultado(self, resultado: Dict) -> Dict:
        """
        Valida se o resultado contém todas as chaves obrigatórias.

        Raises:
            ValueError: Se faltar alguma chave obrigatória
        """
        chaves_obrigatorias = [
            "nota", "nota_posicionamento", "nota_visibilidade",
            "nota_integridade", "nota_conteudo", "status",
            "tipo_ativo", "marca", "visualizacao_ok", "parecer",
            "problemas", "penalidades_aplicadas", "criterio_eliminatorio",
            "recomendacao", "preço", "confianca_avaliacao", "limitacoes_foto"
        ]

        chaves_faltantes = [k for k in chaves_obrigatorias if k not in resultado]

        if chaves_faltantes:
            logger.error(f"Chaves faltantes no resultado: {chaves_faltantes}")
            # Do not raise error to let some flexibility if LLM skips some fields? Let's follow original:
            raise ValueError(f"Resultado incompleto. Chaves faltantes: {chaves_faltantes}")

        # Validar tipos
        assert isinstance(resultado["nota"], int) and 0 <= resultado["nota"] <= 10
        assert resultado["status"] in ["aprovado", "aprovado_com_ressalvas", "reprovado"]
        assert resultado["confianca_avaliacao"] in ["alta", "media", "baixa"]

        logger.info(f"Auditoria concluída: nota={resultado['nota']}, status={resultado['status']}")

        return resultado
