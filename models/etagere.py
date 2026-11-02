class EtagereException(Exception):
    pass

class EtagereMetier:
    @staticmethod
    def verifier_capacite_suffisante(capacite_max: int, occupation: int, quantite_voulue: int):
        if quantite_voulue <= 0:
            raise EtagereException("La quantité doit être supérieure à zéro.")
        if occupation + quantite_voulue > capacite_max:
            place_restante = capacite_max - occupation
            raise EtagereException(f"Dépassement de capacité : {place_restante} place(s) restante(s).")

    @staticmethod
    def verifier_suppression(occupation: int):
        if occupation > 0:
            raise EtagereException("Impossible de supprimer une étagère contenant encore des bouteilles.")