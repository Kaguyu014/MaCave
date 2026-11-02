import re
from typing import List  # <--- Ajouter cette ligne

class VinMetier:
    @staticmethod
    def normaliser(texte: str) -> str:
        return re.sub(r'\s+', ' ', (texte or '').strip().lower())

    @classmethod
    def generer_cle(cls, domaine: str, cuvee: str, type_vin: str, millesime: int, region: str) -> str:
        return f"{cls.normaliser(domaine)}|{cls.normaliser(cuvee)}|{cls.normaliser(type_vin)}|{int(millesime)}|{cls.normaliser(region)}"

    @staticmethod
    def calculer_note_moyenne(notes: List[float]) -> str:  # <--- Remplacer list[float] par List[float]
        if not notes:
            return "Non évalué"
        return f"{sum(notes) / len(notes):.1f}/20"