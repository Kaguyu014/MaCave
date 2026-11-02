PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS etagere (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    nom TEXT NOT NULL,
    capacite_max INTEGER NOT NULL CHECK(capacite_max > 0),
    FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE,
    UNIQUE(user_id, nom)
);

CREATE TABLE IF NOT EXISTS vin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domaine TEXT NOT NULL,
    nom_cuvee TEXT NOT NULL,
    type_vin TEXT NOT NULL CHECK(type_vin IN ('Rouge', 'Blanc', 'Rosé', 'Effervescent')),
    millesime INTEGER NOT NULL,
    region TEXT NOT NULL,
    description TEXT,
    cle_unicite TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS bouteille (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    vin_id INTEGER NOT NULL,
    etagere_id INTEGER,
    prix_achat REAL NOT NULL CHECK(prix_achat >= 0),
    date_ajout TEXT NOT NULL,
    date_sortie TEXT,
    statut TEXT NOT NULL CHECK(statut IN ('STOCK', 'ARCHIVEE')),
    FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY(vin_id) REFERENCES vin(id),
    FOREIGN KEY(etagere_id) REFERENCES etagere(id)
);

CREATE TABLE IF NOT EXISTS evaluation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    vin_id INTEGER NOT NULL,
    bouteille_id INTEGER UNIQUE NOT NULL,
    note REAL NOT NULL CHECK(note >= 0 AND note <= 20),
    commentaire TEXT,
    date_eval TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user(id),
    FOREIGN KEY(vin_id) REFERENCES vin(id),
    FOREIGN KEY(bouteille_id) REFERENCES bouteille(id)
);