import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'collecte_dechets.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Table articles : référentiel des types de déchets
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            indice INTEGER PRIMARY KEY AUTOINCREMENT,
            article TEXT NOT NULL UNIQUE,
            unite TEXT NOT NULL DEFAULT 'kg',
            prix REAL NOT NULL DEFAULT 0
        )
    ''')

    # Table article_collecte : détail des collectes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS article_collecte (
            indice INTEGER PRIMARY KEY AUTOINCREMENT,
            num INTEGER NOT NULL,
            article TEXT NOT NULL,
            qte REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (num) REFERENCES sites_collectes(num)
        )
    ''')

    # Table sites_collectes : en-tête des collectes par site
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sites_collectes (
            num INTEGER PRIMARY KEY AUTOINCREMENT,
            date_collecte TEXT NOT NULL,
            site TEXT NOT NULL,
            contractant TEXT DEFAULT '',
            observation TEXT DEFAULT '',
            bon TEXT DEFAULT '',
            date_bon TEXT DEFAULT '',
            tonnage REAL DEFAULT 0
        )
    ''')

    # Table utilisateurs pour l'authentification
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            mot_de_passe TEXT NOT NULL,
            nom TEXT DEFAULT ''
        )
    ''')

    # Insérer un utilisateur par défaut
    cursor.execute('''
        INSERT OR IGNORE INTO utilisateurs (login, mot_de_passe, nom)
        VALUES ('admin', 'admin', 'Administrateur')
    ''')

    # Insérer quelques articles par défaut
    articles_defaut = [
        ('Plastique', 'kg', 50),
        ('Organique', 'kg', 20),
        ('Papier', 'kg', 30),
        ('Verre', 'kg', 40),
        ('Métal', 'kg', 60),
        ('Autre', 'kg', 10),
    ]
    for art, unite, prix in articles_defaut:
        cursor.execute(
            'INSERT OR IGNORE INTO articles (article, unite, prix) VALUES (?, ?, ?)',
            (art, unite, prix)
        )

    conn.commit()
    conn.close()


# --- CRUD Articles ---

def get_articles():
    conn = get_db()
    rows = conn.execute('SELECT * FROM articles ORDER BY article').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_article(article, unite, prix):
    conn = get_db()
    conn.execute(
        'INSERT INTO articles (article, unite, prix) VALUES (?, ?, ?)',
        (article, unite, prix)
    )
    conn.commit()
    conn.close()


def update_article(indice, article, unite, prix):
    conn = get_db()
    conn.execute(
        'UPDATE articles SET article=?, unite=?, prix=? WHERE indice=?',
        (article, unite, prix, indice)
    )
    conn.commit()
    conn.close()


def delete_article(indice):
    conn = get_db()
    conn.execute('DELETE FROM articles WHERE indice=?', (indice,))
    conn.commit()
    conn.close()


# --- CRUD Sites collectes ---

def get_sites(filtres=None):
    conn = get_db()
    query = 'SELECT * FROM sites_collectes WHERE 1=1'
    params = []

    if filtres:
        if filtres.get('mois'):
            query += " AND strftime('%m', date_collecte) = ?"
            params.append(filtres['mois'].zfill(2))
        if filtres.get('annee'):
            query += " AND strftime('%Y', date_collecte) = ?"
            params.append(filtres['annee'])
        if filtres.get('site'):
            query += " AND site LIKE ?"
            params.append(f"%{filtres['site']}%")
        if filtres.get('date_debut'):
            query += " AND date_collecte >= ?"
            params.append(filtres['date_debut'])
        if filtres.get('date_fin'):
            query += " AND date_collecte <= ?"
            params.append(filtres['date_fin'])

    query += ' ORDER BY date_collecte DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_site(date_collecte, site, contractant, observation, bon, date_bon, tonnage):
    conn = get_db()
    cursor = conn.execute(
        '''INSERT INTO sites_collectes
           (date_collecte, site, contractant, observation, bon, date_bon, tonnage)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (date_collecte, site, contractant, observation, bon, date_bon, tonnage)
    )
    num = cursor.lastrowid
    conn.commit()
    conn.close()
    return num


def update_site(num, date_collecte, site, contractant, observation, bon, date_bon, tonnage):
    conn = get_db()
    conn.execute(
        '''UPDATE sites_collectes
           SET date_collecte=?, site=?, contractant=?, observation=?,
               bon=?, date_bon=?, tonnage=?
           WHERE num=?''',
        (date_collecte, site, contractant, observation, bon, date_bon, tonnage, num)
    )
    conn.commit()
    conn.close()


def delete_site(num):
    conn = get_db()
    conn.execute('DELETE FROM article_collecte WHERE num=?', (num,))
    conn.execute('DELETE FROM sites_collectes WHERE num=?', (num,))
    conn.commit()
    conn.close()


def get_site_by_num(num):
    conn = get_db()
    row = conn.execute('SELECT * FROM sites_collectes WHERE num=?', (num,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- CRUD Article Collecte ---

def get_collectes_by_site(num):
    conn = get_db()
    rows = conn.execute(
        '''SELECT ac.*, a.unite, a.prix
           FROM article_collecte ac
           LEFT JOIN articles a ON ac.article = a.article
           WHERE ac.num = ?''',
        (num,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_collecte(num, article, qte):
    conn = get_db()
    conn.execute(
        'INSERT INTO article_collecte (num, article, qte) VALUES (?, ?, ?)',
        (num, article, qte)
    )
    conn.commit()
    conn.close()


def update_collecte(indice, article, qte):
    conn = get_db()
    conn.execute(
        'UPDATE article_collecte SET article=?, qte=? WHERE indice=?',
        (article, qte, indice)
    )
    conn.commit()
    conn.close()


def delete_collecte(indice):
    conn = get_db()
    conn.execute('DELETE FROM article_collecte WHERE indice=?', (indice,))
    conn.commit()
    conn.close()


# --- Analyse & Statistiques ---

def get_stats_mensuelles(annee=None):
    conn = get_db()
    query = '''
        SELECT strftime('%Y-%m', sc.date_collecte) as mois,
               ac.article,
               SUM(ac.qte) as total_qte
        FROM article_collecte ac
        JOIN sites_collectes sc ON ac.num = sc.num
    '''
    params = []
    if annee:
        query += " WHERE strftime('%Y', sc.date_collecte) = ?"
        params.append(str(annee))
    query += ' GROUP BY mois, ac.article ORDER BY mois'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_totaux_par_article(date_debut=None, date_fin=None):
    conn = get_db()
    query = '''
        SELECT ac.article, SUM(ac.qte) as total_qte,
               a.prix, a.unite,
               SUM(ac.qte * COALESCE(a.prix, 0)) as total_montant
        FROM article_collecte ac
        LEFT JOIN articles a ON ac.article = a.article
        JOIN sites_collectes sc ON ac.num = sc.num
        WHERE 1=1
    '''
    params = []
    if date_debut:
        query += " AND sc.date_collecte >= ?"
        params.append(date_debut)
    if date_fin:
        query += " AND sc.date_collecte <= ?"
        params.append(date_fin)
    query += ' GROUP BY ac.article ORDER BY total_qte DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recapitulatif(date_debut, date_fin):
    """Récapitulatif des articles collectés sur une période, regroupé par article."""
    conn = get_db()
    rows = conn.execute('''
        SELECT ac.article, a.unite, a.prix,
               SUM(ac.qte) as total_qte,
               SUM(ac.qte * COALESCE(a.prix, 0)) as total_montant,
               COUNT(DISTINCT sc.num) as nb_collectes
        FROM article_collecte ac
        LEFT JOIN articles a ON ac.article = a.article
        JOIN sites_collectes sc ON ac.num = sc.num
        WHERE sc.date_collecte BETWEEN ? AND ?
        GROUP BY ac.article
        ORDER BY ac.article
    ''', (date_debut, date_fin)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Authentification ---

def verifier_login(login, mot_de_passe):
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM utilisateurs WHERE login=? AND mot_de_passe=?',
        (login, mot_de_passe)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
