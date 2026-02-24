from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any, List, Literal

class AuditarPDVRequest(BaseModel):
    """Request para auditoria de material promocional de PDV."""
    imagem_url: HttpUrl = Field(
        ...,
        alias="url",
        description="URL pública da imagem do ativo de PDV a ser auditado"
    )
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "url": "https://exemplo.com/fotos/ativo-pdv-001.jpg"
            }
        }

class AuditarPDVResponse(BaseModel):
    """Response inicial (202 Accepted)."""
    sucesso: bool
    processamento_id: str
    status: str = "processando"
    mensagem: str
    tempo_estimado_segundos: int = 15

class ResultadoAuditoriaPDV(BaseModel):
    """Resultado completo da auditoria conforme especificação."""
    nota: int = Field(..., ge=0, le=10)
    nota_posicionamento: int = Field(..., ge=0, le=10)
    nota_visibilidade: int = Field(..., ge=0, le=10)
    nota_integridade: int = Field(..., ge=0, le=10)
    nota_conteudo: int = Field(..., ge=0, le=10)
    status: Literal["aprovado", "aprovado_com_ressalvas", "reprovado"]
    tipo_ativo: str
    marca: Optional[str]
    visualizacao_ok: bool
    parecer: str
    problemas: list[str]
    penalidades_aplicadas: list[str]
    criterio_eliminatorio: Optional[str]
    recomendacao: str
    preco: Optional[str] = Field(None, alias="preço")
    confianca_avaliacao: Literal["alta", "media", "baixa"]
    limitacoes_foto: list[str]

class ProcessamentoAuditoriaPDVResponse(BaseModel):
    """Response completa do processamento."""
    processamento_id: str
    status: Literal["processando", "concluido", "erro"]
    imagem_url: str
    resultado: Optional[ResultadoAuditoriaPDV]
    erro_mensagem: Optional[str]
    tempo_processamento_ms: Optional[int]
    metadata: Optional[dict]
    created_at: str
    updated_at: str
class OpcoesAnalise(BaseModel):
    extrair_texto: bool = True
    detectar_objetos: bool = True
    classificar: bool = True
    idioma_ocr: str = "pt"

class ProcessarAnaliseRequest(BaseModel):
    imagem_base64: str
    nome_arquivo: str
    tipo_analise: str = "completa"
    opcoes: Optional[OpcoesAnalise] = None

class DataResultadoAnalise(BaseModel):
    classificacao: Optional[Dict[str, Any]] = None
    texto_extraido: Optional[Dict[str, Any]] = None
    objetos_detectados: Optional[List[Dict[str, Any]]] = None

class ProcessarAnaliseResponse(BaseModel):
    sucesso: bool
    processamento_id: str
    status: str
    mensagem: str
