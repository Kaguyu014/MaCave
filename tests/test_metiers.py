import pytest
from models.vin import VinMetier
from models.etagere import EtagereMetier, EtagereException
from models.bouteille import BouteilleMetier, BouteilleException

def test_scenario_depassement_capacite():
    """Ajouter 6 bouteilles sur une étagère de 10 occupée à 5 doit être refusé sans modification."""
    capacite = 10
    occupation = 5
    ajout = 6
    with pytest.raises(EtagereException) as exc:
        EtagereMetier.verifier_capacite_suffisante(capacite, occupation, ajout)
    assert "Dépassement de capacité" in str(exc.value)

def test_scenario_suppression_etagere_non_vide():
    """Une étagère non vide ne peut pas être supprimée."""
    with pytest.raises(EtagereException) as exc:
        EtagereMetier.verifier_suppression(occupation=1)
    assert "Impossible de supprimer" in str(exc.value)

def test_scenario_rearchivage_impossible():
    """Empêche qu'une bouteille déjà archivée le soit une seconde fois."""
    with pytest.raises(BouteilleException) as exc:
        BouteilleMetier.valider_archivage(statut="ARCHIVEE", note=14.0)
    assert "Seule une bouteille actuellement en stock" in str(exc.value)

def test_scenario_calcul_moyenne():
    """Les notes 16, 12 et 17 donnent une moyenne exacte de 15.0/20."""
    notes = [16.0, 12.0, 17.0]
    assert VinMetier.calculer_note_moyenne(notes) == "15.0/20"

def test_scenario_moyenne_sans_notes():
    """Sans évaluation, doit afficher 'Non évalué' et non 0."""
    assert VinMetier.calculer_note_moyenne([]) == "Non évalué"

def test_scenario_unicite_reference():
    """Normalisation insensible aux espaces et à la casse."""
    cle1 = VinMetier.generer_cle("Château Montelena", "Cabernet", "Rouge", 1967, "Californie")
    cle2 = VinMetier.generer_cle("château   montelena ", "  cabernet", "ROUGE", 1967, "californie")
    assert cle1 == cle2