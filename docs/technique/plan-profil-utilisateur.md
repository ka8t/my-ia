# Plan : Gestion du Profil Utilisateur avec Chiffrement PII

**Date** : 2025-12-26
**Statut** : En cours
**Version** : 1.1
**Dernière mise à jour** : 2025-12-26

---

## Objectif

Permettre aux utilisateurs de modifier leur profil (informations personnelles, mot de passe) avec :
- Chiffrement des données personnelles (PII) en base
- Recherche sur les champs chiffrés (blind index + trigrammes)
- Politique de mot de passe configurable par l'admin
- Données géographiques stockées localement (pays, villes)

---

## Architecture Technique

### Chiffrement des PII

| Technique | Usage | Description |
|-----------|-------|-------------|
| **AES-256-GCM** | Chiffrement | Advanced Encryption Standard avec Galois/Counter Mode. Chiffrement symétrique 256 bits avec authentification (détecte les modifications). |
| **HMAC-SHA256** | Blind Index (recherche exacte) | Hash à clé pour créer un index de recherche sans exposer la donnée. Permet `WHERE blind_index = hash(valeur)`. |
| **Trigrammes hashés** | Recherche partielle | Découpe en fragments de 3 caractères, chaque trigramme est hashé. Permet recherche LIKE sur données chiffrées. |

### Dérivation des clés

```
ENCRYPTION_KEY (env var, 32 bytes hex)
    │
    ├── AES Key (pour chiffrement)
    │
    └── HMAC Key (dérivée via HKDF pour blind index)
```

---

## Schéma de la Base de Données

### Champs Utilisateur (table `users`)

| Champ | Type | Chiffré | Recherchable | Obligatoire |
|-------|------|---------|--------------|-------------|
| `email` | String | Non (login) | Oui (natif) | Oui |
| `username` | String | Non (login) | Oui (natif) | Oui |
| `first_name` | Text | AES-256-GCM | Trigrammes | Oui |
| `first_name_search` | String | - | Index trigrammes | - |
| `last_name` | Text | AES-256-GCM | Trigrammes | Oui |
| `last_name_search` | String | - | Index trigrammes | - |
| `phone` | Text | AES-256-GCM | Blind Index | Oui |
| `phone_blind_index` | String(64) | - | Exact | - |
| `address_line1` | Text | AES-256-GCM | Non | Non |
| `address_line2` | Text | AES-256-GCM | Non | Non |
| `city_id` | Integer | Non | FK → cities | Non |
| `country_code` | String(2) | Non | FK → countries | Non (défaut: FR) |

### Table `countries` (données géographiques locales)

```sql
CREATE TABLE countries (
    code VARCHAR(2) PRIMARY KEY,      -- ISO 3166-1 alpha-2 (FR, US, DE...)
    name VARCHAR(100) NOT NULL,       -- Nom du pays
    flag VARCHAR(10) NOT NULL,        -- Emoji drapeau (🇫🇷)
    phone_prefix VARCHAR(5),          -- Préfixe téléphonique (+33)
    is_active BOOLEAN DEFAULT true,   -- Actif dans la liste
    display_order INTEGER DEFAULT 999 -- Ordre d'affichage
);
```

### Table `cities` (données géographiques locales)

```sql
CREATE TABLE cities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,           -- Nom de la ville
    postal_code VARCHAR(10) NOT NULL,     -- Code postal
    country_code VARCHAR(2) NOT NULL,     -- FK → countries
    department_code VARCHAR(10),          -- Code département (pour France)
    department_name VARCHAR(100),         -- Nom département
    region_name VARCHAR(100),             -- Nom région
    latitude DECIMAL(10, 8),              -- Coordonnées GPS
    longitude DECIMAL(11, 8),
    population INTEGER,                   -- Population (pour tri pertinence)
    search_name VARCHAR(200),             -- Nom normalisé pour recherche
    FOREIGN KEY (country_code) REFERENCES countries(code)
);
CREATE INDEX idx_cities_search ON cities(search_name, country_code);
CREATE INDEX idx_cities_postal ON cities(postal_code, country_code);
```

### Table `password_policies` (politique mot de passe)

```sql
CREATE TABLE password_policies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,     -- 'default', 'admin', 'strict'
    min_length INTEGER DEFAULT 8,
    max_length INTEGER DEFAULT 128,
    require_uppercase BOOLEAN DEFAULT true,
    require_lowercase BOOLEAN DEFAULT true,
    require_digit BOOLEAN DEFAULT true,
    require_special BOOLEAN DEFAULT true,
    special_characters VARCHAR(50) DEFAULT '!@#$%^&*()_+-=[]{}|;:,.<>?',
    expire_days INTEGER DEFAULT 0,        -- 0 = jamais
    history_count INTEGER DEFAULT 0,      -- Nombre d'anciens mdp interdits
    max_failed_attempts INTEGER DEFAULT 5,
    lockout_duration_minutes INTEGER DEFAULT 30,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Table `password_history` (historique mots de passe)

```sql
CREATE TABLE password_history (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    hashed_password VARCHAR(1024) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_password_history_user ON password_history(user_id, created_at DESC);
```

---

## Phases d'Implémentation

### Phase 1 : Infrastructure Crypto

**Fichiers à créer :**
```
app/common/crypto/
├── __init__.py
├── encryption.py      # EncryptionService (AES-256-GCM)
├── search.py          # SearchIndexService (Blind Index + Trigrammes)
├── types.py           # EncryptedString (type SQLAlchemy custom)
└── key_manager.py     # Gestion des clés (dérivation HKDF)
```

**Fonctionnalités :**
- `EncryptionService.encrypt(plaintext) → ciphertext`
- `EncryptionService.decrypt(ciphertext) → plaintext`
- `SearchIndexService.create_blind_index(value) → hash`
- `SearchIndexService.create_trigram_index(value) → hash_set`
- `SearchIndexService.search_trigrams(query, stored_hashes) → bool`

**Configuration `.env` :**
```env
# Clé de chiffrement (générer avec: openssl rand -hex 32)
ENCRYPTION_KEY=your-256-bit-hex-key-here
```

---

### Phase 2 : Modèle User + Migration

**Modifications `app/models/user.py` :**
- Ajouter champs chiffrés (`first_name`, `last_name`, `phone`, `address_*`)
- Ajouter colonnes d'index (`*_blind_index`, `*_search`)
- Relations vers `countries` et `cities`

**Migration Alembic :**
```bash
alembic revision -m "add_user_profile_fields_encrypted"
```

---

### Phase 3 : Politique Mot de Passe

**Fichiers à créer :**
```
app/features/admin/password_policy/
├── router.py          # CRUD politique (admin only)
├── service.py         # Logique métier
├── repository.py      # Accès DB
└── schemas.py         # DTOs Pydantic
```

**Endpoints Admin :**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/admin/password-policies` | Liste des politiques |
| GET | `/api/admin/password-policies/{id}` | Détail politique |
| POST | `/api/admin/password-policies` | Créer politique |
| PATCH | `/api/admin/password-policies/{id}` | Modifier politique |
| DELETE | `/api/admin/password-policies/{id}` | Supprimer politique |

**Validateur :**
```python
class PasswordValidator:
    def validate(self, password: str, policy: PasswordPolicy) -> list[str]:
        """Retourne liste des erreurs ou [] si valide"""
```

---

### Phase 4 : Données Géographiques (Locales)

**Fichiers à créer :**
```
app/features/geo/
├── router.py          # Endpoints publics (recherche villes)
├── service.py         # Logique métier
├── repository.py      # Accès DB
├── schemas.py         # DTOs
└── importer.py        # Import depuis API externe (admin)

app/features/admin/geo/
├── router.py          # Endpoints admin (import données)
└── service.py         # Service d'import
```

**Tables pré-remplies :**
- `countries` : ~250 pays avec drapeaux emoji
- `cities` : Villes françaises (~35 000) via api.gouv.fr

**Endpoints Publics (utilisateur) :**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/geo/countries` | Liste des pays actifs |
| GET | `/api/geo/cities?q=paris&country=FR` | Recherche villes |
| GET | `/api/geo/cities/{id}` | Détail ville |

**Endpoints Admin :**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/admin/geo/import/countries` | Importer pays |
| POST | `/api/admin/geo/import/cities?country=FR` | Importer villes depuis api.gouv.fr |
| GET | `/api/admin/geo/import/status` | Statut dernière importation |

**Source des données :**
- Pays : Liste statique ISO 3166-1 avec emojis drapeaux
- Villes France : `https://geo.api.gouv.fr/communes`

---

### Phase 5 : API Backend Profil

**Fichiers à créer/modifier :**
```
app/features/user/
├── router.py          # Endpoints profil
├── service.py         # Logique métier (avec chiffrement)
├── repository.py      # Accès DB
└── schemas.py         # DTOs (ProfileUpdate, PasswordChange)
```

**Endpoints Utilisateur :**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/users/me/profile` | Récupérer mon profil complet |
| PATCH | `/api/users/me/profile` | Modifier mon profil |
| POST | `/api/users/me/change-password` | Changer mot de passe |
| POST | `/api/users/me/request-email-change` | Demander changement email |
| POST | `/api/users/me/verify-email-change` | Confirmer avec token |

**Endpoints Admin (recherche utilisateurs) :**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/admin/users/search?q=...` | Recherche sur champs chiffrés |

---

### Phase 6 : Frontend Modal Profil

**Fichiers à créer/modifier :**
```
frontend/
├── css/components/
│   ├── modal-profile.css    # Styles modal profil
│   └── country-selector.css # Sélecteur pays avec drapeaux
├── js/modules/
│   ├── profile.js           # Gestion profil utilisateur
│   ├── countrySelector.js   # Composant sélecteur pays
│   └── cityAutocomplete.js  # Composant autocomplete ville
└── index.html               # Ajout modal profil
```

**Structure Modal :**
```
┌─────────────────────────────────────────┐
│ Mon Profil                          [X] │
├─────────────────────────────────────────┤
│ [Informations] [Sécurité] [Préférences] │
├─────────────────────────────────────────┤
│                                         │
│  Prénom*: [_______________]             │
│  Nom*:    [_______________]             │
│                                         │
│  Téléphone*: [🇫🇷 +33 ▼] [_________]    │
│                                         │
│  Email*:  [_______________] ✓ Vérifié   │
│                                         │
│  Adresse: [_______________]             │
│           [_______________]             │
│                                         │
│  Pays:    [🇫🇷 France          ▼]       │
│  Ville:   [________________] (auto)     │
│  CP:      [_____] (auto-rempli)         │
│                                         │
│           [Annuler] [Enregistrer]       │
└─────────────────────────────────────────┘
```

**Onglet Sécurité :**
```
┌─────────────────────────────────────────┐
│  Mot de passe actuel: [___________] 👁  │
│  Nouveau mot de passe: [__________] 👁  │
│  Confirmer:           [___________] 👁  │
│                                         │
│  Règles:                                │
│  ✓ 8 caractères minimum                 │
│  ✓ 1 majuscule                          │
│  ✗ 1 chiffre                            │
│  ✗ 1 caractère spécial                  │
│                                         │
│           [Changer le mot de passe]     │
└─────────────────────────────────────────┘
```

---

### Phase 7 : Tests Unitaires

**Tests à créer :**
```
tests/
├── crypto/
│   ├── test_encryption.py       # Tests AES-256-GCM
│   ├── test_search_index.py     # Tests Blind Index + Trigrammes
│   └── test_integration.py      # Tests encrypt/decrypt/search
├── user/
│   ├── test_profile_service.py  # Tests service profil
│   └── test_profile_api.py      # Tests endpoints HTTP
├── password_policy/
│   ├── test_validator.py        # Tests validation mot de passe
│   └── test_policy_api.py       # Tests endpoints admin
└── geo/
    ├── test_geo_service.py      # Tests recherche villes
    └── test_geo_import.py       # Tests import admin
```

---

## Variables d'Environnement à Ajouter

```env
# Chiffrement PII (OBLIGATOIRE - générer avec: openssl rand -hex 32)
ENCRYPTION_KEY=

# Optionnel - Clé HMAC séparée (si non fournie, dérivée de ENCRYPTION_KEY)
HMAC_KEY=
```

---

## Sécurité

### Bonnes Pratiques Appliquées

1. **Chiffrement au repos** : Toutes les PII chiffrées en AES-256-GCM
2. **Clés séparées** : Clé de chiffrement ≠ clé HMAC (dérivation HKDF)
3. **IV unique** : Chaque chiffrement utilise un IV aléatoire
4. **Authentification** : GCM détecte toute modification des données chiffrées
5. **Pas de réversibilité** : Blind index = hash, impossible de retrouver l'original
6. **Rate limiting** : Limiter les tentatives de recherche pour éviter énumération

### Risques Mitigés

| Risque | Mitigation |
|--------|------------|
| Vol de base de données | Données chiffrées inutilisables sans clé |
| Recherche par énumération | Rate limiting + blind index (hash) |
| Modification malveillante | GCM détecte les altérations |
| Réutilisation de mot de passe | Historique des N derniers mots de passe |
| Brute force login | Verrouillage après X tentatives |

---

## Ordre d'Exécution

```
Phase 1 ──► Phase 2 ──► Phase 3 ──┐
                                  │
Phase 4 ─────────────────────────►├──► Phase 5 ──► Phase 6 ──► Phase 7
```

- Phases 1-3 et Phase 4 peuvent être développées en parallèle
- Phase 5 (API) nécessite Phases 1-4
- Phase 6 (Frontend) nécessite Phase 5
- Phase 7 (Tests) continue tout au long du développement

---

## Estimation Complexité

| Phase | Fichiers | Complexité |
|-------|----------|------------|
| Phase 1 | 5 | Moyenne |
| Phase 2 | 2 | Faible |
| Phase 3 | 5 | Moyenne |
| Phase 4 | 7 | Moyenne |
| Phase 5 | 4 | Moyenne |
| Phase 6 | 5 | Moyenne |
| Phase 7 | 8 | Moyenne |

**Total** : ~36 fichiers à créer/modifier

---

## Avancement

### Phases Complétées

| Phase | Statut | Notes |
|-------|--------|-------|
| Phase 1 | ✅ Terminé | Infrastructure crypto implémentée |
| Phase 2 | ✅ Terminé | Modèle User + Migration appliquée |
| Phase 3 | ⏳ Partiel | Politique mot de passe basique |
| Phase 4 | ✅ Terminé | Données géo importées (France) |
| Phase 5 | ✅ Terminé | API Backend profil |
| Phase 6 | ✅ Terminé | Frontend Modal Profil |
| Phase 7 | ⏳ En cours | Tests à compléter |

---

## Fonctionnalités Frontend Implémentées

### Modal Profil (`frontend/js/modules/profile.js`)

**Onglet Informations :**
- Affichage/modification des champs : prénom, nom, téléphone, adresse
- Champs non modifiables : email, nom d'utilisateur
- Sélection pays avec drapeaux emoji
- Autocomplétion ville (recherche sur api locale)
- France sélectionnée par défaut

**Onglet Mot de passe :**
- Changement de mot de passe avec validation

**UX Améliorations :**
- Bouton "Annuler" sur toutes les modales
- Touche Escape pour fermer les modales
- Tooltip "Mon profil" sur le nom utilisateur (sidebar)
- Placeholders dynamiques "Veuillez saisir..."
- Validation des champs obligatoires (min 4 caractères)
- Highlight rouge des champs invalides

### Légende des Icônes

Les champs du formulaire affichent des icônes indiquant leur statut :

| Icône | Signification |
|-------|---------------|
| ⚠️ (exclamation cercle) | Champ obligatoire |
| 🔒 (cadenas) | Champ chiffré en base |
| 🚫 (cercle barré) | Champ non modifiable |

---

## Système d'Icônes Centralisé

### Fichier de Configuration

**Emplacement** : `frontend/js/config/icons.js`

Ce fichier centralise toutes les icônes SVG et leurs métadonnées pour faciliter la maintenance.

### Icônes Disponibles

| Nom | Label | Tooltip | Usage |
|-----|-------|---------|-------|
| `required` | Obligatoire | Ce champ est obligatoire | Champs requis |
| `encrypted` | Chiffré | Ce champ est chiffré en base de données | PII chiffrées |
| `readonly` | Non modifiable | Ce champ ne peut pas être modifié | Email, username |
| `verified` | Vérifié | Ce compte a été vérifié | Badge compte |
| `info` | Information | Information supplémentaire | Aide contextuelle |
| `error` | Erreur | Une erreur est survenue | Messages erreur |
| `success` | Succès | Opération réussie | Confirmations |
| `warning` | Attention | Attention requise | Avertissements |

### API JavaScript

```javascript
// Générer une icône SVG
Icons.render('required')           // Taille par défaut 14px
Icons.render('encrypted', 16)      // Taille personnalisée 16px

// Obtenir les métadonnées
Icons.getTooltip('required')       // "Ce champ est obligatoire"
Icons.getLabel('required')         // "Obligatoire"
Icons.get('required')              // Objet complet de définition

// Générer une légende complète
Icons.renderLegend(['required', 'encrypted', 'readonly'])
// Retourne HTML : <div class="profile-legend">...</div>

// Générer un label de champ avec icônes
Icons.renderFieldLabel('profileFirstName', 'Prénom', ['required', 'encrypted'])
// Retourne HTML : <label for="profileFirstName">...</label>

// Lister toutes les icônes disponibles
Icons.list()  // ['required', 'encrypted', 'readonly', 'verified', ...]
```

### Modifier une Icône

Pour modifier une icône ou son tooltip, éditer uniquement `frontend/js/config/icons.js` :

```javascript
// Dans Icons.definitions
required: {
    name: 'required',
    label: 'Obligatoire',              // Texte court (légende)
    tooltip: 'Ce champ est obligatoire', // Tooltip complet
    cssClass: 'required-icon',          // Classe CSS
    color: 'var(--warning-color)',      // Couleur par défaut
    viewBox: '0 0 24 24',               // ViewBox SVG
    path: `<circle cx="12" cy="12" r="10"/>...` // Chemin SVG
}
```

### Ajouter une Nouvelle Icône

1. Ajouter une entrée dans `Icons.definitions`
2. Définir le path SVG (viewBox 24x24 recommandé)
3. Ajouter le style CSS correspondant dans `profile.css` si nécessaire

---

## Validation Frontend

### Champs Obligatoires

Les champs suivants sont validés côté frontend avant enregistrement :

| Champ | Validation |
|-------|------------|
| Prénom | Min 4 caractères |
| Nom | Min 4 caractères |
| Téléphone | Min 4 caractères |
| Pays | Doit être sélectionné |
| Ville | Min 4 caractères + sélection dans liste |

### Comportement

1. Clic sur "Enregistrer" déclenche la validation
2. Si invalide : toast d'erreur + highlight rouge des champs
3. Le highlight disparaît quand l'utilisateur corrige le champ
4. L'enregistrement est bloqué tant que tous les champs ne sont pas valides

### Style CSS des Champs Invalides

```css
.profile-form-group input.field-invalid,
.profile-form-group select.field-invalid {
    border-color: var(--danger-color);
    background-color: rgba(239, 68, 68, 0.05);
}
```
