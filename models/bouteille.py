class BouteilleException(Exception):
    pass

class BouteilleMetier:
    @staticmethod
    def valider_archivage(statut: str, note: float):
        if statut != "STOCK":
            raise BouteilleException("Seule une bouteille actuellement en stock peut être archivée.")
        if not (0.0 <= note <= 20.0):
            raise BouteilleException("La note doit être comprise entre 0 et 20.")