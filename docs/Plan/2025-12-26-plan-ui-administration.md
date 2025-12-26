# Plan UI Administration MY-IA

**Date :** 26 décembre 2025
**Version :** 1.0
**Statut :** À valider

---

## 1. Objectif

Créer une interface d'administration complète et modulaire pour MY-IA, séparée de l'interface utilisateur, avec :
- Architecture multi-UI (frontend + backoffice) avec ressources partagées
- Navigation par onglets fonctionnels
- Préparation pour sous-domaines futurs (app.myia.com / admin.myia.com)

---

## 2. Architecture Globale

### 2.1. Structure des Répertoires

**Convention de nommage :**
- `UI-FRONT` : Interface utilisateur (anciennement `frontend`)
- `UI-BACK` : Interface administration (anciennement `backoffice`)
- `UI-SHARED` : Ressources partagées entre les deux interfaces

```
/                                   # Racine projet
├── UI-FRONT/                       # UI Utilisateur (ex: frontend/)
│   ├── index.html
│   ├── js/
│   │   ├── app.js
│   │   ├── config.js
│   │   ├── modules/
│   │   │   ├── conversations.js
│   │   │   ├── messages.js
│   │   │   ├── streaming.js
│   │   │   ├── upload.js
│   │   │   ├── documents.js
│   │   │   ├── profile.js
│   │   │   └── settings.js
│   │   └── ... (imports shared/)
│   ├── css/
│   │   ├── styles.css              # Import central
│   │   └── layout/
│   │       ├── chat.css
│   │       ├── sidebar.css
│   │       ├── login.css
│   │       └── responsive.css
│   └── shared/ → ../UI-SHARED/     # Lien symbolique
│
├── UI-BACK/                        # UI Administration (ex: backoffice/)
│   ├── index.html
│   ├── js/
│   │   ├── app.js                  # Point d'entrée admin
│   │   ├── router.js               # Gestion onglets
│   │   ├── config.js
│   │   ├── services/
│   │   │   └── adminApi.js         # Appels API /admin/*
│   │   ├── components/
│   │   │   ├── tabs.js             # Système d'onglets
│   │   │   ├── table.js            # Table dynamique réutilisable
│   │   │   ├── pagination.js       # Pagination
│   │   │   ├── filters.js          # Filtres de recherche
│   │   │   ├── stats-card.js       # Cartes statistiques
│   │   │   └── form-builder.js     # Générateur de formulaires
│   │   └── modules/
│   │       ├── dashboard.js        # Onglet Tableau de bord
│   │       ├── users.js            # Onglet Utilisateurs
│   │       ├── content.js          # Onglet Contenu
│   │       ├── audit.js            # Onglet Audit
│   │       └── system.js           # Onglet Système
│   ├── css/
│   │   ├── admin.css               # Import central
│   │   ├── layout.css              # Header, zone contenu
│   │   ├── tabs.css                # Onglets
│   │   ├── table.css               # Tables
│   │   ├── forms.css               # Formulaires admin
│   │   ├── dashboard.css           # Dashboard
│   │   └── responsive.css          # Responsive admin
│   └── shared/ → ../UI-SHARED/     # Lien symbolique
│
├── UI-SHARED/                      # Ressources Partagées (ex: shared/)
│   ├── js/
│   │   ├── services/
│   │   │   ├── api.js              # Client HTTP de base (fetch wrapper)
│   │   │   └── auth.js             # Authentification JWT
│   │   ├── components/
│   │   │   ├── toast.js            # Notifications toast
│   │   │   ├── confirm.js          # Modales de confirmation
│   │   │   ├── modal.js            # Modal générique
│   │   │   └── markdown.js         # Rendu markdown
│   │   ├── utils/
│   │   │   ├── dom.js              # Manipulation DOM
│   │   │   ├── format.js           # Formatage (dates, nombres)
│   │   │   └── validation.js       # Validation formulaires
│   │   └── config/
│   │       └── icons.js            # Icônes SVG centralisées
│   └── css/
│       ├── base/
│       │   ├── variables.css       # Variables CSS (couleurs, thème)
│       │   └── reset.css           # Reset CSS
│       └── components/
│           ├── buttons.css         # Boutons
│           ├── forms.css           # Inputs, selects, etc.
│           ├── modal.css           # Modales
│           ├── toast.css           # Toasts
│           ├── tooltip.css         # Tooltips
│           └── loader.css          # Spinners, loaders
│
└── docker-compose.yml              # Service "ui" (ex-frontend)
```

### 2.2. Migration depuis l'existant

Le dossier `frontend/` actuel sera renommé en `UI-FRONT/`. Voici les étapes :

```bash
# 1. Renommer le dossier frontend existant
mv frontend UI-FRONT

# 2. Créer le dossier UI-SHARED et y déplacer les ressources communes
mkdir UI-SHARED
mv UI-FRONT/js/services UI-SHARED/js/services
mv UI-FRONT/js/components UI-SHARED/js/components
mv UI-FRONT/js/utils UI-SHARED/js/utils
mv UI-FRONT/js/config UI-SHARED/js/config
mv UI-FRONT/css/base UI-SHARED/css/base
# ... (voir Phase 1 pour le détail)

# 3. Créer le dossier UI-BACK
mkdir -p UI-BACK/{js,css}

# 4. Créer les liens symboliques
cd UI-FRONT && ln -s ../UI-SHARED shared
cd ../UI-BACK && ln -s ../UI-SHARED shared
```

### 2.3. Liens Symboliques

Les liens symboliques permettent aux deux UIs d'accéder aux ressources partagées :

```bash
# Création des liens
cd UI-FRONT && ln -s ../UI-SHARED shared
cd ../UI-BACK && ln -s ../UI-SHARED shared
```

**Utilisation dans le HTML :**
```html
<!-- Imports partagés -->
<link rel="stylesheet" href="shared/css/base/variables.css">
<link rel="stylesheet" href="shared/css/base/reset.css">
<link rel="stylesheet" href="shared/css/components/buttons.css">

<script type="module" src="shared/js/services/auth.js"></script>
<script type="module" src="shared/js/components/toast.js"></script>
```

---

## 3. Configuration Docker

### 3.1. Renommage du Service

**docker-compose.yml (avant) :**
```yaml
services:
  frontend:
    image: nginx:alpine
    volumes:
      - ./frontend:/usr/share/nginx/html
    ports:
      - "8080:80"
```

**docker-compose.yml (après) :**
```yaml
services:
  ui:
    image: nginx:alpine
    volumes:
      - ./UI-FRONT:/usr/share/nginx/html/app
      - ./UI-BACK:/usr/share/nginx/html/admin
      - ./UI-SHARED:/usr/share/nginx/html/shared
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "8080:80"    # UI-FRONT (utilisateur)
      - "8081:81"    # UI-BACK (admin)
    depends_on:
      - app
```

### 3.2. URLs d'Accès

| Interface | URL | Port | Description |
|-----------|-----|------|-------------|
| **UI-FRONT** | `http://localhost:8080/` | 8080 | Interface utilisateur |
| **UI-BACK** | `http://localhost:8081/` | 8081 | Interface administration |

### 3.3. Configuration Nginx

**nginx.conf :**
```nginx
# ============================================
# UI-FRONT - Interface Utilisateur (port 80 → 8080)
# ============================================
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html/app;

    # Page principale
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Ressources partagées
    location /shared/ {
        alias /usr/share/nginx/html/shared/;
    }

    # Proxy API Backend
    location /api/ {
        proxy_pass http://app:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Proxy streaming pour chat
    location /chat/ {
        proxy_pass http://app:8000/chat/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_cache off;
    }
}

# ============================================
# UI-BACK - Interface Administration (port 81 → 8081)
# ============================================
server {
    listen 81;
    server_name localhost;
    root /usr/share/nginx/html/admin;

    # Page principale admin
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Ressources partagées
    location /shared/ {
        alias /usr/share/nginx/html/shared/;
    }

    # Proxy API Backend (tous les endpoints)
    location /api/ {
        proxy_pass http://app:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Proxy endpoints admin
    location /admin/ {
        proxy_pass http://app:8000/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3.4. Préparation Sous-domaines (Futur)

Pour le déploiement en production avec sous-domaines :

| Interface | URL Production | Port |
|-----------|----------------|------|
| UI-FRONT | `https://app.myia.com/` | 443 |
| UI-BACK | `https://admin.myia.com/` | 443 |

```nginx
# app.myia.com
server {
    listen 443 ssl;
    server_name app.myia.com;
    root /usr/share/nginx/html/app;
    # ... SSL config ...
}

# admin.myia.com
server {
    listen 443 ssl;
    server_name admin.myia.com;
    root /usr/share/nginx/html/admin;
    # ... SSL config ...
}
```

---

## 4. Interface Backoffice

### 4.1. Layout Général

```
┌─────────────────────────────────────────────────────────────────────┐
│  🛠️ MY-IA Administration                      [Admin Name] [Logout] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────┬───────────────┬───────────┬──────────┬────────────┐ │
│  │ 📊 Tableau │ 👥 Utilisateurs│ 📄 Contenu │ 📋 Audit │ ⚙️ Système │ │
│  │  de bord   │               │           │          │            │ │
│  └────────────┴───────────────┴───────────┴──────────┴────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                                                                 ││
│  │                                                                 ││
│  │                     ZONE DE CONTENU                             ││
│  │                     (change selon l'onglet)                     ││
│  │                                                                 ││
│  │                                                                 ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Footer: Version | Dernière connexion | Liens utiles             ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2. Navigation par Onglets

| Onglet | Icône | Route Hash | Description |
|--------|-------|------------|-------------|
| Tableau de bord | 📊 | `#dashboard` | Vue d'ensemble, KPIs |
| Utilisateurs | 👥 | `#users` | Gestion complète des utilisateurs |
| Contenu | 📄 | `#content` | Documents et conversations |
| Audit | 📋 | `#audit` | Logs et exports |
| Système | ⚙️ | `#system` | Configuration globale |

### 4.3. Système de Routing

```javascript
// UI-BACK/js/router.js
const routes = {
    'dashboard': () => import('./modules/dashboard.js'),
    'users': () => import('./modules/users.js'),
    'content': () => import('./modules/content.js'),
    'audit': () => import('./modules/audit.js'),
    'system': () => import('./modules/system.js')
};

function handleRoute() {
    const hash = window.location.hash.slice(1) || 'dashboard';
    const [tab, ...params] = hash.split('/');
    loadModule(tab, params);
}

window.addEventListener('hashchange', handleRoute);
```

---

## 5. Détail des Onglets

### 5.1. Onglet Tableau de Bord (#dashboard)

**Objectif :** Vue d'ensemble rapide de l'état de la plateforme.

**Contenu :**

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 Tableau de bord                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ 👥 Users │ │ 📄 Docs  │ │ 💬 Convs │ │ 🔐 Active│           │
│  │   125    │ │   847    │ │  1,234   │ │    23    │           │
│  │ +5 today │ │ +12 week │ │ +89 week │ │ sessions │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 📈 Activité des 7 derniers jours                            ││
│  │ [Graphique simple barres/lignes - optionnel]                ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────┐ ┌─────────────────────────────────┐│
│  │ 🕐 Dernières actions    │ │ 🆕 Nouveaux utilisateurs        ││
│  │ • User X a uploadé...   │ │ • john@email.com (il y a 2h)   ││
│  │ • Admin a modifié...    │ │ • marie@test.fr (il y a 5h)    ││
│  │ • User Y s'est connecté │ │ • ...                          ││
│  └─────────────────────────┘ └─────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints utilisés :**
- `GET /admin/dashboard/overview`
- `GET /admin/dashboard/usage`
- `GET /admin/audit?limit=5` (dernières actions)

**Composants :**
- `stats-card.js` : Cartes KPI
- Graphique simple (CSS/SVG ou lib légère)

---

### 5.2. Onglet Utilisateurs (#users)

**Objectif :** Gestion complète des utilisateurs de la plateforme.

**Sous-sections :**

| Sous-section | Route | Description |
|--------------|-------|-------------|
| Liste | `#users` | Liste paginée avec filtres |
| Détail | `#users/view/{id}` | Fiche utilisateur complète |
| Création | `#users/create` | Formulaire création |
| Édition | `#users/edit/{id}` | Formulaire modification |
| Rôles | `#users/roles` | Gestion des rôles |
| Bulk | `#users/bulk` | Opérations en masse |

#### 5.2.1. Liste Utilisateurs

```
┌─────────────────────────────────────────────────────────────────┐
│  👥 Utilisateurs                              [+ Créer] [Bulk]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Filtres: [Rôle ▼] [Statut ▼] [Vérifié ▼] [🔍 Recherche...   ] │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ☐ │ Email          │ Username │ Rôle  │ Statut │ Actions   ││
│  ├───┼────────────────┼──────────┼───────┼────────┼───────────┤│
│  │ ☐ │ john@mail.com  │ john_doe │ User  │ ✅ Actif│ 👁️ ✏️ 🗑️  ││
│  │ ☐ │ admin@myia.com │ admin    │ Admin │ ✅ Actif│ 👁️ ✏️     ││
│  │ ☐ │ marie@test.fr  │ marie_t  │ User  │ ❌ Inac│ 👁️ ✏️ 🗑️  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ◀ 1 2 3 ... 10 ▶  │ Afficher: [25 ▼] │ Total: 125 utilisateurs│
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `GET /admin/users` (liste paginée avec filtres)
- `PATCH /admin/users/{id}/status` (activer/désactiver)
- `DELETE /admin/users/{id}` (supprimer)

**Actions par ligne :**
- 👁️ Voir détail → `#users/view/{id}`
- ✏️ Éditer → `#users/edit/{id}`
- 🗑️ Supprimer (avec confirmation)

#### 5.2.2. Détail Utilisateur

```
┌─────────────────────────────────────────────────────────────────┐
│  👤 john_doe                                    [Éditer] [← Retour]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐ ┌─────────────────────────────────────┐│
│  │ Informations        │ │ Statistiques                        ││
│  │                     │ │                                     ││
│  │ Email: john@mail.com│ │ 📄 Documents: 23                    ││
│  │ Rôle: User          │ │ 💬 Conversations: 45                ││
│  │ Statut: ✅ Actif     │ │ 📅 Inscrit: 15/10/2025             ││
│  │ Vérifié: ✅ Oui      │ │ 🕐 Dernière connexion: il y a 2h   ││
│  │                     │ │                                     ││
│  │ Prénom: John        │ └─────────────────────────────────────┘│
│  │ Nom: Doe            │                                       │
│  │ Tél: +33 6 12 34... │ ┌─────────────────────────────────────┐│
│  │ Pays: France 🇫🇷     │ │ Actions rapides                     ││
│  │ Ville: Paris        │ │                                     ││
│  └─────────────────────┘ │ [🔄 Reset Password]                 ││
│                          │ [❌ Désactiver]                      ││
│                          │ [🗑️ Supprimer]                       ││
│                          └─────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `GET /admin/users/{id}` (détail avec stats)
- `POST /admin/users/{id}/reset-password`
- `PATCH /admin/users/{id}/status`

#### 5.2.3. Formulaire Création/Édition

```
┌─────────────────────────────────────────────────────────────────┐
│  ➕ Créer un utilisateur                            [← Retour] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Email *          [_________________________________]           │
│  Username *       [_________________________________]           │
│  Mot de passe *   [_________________________________]           │
│                                                                 │
│  ─────────────── Informations optionnelles ───────────────      │
│                                                                 │
│  Prénom           [_________________________________]           │
│  Nom              [_________________________________]           │
│  Téléphone        [_________________________________]           │
│                                                                 │
│  Rôle             [User           ▼]                            │
│  Statut           [x] Actif                                     │
│  Vérifié          [ ] Email vérifié                             │
│                                                                 │
│                              [Annuler] [💾 Enregistrer]         │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `POST /admin/users` (création)
- `PATCH /admin/users/{id}` (modification)
- `GET /admin/roles` (liste des rôles pour le select)

#### 5.2.4. Gestion des Rôles

```
┌─────────────────────────────────────────────────────────────────┐
│  🏷️ Rôles                                           [+ Créer]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ID │ Nom     │ Nom affiché    │ Description        │ Actions││
│  ├────┼─────────┼────────────────┼────────────────────┼────────┤│
│  │ 1  │ admin   │ Administrateur │ Accès complet      │ ✏️     ││
│  │ 2  │ user    │ Utilisateur    │ Accès standard     │ ✏️ 🗑️  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `GET /admin/roles`
- `POST /admin/roles`
- `PATCH /admin/roles/{id}`
- `DELETE /admin/roles/{id}`

#### 5.2.5. Opérations Bulk

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚡ Opérations en masse                             [← Retour] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Sélectionnez les utilisateurs dans la liste, puis:            │
│                                                                 │
│  [✅ Activer sélection]  [❌ Désactiver sélection]              │
│  [🏷️ Changer rôle...]   [🗑️ Supprimer sélection]               │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  3 utilisateurs sélectionnés:                                   │
│  • john@mail.com                                                │
│  • marie@test.fr                                                │
│  • paul@example.org                                             │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `POST /admin/bulk/users/activate`
- `POST /admin/bulk/users/deactivate`
- `POST /admin/bulk/users/change-role`
- `POST /admin/bulk/users/delete`

---

### 5.3. Onglet Contenu (#content)

**Objectif :** Gérer les documents et conversations de tous les utilisateurs.

**Sous-onglets internes :**

```
┌─────────────────────────────────────────────────────────────────┐
│  📄 Contenu                                                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────┬────────────────────┐                        │
│  │ 📄 Documents   │ 💬 Conversations    │                        │
│  └────────────────┴────────────────────┘                        │
│  [Contenu du sous-onglet sélectionné]                           │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.3.1. Sous-onglet Documents

```
┌─────────────────────────────────────────────────────────────────┐
│  Filtres: [Utilisateur ▼] [Type ▼] [Visibilité ▼] [🔍 Rech... ]│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Nom fichier     │ User      │ Type │ Visib. │ Taille│Actions││
│  ├─────────────────┼───────────┼──────┼────────┼───────┼───────┤│
│  │ rapport.pdf     │ john_doe  │ PDF  │ 🔒 Privé│ 2.3 MB│👁️ ⚙️ 🗑️││
│  │ data.xlsx       │ marie_t   │ XLSX │ 🌐 Public│ 156 KB│👁️ ⚙️ 🗑️││
│  │ notes.md        │ admin     │ MD   │ 🔒 Privé│ 12 KB │👁️ ⚙️ 🗑️││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Actions sur document sélectionné:                              │
│  [🔄 Réindexer RAG] [🚫 Désindexer] [🔒/🌐 Changer visibilité]  │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `GET /admin/documents`
- `DELETE /admin/documents/{id}`
- `POST /admin/documents/{id}/reindex`
- `POST /admin/documents/{id}/deindex`
- `PATCH /admin/documents/{id}/visibility`

**Détail des actions sur les documents :**

##### 🔄 Réindexer RAG

Régénère les embeddings d'un document dans ChromaDB.

| Cas d'usage | Description |
|-------------|-------------|
| Changement de modèle | Le modèle d'embeddings a été mis à jour |
| Corruption | Les chunks du document ont été corrompus |
| Nouvelle version | Le contenu du document a été modifié |
| Debug | Réponses RAG incorrectes liées à ce document |

**Processus :**
1. Supprime les anciens embeddings dans ChromaDB
2. Recharge le fichier depuis le stockage
3. Re-découpe en chunks (chunking sémantique)
4. Génère les nouveaux embeddings
5. Stocke dans ChromaDB avec métadonnées (user_id, visibility)

##### 🚫 Désindexer

Retire un document du RAG sans le supprimer du stockage.

| Cas d'usage | Description |
|-------------|-------------|
| Document obsolète | À conserver mais exclure des réponses |
| Contenu sensible | À retirer temporairement du RAG |
| Révision en cours | En attente de mise à jour |
| Test | Voir l'impact de l'absence du document |

**Processus :**
1. Supprime tous les embeddings/chunks dans ChromaDB
2. Marque le document comme `indexed = false` en base
3. Le fichier reste disponible (téléchargement possible)
4. N'apparaît plus dans les contextes RAG

**Réversible :** Oui, via "Réindexer RAG"

##### 🔒/🌐 Changer visibilité

Modifie qui peut voir le document dans le RAG.

| Visibilité | Icône | Description |
|------------|-------|-------------|
| **Privé** | 🔒 | Seul le propriétaire voit ce doc dans ses réponses RAG |
| **Public** | 🌐 | Tous les utilisateurs voient ce doc dans leurs réponses RAG |

**Processus :**
1. Met à jour `visibility` en base (`private` ↔ `public`)
2. Met à jour les métadonnées dans ChromaDB
3. Effet immédiat sur les prochaines requêtes RAG

**Payload :**
```json
{ "visibility": "public" }  // ou "private"
```

#### 5.3.2. Sous-onglet Conversations

```
┌─────────────────────────────────────────────────────────────────┐
│  Filtres: [Utilisateur ▼] [Mode ▼] [Archivé ▼] [🔍 Recherche ] │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Titre           │ User     │ Mode │ Messages│ Date   │ Act. ││
│  ├─────────────────┼──────────┼──────┼─────────┼────────┼──────┤│
│  │ Question RAG    │ john_doe │ RAG  │ 12      │ 26/12  │ 👁️ 🗑️││
│  │ Discussion lib..│ marie_t  │ Asst │ 45      │ 25/12  │ 👁️ 🗑️││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Détail conversation :**
```
┌─────────────────────────────────────────────────────────────────┐
│  💬 Conversation: "Question RAG"                   [← Retour]  │
├─────────────────────────────────────────────────────────────────┤
│  User: john_doe │ Mode: RAG │ Messages: 12 │ Créé: 26/12/2025  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [👤 User] Bonjour, peux-tu m'expliquer...                      │
│  [🤖 AI] Bien sûr ! Voici l'explication...                      │
│  [👤 User] Et concernant...                                     │
│  ...                                                            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  [📦 Archiver] [🗑️ Supprimer conversation]                      │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `GET /admin/conversations-admin`
- `GET /admin/conversations-admin/{id}`
- `POST /admin/conversations-admin/{id}/archive`
- `DELETE /admin/conversations-admin/{id}`
- `GET /admin/messages?conversation_id={id}`

---

### 5.4. Onglet Audit (#audit)

**Objectif :** Traçabilité des actions et export de données.

**Sous-onglets internes :**

```
┌───────────────┬────────────────┐
│ 📋 Logs       │ 📤 Exports     │
└───────────────┴────────────────┘
```

#### 5.4.1. Sous-onglet Logs

```
┌─────────────────────────────────────────────────────────────────┐
│  📋 Logs d'audit                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Filtres: [Utilisateur ▼] [Action ▼] [Sévérité ▼]              │
│           [📅 Du: ____] [📅 Au: ____] [🔍 Recherche...]        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Date/Heure      │ User    │ Action        │ Sév. │ Détails  ││
│  ├─────────────────┼─────────┼───────────────┼──────┼──────────┤│
│  │ 26/12 14:32:15  │ admin   │ user.update   │ 🟡   │ 👁️       ││
│  │ 26/12 14:30:02  │ john    │ doc.upload    │ 🟢   │ 👁️       ││
│  │ 26/12 14:28:45  │ admin   │ user.delete   │ 🔴   │ 👁️       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Légende: 🟢 Info  🟡 Warning  🔴 Critical                      │
└─────────────────────────────────────────────────────────────────┘
```

**Détail d'un log :**
```
┌─────────────────────────────────────────────────────────────────┐
│  📋 Détail du log                                  [× Fermer]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Date:        26/12/2025 14:28:45                               │
│  Utilisateur: admin (admin@myia.com)                            │
│  Action:      user.delete                                       │
│  Sévérité:    🔴 Critical                                       │
│                                                                 │
│  Ressource:   User #a1b2c3d4                                    │
│  IP:          192.168.1.100                                     │
│  User-Agent:  Mozilla/5.0 (Macintosh...)                        │
│                                                                 │
│  Détails:                                                       │
│  { "deleted_user_email": "marie@test.fr" }                      │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `GET /admin/audit`
- `GET /admin/audit-actions` (liste des types d'actions)

#### 5.4.2. Sous-onglet Exports

```
┌─────────────────────────────────────────────────────────────────┐
│  📤 Exports de données                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 👥 Utilisateurs                                             ││
│  │ Exporter la liste des utilisateurs                          ││
│  │ Format: [CSV ▼]  Filtres: [Tous ▼]                          ││
│  │                                    [📥 Télécharger]         ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 💬 Conversations                                            ││
│  │ Exporter les conversations                                  ││
│  │ Format: [JSON ▼]  User: [Tous ▼]                            ││
│  │                                    [📥 Télécharger]         ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 📄 Documents                                                ││
│  │ Exporter la liste des documents                             ││
│  │ Format: [CSV ▼]  User: [Tous ▼]                             ││
│  │                                    [📥 Télécharger]         ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `GET /admin/export/users?format=csv`
- `GET /admin/export/conversations?format=json`
- `GET /admin/export/documents?format=csv`

---

### 5.5. Onglet Système (#system)

**Objectif :** Configuration globale de la plateforme.

**Sous-onglets internes :**

```
┌─────────────┬────────────────┬───────────────┬──────────────┐
│ 💬 Modes    │ 🔐 Mot de passe│ 🤖 RAG        │ 🌍 Géo       │
└─────────────┴────────────────┴───────────────┴──────────────┘
```

#### 5.5.1. Modes de Conversation

```
┌─────────────────────────────────────────────────────────────────┐
│  💬 Modes de conversation                           [+ Créer]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Nom        │ Prompt système (extrait)              │ Actions││
│  ├────────────┼───────────────────────────────────────┼────────┤│
│  │ RAG        │ Tu es un assistant qui utilise...     │ ✏️     ││
│  │ Assistant  │ Tu es un assistant général...         │ ✏️ 🗑️  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Formulaire mode :**
```
┌─────────────────────────────────────────────────────────────────┐
│  Nom du mode *    [_________________________________]           │
│                                                                 │
│  Prompt système * [                                 ]           │
│                   [                                 ]           │
│                   [_________________________________]           │
│                                                                 │
│                              [Annuler] [💾 Enregistrer]         │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `GET /admin/conversation-modes`
- `POST /admin/conversation-modes`
- `PATCH /admin/conversation-modes/{id}`
- `DELETE /admin/conversation-modes/{id}`

#### 5.5.2. Politique de Mot de Passe

```
┌─────────────────────────────────────────────────────────────────┐
│  🔐 Politique de mot de passe                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Longueur minimale        [8    ] caractères                    │
│  Longueur maximale        [128  ] caractères                    │
│                                                                 │
│  Exigences:                                                     │
│  [x] Majuscules requises                                        │
│  [x] Minuscules requises                                        │
│  [x] Chiffres requis                                            │
│  [x] Caractères spéciaux requis                                 │
│                                                                 │
│  Expiration:                                                    │
│  [ ] Activer l'expiration   [90] jours                          │
│                                                                 │
│  Historique:                                                    │
│  [x] Empêcher réutilisation [5 ] derniers mots de passe        │
│                                                                 │
│                                          [💾 Enregistrer]       │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `GET /admin/password-policies`
- `PATCH /admin/password-policies/{id}`

#### 5.5.3. Configuration RAG

```
┌─────────────────────────────────────────────────────────────────┐
│  🤖 Configuration RAG                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Recherche vectorielle:                                         │
│  Top K (documents retournés)  [5    ]                           │
│  Seuil de similarité          [0.7  ]                           │
│                                                                 │
│  Modèle LLM:                                                    │
│  Modèle actuel               [mistral        ▼]                 │
│  Température                  [0.7  ]                           │
│                                                                 │
│  Embeddings:                                                    │
│  Modèle                      [nomic-embed-text]                 │
│                                                                 │
│                                          [💾 Enregistrer]       │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `GET /admin/config/rag`
- `PATCH /admin/config/rag`

#### 5.5.4. Données Géographiques

```
┌─────────────────────────────────────────────────────────────────┐
│  🌍 Données géographiques                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 🏳️ Pays                                          [+ Créer] ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ Code │ Drapeau │ Nom          │ Préfixe │ Actif  │ Actions  ││
│  ├──────┼─────────┼──────────────┼─────────┼────────┼──────────┤│
│  │ FR   │ 🇫🇷      │ France       │ +33     │ ✅     │ ✏️       ││
│  │ BE   │ 🇧🇪      │ Belgique     │ +32     │ ✅     │ ✏️       ││
│  │ CH   │ 🇨🇭      │ Suisse       │ +41     │ ❌     │ ✏️       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 🏙️ Villes                    Total: 35,247                 ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ [🔍 Rechercher ville...]                                    ││
│  │                                                             ││
│  │ [📤 Importer CSV]  Dernier import: 25/12/2025              ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints :**
- `GET /admin/geo/countries`
- `PATCH /admin/geo/countries/{code}`
- `GET /admin/geo/cities`
- `POST /admin/geo/import`

---

## 6. Composants Réutilisables

### 6.1. Table Dynamique (`table.js`)

```javascript
/**
 * Composant table générique avec:
 * - Colonnes configurables
 * - Tri par colonne
 * - Sélection multiple (checkbox)
 * - Actions par ligne
 * - Responsive (scroll horizontal)
 */
class DataTable {
    constructor(containerId, options) {
        this.container = document.getElementById(containerId);
        this.columns = options.columns;      // [{key, label, sortable, render}]
        this.actions = options.actions;      // [{icon, label, onClick}]
        this.selectable = options.selectable; // boolean
        this.onSelect = options.onSelect;    // callback(selectedIds)
    }

    render(data) { /* ... */ }
    sort(column, direction) { /* ... */ }
    getSelected() { /* ... */ }
}
```

### 6.2. Pagination (`pagination.js`)

```javascript
/**
 * Composant pagination avec:
 * - Navigation première/dernière page
 * - Pages numérotées avec ellipsis
 * - Sélecteur "items par page"
 * - Affichage total
 */
class Pagination {
    constructor(options) {
        this.total = options.total;
        this.perPage = options.perPage || 25;
        this.current = options.current || 1;
        this.onChange = options.onChange;
    }

    render(containerId) { /* ... */ }
    goTo(page) { /* ... */ }
}
```

### 6.3. Filtres (`filters.js`)

```javascript
/**
 * Composant filtres avec:
 * - Champs select/input configurables
 * - Recherche avec debounce
 * - Bouton "Réinitialiser"
 * - Callback onChange
 */
class Filters {
    constructor(containerId, fields) {
        this.fields = fields; // [{type, key, label, options?}]
    }

    render() { /* ... */ }
    getValues() { /* ... */ }
    reset() { /* ... */ }
}
```

### 6.4. Stats Card (`stats-card.js`)

```javascript
/**
 * Carte statistique avec:
 * - Icône
 * - Valeur principale
 * - Label
 * - Variation (optionnel)
 */
class StatsCard {
    constructor(options) {
        this.icon = options.icon;
        this.value = options.value;
        this.label = options.label;
        this.trend = options.trend; // {value, direction: 'up'|'down'}
    }

    render(containerId) { /* ... */ }
}
```

### 6.5. Système d'Onglets (`tabs.js`)

```javascript
/**
 * Gestion des onglets avec:
 * - Onglets principaux (header)
 * - Sous-onglets (dans le contenu)
 * - Navigation hash-based
 * - Animation de transition
 */
class TabSystem {
    constructor(containerId, tabs) {
        this.tabs = tabs; // [{id, label, icon, content}]
    }

    render() { /* ... */ }
    activate(tabId) { /* ... */ }
}
```

---

## 7. Services API Admin

### 7.1. Structure `adminApi.js`

```javascript
// UI-BACK/js/services/adminApi.js
import { api } from '../../shared/js/services/api.js';

export const adminApi = {
    // Dashboard
    dashboard: {
        overview: () => api.get('/admin/dashboard/overview'),
        usage: () => api.get('/admin/dashboard/usage'),
    },

    // Users
    users: {
        list: (params) => api.get('/admin/users', params),
        get: (id) => api.get(`/admin/users/${id}`),
        create: (data) => api.post('/admin/users', data),
        update: (id, data) => api.patch(`/admin/users/${id}`, data),
        delete: (id) => api.delete(`/admin/users/${id}`),
        updateStatus: (id, active) => api.patch(`/admin/users/${id}/status`, { is_active: active }),
        updateRole: (id, roleId) => api.patch(`/admin/users/${id}/role`, { role_id: roleId }),
        resetPassword: (id) => api.post(`/admin/users/${id}/reset-password`),
    },

    // Bulk operations
    bulk: {
        activate: (ids) => api.post('/admin/bulk/users/activate', { user_ids: ids }),
        deactivate: (ids) => api.post('/admin/bulk/users/deactivate', { user_ids: ids }),
        changeRole: (ids, roleId) => api.post('/admin/bulk/users/change-role', { user_ids: ids, role_id: roleId }),
        delete: (ids) => api.post('/admin/bulk/users/delete', { user_ids: ids }),
    },

    // Documents
    documents: {
        list: (params) => api.get('/admin/documents', params),
        delete: (id) => api.delete(`/admin/documents/${id}`),
        reindex: (id) => api.post(`/admin/documents/${id}/reindex`),
        deindex: (id) => api.post(`/admin/documents/${id}/deindex`),
        updateVisibility: (id, visibility) => api.patch(`/admin/documents/${id}/visibility`, { visibility }),
    },

    // Conversations
    conversations: {
        list: (params) => api.get('/admin/conversations-admin', params),
        get: (id) => api.get(`/admin/conversations-admin/${id}`),
        archive: (id) => api.post(`/admin/conversations-admin/${id}/archive`),
        delete: (id) => api.delete(`/admin/conversations-admin/${id}`),
    },

    // Audit
    audit: {
        list: (params) => api.get('/admin/audit', params),
        actions: () => api.get('/admin/audit-actions'),
    },

    // Exports
    export: {
        users: (format) => api.download(`/admin/export/users?format=${format}`),
        conversations: (format) => api.download(`/admin/export/conversations?format=${format}`),
        documents: (format) => api.download(`/admin/export/documents?format=${format}`),
    },

    // Roles
    roles: {
        list: () => api.get('/admin/roles'),
        create: (data) => api.post('/admin/roles', data),
        update: (id, data) => api.patch(`/admin/roles/${id}`, data),
        delete: (id) => api.delete(`/admin/roles/${id}`),
    },

    // Conversation modes
    modes: {
        list: () => api.get('/admin/conversation-modes'),
        create: (data) => api.post('/admin/conversation-modes', data),
        update: (id, data) => api.patch(`/admin/conversation-modes/${id}`, data),
        delete: (id) => api.delete(`/admin/conversation-modes/${id}`),
    },

    // Password policy
    passwordPolicy: {
        get: () => api.get('/admin/password-policies'),
        update: (id, data) => api.patch(`/admin/password-policies/${id}`, data),
    },

    // RAG config
    rag: {
        get: () => api.get('/admin/config/rag'),
        update: (data) => api.patch('/admin/config/rag', data),
    },

    // Geo
    geo: {
        countries: () => api.get('/admin/geo/countries'),
        updateCountry: (code, data) => api.patch(`/admin/geo/countries/${code}`, data),
        cities: (params) => api.get('/admin/geo/cities', params),
        importCities: (file) => api.upload('/admin/geo/import', file),
    },
};
```

---

## 8. Sécurité

### 8.1. Vérification des Accès

```javascript
// UI-BACK/js/app.js
import { auth } from '../shared/js/services/auth.js';

async function init() {
    // Vérifier si l'utilisateur est connecté et admin
    const user = await auth.getCurrentUser();

    if (!user) {
        window.location.href = '/app/#login';
        return;
    }

    if (user.role_id !== 1) {
        // Pas admin → redirection
        showToast('Accès non autorisé', 'error');
        window.location.href = '/app/';
        return;
    }

    // Initialiser l'interface admin
    initAdminUI(user);
}
```

### 8.2. Intercepteur API

```javascript
// UI-SHARED/js/services/api.js
api.interceptors.response = async (response) => {
    if (response.status === 401) {
        // Token expiré → déconnexion
        auth.logout();
        window.location.href = '/app/#login';
    }
    if (response.status === 403) {
        // Pas autorisé
        showToast('Action non autorisée', 'error');
    }
    return response;
};
```

---

## 9. Phases d'Implémentation

### Phase 1 : Infrastructure (Priorité: 🔴 Haute)

| Étape | Description | Fichiers |
|-------|-------------|----------|
| 1.1 | Renommer `frontend/` en `UI-FRONT/` | Renommage dossier |
| 1.2 | Créer répertoire `UI-SHARED/` | Nouveau dossier |
| 1.3 | Migrer ressources communes vers `UI-SHARED/` | Déplacer depuis UI-FRONT/ |
| 1.4 | Créer répertoire `UI-BACK/` | Nouveau dossier |
| 1.5 | Créer liens symboliques | UI-FRONT/shared, UI-BACK/shared |
| 1.6 | Modifier docker-compose.yml | Renommer service, ajouter volumes |
| 1.7 | Créer nginx.conf | Configuration routing |
| 1.8 | Mettre à jour les imports dans UI-FRONT | Chemins vers shared/ |
| 1.9 | Tester UI-FRONT existant | Vérifier que rien n'est cassé |

### Phase 2 : Layout Admin (Priorité: 🔴 Haute)

| Étape | Description | Fichiers |
|-------|-------------|----------|
| 2.1 | Créer UI-BACK/index.html | Structure HTML |
| 2.2 | Créer CSS layout | layout.css, tabs.css |
| 2.3 | Créer système onglets | tabs.js, router.js |
| 2.4 | Créer app.js admin | Point d'entrée |
| 2.5 | Vérification accès admin | Redirection si non-admin |

### Phase 3 : Composants Réutilisables (Priorité: 🔴 Haute)

| Étape | Description | Fichiers |
|-------|-------------|----------|
| 3.1 | Composant Table | table.js, table.css |
| 3.2 | Composant Pagination | pagination.js |
| 3.3 | Composant Filtres | filters.js |
| 3.4 | Composant Stats Card | stats-card.js |
| 3.5 | Service adminApi | adminApi.js |

### Phase 4 : Onglet Dashboard (Priorité: 🔴 Haute)

| Étape | Description | Fichiers |
|-------|-------------|----------|
| 4.1 | Module dashboard.js | Logique métier |
| 4.2 | CSS dashboard | dashboard.css |
| 4.3 | Cartes KPI | Intégration stats-card |
| 4.4 | Liste dernières actions | Mini-table audit |
| 4.5 | Tests et ajustements | - |

### Phase 5 : Onglet Utilisateurs (Priorité: 🔴 Haute)

| Étape | Description | Fichiers |
|-------|-------------|----------|
| 5.1 | Liste utilisateurs | users.js (liste) |
| 5.2 | Détail utilisateur | users.js (view) |
| 5.3 | Création utilisateur | users.js (create) |
| 5.4 | Édition utilisateur | users.js (edit) |
| 5.5 | Gestion rôles | users.js (roles) |
| 5.6 | Opérations bulk | users.js (bulk) |
| 5.7 | Tests et ajustements | - |

### Phase 6 : Onglet Contenu (Priorité: 🟠 Moyenne)

| Étape | Description | Fichiers |
|-------|-------------|----------|
| 6.1 | Sous-onglet Documents | content.js (documents) |
| 6.2 | Actions documents (reindex, visibilité) | - |
| 6.3 | Sous-onglet Conversations | content.js (conversations) |
| 6.4 | Détail conversation | Modal messages |
| 6.5 | Tests et ajustements | - |

### Phase 7 : Onglet Audit (Priorité: 🟠 Moyenne)

| Étape | Description | Fichiers |
|-------|-------------|----------|
| 7.1 | Liste logs audit | audit.js (logs) |
| 7.2 | Détail log (modal) | - |
| 7.3 | Section exports | audit.js (exports) |
| 7.4 | Téléchargement fichiers | - |
| 7.5 | Tests et ajustements | - |

### Phase 8 : Onglet Système (Priorité: 🟢 Basse)

| Étape | Description | Fichiers |
|-------|-------------|----------|
| 8.1 | Modes de conversation | system.js (modes) |
| 8.2 | Politique mot de passe | system.js (password) |
| 8.3 | Configuration RAG | system.js (rag) |
| 8.4 | Données géographiques | system.js (geo) |
| 8.5 | Tests et ajustements | - |

---

## 10. Estimation

| Phase | Complexité | Estimation |
|-------|------------|------------|
| Phase 1 | Moyenne | Infrastructure |
| Phase 2 | Moyenne | Layout + routing |
| Phase 3 | Haute | Composants génériques |
| Phase 4 | Faible | Dashboard simple |
| Phase 5 | Haute | CRUD complet users |
| Phase 6 | Moyenne | Documents + conversations |
| Phase 7 | Faible | Audit + exports |
| Phase 8 | Moyenne | Configuration système |

---

## 11. Notes Techniques

### 11.1. Compatibilité Navigateurs

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

### 11.2. Responsive Design

- Desktop : Layout complet
- Tablet (768px-1024px) : Sidebar réduite, onglets scrollables
- Mobile (<768px) : Menu hamburger, contenu full-width

### 11.3. Performance

- Lazy loading des modules par onglet
- Pagination côté serveur (pas de chargement complet)
- Debounce sur les recherches (300ms)
- Cache des données de référence (rôles, modes)

### 11.4. Accessibilité

- Navigation clavier (Tab, Enter, Escape)
- Labels ARIA sur les éléments interactifs
- Contraste suffisant (WCAG AA)
- Focus visible

---

*Document créé le 26 décembre 2025*
