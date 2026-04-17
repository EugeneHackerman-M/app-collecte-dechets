import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get('DATABASE_URL')


def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            indice SERIAL PRIMARY KEY,
            article TEXT NOT NULL UNIQUE,
            unite TEXT NOT NULL DEFAULT 'kg',
            prix REAL NOT NULL DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sites_collectes (
            num SERIAL PRIMARY KEY,
            date_collecte TEXT NOT NULL,
            site TEXT NOT NULL,
            contractant TEXT DEFAULT '',
            observation TEXT DEFAULT '',
            bon TEXT DEFAULT '',
            date_bon TEXT DEFAULT '',
            tonnage REAL DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS article_collecte (
            indice SERIAL PRIMARY KEY,
            num INTEGER NOT NULL,
            article TEXT NOT NULL,
            qte REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (num) REFERENCES sites_collectes(num)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id SERIAL PRIMARY KEY,
            login TEXT NOT NULL UNIQUE,
            mot_de_passe TEXT NOT NULL,
            nom TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        INSERT INTO utilisateurs (login, mot_de_passe, nom)
        VALUES ('admin', 'admin', 'Administrateur')
        ON CONFLICT (login) DO NOTHING
    ''')

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
            'INSERT INTO articles (article, unite, prix) VALUES (%s, %s, %s) ON CONFLICT (article) DO NOTHING',
            (art, unite, prix)
        )

    conn.commit()
    conn.close()


def get_articles():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM articles ORDER BY article')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_article(article, unite, prix):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO articles (article, unite, prix) VALUES (%s, %s, %s)',
        (article, unite, prix)
    )
    conn.commit()
    conn.close()


def update_article(indice, article, unite, prix):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE articles SET article=%s, unite=%s, prix=%s WHERE indice=%s',
        (article, unite, prix, indice)
    )
    conn.commit()
    conn.close()


def delete_article(indice):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM articles WHERE indice=%s', (indice,))
    conn.commit()
    conn.close()


def get_sites(filtres=None):
    conn = get_db()
    cursor = conn.cursor()
    query = 'SELECT * FROM sites_collectes WHERE 1=1'
    params = []

    if filtres:
        if filtres.get('mois'):
            query += " AND TO_CHAR(date_collecte::date, 'MM') = %s"
            params.append(filtres['mois'].zfill(2))
        if filtres.get('annee'):
            query += " AND TO_CHAR(date_collecte::date, 'YYYY') = %s"
            params.append(filtres['annee'])
        if filtres.get('site'):
            query += " AND site ILIKE %s"
            params.append(f"%{filtres['site']}%")
        if filtres.get('date_debut'):
            query += " AND date_collecte >= %s"
            params.append(filtres['date_debut'])
        if filtres.get('date_fin'):
            query += " AND date_collecte <= %s"
            params.append(filtres['date_fin'])

    query += ' ORDER BY date_collecte DESC'
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_site(date_collecte, site, contractant, observation, bon, date_bon, tonnage):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO sites_collectes
           (date_collecte, site, contractant, observation, bon, date_bon, tonnage)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING num''',
        (date_collecte, site, contractant, observation, bon, date_bon, tonnage)
    )
    num = cursor.fetchone()['num']
    conn.commit()
    conn.close()
    return num


def update_site(num, date_collecte, site, contractant, observation, bon, date_bon, tonnage):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''UPDATE sites_collectes
           SET date_collecte=%s, site=%s, contractant=%s, observation=%s,
               bon=%s, date_bon=%s, tonnage=%s
           WHERE num=%s''',
        (date_collecte, site, contractant, observation, bon, date_bon, tonnage, num)
    )
    conn.commit()
    conn.close()


def delete_site(num):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM article_collecte WHERE num=%s', (num,))
    cursor.execute('DELETE FROM sites_collectes WHERE num=%s', (num,))
    conn.commit()
    conn.close()


def get_site_by_num(num):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sites_collectes WHERE num=%s', (num,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_collectes_by_site(num):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT ac.*, a.unite, a.prix
           FROM article_collecte ac
           LEFT JOIN articles a ON ac.article = a.article
           WHERE ac.num = %s''',
        (num,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_collecte(num, article, qte):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO article_collecte (num, article, qte) VALUES (%s, %s, %s)',
        (num, article, qte)
    )
    conn.commit()
    conn.close()


def update_collecte(indice, article, qte):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE article_collecte SET article=%s, qte=%s WHERE indice=%s',
        (article, qte, indice)
    )
    conn.commit()
    conn.close()


def delete_collecte(indice):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM article_collecte WHERE indice=%s', (indice,))
    conn.commit()
    conn.close()


def get_stats_mensuelles(annee=None):
    conn = get_db()
    cursor = conn.cursor()
    query = '''
        SELECT TO_CHAR(sc.date_collecte::date, 'YYYY-MM') as mois,
               ac.article,
               SUM(ac.qte) as total_qte
        FROM article_collecte ac
        JOIN sites_collectes sc ON ac.num = sc.num
    '''
    params = []
    if annee:
        query += " WHERE TO_CHAR(sc.date_collecte::date, 'YYYY') = %s"
        params.append(str(annee))
    query += ' GROUP BY mois, ac.article ORDER BY mois'
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_totaux_par_article(date_debut=None, date_fin=None):
    conn = get_db()
    cursor = conn.cursor()
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
        query += " AND sc.date_collecte >= %s"
        params.append(date_debut)
    if date_fin:
        query += " AND sc.date_collecte <= %s"
        params.append(date_fin)
    query += ' GROUP BY ac.article, a.prix, a.unite ORDER BY total_qte DESC'
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recapitulatif(date_debut, date_fin):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ac.article, a.unite, a.prix,
               SUM(ac.qte) as total_qte,
               SUM(ac.qte * COALESCE(a.prix, 0)) as total_montant,
               COUNT(DISTINCT sc.num) as nb_collectes
        FROM article_collecte ac
        LEFT JOIN articles a ON ac.article = a.article
        JOIN sites_collectes sc ON ac.num = sc.num
        WHERE sc.date_collecte BETWEEN %s AND %s
        GROUP BY ac.article, a.unite, a.prix
        ORDER BY ac.article
    ''', (date_debut, date_fin))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def verifier_login(login, mot_de_passe):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM utilisateurs WHERE login=%s AND mot_de_passe=%s',
        (login, mot_de_passe)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
