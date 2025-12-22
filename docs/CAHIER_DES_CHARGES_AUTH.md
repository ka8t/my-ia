# Cahier des Charges - Système d'Authentification et Backend de Gestion

**Projet :** MY-IA - Système d'authentification multi-utilisateurs avec gestion des rôles
**Version :** 1.0
**Date :** 21 décembre 2025
**Statut :** Spécifications initiales

---

## 1. Contexte et Objectifs

### 1.1 Contexte
Le projet MY-IA est actuellement une application monoposte utilisant le localStorage du navigateur pour stocker les conversations et préférences. Cette approche présente des limitations :
- Pas de synchronisation entre appareils
- Pas de gestion multi-utilisateurs
- Données volatiles (suppression cache = perte données)
- Pas de contrôle d'accès aux documents

### 1.2 Objectifs du projet
Développer un système d'authentification complet avec :
1. Gestion multi-utilisateurs avec 3 niveaux de rôles
2. Persistence des données en base de données PostgreSQL
3. Backend d'administration pour la gestion des utilisateurs
4. Architecture préparée pour l'intégration SSO future
5. Sécurité renforcée (JWT, HTTPS, rate limiting)

### 1.3 Bénéfices attendus
- **Pour les utilisateurs** : Accès sécurisé, données persistantes, synchronisation multi-appareils
- **Pour les administrateurs** : Contrôle granulaire des accès, monitoring des utilisateurs
- **Pour le projet** : Évolutivité, conformité sécurité, préparation enterprise

---

## 2. Périmètre Fonctionnel

### 2.1 Fonctionnalités principales

#### 2.1.1 Authentification (Front-end utilisateur)
- Inscription de nouveaux utilisateurs (email, username, mot de passe)
- Connexion avec email/password
- Déconnexion
- Réinitialisation de mot de passe (forgot password)
- Gestion du profil utilisateur
- Sessions persistantes avec refresh tokens

#### 2.1.2 Gestion des conversations
- Création de conversations (liées à l'utilisateur)
- Lecture de l'historique des conversations
- Modification (renommage) de conversations
- Suppression de conversations
- Isolation des conversations par utilisateur

#### 2.1.3 Gestion des préférences
- Sauvegarde des préférences utilisateur (thème, topK, etc.)
- Récupération au login
- Modification des préférences

#### 2.1.4 Gestion des documents (selon rôle)
- Upload de documents (Contributeur, Admin)
- Isolation des documents par utilisateur
- Suppression de documents (droits selon rôle)

#### 2.1.5 Backend d'Administration
- **Dashboard administrateur**
  - Vue d'ensemble du système (statistiques)
  - Nombre d'utilisateurs actifs
  - Nombre de conversations totales
  - Documents indexés
  - Utilisation ressources

- **Gestion des utilisateurs**
  - Liste de tous les utilisateurs (tableau paginé)
  - Recherche d'utilisateurs (nom, email)
  - Création manuelle d'utilisateurs
  - Modification des informations utilisateur
  - Changement de rôle (user ↔ contributor ↔ admin)
  - Activation/désactivation de comptes
  - Suppression d'utilisateurs
  - Réinitialisation de mot de passe (admin)

- **Audit et Monitoring**
  - Journal des connexions (login/logout)
  - Journal des actions administratives
  - Statistiques par utilisateur (nb conversations, uploads)
  - Détection comportements anormaux

- **Gestion des documents**
  - Liste des documents indexés
  - Filtrage par utilisateur propriétaire
  - Suppression de documents
  - Statistiques d'utilisation

- **Configuration système**
  - Paramètres globaux de l'API
  - Configuration rate limiting
  - Maintenance mode

### 2.2 Rôles et permissions

**Explication : Paramètre top_k**
Le paramètre `top_k` est un paramètre clé du système RAG (Retrieval Augmented Generation) qui détermine le nombre de documents/chunks les plus similaires à récupérer de la base vectorielle ChromaDB pour construire le contexte de la réponse de l'IA.

- **top_k = 4** (défaut) : Contexte équilibré (recommandé pour la plupart des cas)
- **top_k élevé (8-20)** : Contexte plus riche, utile pour questions complexes (risque de bruit)
- **top_k faible (1-3)** : Réponses plus ciblées, rapides

L'administrateur peut ajuster ce paramètre pour chaque utilisateur via `/admin/users/{id}/preferences`.

**Tableau des permissions**

| Fonctionnalité | Utilisateur | Contributeur | Administrateur |
|----------------|-------------|--------------|----------------|
| **Authentification** |
| Se connecter / Déconnecter | ✅ | ✅ | ✅ |
| Modifier son profil | ✅ | ✅ | ✅ |
| Réinitialiser son mot de passe | ✅ | ✅ | ✅ |
| Modifier ses préférences (top_k, thème, etc.) | ✅ | ✅ | ✅ |
| **Conversations** |
| Créer des conversations | ✅ | ✅ | ✅ |
| Voir ses conversations | ✅ | ✅ | ✅ |
| Modifier ses conversations | ✅ | ✅ | ✅ |
| Supprimer ses conversations | ✅ | ✅ | ✅ |
| Voir conversations des autres | ❌ | ❌ | ✅ |
| **Documents** |
| Uploader des documents | ❌ | ✅ | ✅ |
| Voir ses documents | ❌ | ✅ | ✅ |
| Supprimer ses documents | ❌ | ✅ | ✅ |
| Voir tous les documents | ❌ | ❌ | ✅ |
| Supprimer documents des autres | ❌ | ❌ | ✅ |
| **Administration** |
| Accéder au backend admin | ❌ | ❌ | ✅ |
| Gérer les utilisateurs | ❌ | ❌ | ✅ |
| Modifier rôles utilisateurs | ❌ | ❌ | ✅ |
| Modifier préférences d'autres utilisateurs | ❌ | ❌ | ✅ |
| Voir les statistiques | ❌ | ❌ | ✅ |
| Consulter l'audit trail | ❌ | ❌ | ✅ |
| Modifier la configuration système | ❌ | ❌ | ✅ |

---

## 3. Spécifications Techniques

### 3.1 Architecture

#### 3.1.1 Stack technique

**Backend**
- **Framework** : FastAPI 0.104+
- **Authentification** : FastAPI-Users 12.1+
- **Base de données** : PostgreSQL 15+
- **ORM** : SQLAlchemy 2.0+
- **Migrations** : Alembic 1.13+
- **Tokens** : JWT (python-jose)
- **Hashing** : bcrypt (passlib)
- **Validation** : Pydantic v2

**Frontend**
- **Technologies** : HTML5, CSS3, JavaScript (ES6+)
- **Librairies** : Existantes (marked.js, highlight.js)
- **Nouvelles pages** : login.html, admin.html

**Infrastructure**
- **Conteneurisation** : Docker + docker-compose
- **Base de données** : PostgreSQL (container existant)
- **Serveur web** : Nginx (pour frontend)

#### 3.1.2 Diagramme d'architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       FRONTEND                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ login.html│  │ index.html│  │ admin.html│  │  Nginx   │   │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └────┬─────┘   │
│        │             │             │             │          │
└────────┼─────────────┼─────────────┼─────────────┼──────────┘
         │             │             │             │
         ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND - FastAPI                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Auth Routes │  │  API Routes  │  │ Admin Routes │      │
│  │ /auth/*      │  │ /chat        │  │ /admin/*     │      │
│  │              │  │ /conversations│  │              │      │
│  │ FastAPI-Users│  │ /preferences │  │ (Admin only) │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │              │
│         └─────────────────┼──────────────────┘              │
│                           │                                 │
│                  ┌────────▼────────┐                        │
│                  │  Middleware     │                        │
│                  │  - JWT Auth     │                        │
│                  │  - Role Check   │                        │
│                  │  - Rate Limit   │                        │
│                  └────────┬────────┘                        │
└───────────────────────────┼──────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
│   PostgreSQL    │ │  ChromaDB   │ │     Ollama      │
│   (Users, Conv) │ │  (RAG Vec)  │ │     (LLM)       │
└─────────────────┘ └─────────────┘ └─────────────────┘
```

#### 3.1.3 Infrastructure de Déploiement

**Architecture Docker-Compose**

Le système sera déployé sur une infrastructure conteneurisée existante, avec ajout de services pour l'authentification.

**Services Docker (docker-compose.yml)**

```yaml
version: '3.8'

services:
  # SERVEUR 1: PostgreSQL (EXISTANT - à étendre)
  postgres:
    image: postgres:15
    container_name: my-ia-postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=n8n
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=n8n
      - POSTGRES_MULTIPLE_DATABASES=n8n,myia_auth  # Ajout BDD auth
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./scripts/init-multiple-databases.sh:/docker-entrypoint-initdb.d/init-multiple-databases.sh
    networks:
      - my-ia-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U n8n"]
      interval: 10s
      timeout: 5s
      retries: 5

  # SERVEUR 2: Application FastAPI (EXISTANT - à modifier)
  app:
    build: ./app
    container_name: my-ia-app
    ports:
      - "8080:8080"
    environment:
      # Existant
      - OLLAMA_URL=http://ollama:11434
      - CHROMA_URL=http://chromadb:8000
      # Nouveau - Auth
      - DATABASE_URL=postgresql+asyncpg://n8n:${POSTGRES_PASSWORD}@postgres:5432/myia_auth
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - JWT_ALGORITHM=HS256
      - ACCESS_TOKEN_EXPIRE_MINUTES=30
      - REFRESH_TOKEN_EXPIRE_DAYS=7
      - ENVIRONMENT=production
    volumes:
      - ./app:/app
      - ./datasets:/datasets
    depends_on:
      postgres:
        condition: service_healthy
      chromadb:
        condition: service_started
      ollama:
        condition: service_started
    networks:
      - my-ia-network
    restart: unless-stopped

  # SERVEUR 3: Frontend (EXISTANT - à modifier)
  frontend:
    image: nginx:alpine
    container_name: my-ia-frontend
    ports:
      - "3000:80"
    volumes:
      - ./frontend:/usr/share/nginx/html:ro
      - ./frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - app
    networks:
      - my-ia-network
    restart: unless-stopped

  # SERVEUR 4: ChromaDB (EXISTANT)
  chromadb:
    image: chromadb/chroma:latest
    container_name: my-ia-chromadb
    ports:
      - "8000:8000"
    volumes:
      - chroma-data:/chroma/chroma
    networks:
      - my-ia-network
    restart: unless-stopped

  # SERVEUR 5: Ollama (EXISTANT)
  ollama:
    image: ollama/ollama:latest
    container_name: my-ia-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - my-ia-network
    restart: unless-stopped

  # SERVEUR 6: N8N (EXISTANT)
  n8n:
    image: n8nio/n8n:latest
    container_name: my-ia-n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - n8n-data:/home/node/.n8n
      - ./n8n/workflows:/workflows
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - my-ia-network
    restart: unless-stopped

volumes:
  postgres-data:
    driver: local
  chroma-data:
    driver: local
  ollama-data:
    driver: local
  n8n-data:
    driver: local

networks:
  my-ia-network:
    driver: bridge
```

**Résumé des serveurs**

| Serveur | Container | Port(s) | Rôle | Statut | Modifications |
|---------|-----------|---------|------|--------|---------------|
| **PostgreSQL** | `my-ia-postgres` | 5432 | BDD (N8N + Auth) | Existant | ✏️ Ajout BDD `myia_auth` |
| **FastAPI** | `my-ia-app` | 8080 | API Backend | Existant | ✏️ Ajout routes auth + admin |
| **Nginx** | `my-ia-frontend` | 3000 | Frontend Web | Existant | ✏️ Ajout pages login/admin |
| **ChromaDB** | `my-ia-chromadb` | 8000 | Base vectorielle RAG | Existant | ⚪ Aucune |
| **Ollama** | `my-ia-ollama` | 11434 | Modèle LLM | Existant | ⚪ Aucune |
| **N8N** | `my-ia-n8n` | 5678 | Automatisation | Existant | ⚪ Aucune |

**Volumes persistants**

| Volume | Description | Taille estimée |
|--------|-------------|----------------|
| `postgres-data` | Données PostgreSQL (N8N + Auth) | ~500 MB → 2 GB |
| `chroma-data` | Embeddings ChromaDB | ~1-5 GB |
| `ollama-data` | Modèles LLM | ~10-20 GB |
| `n8n-data` | Workflows N8N | ~100 MB |

**Réseau Docker**

- **Réseau** : `my-ia-network` (bridge)
- **Isolation** : Tous les services communiquent via le réseau interne
- **Exposition** : Seuls les ports nécessaires sont exposés sur l'hôte

**Script d'initialisation PostgreSQL**

Création de `scripts/init-multiple-databases.sh` :

```bash
#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE myia_auth;
    GRANT ALL PRIVILEGES ON DATABASE myia_auth TO n8n;
EOSQL
```

**Configuration Nginx pour Frontend**

Modification de `frontend/nginx.conf` :

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/css application/javascript application/json;

    # Pages frontend
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Page de login
    location /login.html {
        try_files $uri =404;
    }

    # Page admin
    location /admin.html {
        try_files $uri =404;
    }

    # Proxy vers API Backend
    location /api/ {
        proxy_pass http://app:8080/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }

    # Support Server-Sent Events (SSE) pour streaming
    location /api/chat/stream {
        proxy_pass http://app:8080/chat/stream;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
    }
}
```

**Ressources serveur requises**

| Ressource | Minimum | Recommandé | Production |
|-----------|---------|------------|------------|
| **CPU** | 4 cores | 8 cores | 16+ cores |
| **RAM** | 8 GB | 16 GB | 32+ GB |
| **Stockage** | 50 GB | 100 GB | 500+ GB (SSD) |
| **Réseau** | 100 Mbps | 1 Gbps | 10 Gbps |

**Déploiement en production**

Pour un déploiement production, envisager :

1. **Reverse Proxy** : Nginx/Traefik en frontal avec SSL/TLS
2. **Load Balancer** : HAProxy pour scaling horizontal
3. **Orchestration** : Kubernetes (optionnel pour haute disponibilité)
4. **Monitoring** : Prometheus + Grafana (à ajouter en Phase 2)
5. **Backup** : Cron jobs pour PostgreSQL et ChromaDB
6. **Secrets** : Vault ou Docker Secrets (pas de .env en clair)

### 3.2 Modèle de données

#### 3.2.1 Base PostgreSQL

**Tables de référence (normalisées)**

**Table : roles** (Table de référence pour les rôles utilisateurs)
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'user', 'contributor', 'admin'
    display_name VARCHAR(100) NOT NULL,  -- 'Utilisateur', 'Contributeur', 'Administrateur'
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed data
INSERT INTO roles (name, display_name, description) VALUES
    ('user', 'Utilisateur', 'Accès basique : chat et conversations personnelles'),
    ('contributor', 'Contributeur', 'Peut uploader et gérer des documents'),
    ('admin', 'Administrateur', 'Accès complet incluant le backend d''administration');
```

**Table : conversation_modes** (Table de référence pour les modes de conversation)
```sql
CREATE TABLE conversation_modes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'chatbot', 'assistant'
    display_name VARCHAR(100) NOT NULL,  -- 'ChatBot', 'Assistant'
    description TEXT,
    system_prompt TEXT,  -- Prompt système associé au mode
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed data
INSERT INTO conversation_modes (name, display_name, description) VALUES
    ('chatbot', 'ChatBot', 'Mode conversationnel général avec RAG'),
    ('assistant', 'Assistant', 'Mode orienté tâches et procédures');
```

**Table : resource_types** (Types de ressources pour l'audit)
```sql
CREATE TABLE resource_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'user', 'conversation', 'document', 'config'
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed data
INSERT INTO resource_types (name, display_name) VALUES
    ('user', 'Utilisateur'),
    ('conversation', 'Conversation'),
    ('document', 'Document'),
    ('preference', 'Préférence'),
    ('config', 'Configuration');
```

**Table : audit_actions** (Actions auditées)
```sql
CREATE TABLE audit_actions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,  -- 'login', 'user_created', 'role_changed', etc.
    display_name VARCHAR(200) NOT NULL,
    severity VARCHAR(20) DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'critical')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed data (exemples)
INSERT INTO audit_actions (name, display_name, severity) VALUES
    ('login_success', 'Connexion réussie', 'info'),
    ('login_failed', 'Échec de connexion', 'warning'),
    ('logout', 'Déconnexion', 'info'),
    ('user_created', 'Utilisateur créé', 'info'),
    ('user_updated', 'Utilisateur modifié', 'info'),
    ('user_deleted', 'Utilisateur supprimé', 'warning'),
    ('role_changed', 'Rôle modifié', 'warning'),
    ('user_activated', 'Compte activé', 'info'),
    ('user_deactivated', 'Compte désactivé', 'warning'),
    ('password_reset_requested', 'Réinitialisation mot de passe demandée', 'info'),
    ('password_reset_completed', 'Mot de passe réinitialisé', 'warning'),
    ('password_changed', 'Mot de passe modifié', 'info'),
    ('document_uploaded', 'Document uploadé', 'info'),
    ('document_deleted', 'Document supprimé', 'warning'),
    ('conversation_created', 'Conversation créée', 'info'),
    ('conversation_deleted', 'Conversation supprimée', 'info'),
    ('preferences_updated', 'Préférences modifiées', 'info'),
    ('preferences_updated_by_admin', 'Préférences modifiées par admin', 'warning'),
    ('config_updated', 'Configuration modifiée', 'warning'),
    ('admin_action', 'Action administrative', 'warning');
```

**Tables principales**

**Table : users**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role_id INTEGER REFERENCES roles(id) DEFAULT 1,  -- Default: 'user' role
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,

    CONSTRAINT email_valid CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role_id);
CREATE INDEX idx_users_active ON users(is_active);
```

**Table : user_preferences**
```sql
-- Note: top_k est le nombre de documents/chunks similaires récupérés par le RAG
-- Plus top_k est élevé, plus le contexte est riche (mais potentiellement bruité)
-- Valeur par défaut: 4, modifiable par l'utilisateur ou par l'admin
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    top_k INTEGER DEFAULT 4 CHECK (top_k > 0 AND top_k <= 20),  -- Paramètre RAG: nombre de chunks à récupérer
    show_sources BOOLEAN DEFAULT TRUE,  -- Afficher les sources dans l'interface
    theme VARCHAR(20) DEFAULT 'light' CHECK (theme IN ('light', 'dark')),
    default_mode_id INTEGER REFERENCES conversation_modes(id) DEFAULT 1,  -- Mode par défaut (chatbot)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id)
);

CREATE INDEX idx_preferences_user ON user_preferences(user_id);
```

**Table : conversations**
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    mode_id INTEGER REFERENCES conversation_modes(id) DEFAULT 1,  -- Référence au mode
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conversations_user ON conversations(user_id, created_at DESC);
CREATE INDEX idx_conversations_mode ON conversations(mode_id);
```

**Table : messages**
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL CHECK (sender_type IN ('user', 'assistant')),  -- Type d'émetteur du message (user=humain, assistant=IA)
    content TEXT NOT NULL,
    sources JSONB,  -- Sources RAG utilisées (si message assistant)
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at ASC);
CREATE INDEX idx_messages_sender ON messages(sender_type);
```

**Table : sessions** (Refresh tokens)
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refresh_token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    user_agent VARCHAR(500),
    ip_address VARCHAR(45)
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(refresh_token);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);
```

**Table : documents** (Tracking documents uploadés)
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_documents_user ON documents(user_id);
CREATE INDEX idx_documents_hash ON documents(file_hash);
```

**Table : audit_logs** (Journal d'audit)
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,  -- Utilisateur ayant effectué l'action
    action_id INTEGER REFERENCES audit_actions(id) NOT NULL,  -- Action effectuée (référence normalisée)
    resource_type_id INTEGER REFERENCES resource_types(id),  -- Type de ressource concernée
    resource_id UUID,  -- ID de la ressource concernée
    details JSONB,  -- Détails additionnels (ancienne/nouvelle valeur, etc.)
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_action ON audit_logs(action_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type_id, resource_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
```

### 3.3 API Endpoints

#### 3.3.1 Authentification (Public)

| Méthode | Endpoint | Description | Body | Réponse |
|---------|----------|-------------|------|---------|
| POST | `/auth/register` | Inscription | `{email, username, password, full_name?}` | `{user, access_token, refresh_token}` |
| POST | `/auth/login` | Connexion | `{email, password}` | `{access_token, refresh_token, user}` |
| POST | `/auth/logout` | Déconnexion | - | `{message}` |
| POST | `/auth/refresh` | Renouveler token | `{refresh_token}` | `{access_token}` |
| GET | `/auth/me` | Infos utilisateur | - | `{user}` |
| PATCH | `/auth/me` | Modifier profil | `{full_name?, username?}` | `{user}` |
| POST | `/auth/forgot-password` | Demande reset | `{email}` | `{message}` |
| POST | `/auth/reset-password` | Valider reset | `{token, new_password}` | `{message}` |

#### 3.3.2 Conversations (Authentifié)

| Méthode | Endpoint | Description | Permissions | Réponse |
|---------|----------|-------------|-------------|---------|
| GET | `/conversations` | Liste conversations | User | `[{id, title, mode, created_at, message_count}]` |
| POST | `/conversations` | Créer conversation | User | `{id, title, mode, created_at}` |
| GET | `/conversations/{id}` | Détails + messages | User (owner) / Admin | `{conversation, messages[]}` |
| PATCH | `/conversations/{id}` | Renommer | User (owner) / Admin | `{conversation}` |
| DELETE | `/conversations/{id}` | Supprimer | User (owner) / Admin | `{message}` |
| POST | `/conversations/{id}/messages` | Ajouter message | User (owner) / Admin | `{message}` |

#### 3.3.3 Préférences (Authentifié)

| Méthode | Endpoint | Description | Body | Réponse |
|---------|----------|-------------|------|---------|
| GET | `/preferences` | Récupérer préfs | - | `{top_k, show_sources, theme, default_mode_id}` |
| PATCH | `/preferences` | Modifier préfs | `{top_k?, show_sources?, theme?, default_mode_id?}` | `{preferences}` |

#### 3.3.4 Documents (Contributeur / Admin)

| Méthode | Endpoint | Description | Permissions | Réponse |
|---------|----------|-------------|-------------|---------|
| POST | `/upload/v2` | Upload document | Contributor / Admin | `{document, chunks_created}` |
| GET | `/documents` | Liste documents | Contributor (siens) / Admin (tous) | `[{id, filename, file_type, size, created_at}]` |
| DELETE | `/documents/{id}` | Supprimer document | Contributor (sien) / Admin | `{message}` |

#### 3.3.5 Administration (Admin uniquement)

**Gestion utilisateurs**
| Méthode | Endpoint | Description | Body | Réponse |
|---------|----------|-------------|------|---------|
| GET | `/admin/users` | Liste utilisateurs | - | `[{id, email, username, role, is_active, created_at}]` |
| POST | `/admin/users` | Créer utilisateur | `{email, username, password, role_id, full_name?}` | `{user}` |
| GET | `/admin/users/{id}` | Détails utilisateur | - | `{user, stats: {conversations_count, documents_count}}` |
| PATCH | `/admin/users/{id}` | Modifier utilisateur | `{role_id?, is_active?, full_name?}` | `{user}` |
| DELETE | `/admin/users/{id}` | Supprimer utilisateur | - | `{message}` |
| POST | `/admin/users/{id}/reset-password` | Reset password | `{new_password}` | `{message}` |
| PATCH | `/admin/users/{id}/preferences` | Modifier préférences utilisateur | `{top_k?, show_sources?, theme?, default_mode_id?}` | `{preferences}` |

**Statistiques**
| Méthode | Endpoint | Description | Réponse |
|---------|----------|-------------|---------|
| GET | `/admin/stats` | Stats globales | `{users_count, conversations_count, documents_count, active_sessions}` |
| GET | `/admin/stats/users/{id}` | Stats utilisateur | `{conversations, documents, last_login, total_messages}` |

**Audit**
| Méthode | Endpoint | Description | Query Params | Réponse |
|---------|----------|-------------|--------------|---------|
| GET | `/admin/audit` | Journal d'audit | `?user_id, ?action, ?limit, ?offset` | `[{id, user, action, resource, details, created_at}]` |

**Gestion documents**
| Méthode | Endpoint | Description | Réponse |
|---------|----------|-------------|---------|
| GET | `/admin/documents` | Tous les documents | `[{id, user, filename, size, chunks, created_at}]` |
| DELETE | `/admin/documents/{id}` | Supprimer document | `{message}` |

### 3.4 Sécurité

#### 3.4.1 Authentification JWT
- **Algorithm** : HS256
- **Access token lifetime** : 30 minutes
- **Refresh token lifetime** : 7 jours
- **Secret key** : 256 bits minimum (variable d'environnement)
- **Storage** : httpOnly cookies (préféré) ou localStorage (fallback)

#### 3.4.2 Mots de passe
- **Hashing** : bcrypt
- **Rounds** : 12 (configurable)
- **Contraintes** :
  - Minimum 8 caractères
  - Au moins 1 majuscule
  - Au moins 1 minuscule
  - Au moins 1 chiffre
  - Au moins 1 caractère spécial recommandé

#### 3.4.3 Rate Limiting
- **Login** : 5 tentatives / 15 minutes par IP
- **Register** : 3 inscriptions / heure par IP
- **API calls** : 100 requêtes / minute par utilisateur
- **Upload** : 10 uploads / heure pour Contributor, illimité pour Admin

#### 3.4.4 Protection CSRF
- Tokens CSRF pour formulaires critiques
- SameSite cookies

#### 3.4.5 HTTPS
- **Obligatoire en production**
- Certificats Let's Encrypt
- Redirection HTTP → HTTPS
- HSTS headers

#### 3.4.6 Validation des données
- Pydantic schemas pour tous les endpoints
- Sanitization des inputs (XSS protection)
- Validation email (regex + DNS check optionnel)

---

## 4. Interface Utilisateur - Modifications Frontend

### 4.0 Vue d'ensemble des modifications Frontend

Cette section détaille tous les fichiers frontend à créer ou modifier pour implémenter le système d'authentification.

#### 4.0.1 Structure des fichiers Frontend

```
frontend/
├── index.html                    # ✏️ MODIFIER - Page principale chat
├── login.html                    # ✨ NOUVEAU - Page authentification
├── admin.html                    # ✨ NOUVEAU - Backend administration
├── nginx.conf                    # ✏️ MODIFIER - Configuration Nginx
├── css/
│   ├── styles.css               # ✏️ MODIFIER - Styles globaux
│   ├── login.css                # ✨ NOUVEAU - Styles page login
│   └── admin.css                # ✨ NOUVEAU - Styles page admin
├── js/
│   ├── app.js                   # ✏️ MODIFIER - Application principale
│   ├── auth.js                  # ✨ NOUVEAU - Gestion authentification
│   ├── admin.js                 # ✨ NOUVEAU - Logique backend admin
│   ├── api.js                   # ✨ NOUVEAU - Client API centralisé
│   └── utils.js                 # ✏️ MODIFIER - Utilitaires (add token helpers)
└── assets/
    └── (existants - logos, etc.) # ⚪ AUCUNE MODIFICATION
```

#### 4.0.2 Fichiers à créer (NOUVEAUX)

**1. `frontend/login.html`** - Page d'authentification
- Formulaire de connexion (email, password)
- Formulaire d'inscription (email, username, password, full_name)
- Lien "Mot de passe oublié"
- Switch entre les onglets Login/Register
- Responsive design (mobile-first)
- Support dark/light mode

**2. `frontend/admin.html`** - Backend d'administration
- Sidebar de navigation (Dashboard, Users, Documents, Audit, Config)
- Dashboard avec statistiques (cards + graphiques)
- Gestion utilisateurs (tableau CRUD)
- Gestion documents (liste + filtres)
- Journal d'audit (tableau chronologique)
- Configuration système
- Header avec nom admin + logout

**3. `frontend/js/auth.js`** - Logique d'authentification
```javascript
// Fonctions principales
- login(email, password)
- register(email, username, password, fullName)
- logout()
- checkAuth()
- refreshToken()
- getCurrentUser()
- isAdmin()
- hasRole(roleName)
```

**4. `frontend/js/admin.js`** - Logique backend admin
```javascript
// Fonctions principales
- loadDashboard()
- loadUsers(page, limit, filters)
- createUser(userData)
- updateUser(userId, updates)
- deleteUser(userId)
- changeUserRole(userId, roleId)
- loadAuditLogs(filters)
- loadDocuments(filters)
- updateUserPreferences(userId, preferences)
```

**5. `frontend/js/api.js`** - Client API centralisé
```javascript
// Wrapper autour de fetch() avec:
- Gestion automatique JWT (Authorization header)
- Refresh automatique des tokens expirés
- Gestion erreurs HTTP (401, 403, 500)
- Support streaming (SSE)
- Retry logic

// Exemples de fonctions
- api.get(url, options)
- api.post(url, body, options)
- api.patch(url, body, options)
- api.delete(url, options)
- api.stream(url, onMessage, options)
```

**6. `frontend/css/login.css`** - Styles page login
- Centered layout
- Card avec ombre
- Animations des transitions (tabs)
- Indicateur de force mot de passe
- Messages d'erreur inline
- Responsive breakpoints

**7. `frontend/css/admin.css`** - Styles page admin
- Layout avec sidebar (250px) + contenu
- Tables stylisées (hover, striped)
- Cards pour statistiques
- Boutons actions (icons)
- Modal pour édition
- Filtres et recherche

#### 4.0.3 Fichiers à modifier (EXISTANTS)

**1. `frontend/index.html`** - Page principale chat

**Modifications :**
```html
<!-- AJOUT: Vérification authentification au chargement -->
<script>
  // Redirect vers /login.html si non authentifié
  if (!checkAuth()) {
    window.location.href = '/login.html';
  }
</script>

<!-- AJOUT: Header utilisateur -->
<header class="app-header">
  <div class="user-info">
    <img src="avatar.png" class="user-avatar" alt="Avatar">
    <span class="user-name" id="userName">John Doe</span>
    <div class="dropdown">
      <button class="dropdown-toggle">▼</button>
      <ul class="dropdown-menu">
        <li><a href="#" id="myProfile">Mon profil</a></li>
        <li><a href="#" id="myPreferences">Préférences</a></li>
        <li class="admin-only"><a href="/admin.html">Administration</a></li>
        <li class="divider"></li>
        <li><a href="#" id="logout">Se déconnecter</a></li>
      </ul>
    </div>
  </div>
</header>

<!-- MODIFICATION: Sidebar conversations -->
<!-- Bouton "Nouvelle conversation" reste -->
<!-- Chargement conversations depuis API au lieu de localStorage -->

<!-- MODIFICATION: Settings panel -->
<!-- Retrait du champ "API Key" (géré côté serveur) -->
<!-- Ajout "Mode par défaut" (chatbot/assistant) -->
```

**Changements JavaScript dans index.html/app.js :**
- Remplacer `localStorage.getItem('conversations')` par `api.get('/conversations')`
- Remplacer `localStorage.setItem('conversations')` par `api.post('/conversations')`
- Ajouter auto-refresh token (toutes les 25 minutes)
- Ajouter listener logout
- Charger profil utilisateur au démarrage
- Afficher badge rôle si admin/contributeur

**2. `frontend/js/app.js`** - Application principale

**Modifications :**
```javascript
// SUPPRESSION: CONFIG en dur (localStorage)
// REMPLACEMENT par: Chargement depuis /preferences

// AJOUT: Import module auth
import { checkAuth, getCurrentUser, logout } from './auth.js';
import { api } from './api.js';

// MODIFICATION: Fonction initApp()
async function initApp() {
  // Vérifier auth
  if (!await checkAuth()) {
    window.location.href = '/login.html';
    return;
  }

  // Charger user
  const user = await getCurrentUser();
  displayUserInfo(user);

  // Charger préférences
  const prefs = await api.get('/preferences');
  applyPreferences(prefs);

  // Charger conversations
  const conversations = await api.get('/conversations');
  renderConversations(conversations);

  // Setup auto-refresh token
  startTokenRefresh();
}

// MODIFICATION: saveConversation()
async function saveConversation(conversation) {
  // Au lieu de localStorage
  if (conversation.id) {
    await api.patch(`/conversations/${conversation.id}`, conversation);
  } else {
    const created = await api.post('/conversations', conversation);
    conversation.id = created.id;
  }
}

// MODIFICATION: sendMessage()
async function sendMessage(conversationId, message) {
  // Sauvegarder message user
  await api.post(`/conversations/${conversationId}/messages`, {
    sender_type: 'user',
    content: message
  });

  // Appel API chat (existant, mais avec auth)
  // ...
}

// AJOUT: displayUserInfo()
function displayUserInfo(user) {
  document.getElementById('userName').textContent = user.full_name || user.username;

  // Afficher menu admin si role admin
  if (user.role.name === 'admin') {
    document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
  }
}

// AJOUT: startTokenRefresh()
function startTokenRefresh() {
  setInterval(async () => {
    await refreshToken(); // refresh toutes les 25 min
  }, 25 * 60 * 1000);
}
```

**3. `frontend/css/styles.css`** - Styles globaux

**Ajouts :**
```css
/* Header utilisateur */
.app-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
}

.dropdown {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  right: 0;
  top: 100%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: none;
  min-width: 200px;
}

.dropdown-menu.show {
  display: block;
}

.admin-only {
  display: none; /* Afficher seulement si role admin */
}

/* Toast notifications */
.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  background: var(--bg-secondary);
  border-left: 4px solid var(--accent-color);
  padding: 1rem;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  z-index: 9999;
  animation: slideIn 0.3s ease;
}

.toast.error {
  border-left-color: var(--error-color);
}

.toast.success {
  border-left-color: var(--success-color);
}

@keyframes slideIn {
  from {
    transform: translateX(400px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
```

**4. `frontend/js/utils.js`** - Utilitaires

**Ajouts :**
```javascript
// AJOUT: Gestion tokens
export function getAccessToken() {
  return localStorage.getItem('access_token');
}

export function setAccessToken(token) {
  localStorage.setItem('access_token', token);
}

export function getRefreshToken() {
  return localStorage.getItem('refresh_token');
}

export function setRefreshToken(token) {
  localStorage.setItem('refresh_token', token);
}

export function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
}

// AJOUT: Toast notifications
export function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 3000);
}

// AJOUT: Formatage dates
export function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleString('fr-FR');
}

// AJOUT: Formatage taille fichiers
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
```

**5. `frontend/nginx.conf`** - Configuration Nginx

**Modifications détaillées** (déjà documentées dans section 3.1.3)

#### 4.0.4 Diagramme de navigation

```
┌─────────────────┐
│   login.html    │ (Non authentifié)
│   ┌─────────┐   │
│   │  Login  │   │
│   │ Register│   │
│   └────┬────┘   │
└────────┼────────┘
         │ Authentification réussie
         ▼
┌─────────────────┐
│   index.html    │ (Authentifié - Tous rôles)
│  ┌───────────┐  │
│  │   Chat    │  │
│  │Conversatio│  │
│  │    ns     │  │
│  └─────┬─────┘  │
└────────┼────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
  [User/Contributor]  [Admin uniquement]
                      ┌─────────────────┐
                      │   admin.html    │
                      │  ┌───────────┐  │
                      │  │Dashboard  │  │
                      │  │Users      │  │
                      │  │Documents  │  │
                      │  │Audit      │  │
                      │  │Config     │  │
                      │  └───────────┘  │
                      └─────────────────┘
```

#### 4.0.5 Gestion de l'état (State Management)

**Avant (localStorage uniquement) :**
```javascript
conversations → localStorage
preferences → localStorage
```

**Après (Hybride API + localStorage) :**
```javascript
// Auth tokens → localStorage (temporaire, httpOnly cookies recommandé)
access_token → localStorage
refresh_token → localStorage

// User info → localStorage (cache, source: API)
user → localStorage (cache de /auth/me)

// Conversations → API uniquement (plus de localStorage)
conversations → GET /conversations (source unique de vérité)

// Préférences → API uniquement
preferences → GET /preferences
```

**Pattern de synchronisation :**
1. Au chargement : API → État local (variables JS)
2. Modification : État local → API
3. Cache : API responses peuvent être cachées temporairement (5 min)

#### 4.0.6 Gestion des erreurs Frontend

**Codes HTTP à gérer :**

| Code | Signification | Action Frontend |
|------|---------------|-----------------|
| 401 | Non authentifié | Redirect `/login.html` |
| 403 | Non autorisé (rôle insuffisant) | Toast "Accès refusé" |
| 404 | Ressource non trouvée | Toast "Non trouvé" |
| 422 | Validation failed | Afficher erreurs sous champs |
| 429 | Rate limit exceeded | Toast "Trop de requêtes, réessayez" |
| 500 | Erreur serveur | Toast "Erreur serveur" |

**Retry logic :**
- 401 : Tenter refresh token 1 fois, sinon redirect login
- 429 : Retry avec exponential backoff (1s, 2s, 4s)
- 500/502/503 : Retry 3 fois avec délai

#### 4.0.7 Accessibilité (a11y)

Tous les nouveaux composants doivent respecter :
- **ARIA labels** sur boutons/liens
- **Focus management** (login → register, modals)
- **Keyboard navigation** (Tab, Escape, Enter)
- **Screen reader** compatible
- **Contrast ratio** WCAG AA minimum (4.5:1)

#### 4.0.8 Performance Frontend

**Optimisations :**
- **Code splitting** : Charger admin.js uniquement si admin
- **Lazy loading** : Images/avatars chargés on-demand
- **Debouncing** : Recherche utilisateurs (300ms)
- **Pagination** : Conversations/users (25 par page)
- **Caching** : API responses (SWR pattern - stale-while-revalidate)

**Métriques cibles :**
- First Contentful Paint (FCP) : < 1.5s
- Time to Interactive (TTI) : < 3s
- Lighthouse score : > 90

---

### 4.1 Page de Login (`/login.html`)

#### Design
- Layout centré, responsive
- Formulaire login/register avec tabs
- Cohérence visuelle avec l'interface existante (même palette, même fonts)
- Support dark/light mode

#### Composants
1. **Tab Login**
   - Champ Email (type email, required)
   - Champ Password (type password, required, toggle visibility)
   - Bouton "Se connecter"
   - Lien "Mot de passe oublié ?"
   - Checkbox "Se souvenir de moi" (extend refresh token)

2. **Tab Register**
   - Champ Email (validation en temps réel)
   - Champ Username (unique, 3-30 caractères)
   - Champ Nom complet (optionnel)
   - Champ Password (indicateur de force)
   - Champ Confirm Password
   - Bouton "S'inscrire"
   - Checkbox "J'accepte les CGU"

3. **Messages**
   - Toast notifications pour erreurs/succès
   - Messages d'erreur contextuels sous champs

#### Comportement
- Auto-focus sur premier champ
- Validation en temps réel
- Loading state sur boutons (spinner)
- Redirection automatique après login → `/` (chat)

### 4.2 Page Admin (`/admin.html`)

#### Layout
- Sidebar avec navigation
  - Dashboard
  - Utilisateurs
  - Documents
  - Audit
  - Configuration
- Header avec nom admin + logout
- Zone de contenu principale

#### Vues

**1. Dashboard**
- Cards de statistiques :
  - Nombre total d'utilisateurs
  - Utilisateurs actifs (7 derniers jours)
  - Total conversations
  - Total documents
  - Stockage utilisé
- Graphiques :
  - Évolution inscriptions (30 derniers jours)
  - Activité par jour (connexions)
  - Top 5 utilisateurs les plus actifs

**2. Gestion Utilisateurs**
- Tableau paginé (25 par page)
- Colonnes : Email, Username, Rôle, Statut, Dernière connexion, Actions
- Filtres : Rôle, Statut (actif/inactif)
- Recherche (email, username)
- Actions par ligne :
  - Éditer (modal)
  - Changer rôle (dropdown)
  - Activer/Désactiver
  - Réinitialiser mot de passe
  - Supprimer (confirmation)
- Bouton "Créer utilisateur"

**3. Gestion Documents**
- Tableau paginé
- Colonnes : Nom, Type, Taille, Propriétaire, Date upload, Actions
- Filtres : Type de fichier, Utilisateur
- Recherche par nom
- Action : Supprimer (confirmation)

**4. Journal d'Audit**
- Tableau chronologique inversé
- Colonnes : Date/Heure, Utilisateur, Action, Ressource, Détails, IP
- Filtres : Action, Utilisateur, Date
- Export CSV

**5. Configuration**
- Formulaire de paramètres :
  - Rate limiting (valeurs)
  - Durée tokens JWT
  - Mode maintenance
  - SMTP settings (réinitialisation password)

### 4.3 Modifications Interface Chat (`/index.html`)

#### Ajouts
- **Header** :
  - Avatar + nom utilisateur (top-right)
  - Dropdown menu :
    - Mon profil
    - Mes préférences
    - [Admin] Panneau d'administration
    - Se déconnecter

- **Settings** :
  - Retirer API Key (géré en backend)
  - Garder topK, show_sources, theme
  - Ajouter "Mode par défaut" (chatbot/assistant)

#### Comportements
- Auto-redirect vers `/login.html` si non authentifié
- Chargement conversations depuis API au login
- Sauvegarde automatique dans BDD (plus localStorage)
- Refresh token automatique (background, avant expiration)

---

## 5. Backend d'Administration

### 5.1 Architecture Backend Admin

Le backend d'administration est une API REST intégrée à FastAPI avec les caractéristiques :
- Routes préfixées `/admin`
- Middleware de vérification rôle "admin"
- Logging de toutes les actions admin (audit trail)
- Pagination pour toutes les listes
- Filtres et recherche

### 5.2 Fonctionnalités détaillées

#### 5.2.1 Dashboard
- **Endpoint** : `GET /admin/stats`
- **Données** :
  ```json
  {
    "users": {
      "total": 150,
      "active_7d": 42,
      "new_30d": 12,
      "by_role": {"user": 120, "contributor": 25, "admin": 5}
    },
    "conversations": {
      "total": 1240,
      "total_messages": 8500
    },
    "documents": {
      "total": 85,
      "total_size_mb": 450,
      "by_type": {"pdf": 30, "docx": 20, "txt": 35}
    },
    "activity": {
      "logins_7d": [12, 15, 10, 18, 14, 16, 20],
      "uploads_7d": [2, 1, 3, 0, 1, 2, 1]
    }
  }
  ```

#### 5.2.2 Gestion Utilisateurs
- **Liste** : `GET /admin/users?page=1&limit=25&role=&search=`
- **Détails** : `GET /admin/users/{id}` (+ stats utilisateur)
- **Création** : `POST /admin/users`
  - Génération mot de passe temporaire si non fourni
  - Email de bienvenue (optionnel)
- **Modification** : `PATCH /admin/users/{id}`
  - Changement de rôle → log audit
  - Activation/désactivation → révoque sessions actives si désactivé
- **Modification préférences** : `PATCH /admin/users/{id}/preferences`
  - Permet à l'admin d'ajuster top_k pour optimiser les réponses RAG par utilisateur
  - Modifier thème, mode par défaut, affichage sources
  - Toute modification → log audit
- **Suppression** : `DELETE /admin/users/{id}`
  - Suppression en cascade : conversations, messages, documents
  - Confirmation requise (param `?confirm=true`)
  - Archive dans logs avant suppression

#### 5.2.3 Audit Trail
Chaque action administrative est loggée dans la table `audit_logs` avec références normalisées :
```python
# Exemple de log (changement de rôle)
{
  "user_id": "uuid-admin",
  "action_id": 7,  # Référence à audit_actions (role_changed)
  "resource_type_id": 1,  # Référence à resource_types (user)
  "resource_id": "uuid-user-cible",
  "details": {
    "old_role_id": 1,
    "old_role_name": "user",
    "new_role_id": 2,
    "new_role_name": "contributor",
    "reason": "User request approved"
  },
  "ip_address": "192.168.1.10",
  "user_agent": "Mozilla/5.0...",
  "created_at": "2025-12-21T10:30:00Z"
}

# Exemple de log (modification préférences par admin)
{
  "user_id": "uuid-admin",
  "action_id": 19,  # preferences_updated_by_admin
  "resource_type_id": 4,  # preference
  "resource_id": "uuid-preference",
  "details": {
    "target_user_id": "uuid-user-cible",
    "target_user_email": "user@example.com",
    "old_top_k": 4,
    "new_top_k": 8,
    "reason": "User needs richer context for technical queries"
  },
  "ip_address": "192.168.1.10",
  "created_at": "2025-12-21T11:15:00Z"
}
```

**Actions loggées** (référencées dans `audit_actions`) :
- Authentification : `login_success`, `login_failed`, `logout`
- Utilisateurs : `user_created`, `user_updated`, `user_deleted`
- Rôles : `role_changed`, `user_activated`, `user_deactivated`
- Mots de passe : `password_reset_requested`, `password_reset_completed`, `password_changed`
- Documents : `document_uploaded`, `document_deleted`
- Conversations : `conversation_created`, `conversation_deleted`
- Préférences : `preferences_updated`, `preferences_updated_by_admin`
- Configuration : `config_updated`
- Général : `admin_action`

**Niveau de sévérité** :
- `info` : Actions normales (login, création, modification standard)
- `warning` : Actions sensibles (suppression, changement rôle, désactivation)
- `critical` : Actions critiques (suppression admin, changement config sécurité)

---

## 6. Plan de Réalisation

### 6.1 Découpage en sprints

#### Sprint 1 : Backend Authentification (3 jours)
- [ ] Setup FastAPI-Users
- [ ] Modèles SQLAlchemy (users, preferences, sessions)
- [ ] Migrations Alembic
- [ ] Endpoints auth (/register, /login, /logout, /refresh, /me)
- [ ] Middleware JWT
- [ ] Tests unitaires auth

#### Sprint 2 : Backend Conversations & Préférences (2 jours)
- [ ] Modèles conversations, messages
- [ ] Endpoints CRUD conversations
- [ ] Endpoints préférences
- [ ] Isolation par utilisateur
- [ ] Tests unitaires

#### Sprint 3 : Frontend Login (2 jours)
- [ ] Page login.html (design + responsive)
- [ ] Formulaires login/register
- [ ] Gestion erreurs/validation
- [ ] Integration API auth
- [ ] Tests fonctionnels

#### Sprint 4 : Migration Interface Chat (2 jours)
- [ ] Protection route (redirect si non auth)
- [ ] Remplacement localStorage par API calls
- [ ] Header utilisateur + dropdown
- [ ] Auto-refresh token
- [ ] Tests E2E (register → login → chat → logout)

#### Sprint 5 : Backend Admin - Gestion Users (2 jours)
- [ ] Endpoints admin/users (CRUD)
- [ ] Middleware require_admin
- [ ] Stats utilisateur
- [ ] Audit logging
- [ ] Tests

#### Sprint 6 : Frontend Admin - Interface (3 jours)
- [ ] Page admin.html (layout, sidebar)
- [ ] Dashboard avec stats
- [ ] Gestion utilisateurs (tableau, actions)
- [ ] Gestion documents
- [ ] Audit trail
- [ ] Tests UI

#### Sprint 7 : Permissions Documents (1 jour)
- [ ] Modifier /upload/v2 (vérif rôle)
- [ ] Association document → user
- [ ] Filtrage par user dans ChromaDB
- [ ] Tests permissions

#### Sprint 8 : Sécurité & Production (2 jours)
- [ ] Rate limiting (par IP + par user)
- [ ] HTTPS configuration
- [ ] httpOnly cookies
- [ ] CSRF protection
- [ ] Validation renforcée
- [ ] Tests sécurité

#### Sprint 9 : Documentation & Déploiement (1 jour)
- [ ] Update docs/API.md
- [ ] Créer docs/AUTHENTICATION.md
- [ ] Créer docs/ADMIN_GUIDE.md
- [ ] Update README
- [ ] Configuration production (.env)
- [ ] Script de seed admin initial

**Durée totale estimée : 18 jours**

### 6.2 Livrables

| Livrable | Description | Format |
|----------|-------------|--------|
| Code backend | Endpoints auth + admin | Python/FastAPI |
| Code frontend | Pages login + admin | HTML/CSS/JS |
| Migrations BDD | Scripts Alembic | SQL |
| Tests | Unitaires + intégration | pytest |
| Documentation API | Endpoints complets | Markdown |
| Guide utilisateur | Utilisation auth | Markdown |
| Guide admin | Utilisation backend admin | Markdown |
| Configuration | Variables d'environnement | .env.example |

---

## 7. Tests et Validation

### 7.1 Stratégie de tests

#### Tests unitaires (Backend)
- Couverture cible : 80%+
- Framework : pytest
- Endpoints auth (register, login, logout, refresh)
- Permissions (rôles)
- CRUD conversations
- Admin endpoints

#### Tests d'intégration
- Flow complet : register → login → create conv → logout
- Refresh token automatique
- Isolation données entre users
- Permissions upload par rôle

#### Tests fonctionnels (Frontend)
- Formulaires (validation, erreurs)
- Navigation (redirections)
- Responsive design (mobile, tablet, desktop)

#### Tests de sécurité
- Injection SQL (via ORM)
- XSS (sanitization)
- CSRF
- Brute-force (rate limiting)
- Token expiration

### 7.2 Critères d'acceptation

- [ ] Un utilisateur peut s'inscrire et se connecter
- [ ] Les conversations sont sauvegardées en BDD et persistantes
- [ ] Un utilisateur ne voit que ses propres conversations
- [ ] Un contributeur peut uploader des documents
- [ ] Un admin peut voir tous les utilisateurs et les gérer
- [ ] Le changement de rôle applique immédiatement les nouvelles permissions
- [ ] Les tokens expirent correctement et sont refresh automatiquement
- [ ] Le rate limiting empêche les attaques brute-force
- [ ] Le backend admin affiche des statistiques correctes
- [ ] L'audit trail enregistre toutes les actions administratives
- [ ] L'application fonctionne en HTTPS
- [ ] Tous les tests passent (>80% couverture)

---

## 8. Contraintes et Risques

### 8.1 Contraintes

#### Techniques
- Utiliser l'infrastructure existante (PostgreSQL, Docker)
- Compatibilité avec le système d'ingestion v2
- Pas de migration de données localStorage (démarrage propre)

#### Délais
- Développement : 18 jours
- Deadline souhaitée : Mi-janvier 2026

#### Ressources
- 1 développeur full-stack
- Environnement de dev local

### 8.2 Risques

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Complexité FastAPI-Users | Moyenne | Moyen | Étude préalable de la doc, exemples de code |
| Performance BDD (volume) | Faible | Moyen | Index optimisés, pagination |
| Sécurité (vulnérabilités) | Moyenne | Élevé | Tests sécurité, audit code, HTTPS obligatoire |
| UX (complexité admin) | Moyenne | Moyen | Wireframes préalables, tests utilisateurs |
| Intégration SSO future | Faible | Faible | Architecture déjà compatible (OAuth2) |

---

## 9. Évolutions Futures (Hors scope v1)

### Phase 2 : SSO (Authentik)
- Intégration Authentik via OAuth2/OIDC
- Fédération d'identités
- SSO enterprise (SAML)

### Phase 3 : Fonctionnalités avancées
- Email verification obligatoire
- Two-Factor Authentication (2FA)
- Sessions management (liste appareils connectés)
- Notifications (email pour actions importantes)
- Export de données (RGPD compliance)
- Gestion des quotas (limites upload, conversations)

### Phase 4 : Analytics avancés
- Dashboard analytics avancé (temps réponse, satisfaction)
- Graphiques interactifs (Chart.js)
- Export rapports PDF

---

## 10. Annexes

### 10.1 Variables d'environnement

```env
# JWT
JWT_SECRET_KEY=<générer avec: openssl rand -hex 32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://n8n:n8n_password@postgres:5432/n8n

# Admin initial (seed)
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=ChangeMe123!

# SMTP (pour reset password - optionnel v1)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@mydomain.com
SMTP_PASSWORD=<app-password>

# Rate Limiting
RATE_LIMIT_LOGIN=5/15minutes
RATE_LIMIT_API=100/minute
RATE_LIMIT_UPLOAD=10/hour

# Production
ENVIRONMENT=production  # development | production
HTTPS_ONLY=true
```

### 10.2 Commandes utiles

```bash
# Créer migration
alembic revision --autogenerate -m "Add authentication tables"

# Appliquer migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Créer admin initial
python scripts/create_admin.py --email admin@example.com --password SecurePass123!

# Tests
pytest tests/ -v --cov=app --cov-report=html

# Lancer en dev
docker compose up -d

# Logs
docker compose logs -f app
```

### 10.3 Ressources et Références

- **FastAPI-Users** : https://fastapi-users.github.io/fastapi-users/
- **SQLAlchemy 2.0** : https://docs.sqlalchemy.org/en/20/
- **Alembic** : https://alembic.sqlalchemy.org/
- **JWT Best Practices** : https://tools.ietf.org/html/rfc8725
- **OWASP Top 10** : https://owasp.org/www-project-top-ten/

---

**Document validé par :** _______________
**Date :** _______________
**Signature :** _______________
