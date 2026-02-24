from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any, Literal

class ProcessarPlantaRequest(BaseModel):
    loja_id: str = Field(..., description="ID da Loja para buscar a configuração da planta/share")
    imagem_base64: str = Field(
        ...,
        description="String em base64 da imagem da planta baixa"
    )
    nome_arquivo: str = Field(
        ...,
        description="Nome original do arquivo submetido (ex: planta_floor1.png)"
    )
    modelo_llm: Optional[str] = Field(
        "gpt-4o",
        description="Modelo de LLM a usar para a análise visual"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "loja_id": "loja-1001",
                "imagem_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
                "nome_arquivo": "planta_t1.jpg",
                "modelo_llm": "gpt-4o"
            }
        }

class EnderecoDetectado(BaseModel):
    codigo: str
    tipo_endereco_id: int
    categoria_id: Optional[int] = None
    nome: str
    x_pct: float
    y_pct: float
    confidence: float
    alertas: List[str] = []

class RelatorioProcessamentoV2(BaseModel):
    quantidade_detectada: int
    quantidade_cadastravel: int
    quantidade_descartada: int

class ProcessamentoPlantaV2Response(BaseModel):
    loja_id: str
    planta_id: str
    status: Literal["SUCESSO", "ERRO", "PROCESSANDO"]
    alertas: List[str] = []
    enderecos: List[EnderecoDetectado] = []
    relatorio: Optional[RelatorioProcessamentoV2] = None
