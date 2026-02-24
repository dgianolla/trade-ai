import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.plantas.categoria import PlantaCategoria

def seed_categorias():
    db = SessionLocal()
    categorias = [
        {"nome": "Bebidas", "sinonimos": ["refrigerante", "cerveja", "suco", "agua"]},
        {"nome": "Higiene", "sinonimos": ["sabonete", "shampoo", "creme dental"]},
        {"nome": "Limpeza", "sinonimos": ["detergente", "sabão em pó", "desinfetante"]}
    ]
    
    for cat in categorias:
        if not db.query(PlantaCategoria).filter_by(nome=cat["nome"]).first():
            nova_cat = PlantaCategoria(**cat)
            db.add(nova_cat)
            
    db.commit()
    db.close()
    print("Categorias inseridas com sucesso!")

if __name__ == "__main__":
    seed_categorias()
