import easyocr
import cv2
import numpy as np
from typing import List, Dict
import base64

class BaseOCRService:
    """Serviço base de OCR compartilhado entre módulos."""

    def __init__(self):
        self.reader = easyocr.Reader(['pt', 'en'], gpu=True)

    def detectar_texto(self, imagem_base64: str) -> Dict:
        """
        Detecta texto em uma imagem.

        Returns:
            {
                "deteccoes": [
                    {
                        "texto": "C01",
                        "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
                        "confidence": 0.95
                    }
                ],
                "dimensoes": {"width": 1920, "height": 1080}
            }
        """
        # Decodificar imagem
        imagem_bytes = base64.b64decode(imagem_base64)
        imagem_array = np.frombuffer(imagem_bytes, dtype=np.uint8)
        imagem = cv2.imdecode(imagem_array, cv2.IMREAD_COLOR)

        # Pré-processar
        imagem_processada = self._preprocessar_imagem(imagem)

        # Executar OCR
        resultados = self.reader.readtext(imagem_processada)

        # Formatar resultados
        deteccoes = []
        for bbox, texto, confidence in resultados:
            deteccoes.append({
                "texto": texto,
                "bbox": bbox,
                "confidence": float(confidence)
            })

        return {
            "deteccoes": deteccoes,
            "dimensoes": {
                "width": imagem.shape[1],
                "height": imagem.shape[0]
            }
        }

    def _preprocessar_imagem(self, imagem: np.ndarray) -> np.ndarray:
        """Pré-processamento para melhorar OCR."""
        # Converter para escala de cinza
        gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)

        # Aumentar contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)

        # Binarização adaptativa
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        return binary
