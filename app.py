import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_connection, init_db
from models.vin import VinMetier
from models.etagere import EtagereMetier, EtagereException
from models.bouteille import BouteilleMetier, BouteilleException

app = Flask(__name__)
app.secret_key = "cle_secrete_tp_macave"

@app.before_request
def verifier_session():
    routes_libres = ['login', 'register', 'static']
    if request.endpoint and request.endpoint not in routes_libres and 'user_id' not in session:
        return redirect(url_for('login'))

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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    u_id = session['user_id']
    db = get_connection()
    
    etageres = db.execute("""
        SELECT e.*, COUNT(b.id) as occupation 
        FROM etagere e 
        LEFT JOIN bouteille b ON e.id = b.etagere_id AND b.statut = 'STOCK'
        WHERE e.user_id = ? 
        GROUP BY e.id
    """, (u_id,)).fetchall()
    
    total_bouteilles = db.execute("SELECT COUNT(*) FROM bouteille WHERE user_id = ? AND statut = 'STOCK'", (u_id,)).fetchone()[0]
    total_refs = db.execute("SELECT COUNT(DISTINCT vin_id) FROM bouteille WHERE user_id = ? AND statut = 'STOCK'", (u_id,)).fetchone()[0]
    valeur_stock = db.execute("SELECT COALESCE(SUM(prix_achat), 0) FROM bouteille WHERE user_id = ? AND statut = 'STOCK'", (u_id,)).fetchone()[0]
    
    capacite_totale = sum(e['capacite_max'] for e in etageres)
    taux_occ = f"{(total_bouteilles / capacite_totale * 100):.1f}%" if capacite_totale > 0 else "Aucune étagère"

    tri = request.args.get('tri', 'domaine')
    champ_tri = {'domaine': 'v.domaine', 'prix': 'b.prix_achat', 'millesime': 'v.millesime'}.get(tri, 'v.domaine')

    stock = db.execute(f"""
        SELECT b.id, b.prix_achat, e.nom as etagere_nom, v.domaine, v.nom_cuvee, v.type_vin, v.millesime, v.region
        FROM bouteille b
        JOIN vin v ON b.vin_id = v.id
        LEFT JOIN etagere e ON b.etagere_id = e.id
        WHERE b.user_id = ? AND b.statut = 'STOCK'
        ORDER BY {champ_tri} ASC
    """, (u_id,)).fetchall()
    
    db.close()
    return render_template('dashboard.html', etageres=etageres, stock=stock, 
                           total_b=total_bouteilles, total_r=total_refs, 
                           valeur=valeur_stock, taux=taux_occ)

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
                INSERT INTO vin (domaine, nom_cuvee, type_vin, millesime, region, cle_unicite)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (dom, cuv, t_vin, mill, reg, cle))
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

@app.route('/catalogue')
def catalogue():
    db = get_connection()
    vins = db.execute("SELECT * FROM vin ORDER BY domaine ASC").fetchall()
    donnees = []
    for v in vins:
        evals = db.execute("SELECT note, commentaire, date_eval FROM evaluation WHERE vin_id = ?", (v['id'],)).fetchall()
        notes = [e['note'] for e in evals]
        donnees.append({
            'vin': v,
            'moyenne': VinMetier.calculer_note_moyenne(notes),
            'evaluations': evals
        })
    db.close()
    return render_template('catalogue.html', catalogue=donnees)

if __name__ == '__main__':
    if not os.path.exists("macave.db"):
        init_db()
    app.run(debug=True, port=5000)