import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_connection, init_db
from models.vin import VinMetier
from models.etagere import EtagereMetier, EtagereException
from models.bouteille import BouteilleMetier, BouteilleException

app = Flask(__name__)
app.secret_key = "cle_secrete_tp_macave"  # Clé pour sécuriser les sessions

# Redirige vers la connexion si l'utilisateur n'est pas connecté
@app.before_request
def verifier_session():
    routes_libres = ['login', 'register', 'static']
    if request.endpoint and request.endpoint not in routes_libres and 'user_id' not in session:
        return redirect(url_for('login'))

# Création d'un compte utilisateur
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = request.form['username'].strip()
        email = request.form['email'].strip()
        pwd = request.form['password']
        db = get_connection()
        try:
            db.execute("INSERT INTO user (username, email, password_hash) VALUES (?, ?, ?)",
                       (user, email, generate_password_hash(pwd)))
            db.commit()
            return redirect(url_for('login'))
        except Exception:
            flash("Identifiant ou email déjà utilisé.")
        finally:
            db.close()
    return render_template('register.html')

# Connexion à l'application
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username'].strip()
        pwd = request.form['password']
        db = get_connection()
        u = db.execute("SELECT * FROM user WHERE username = ?", (user,)).fetchone()
        db.close()
        if u and check_password_hash(u['password_hash'], pwd):
            session['user_id'] = u['id']
            session['username'] = u['username']
            return redirect(url_for('dashboard'))
        flash("Identifiants incorrects.")
    return render_template('login.html')

# Déconnexion
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Modification du profil utilisateur (email et/ou mot de passe)
@app.route('/profil', methods=['GET', 'POST'])
def profil():
    u_id = session['user_id']
    db = get_connection()
    if request.method == 'POST':
        email = request.form['email'].strip()
        nouveau_pwd = request.form.get('password', '').strip()
        try:
            if nouveau_pwd:
                db.execute("UPDATE user SET email = ?, password_hash = ? WHERE id = ?",
                           (email, generate_password_hash(nouveau_pwd), u_id))
            else:
                db.execute("UPDATE user SET email = ? WHERE id = ?", (email, u_id))
            db.commit()
            flash("Profil mis à jour avec succès.")
        except Exception:
            flash("Cet email est déjà utilisé par un autre compte.")
    u = db.execute("SELECT username, email FROM user WHERE id = ?", (u_id,)).fetchone()
    db.close()
    return render_template('profil.html', user=u)

# Page principale : étagères, statistiques, stock filtrable et historique archivé
@app.route('/')
def dashboard():
    u_id = session['user_id']
    db = get_connection()
    
    # Récupère les étagères et compte les bouteilles dessus
    etageres = db.execute("""
        SELECT e.*, COUNT(b.id) as occupation 
        FROM etagere e 
        LEFT JOIN bouteille b ON e.id = b.etagere_id AND b.statut = 'STOCK'
        WHERE e.user_id = ? 
        GROUP BY e.id
    """, (u_id,)).fetchall()
    
    # Calcul des statistiques du tableau de bord
    total_bouteilles = db.execute("SELECT COUNT(*) FROM bouteille WHERE user_id = ? AND statut = 'STOCK'", (u_id,)).fetchone()[0]
    total_refs = db.execute("SELECT COUNT(DISTINCT vin_id) FROM bouteille WHERE user_id = ? AND statut = 'STOCK'", (u_id,)).fetchone()[0]
    valeur_stock = db.execute("SELECT COALESCE(SUM(prix_achat), 0) FROM bouteille WHERE user_id = ? AND statut = 'STOCK'", (u_id,)).fetchone()[0]
    
    capacite_totale = sum(e['capacite_max'] for e in etageres)
    taux_occ = f"{(total_bouteilles / capacite_totale * 100):.1f}%" if capacite_totale > 0 else "Aucune étagère"

    # Filtres de recherche et tri sur le stock
    recherche = request.args.get('q', '').strip()
    filtre_type = request.args.get('type_vin', '').strip()
    tri = request.args.get('tri', 'domaine')
    champ_tri = {'domaine': 'v.domaine', 'prix': 'b.prix_achat', 'millesime': 'v.millesime'}.get(tri, 'v.domaine')

    requete_stock = """
        SELECT b.id, b.prix_achat, e.nom as etagere_nom, v.domaine, v.nom_cuvee, v.type_vin, v.millesime, v.region
        FROM bouteille b
        JOIN vin v ON b.vin_id = v.id
        LEFT JOIN etagere e ON b.etagere_id = e.id
        WHERE b.user_id = ? AND b.statut = 'STOCK'
    """
    params = [u_id]

    if recherche:
        requete_stock += " AND (v.domaine LIKE ? OR v.nom_cuvee LIKE ? OR v.region LIKE ?)"
        motif = f"%{recherche}%"
        params.extend([motif, motif, motif])
    if filtre_type:
        requete_stock += " AND v.type_vin = ?"
        params.append(filtre_type)

    requete_stock += f" ORDER BY {champ_tri} ASC"
    stock = db.execute(requete_stock, params).fetchall()

    # Historique privé des bouteilles dégustées et archivées
    archives = db.execute("""
        SELECT b.id, b.date_sortie, b.prix_achat, v.domaine, v.nom_cuvee, v.millesime, ev.note, ev.commentaire
        FROM bouteille b
        JOIN vin v ON b.vin_id = v.id
        LEFT JOIN evaluation ev ON ev.bouteille_id = b.id
        WHERE b.user_id = ? AND b.statut = 'ARCHIVEE'
        ORDER BY b.date_sortie DESC
    """, (u_id,)).fetchall()
    
    db.close()
    return render_template('dashboard.html', etageres=etageres, stock=stock, archives=archives,
                           total_b=total_bouteilles, total_r=total_refs, 
                           valeur=valeur_stock, taux=taux_occ,
                           recherche=recherche, filtre_type=filtre_type)

# Création d'une étagère
@app.route('/etagere/creer', methods=['POST'])
def creer_etagere():
    nom = request.form['nom'].strip()
    cap = int(request.form['capacite_max'])
    db = get_connection()
    try:
        if cap <= 0:
            raise EtagereException("Capacité invalide.")
        db.execute("INSERT INTO etagere (user_id, nom, capacite_max) VALUES (?, ?, ?)",
                   (session['user_id'], nom, cap))
        db.commit()
    except Exception as e:
        flash(f"Erreur étagère : {e}")
    finally:
        db.close()
    return redirect(url_for('dashboard'))

# Modification du nom et de la capacité d'une étagère
@app.route('/etagere/modifier/<int:id>', methods=['POST'])
def modifier_etagere(id):
    nom = request.form['nom'].strip()
    nouv_cap = int(request.form['capacite_max'])
    db = get_connection()
    try:
        et = db.execute("SELECT id FROM etagere WHERE id = ? AND user_id = ?", (id, session['user_id'])).fetchone()
        if not et:
            raise EtagereException("Étagère non trouvée.")
        occ = db.execute("SELECT COUNT(*) FROM bouteille WHERE etagere_id = ? AND statut = 'STOCK'", (id,)).fetchone()[0]
        EtagereMetier.verifier_modification_capacite(nouv_cap, occ)
        db.execute("UPDATE etagere SET nom = ?, capacite_max = ? WHERE id = ?", (nom, nouv_cap, id))
        db.commit()
        flash("Étagère mise à jour.")
    except Exception as e:
        flash(str(e))
    finally:
        db.close()
    return redirect(url_for('dashboard'))

# Suppression d'une étagère vide
@app.route('/etagere/supprimer/<int:id>', methods=['POST'])
def supprimer_etagere(id):
    db = get_connection()
    try:
        et = db.execute("SELECT id FROM etagere WHERE id = ? AND user_id = ?", (id, session['user_id'])).fetchone()
        if not et:
            raise EtagereException("Étagère non trouvée.")
        occ = db.execute("SELECT COUNT(*) FROM bouteille WHERE etagere_id = ? AND statut = 'STOCK'", (id,)).fetchone()[0]
        EtagereMetier.verifier_suppression(occ)
        db.execute("DELETE FROM etagere WHERE id = ?", (id,))
        db.commit()
    except Exception as e:
        flash(str(e))
    finally:
        db.close()
    return redirect(url_for('dashboard'))

# Ajout d'une ou plusieurs bouteilles dans le stock
@app.route('/bouteilles/ajouter', methods=['POST'])
def ajouter_bouteilles():
    u_id = session['user_id']
    et_id = int(request.form['etagere_id'])
    qte = int(request.form['quantite'])
    prix = float(request.form['prix_achat'])
    dom = request.form['domaine'].strip()
    cuv = request.form['nom_cuvee'].strip()
    t_vin = request.form['type_vin']
    mill = int(request.form['millesime'])
    reg = request.form['region'].strip()
    desc = request.form.get('description', '').strip()

    db = get_connection()
    try:
        et = db.execute("SELECT capacite_max FROM etagere WHERE id = ? AND user_id = ?", (et_id, u_id)).fetchone()
        if not et:
            raise EtagereException("Étagère invalide.")
        occ = db.execute("SELECT COUNT(*) FROM bouteille WHERE etagere_id = ? AND statut = 'STOCK'", (et_id,)).fetchone()[0]
        EtagereMetier.verifier_capacite_suffisante(et['capacite_max'], occ, qte)

        cle = VinMetier.generer_cle(dom, cuv, t_vin, mill, reg)
        db.execute("BEGIN TRANSACTION")
        vin = db.execute("SELECT id FROM vin WHERE cle_unicite = ?", (cle,)).fetchone()
        if not vin:
            cur = db.execute("""
                INSERT INTO vin (domaine, nom_cuvee, type_vin, millesime, region, description, cle_unicite)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (dom, cuv, t_vin, mill, reg, desc, cle))
            vin_id = cur.lastrowid
        else:
            vin_id = vin['id']

        maintenant = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        for _ in range(qte):
            db.execute("""
                INSERT INTO bouteille (user_id, vin_id, etagere_id, prix_achat, date_ajout, statut)
                VALUES (?, ?, ?, ?, ?, 'STOCK')
            """, (u_id, vin_id, et_id, prix, maintenant))
        db.commit()
        flash(f"{qte} bouteille(s) ajoutée(s).")
    except Exception as e:
        db.execute("ROLLBACK")
        flash(f"Échec de l'ajout : {e}")
    finally:
        db.close()
    return redirect(url_for('dashboard'))

# Déplacement d'une bouteille vers une autre étagère
@app.route('/bouteille/deplacer/<int:b_id>', methods=['POST'])
def deplacer_bouteille(b_id):
    nouv_et_id = int(request.form['nouvelle_etagere_id'])
    u_id = session['user_id']
    db = get_connection()
    try:
        b = db.execute("SELECT * FROM bouteille WHERE id = ? AND user_id = ? AND statut = 'STOCK'", (b_id, u_id)).fetchone()
        if not b:
            raise BouteilleException("Bouteille inaccessible.")
        dest = db.execute("SELECT capacite_max FROM etagere WHERE id = ? AND user_id = ?", (nouv_et_id, u_id)).fetchone()
        if not dest:
            raise EtagereException("Étagère cible introuvable.")
        occ = db.execute("SELECT COUNT(*) FROM bouteille WHERE etagere_id = ? AND statut = 'STOCK'", (nouv_et_id,)).fetchone()[0]
        EtagereMetier.verifier_capacite_suffisante(dest['capacite_max'], occ, 1)

        db.execute("UPDATE bouteille SET etagere_id = ? WHERE id = ?", (nouv_et_id, b_id))
        db.commit()
        flash("Bouteille déplacée avec succès.")
    except Exception as e:
        db.rollback()
        flash(str(e))
    finally:
        db.close()
    return redirect(url_for('dashboard'))

# Suppression simple d'une bouteille en stock (erreur de saisie ou casse)
@app.route('/bouteille/supprimer/<int:b_id>', methods=['POST'])
def supprimer_bouteille(b_id):
    u_id = session['user_id']
    db = get_connection()
    try:
        b = db.execute("SELECT id FROM bouteille WHERE id = ? AND user_id = ? AND statut = 'STOCK'", (b_id, u_id)).fetchone()
        if not b:
            raise BouteilleException("Bouteille introuvable ou déjà archivée.")
        db.execute("DELETE FROM bouteille WHERE id = ?", (b_id,))
        db.commit()
        flash("Bouteille supprimée du stock.")
    except Exception as e:
        flash(str(e))
    finally:
        db.close()
    return redirect(url_for('dashboard'))

# Archivage d'une bouteille après dégustation + ajout d'une note
@app.route('/bouteille/archiver/<int:b_id>', methods=['POST'])
def archiver_bouteille(b_id):
    u_id = session['user_id']
    note = float(request.form['note'])
    comm = request.form.get('commentaire', '').strip()

    db = get_connection()
    try:
        b = db.execute("SELECT * FROM bouteille WHERE id = ? AND user_id = ?", (b_id, u_id)).fetchone()
        if not b:
            raise BouteilleException("Bouteille non trouvée.")
        BouteilleMetier.valider_archivage(b['statut'], note)

        maintenant = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        db.execute("BEGIN TRANSACTION")
        db.execute("UPDATE bouteille SET statut = 'ARCHIVEE', etagere_id = NULL, date_sortie = ? WHERE id = ?", (maintenant, b_id))
        db.execute("""
            INSERT INTO evaluation (user_id, vin_id, bouteille_id, note, commentaire, date_eval)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (u_id, b['vin_id'], b_id, note, comm, maintenant))
        db.commit()
        flash("Bouteille dégustée et archivée.")
    except Exception as e:
        db.execute("ROLLBACK")
        flash(f"Erreur : {e}")
    finally:
        db.close()
    return redirect(url_for('dashboard'))

# Modification d'une évaluation existante par son auteur
@app.route('/evaluation/modifier/<int:e_id>', methods=['POST'])
def modifier_evaluation(e_id):
    u_id = session['user_id']
    nouv_note = float(request.form['note'])
    nouv_comm = request.form.get('commentaire', '').strip()
    db = get_connection()
    try:
        ev = db.execute("SELECT id FROM evaluation WHERE id = ? AND user_id = ?", (e_id, u_id)).fetchone()
        if not ev:
            raise BouteilleException("Évaluation introuvable ou non autorisée.")
        BouteilleMetier.valider_note(nouv_note)
        db.execute("UPDATE evaluation SET note = ?, commentaire = ? WHERE id = ?", (nouv_note, nouv_comm, e_id))
        db.commit()
        flash("Évaluation mise à jour.")
    except Exception as e:
        flash(str(e))
    finally:
        db.close()
    return redirect(url_for('catalogue'))

# Page du catalogue partagé et des avis de la communauté
@app.route('/catalogue')
def catalogue():
    recherche = request.args.get('q', '').strip()
    filtre_type = request.args.get('type_vin', '').strip()

    db = get_connection()
    requete_vins = "SELECT * FROM vin WHERE 1=1"
    params = []

    if recherche:
        requete_vins += " AND (domaine LIKE ? OR nom_cuvee LIKE ? OR region LIKE ?)"
        motif = f"%{recherche}%"
        params.extend([motif, motif, motif])
    if filtre_type:
        requete_vins += " AND type_vin = ?"
        params.append(filtre_type)

    requete_vins += " ORDER BY domaine ASC"
    vins = db.execute(requete_vins, params).fetchall()

    donnees = []
    for v in vins:
        evals = db.execute("""
            SELECT ev.id, ev.user_id, ev.note, ev.commentaire, ev.date_eval, u.username
            FROM evaluation ev
            JOIN user u ON ev.user_id = u.id
            WHERE ev.vin_id = ?
            ORDER BY ev.date_eval DESC
        """, (v['id'],)).fetchall()
        notes = [e['note'] for e in evals]
        donnees.append({
            'vin': v,
            'moyenne': VinMetier.calculer_note_moyenne(notes),
            'evaluations': evals
        })
    db.close()
    return render_template('catalogue.html', catalogue=donnees,
                           recherche=recherche, filtre_type=filtre_type,
                           current_user_id=session['user_id'])

if __name__ == '__main__':
    if not os.path.exists("macave.db"):
        init_db()
    app.run(debug=True, port=5000)