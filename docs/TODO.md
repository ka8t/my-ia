# TODO - MY-IA

Ce fichier suit l'évolution du projet MY-IA. Les tâches sont organisées par priorité et leur statut est mis à jour au fil de l'avancement.

**Légende des statuts :**
- ⏳ À faire
- 🚧 En cours
- ✅ Terminé
- ❌ Abandonné

---

## État actuel du projet

**Date de dernière mise à jour :** 29 novembre 2025 (Fonctionnalités Régénérer + Éditer terminées ✅)

**Analyse globale :**
- ✅ Architecture de base : Ollama + ChromaDB + FastAPI + N8N + PostgreSQL
- ✅ Documentation principale (README.md, API.md, INSTALLATION.md, TROUBLESHOOTING.md)
- ✅ Scripts de setup, backup, restore
- ✅ Endpoints API fonctionnels (/chat, /assistant, /chat/stream)
- ✅ Système d'ingestion multi-formats (JSONL, MD, TXT, PDF, HTML)
- ✅ Rate limiting et métriques Prometheus
- ✅ Interface de chat web (frontend/ - http://localhost:3000)
- ⏳ Tests (répertoire vide)
- ⏳ Monitoring (répertoire vide)
- ⏳ Gestion de la mémoire conversationnelle (partielle)

---

## PRIORITÉ HAUTE

### 1. Interface de Chat Web (type ChatGPT) ✅
**Statut :** ✅ Terminé (27 novembre 2025)
**Répertoire :** `frontend/`
**URL :** http://localhost:3000

#### 1.1 Interface utilisateur moderne ✅
- ✅ Design responsive type ChatGPT/Claude
  - Sidebar avec liste des conversations
  - Zone de chat centrale avec messages
  - Input avec support markdown
  - Bouton pour nouvelle conversation
  - Mode dark/light
- ✅ Composants HTML/CSS/JS vanilla :
  - ChatMessage (avec avatar, timestamp, markdown rendering)
  - ChatInput (avec auto-resize, shortcuts)
  - ConversationList (avec delete)
  - SourcesPanel (affichage des sources RAG)
  - SettingsPanel

#### 1.2 Fonctionnalités core
- ✅ Streaming des réponses en temps réel
- ✅ Support markdown avec syntax highlighting (marked.js + highlight.js)
- ✅ Copier le texte d'un message
- ✅ Régénérer une réponse
- ✅ Éditer et renvoyer un message
- ✅ Stop generation (annuler une réponse en cours)
- ⏳ Upload de fichiers (pour ingestion future) (TODO)
- ✅ Affichage des sources utilisées par le RAG

#### 1.3 Gestion des conversations
- ✅ Créer nouvelle conversation
- ✅ Sauvegarder automatiquement les conversations (localStorage)
- ✅ Renommer les conversations (automatique basé sur 1er message)
- ✅ Supprimer les conversations
- ⏳ Rechercher dans l'historique (TODO)
- ⏳ Export conversation (JSON, Markdown, PDF) (TODO)

#### 1.4 Paramètres utilisateur
- ⏳ Choix du modèle (si plusieurs modèles Ollama disponibles) (TODO)
- ✅ Ajuster les paramètres RAG (TOP_K, etc.)
- ✅ Choix entre ChatBot et Assistant
- ✅ Thème (dark/light)
- ⏳ Raccourcis clavier personnalisables (TODO - Enter et Shift+Enter fonctionnent)

#### 1.5 Intégration backend
- ✅ Streaming via fetch API et ReadableStream
- ⏳ API REST pour CRUD conversations (local storage pour l'instant)
- ⏳ Gestion des sessions/auth (si multi-users) (TODO)
- ⏳ Upload de documents pour enrichir la base de connaissance (TODO)
- ⏳ Voir les statistiques (nombre de requêtes, tokens utilisés) (TODO)

#### 1.6 Stack technique choisi ✅
- ✅ **HTML5 + CSS3 + JavaScript vanilla** (choix final pour simplicité)
- ✅ Librairies :
  - ✅ `marked.js` pour le rendu markdown
  - ✅ `highlight.js` pour syntax highlighting
  - ✅ `fetch API` pour les requêtes HTTP
  - ✅ `localStorage` pour persistence

#### 1.7 Déploiement ✅
- ✅ Dockerfile pour le frontend (Nginx Alpine)
- ✅ Ajout du service dans docker-compose.yml (port 3000)
- ✅ Configuration Nginx pour servir le frontend
- ✅ README.md dédié au frontend

---

### 2. Tests ⏳
**Statut :** ⏳ À faire
**Répertoire :** `tests/` (actuellement vide)

#### 2.1 Tests unitaires
- ⏳ Tests pour `app/main.py`
  - Endpoints `/chat`, `/assistant`, `/chat/stream`, `/test`
  - Fonction `verify_api_key()`
  - Fonction `get_embeddings()`
  - Fonction `search_context()`
  - Fonction `generate_response()`
- ⏳ Tests pour `app/ingest.py`
  - Fonction `chunk()`
  - Fonction `embed()`
  - Fonction `read_jsonl()`
  - Fonction `extract_pdf_text()`
  - Fonction `extract_html_text()`
  - Fonctions d'interaction avec ChromaDB

#### 2.2 Tests d'intégration
- ⏳ Test end-to-end du workflow complet :
  - Ingestion de données → ChromaDB → Requête API → Réponse
- ⏳ Test d'intégration avec Ollama
- ⏳ Test d'intégration avec ChromaDB
- ⏳ Test des workflows N8N

#### 2.3 Tests de performance
- ⏳ Tests de charge sur les endpoints API
- ⏳ Benchmarking du temps de réponse
- ⏳ Tests de stress sur ChromaDB
- ⏳ Tests de concurrence (multi-requêtes simultanées)

#### 2.4 Infrastructure de tests
- ⏳ Configuration pytest
- ⏳ Fixtures pour tests avec mocks
- ⏳ Tests avec données de test dédiées
- ⏳ Coverage reports

---

### 2. Monitoring ⏳
**Statut :** ⏳ À faire
**Répertoire :** `monitoring/` (actuellement vide)

#### 2.1 Dashboard Grafana
- ⏳ Configuration Grafana dans docker-compose.yml
- ⏳ Connexion à Prometheus pour scraper les métriques
- ⏳ Dashboard pour :
  - Nombre de requêtes par endpoint
  - Temps de réponse moyen/médian/p95/p99
  - Taux d'erreur
  - Utilisation CPU/RAM des containers
  - Nombre de documents dans ChromaDB
  - Statut des services (health checks)

#### 2.2 Alerting
- ⏳ Configuration d'Alertmanager
- ⏳ Alertes critiques :
  - API down
  - Ollama non disponible
  - ChromaDB non disponible
  - Temps de réponse > seuil
  - Taux d'erreur > seuil
  - Espace disque < 10%
- ⏳ Canaux de notification (email, Slack, etc.)

#### 2.3 Logs centralisés
- ⏳ Configuration ELK Stack ou Loki + Promtail
- ⏳ Agrégation des logs de tous les services
- ⏳ Dashboard de visualisation des logs
- ⏳ Recherche et filtrage des logs
- ⏳ Retention policy pour les logs

---

### 3. Gestion de la mémoire conversationnelle ⏳
**Statut :** ⏳ À faire (session_id existe mais non utilisé)

#### 3.1 Stockage des conversations
- ⏳ Choix du backend (Redis, PostgreSQL, ou ChromaDB)
- ⏳ Schéma de données pour les sessions :
  - session_id (clé)
  - user_id (optionnel)
  - messages[] (historique)
  - created_at
  - updated_at
  - metadata
- ⏳ Fonction de sauvegarde de session
- ⏳ Fonction de récupération de session

#### 3.2 Intégration dans les endpoints
- ⏳ Modifier `/chat` pour inclure l'historique dans le prompt
- ⏳ Modifier `/assistant` pour inclure l'historique
- ⏳ Limiter la taille de l'historique (ex: 10 derniers messages)
- ⏳ Format de l'historique : User/Assistant alternés

#### 3.3 Gestion avancée
- ⏳ Résumé automatique des anciennes conversations (> N messages)
- ⏳ TTL pour les sessions inactives (ex: 24h)
- ⏳ Endpoint pour reset/supprimer une session
- ⏳ Endpoint pour lister les sessions d'un utilisateur

---

## PRIORITÉ MOYENNE

### 4. Sécurité en production ⏳
**Statut :** ⏳ À faire

#### 4.1 Variables d'environnement
- ⏳ Créer un fichier `.env` pour les secrets
- ⏳ Retirer les mots de passe du `docker-compose.yml`
- ⏳ Documentation sur la configuration des variables
- ⏳ Validation des variables au démarrage

#### 4.2 HTTPS/TLS
- ⏳ Configuration reverse proxy (Nginx ou Traefik)
- ⏳ Certificats SSL/TLS (Let's Encrypt)
- ⏳ Redirection HTTP → HTTPS
- ⏳ Configuration HSTS

#### 4.3 Authentification améliorée
- ⏳ Remplacer API Key par JWT
- ⏳ Système de users/tokens
- ⏳ Refresh tokens
- ⏳ Révocation de tokens
- ⏳ Rate limiting par utilisateur

#### 4.4 Hardening
- ⏳ Scan de vulnérabilités des images Docker
- ⏳ User non-root dans les containers
- ⏳ Network policies plus restrictives
- ⏳ Secrets management (Vault, Docker secrets)

---

### 5. Optimisations ⏳
**Statut :** ⏳ À faire

#### 5.1 Cache Redis
- ⏳ Ajout de Redis dans docker-compose.yml
- ⏳ Cache des embeddings pour requêtes identiques
- ⏳ Cache des réponses fréquentes
- ⏳ TTL configurable
- ⏳ Invalidation du cache lors de réindexation

#### 5.2 File d'attente asynchrone
- ⏳ Ajout de Celery + RabbitMQ ou Redis
- ⏳ Traitement asynchrone des requêtes longues
- ⏳ Endpoint pour soumettre une tâche
- ⏳ Endpoint pour récupérer le résultat
- ⏳ Webhook de notification de fin de traitement

#### 5.3 Amélioration du chunking
- ⏳ Remplacer chunking fixe par semantic chunking
- ⏳ Utiliser LangChain ou LlamaIndex pour le chunking
- ⏳ Chunking basé sur les paragraphes/sections
- ⏳ Overlap intelligent basé sur le contexte
- ⏳ Support des métadonnées enrichies (titre, section, page)

#### 5.4 Optimisation des requêtes
- ⏳ Batch processing pour l'ingestion
- ⏳ Parallélisation des embeddings
- ⏳ Compression des embeddings
- ⏳ Index HNSW optimisé dans ChromaDB

---

### 6. Workflows N8N ⏳
**Statut :** ⏳ À faire (1 exemple existe)

#### 6.1 Templates de workflows
- ⏳ Email Auto-responder
  - Gmail Trigger → API /chat → Gmail Send
- ⏳ Document Summarizer
  - Google Drive Trigger → Download → API /assistant → Save summary
- ⏳ Slack Bot
  - Slack Trigger → API /chat → Slack Reply
- ⏳ Daily Report Generator
  - Cron Trigger → Fetch data → API /assistant → Send report
- ⏳ Customer Support
  - Webhook Trigger → API /chat → Create ticket if needed
- ⏳ Content Generator
  - Cron → API /assistant → Post to social media

#### 6.2 Documentation des workflows
- ⏳ Guide pas-à-pas pour chaque workflow
- ⏳ Screenshots des configurations
- ⏳ Variables d'environnement nécessaires
- ⏳ Exemples de payloads

---

## PRIORITÉ BASSE

### 7. Features additionnelles ⏳
**Statut :** ⏳ À faire

#### 7.1 Multi-utilisateurs
- ⏳ Système d'authentification multi-users
- ⏳ Isolation des données par utilisateur
- ⏳ Collections ChromaDB par utilisateur ou tenant
- ⏳ Quotas par utilisateur
- ⏳ Tableau de bord administrateur

#### 7.2 Interface web
- ⏳ Frontend React ou Vue.js
- ⏳ Chat interface simple
- ⏳ Upload de documents via UI
- ⏳ Visualisation des sources
- ⏳ Historique des conversations
- ⏳ Settings utilisateur

#### 7.3 Support de nouveaux formats
- ⏳ CSV (avec détection de colonnes pertinentes)
- ⏳ DOCX (Microsoft Word)
- ⏳ XLSX (Excel)
- ⏳ PPTX (PowerPoint)
- ⏳ Images avec OCR
- ⏳ Audio/Video avec transcription

#### 7.4 Feedback système
- ⏳ Thumbs up/down sur les réponses
- ⏳ Stockage des feedbacks
- ⏳ Utilisation des feedbacks pour améliorer le RAG
- ⏳ Fine-tuning basé sur les feedbacks
- ⏳ Analytics des feedbacks

#### 7.5 Features avancées RAG
- ⏳ Reranking des résultats de recherche
- ⏳ Hybrid search (dense + sparse)
- ⏳ Multi-query retrieval
- ⏳ Parent document retrieval
- ⏳ Query expansion/rephrasing

---

### 8. DevOps ⏳
**Statut :** ⏳ À faire

#### 8.1 CI/CD
- ⏳ GitHub Actions pour :
  - Linting (flake8, black)
  - Tests automatiques
  - Build des images Docker
  - Push vers Docker Hub/Registry
  - Déploiement automatique
- ⏳ Environnements multiples (dev, staging, prod)
- ⏳ Rollback automatique en cas d'échec

#### 8.2 Kubernetes
- ⏳ Manifests K8s (Deployments, Services, ConfigMaps, Secrets)
- ⏳ Helm charts
- ⏳ Horizontal Pod Autoscaling
- ⏳ Persistent Volumes pour les données
- ⏳ Ingress configuration
- ⏳ Service Mesh (Istio/Linkerd) optionnel

#### 8.3 Scripts de migration
- ⏳ Migration de données ChromaDB (upgrade versions)
- ⏳ Migration de schéma PostgreSQL (Alembic)
- ⏳ Scripts de rollback
- ⏳ Scripts de seed data pour dev/test

#### 8.4 Documentation DevOps
- ⏳ Guide de déploiement production
- ⏳ Architecture de haute disponibilité
- ⏳ Disaster recovery plan
- ⏳ Scaling guide

---

## BACKLOG (Idées futures)

### 9. Fonctionnalités avancées ⏳
- ⏳ Support multi-lingue (détection automatique)
- ⏳ Agents spécialisés par domaine
- ⏳ RAG avec sources externes (web scraping, APIs)
- ⏳ Fine-tuning de modèles Ollama custom
- ⏳ A/B testing de prompts
- ⏳ Versioning des prompts système
- ⏳ Playground pour tester différents paramètres
- ⏳ Export des conversations (PDF, JSON)
- ⏳ Intégrations tierces (Zapier, Make, etc.)

---

## Notes de développement

### Bonnes pratiques à suivre
1. Toujours écrire des tests avant de marquer une feature comme terminée
2. Documenter les nouvelles features dans `/docs`
3. Mettre à jour le README si nécessaire
4. Versionner les changements (semantic versioning)
5. Faire des commits atomiques et descriptifs
6. Code review avant merge en main

### Décisions techniques à prendre
- [ ] Backend pour la mémoire conversationnelle (Redis vs PostgreSQL)
- [ ] Solution de monitoring (Grafana vs alternatives)
- [ ] Framework de tests (pytest vs unittest)
- [ ] Stratégie de cache (Redis vs autre)
- [ ] Solution de queue (Celery+RabbitMQ vs Celery+Redis vs autre)

---

**Dernière révision :** 27 novembre 2025
