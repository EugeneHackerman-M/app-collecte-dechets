// === NAVIGATION PAR ONGLETS ===
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');

        // Charger les données de l'onglet
        const tab = btn.dataset.tab;
        if (tab === 'dashboard') loadDashboard();
        if (tab === 'collectes') loadCollectes();
        if (tab === 'articles') loadArticles();
        if (tab === 'saisie') loadArticleOptions();
        if (tab === 'analyse') loadAnalyse();
    });
});

// === UTILITAIRES ===
async function api(url, options = {}) {
    if (options.body && typeof options.body === 'object') {
        options.body = JSON.stringify(options.body);
        options.headers = { 'Content-Type': 'application/json', ...options.headers };
    }
    const res = await fetch(url, options);
    if (res.status === 401) {
        window.location.href = '/login';
        return null;
    }
    return res;
}

function formatNumber(n) {
    return (n || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Couleurs pour les graphiques
const COLORS = [
    '#2e7d32', '#1565c0', '#ef6c00', '#7b1fa2',
    '#c62828', '#00838f', '#4e342e', '#f9a825',
    '#1a237e', '#e65100', '#ad1457', '#00695c'
];

// === TABLEAU DE BORD ===
let chartPie = null;
let chartBar = null;

async function loadDashboard() {
    const [rSites, rTotaux, rStats] = await Promise.all([
        api('/api/sites').then(r => r.json()),
        api('/api/stats/totaux').then(r => r.json()),
        api('/api/stats/mensuelles').then(r => r.json())
    ]);

    // Cartes statistiques
    const totalQte = rTotaux.reduce((s, r) => s + (r.total_qte || 0), 0);
    const totalMontant = rTotaux.reduce((s, r) => s + (r.total_montant || 0), 0);
    const nbCollectes = rSites.length;
    const nbArticles = rTotaux.length;

    document.getElementById('stats-cards').innerHTML = `
        <div class="stat-card">
            <h4>Total collectes</h4>
            <div class="value">${nbCollectes}</div>
            <div class="sub">interventions enregistrees</div>
        </div>
        <div class="stat-card">
            <h4>Quantite totale</h4>
            <div class="value">${formatNumber(totalQte)}</div>
            <div class="sub">kg collectes</div>
        </div>
        <div class="stat-card">
            <h4>Montant total</h4>
            <div class="value">${formatNumber(totalMontant)}</div>
            <div class="sub">valeur des collectes</div>
        </div>
        <div class="stat-card">
            <h4>Types d'articles</h4>
            <div class="value">${nbArticles}</div>
            <div class="sub">articles differents collectes</div>
        </div>
    `;

    // Camembert
    if (chartPie) chartPie.destroy();
    const pieCtx = document.getElementById('chart-pie').getContext('2d');
    chartPie = new Chart(pieCtx, {
        type: 'doughnut',
        data: {
            labels: rTotaux.map(r => r.article),
            datasets: [{
                data: rTotaux.map(r => r.total_qte),
                backgroundColor: COLORS.slice(0, rTotaux.length)
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { position: 'bottom' } }
        }
    });

    // Barres evolution mensuelle
    if (chartBar) chartBar.destroy();
    const moisSet = [...new Set(rStats.map(r => r.mois))].sort();
    const articlesSet = [...new Set(rStats.map(r => r.article))];
    const datasets = articlesSet.map((art, i) => ({
        label: art,
        data: moisSet.map(m => {
            const found = rStats.find(r => r.mois === m && r.article === art);
            return found ? found.total_qte : 0;
        }),
        backgroundColor: COLORS[i % COLORS.length]
    }));

    const barCtx = document.getElementById('chart-bar').getContext('2d');
    chartBar = new Chart(barCtx, {
        type: 'bar',
        data: { labels: moisSet, datasets },
        options: {
            responsive: true,
            scales: {
                x: { stacked: true },
                y: { stacked: true, beginAtZero: true }
            },
            plugins: { legend: { position: 'bottom' } }
        }
    });
}

// === GESTION DES ARTICLES ===
async function loadArticles() {
    const articles = await api('/api/articles').then(r => r.json());
    const tbody = document.querySelector('#table-articles tbody');
    tbody.innerHTML = articles.map(a => `
        <tr>
            <td>${a.indice}</td>
            <td>${a.article}</td>
            <td>${a.unite}</td>
            <td>${formatNumber(a.prix)}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editArticle(${a.indice}, '${a.article}', '${a.unite}', ${a.prix})">Modifier</button>
                <button class="btn btn-sm btn-danger" onclick="deleteArticle(${a.indice})">Supprimer</button>
            </td>
        </tr>
    `).join('');
}

function editArticle(indice, article, unite, prix) {
    document.getElementById('a-edit-indice').value = indice;
    document.getElementById('a-article').value = article;
    document.getElementById('a-unite').value = unite;
    document.getElementById('a-prix').value = prix;
}

async function saveArticle() {
    const indice = document.getElementById('a-edit-indice').value;
    const data = {
        article: document.getElementById('a-article').value,
        unite: document.getElementById('a-unite').value,
        prix: document.getElementById('a-prix').value
    };

    if (!data.article) { alert('Le nom de l\'article est requis'); return; }

    if (indice) {
        await api(`/api/articles/${indice}`, { method: 'PUT', body: data });
    } else {
        await api('/api/articles', { method: 'POST', body: data });
    }

    document.getElementById('a-edit-indice').value = '';
    document.getElementById('a-article').value = '';
    document.getElementById('a-unite').value = 'kg';
    document.getElementById('a-prix').value = '0';
    loadArticles();
}

async function deleteArticle(indice) {
    if (!confirm('Supprimer cet article ?')) return;
    await api(`/api/articles/${indice}`, { method: 'DELETE' });
    loadArticles();
}

// === SAISIE DES COLLECTES ===
async function loadArticleOptions() {
    const articles = await api('/api/articles').then(r => r.json());
    document.querySelectorAll('.art-select').forEach(sel => {
        const val = sel.value;
        sel.innerHTML = '<option value="">-- Choisir --</option>' +
            articles.map(a => `<option value="${a.article}">${a.article} (${a.unite} - ${a.prix})</option>`).join('');
        sel.value = val;
    });
}

// Ajouter une ligne article
document.getElementById('btn-add-art').addEventListener('click', () => {
    const container = document.getElementById('articles-lignes');
    const ligne = document.createElement('div');
    ligne.className = 'article-ligne form-row';
    ligne.innerHTML = `
        <div class="form-group" style="flex:2">
            <label>Article</label>
            <select class="art-select"><option value="">-- Choisir --</option></select>
        </div>
        <div class="form-group" style="flex:1">
            <label>Quantite</label>
            <input type="number" class="art-qte" step="0.01" placeholder="0">
        </div>
        <div class="form-group" style="flex:0 0 40px; align-self:flex-end;">
            <button type="button" class="btn-icon btn-remove-art" title="Supprimer">&times;</button>
        </div>
    `;
    container.appendChild(ligne);
    loadArticleOptions();
});

// Supprimer une ligne article
document.addEventListener('click', e => {
    if (e.target.classList.contains('btn-remove-art')) {
        const lignes = document.querySelectorAll('.article-ligne');
        if (lignes.length > 1) {
            e.target.closest('.article-ligne').remove();
        }
    }
});

// Soumission du formulaire
document.getElementById('form-collecte').addEventListener('submit', async (e) => {
    e.preventDefault();

    const articles = [];
    document.querySelectorAll('.article-ligne').forEach(ligne => {
        const art = ligne.querySelector('.art-select').value;
        const qte = parseFloat(ligne.querySelector('.art-qte').value) || 0;
        if (art && qte > 0) articles.push({ article: art, qte });
    });

    if (articles.length === 0) {
        alert('Ajoutez au moins un article avec une quantite.');
        return;
    }

    const data = {
        date_collecte: document.getElementById('s-date').value,
        site: document.getElementById('s-site').value,
        contractant: document.getElementById('s-contractant').value,
        observation: document.getElementById('s-observation').value,
        bon: document.getElementById('s-bon').value,
        date_bon: document.getElementById('s-date-bon').value,
        tonnage: document.getElementById('s-tonnage').value || 0,
        articles
    };

    if (!data.date_collecte || !data.site) {
        alert('La date et le site sont requis.');
        return;
    }

    const editNum = document.getElementById('edit-num').value;
    if (editNum) {
        await api(`/api/sites/${editNum}`, { method: 'PUT', body: data });
        alert('Collecte modifiee avec succes !');
    } else {
        await api('/api/sites', { method: 'POST', body: data });
        alert('Collecte enregistree avec succes !');
    }

    resetForm();
});

function resetForm() {
    document.getElementById('form-collecte').reset();
    document.getElementById('edit-num').value = '';
    document.getElementById('btn-save').textContent = 'Enregistrer la collecte';
    // Garder une seule ligne article
    const container = document.getElementById('articles-lignes');
    const lignes = container.querySelectorAll('.article-ligne');
    for (let i = 1; i < lignes.length; i++) lignes[i].remove();
    const firstSelect = container.querySelector('.art-select');
    if (firstSelect) firstSelect.value = '';
    const firstQte = container.querySelector('.art-qte');
    if (firstQte) firstQte.value = '';
}

document.getElementById('btn-reset').addEventListener('click', resetForm);

// === LISTE DES COLLECTES ===
async function loadCollectes() {
    const params = new URLSearchParams({
        mois: document.getElementById('f-mois').value,
        annee: document.getElementById('f-annee').value,
        site: document.getElementById('f-site').value
    });

    const sites = await api(`/api/sites?${params}`).then(r => r.json());
    const tbody = document.querySelector('#table-collectes tbody');

    tbody.innerHTML = sites.map(s => `
        <tr>
            <td>${s.num}</td>
            <td>${s.date_collecte}</td>
            <td>${s.site}</td>
            <td>${s.contractant || '-'}</td>
            <td>${s.bon || '-'}</td>
            <td>${formatNumber(s.tonnage)}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="voirDetail(${s.num})">Detail</button>
                <button class="btn btn-sm btn-secondary" onclick="modifierCollecte(${s.num})">Modifier</button>
                <button class="btn btn-sm btn-danger" onclick="supprimerCollecte(${s.num})">Supprimer</button>
                <button class="btn btn-sm btn-success" onclick="window.open('/api/facture/${s.num}')">Facture</button>
            </td>
        </tr>
    `).join('');
}

async function voirDetail(num) {
    const site = await api(`/api/sites/${num}`).then(r => r.json());
    let html = `
        <p><strong>Date :</strong> ${site.date_collecte}</p>
        <p><strong>Site :</strong> ${site.site}</p>
        <p><strong>Contractant :</strong> ${site.contractant || '-'}</p>
        <p><strong>Bon :</strong> ${site.bon || '-'} ${site.date_bon ? '(' + site.date_bon + ')' : ''}</p>
        <p><strong>Tonnage :</strong> ${formatNumber(site.tonnage)}</p>
        <p><strong>Observation :</strong> ${site.observation || '-'}</p>
        <h4 style="margin-top:16px;">Articles collectes</h4>
        <table>
            <thead><tr><th>Article</th><th>Quantite</th><th>Unite</th><th>Prix</th><th>Montant</th></tr></thead>
            <tbody>
    `;
    let total = 0;
    for (const a of site.articles) {
        const montant = a.qte * (a.prix || 0);
        total += montant;
        html += `<tr><td>${a.article}</td><td>${formatNumber(a.qte)}</td><td>${a.unite || ''}</td><td>${formatNumber(a.prix || 0)}</td><td>${formatNumber(montant)}</td></tr>`;
    }
    html += `<tr style="font-weight:bold;"><td colspan="4" style="text-align:right;">TOTAL</td><td>${formatNumber(total)}</td></tr>`;
    html += '</tbody></table>';

    document.getElementById('modal-body').innerHTML = html;
    document.getElementById('modal-detail').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal-detail').style.display = 'none';
}

async function modifierCollecte(num) {
    const site = await api(`/api/sites/${num}`).then(r => r.json());

    // Basculer vers l'onglet saisie
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelector('[data-tab="saisie"]').classList.add('active');
    document.getElementById('tab-saisie').classList.add('active');

    await loadArticleOptions();

    // Remplir le formulaire
    document.getElementById('edit-num').value = num;
    document.getElementById('s-date').value = site.date_collecte;
    document.getElementById('s-site').value = site.site;
    document.getElementById('s-contractant').value = site.contractant || '';
    document.getElementById('s-bon').value = site.bon || '';
    document.getElementById('s-date-bon').value = site.date_bon || '';
    document.getElementById('s-tonnage').value = site.tonnage || '';
    document.getElementById('s-observation').value = site.observation || '';
    document.getElementById('btn-save').textContent = 'Modifier la collecte';

    // Remplir les articles
    const container = document.getElementById('articles-lignes');
    container.innerHTML = '';
    for (const a of site.articles) {
        const ligne = document.createElement('div');
        ligne.className = 'article-ligne form-row';
        ligne.innerHTML = `
            <div class="form-group" style="flex:2">
                <label>Article</label>
                <select class="art-select"><option value="">-- Choisir --</option></select>
            </div>
            <div class="form-group" style="flex:1">
                <label>Quantite</label>
                <input type="number" class="art-qte" step="0.01" value="${a.qte}">
            </div>
            <div class="form-group" style="flex:0 0 40px; align-self:flex-end;">
                <button type="button" class="btn-icon btn-remove-art" title="Supprimer">&times;</button>
            </div>
        `;
        container.appendChild(ligne);
    }
    await loadArticleOptions();
    // Selectionner les bons articles
    const selects = container.querySelectorAll('.art-select');
    site.articles.forEach((a, i) => {
        if (selects[i]) selects[i].value = a.article;
    });
}

async function supprimerCollecte(num) {
    if (!confirm('Supprimer cette collecte et tous ses articles ?')) return;
    await api(`/api/sites/${num}`, { method: 'DELETE' });
    loadCollectes();
}

// === ANALYSE ===
let chartAnalyseBar = null;
let chartAnalysePie = null;

async function loadAnalyse() {
    const annee = document.getElementById('analyse-annee').value;
    const params = annee ? `?annee=${annee}` : '';

    const [stats, totaux] = await Promise.all([
        api(`/api/stats/mensuelles${params}`).then(r => r.json()),
        api(`/api/stats/totaux`).then(r => r.json())
    ]);

    // Graphique barres
    if (chartAnalyseBar) chartAnalyseBar.destroy();
    const moisSet = [...new Set(stats.map(r => r.mois))].sort();
    const articlesSet = [...new Set(stats.map(r => r.article))];
    const datasets = articlesSet.map((art, i) => ({
        label: art,
        data: moisSet.map(m => {
            const found = stats.find(r => r.mois === m && r.article === art);
            return found ? found.total_qte : 0;
        }),
        backgroundColor: COLORS[i % COLORS.length]
    }));

    chartAnalyseBar = new Chart(document.getElementById('chart-analyse-bar').getContext('2d'), {
        type: 'bar',
        data: { labels: moisSet, datasets },
        options: {
            responsive: true,
            scales: { y: { beginAtZero: true } },
            plugins: { legend: { position: 'bottom' } }
        }
    });

    // Camembert totaux
    if (chartAnalysePie) chartAnalysePie.destroy();
    chartAnalysePie = new Chart(document.getElementById('chart-analyse-pie').getContext('2d'), {
        type: 'pie',
        data: {
            labels: totaux.map(r => r.article),
            datasets: [{
                data: totaux.map(r => r.total_qte),
                backgroundColor: COLORS.slice(0, totaux.length)
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { position: 'bottom' } }
        }
    });
}

// === RECAPITULATIF ===
async function loadRecap() {
    const dateDebut = document.getElementById('r-date-debut').value;
    const dateFin = document.getElementById('r-date-fin').value;
    const params = new URLSearchParams();
    if (dateDebut) params.set('date_debut', dateDebut);
    if (dateFin) params.set('date_fin', dateFin);

    const recap = await api(`/api/recapitulatif?${params}`).then(r => r.json());
    const tbody = document.querySelector('#table-recap tbody');
    let totalGeneral = 0;

    tbody.innerHTML = recap.map(r => {
        totalGeneral += r.total_montant || 0;
        return `
            <tr>
                <td>${r.article}</td>
                <td>${r.unite || ''}</td>
                <td>${formatNumber(r.prix || 0)}</td>
                <td>${formatNumber(r.total_qte)}</td>
                <td>${formatNumber(r.total_montant || 0)}</td>
                <td>${r.nb_collectes}</td>
            </tr>
        `;
    }).join('');

    document.getElementById('recap-total').textContent = formatNumber(totalGeneral);
}

function exportExcel() {
    const dateDebut = document.getElementById('r-date-debut').value || '2000-01-01';
    const dateFin = document.getElementById('r-date-fin').value || '2099-12-31';
    window.open(`/api/export/excel?date_debut=${dateDebut}&date_fin=${dateFin}`);
}

function exportCSV() {
    const dateDebut = document.getElementById('r-date-debut').value || '2000-01-01';
    const dateFin = document.getElementById('r-date-fin').value || '2099-12-31';
    window.open(`/api/export/csv?date_debut=${dateDebut}&date_fin=${dateFin}`);
}

// === INITIALISATION ===
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    // Date par defaut
    document.getElementById('s-date').valueAsDate = new Date();
});
