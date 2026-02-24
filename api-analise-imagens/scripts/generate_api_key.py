import sys
import os
import uuid
import secrets
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.api_key import APIKey

def generate_key(nome: str, cliente_id: str = None):
    db = SessionLocal()
    nova_key = secrets.token_hex(32)
    api_key_record = APIKey(
        key=nova_key,
        nome=nome,
        cliente_id=cliente_id
    )
    db.add(api_key_record)
    db.commit()
    print(f"Nova API Key gerada para {nome}: {nova_key}")
    db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        nome = sys.argv[1]
        generate_key(nome)
    else:
        print("Uso: python generate_api_key.py <nome_do_cliente>")
