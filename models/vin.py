import re
from typing import List

class VinMetier:
    # Met en minuscules et supprime les espaces inutiles
    @staticmethod
    def normaliser(texte: str) -> str:
        return re.sub(r'\s+', ' ', (texte or '').strip().lower())

    # Crée une clé unique pour éviter les doublons de vins dans le catalogue
    @classmethod
    def generer_cle(cls, domaine: str, cuvee: str, type_vin: str, millesime: int, region: str) -> str:
        return f"{cls.normaliser(domaine)}|{cls.normaliser(cuvee)}|{cls.normaliser(type_vin)}|{int(millesime)}|{cls.normaliser(region)}"

    # Calcule la moyenne des notes sur 20 (ou affiche "Non évalué")
    @staticmethod
    def calculer_note_moyenne(notes: List[float]) -> str:
        if not notes:
            return "Non évalué"
        return f"{sum(notes) / len(notes):.1f}/20"