class EtagereException(Exception):
    pass

class EtagereMetier:
    # Vérifie qu'il reste assez de place sur l'étagère avant d'ajouter des bouteilles
    @staticmethod
    def verifier_capacite_suffisante(capacite_max: int, occupation: int, quantite_voulue: int):
        if quantite_voulue <= 0:
            raise EtagereException("La quantité doit être supérieure à zéro.")
        if occupation + quantite_voulue > capacite_max:
            place_restante = capacite_max - occupation
            raise EtagereException(f"Dépassement de capacité : {place_restante} place(s) restante(s).")

    # Vérifie que la nouvelle capacité n'est pas inférieure au nombre de bouteilles déjà présentes
    @staticmethod
    def verifier_modification_capacite(nouvelle_capacite: int, occupation: int):
        if nouvelle_capacite <= 0:
            raise EtagereException("La capacité doit être supérieure à zéro.")
        if nouvelle_capacite < occupation:
            raise EtagereException(f"Impossible : l'étagère contient déjà {occupation} bouteille(s).")

    # Empêche de supprimer une étagère qui n'est pas vide
    @staticmethod
    def verifier_suppression(occupation: int):
        if occupation > 0:
            raise EtagereException("Impossible de supprimer une étagère contenant encore des bouteilles.")