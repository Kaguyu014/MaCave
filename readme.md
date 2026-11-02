# 🍷 MaCave — Gestionnaire Collaborative de Cave à Vin

**MaCave** est une application web multi-utilisateurs développée avec Python, Flask et SQLite. Elle permet aux amateurs de vin de gérer leur cave privée, d'organiser leurs bouteilles sur des étagères virtuelles, de suivre leur historique de dégustation et de partager leurs évaluations au sein d'une communauté[cite: 1].

---

## 📌 Présentation du Projet

L'application résout la problématique de la gestion physique et qualitative du vin au quotidien en proposant une séparation stricte entre **l'espace privé** (stock, emplacements, prix d'achat) et **l'espace communautaire** (catalogue partagé, notes et commentaires)[cite: 2, 3].

### Key Features & Innovation Métier
- 🔒 **Confidentialité & Étanchéité (R1) :** Chaque utilisateur accède uniquement à son propre stock privé et à ses étagères[cite: 2]. Les données financières et les emplacements physiques restent strictement personnels[cite: 2].
- 📐 **Distinction Référence vs Exemplaire physique :** Une référence de vin (`Vin`) est unique au catalogue collectif (évitant les doublons grâce à un nettoyage de la casse et des espaces)[cite: 3]. Une bouteille (`Bouteille`) représente l'exemplaire physique réel possédant son propre prix, sa date d'entrée et son étagère[cite: 3].
- 📦 **Gestion fine des étagères (R2 à R5) :** Contrôle dynamique de la capacité[cite: 2]. Impossible de surcharger une étagère ou de supprimer une étagère non vide[cite: 2].
- ⚛️ **Atomicité des ajouts & déplacements (R7) :** Toutes les opérations de stock sont transactionnelles (`BEGIN` / `COMMIT` / `ROLLBACK`), empêchant tout état partiel en base de données[cite: 2, 3].
- 🍷 **Dégustation & Archivage (R8 à R11) :** Lorsqu'une bouteille est dégustée, elle quitte l'étagère pour intégrer l'historique privé avec une note sur 20 et un avis facultatif[cite: 4].
- ⭐ **Moyenne communautaire dynamique :** Le catalogue calcul à la volée la note globale de chaque référence[cite: 4]. Si aucune évaluation n'est encore enregistrée, la mention obligatoire *« Non évalué »* est affichée[cite: 4].

---

## 🛠️ Architecture & Technologies

Le projet suit une architecture modulaire en couches, garantissant un découplage total entre l'interface HTTP et la logique métier.

- **Langage & Framework Web :** Python 3, Flask
- **Moteur de Template & Design :** Jinja2, HTML5 / CSS3 (Design personnalisé Bordeau & Chêne)
- **Base de Données :** SQLite avec gestion des clés étrangères (`PRAGMA foreign_keys = ON;`) et contraintes d'intégrité[cite: 5]
- **Validation & Sécurité :** Hachage des mots de passe (`Werkzeug`), contrôles d'accès côté serveur[cite: 2, 5]
- **Tests unitaires :** `pytest`[cite: 5]

### Architecture du Projet (`MVC / Domain-Driven`)

```text
macave/
├── app.py                  # Contrôleur Flask & Routes HTTP
├── database.py             # Gestionnaire de connexions et transactions SQLite
├── schema.sql              # Modèle relationnel DDL
├── models/                 # Couche Métier découpée (POO)
│   ├── vin.py              # Catalogue, unicité et moyennes
│   ├── etagere.py          # Validation des capacités et suppressions
│   └── bouteille.py        # Cycle de vie et règles d'archivage
├── templates/              # Vues Jinja2 (base, dashboard, catalogue, etc.)
├── static/                 # Fichier de style (style.css)
├── tests/                  # Tests automatisés (pytest)
└── docs/                   # Sources UML (Classes, Séquence, Cas d'utilisation)