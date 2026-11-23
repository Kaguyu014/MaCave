class BouteilleException(Exception):
    pass

class BouteilleMetier:
    # Vérifie qu'une note est bien comprise entre 0 et 20
    @staticmethod
    def valider_note(note: float):
        if not (0.0 <= note <= 20.0):
            raise BouteilleException("La note doit être comprise entre 0 et 20.")

    # Vérifie qu'une bouteille est bien en stock et que sa note est valide
    @classmethod
    def valider_archivage(cls, statut: str, note: float):
        if statut != "STOCK":
            raise BouteilleException("Seule une bouteille actuellement en stock peut être archivée.")
        cls.valider_note(note)