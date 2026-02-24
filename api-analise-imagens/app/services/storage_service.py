from minio import Minio
from minio.error import S3Error
import base64
from datetime import datetime
from app.config import settings
import io

class StorageService:
    """Serviço de armazenamento de imagens (MinIO/S3)."""

    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )

    def salvar_imagem(self, bucket: str, loja_id: str | None, nome_arquivo: str, imagem_base64: str = None, imagem_bytes: bytes = None) -> str:
        """
        Salva imagem no storage e retorna URL.

        Args:
            bucket: Nome do bucket ('plantas' ou 'analise_fotos')
            loja_id: ID da loja (opcional, pode ser None)
            nome_arquivo: Nome original do arquivo
            imagem_base64: Imagem em base64 (opcional se imagem_bytes for passado)
            imagem_bytes: Bytes da imagem (opcional se imagem_base64 for passado)

        Returns:
            URL da imagem armazenada
        """
        # Criar bucket se não existir
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

        # Gerar nome único
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        prefixo = f"{loja_id}/" if loja_id else ""
        object_name = f"{prefixo}{timestamp}_{nome_arquivo}"

        # Decodificar base64 ou usar bytes diretamente
        if imagem_base64:
            imagem_bytes = base64.b64decode(imagem_base64)
        elif not imagem_bytes:
            raise ValueError("Pelo menos um formato de imagem deve ser fornecido (base64 ou bytes)")

        # Upload
        self.client.put_object(
            bucket,
            object_name,
            data=io.BytesIO(imagem_bytes),
            length=len(imagem_bytes),
            content_type="image/jpeg"
        )

        # Retornar URL
        return f"http://{settings.MINIO_ENDPOINT}/{bucket}/{object_name}"
