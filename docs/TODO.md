# TODO - MY-IA

Ce fichier suit l'évolution du projet MY-IA. Les tâches sont organisées par priorité et leur statut est mis à jour au fil de l'avancement.

**Légende des statuts :**
- ⏳ À faire
- 🚧 En cours
- ✅ Terminé
- ❌ Abandonné

---

## État actuel du projet

**Date de dernière mise à jour :** 21 décembre 2025 (Système d'ingestion v2 + Tests actualisés ✅)

**Analyse globale :**
- ✅ Architecture de base : Ollama + ChromaDB + FastAPI + N8N + PostgreSQL
- ✅ Documentation principale (README.md, API.md, INSTALLATION.md, TROUBLESHOOTING.md, INGESTION_V2.md, DEV_WORKFLOW.md)
- ✅ Scripts de setup, backup, restore
- ✅ Endpoints API fonctionnels (/chat, /assistant, /chat/stream, /upload/v2)
- ✅ Système d'ingestion v2 multi-formats (13 formats : PDF, DOCX, XLSX, PPTX, TXT, MD, HTML, JSONL, CSV, images avec OCR)
- ✅ Chunking sémantique avec LangChain + Parsing intelligent avec Unstructured.io
- ✅ Déduplication automatique (SHA256) et métadonnées enrichies (11 champs)
- ✅ Hot reload activé pour développement rapide
- ✅ Rate limiting et métriques Prometheus
- ✅ Interface de chat web avec upload de fichiers (frontend/ - http://localhost:3000)
- 🚧 Tests (infrastructure de base créée, tests unitaires en cours)
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
- ✅ Upload de fichiers (13 formats supportés avec ingestion v2)
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

### 2. Système d'Ingestion v2 ✅
**Statut :** ✅ Terminé (20-21 décembre 2025)
**Fichier principal :** `app/ingest_v2.py`
**Documentation :** `docs/INGESTION_V2.md` + `docs/CHANGELOG_INGESTION_V2.md`

#### 2.1 Parsing intelligent ✅
- ✅ Unstructured.io intégré pour parsing avancé
- ✅ Détection automatique du type de document
- ✅ Extraction de structure (titres, sections, tables)
- ✅ 3 stratégies de parsing : fast, auto, hi_res
- ✅ Support de 13 formats :
  - Documents : PDF, DOCX, XLSX, PPTX
  - Texte : TXT, MD, HTML
  - Données : JSONL, CSV
  - Images : PNG, JPG (avec OCR Tesseract)

#### 2.2 Chunking sémantique ✅
- ✅ RecursiveCharacterTextSplitter de LangChain
- ✅ Respect de la structure des documents
- ✅ Chunk size adaptatif (1000 caractères par défaut)
- ✅ Overlap intelligent (200 caractères)
- ✅ Préservation du contexte entre chunks

#### 2.3 Métadonnées enrichies ✅
- ✅ 11 champs de métadonnées vs 1 auparavant :
  - source : chemin du fichier source
  - chunk_index : position du chunk dans le document
  - total_chunks : nombre total de chunks
  - doc_type : type de document (pdf, docx, etc.)
  - created_at : timestamp d'ingestion
  - file_size : taille du fichier en octets
  - page_number : numéro de page (si applicable)
  - section : section du document (si détectée)
  - title : titre du document (si détecté)
  - hash : hash SHA256 du contenu
  - parsing_strategy : stratégie utilisée (fast/auto/hi_res)

#### 2.4 Déduplication et performance ✅
- ✅ Hash SHA256 du contenu pour détecter les duplicatas
- ✅ Skip automatique des documents déjà indexés
- ✅ Logs détaillés de l'ingestion
- ✅ Gestion d'erreurs robuste (continue sur erreur)

#### 2.5 OCR intégré ✅
- ✅ Tesseract OCR pour images et PDFs scannés
- ✅ Support PNG, JPG
- ✅ Détection automatique du texte dans les images
- ✅ Qualité configurable

#### 2.6 API et Endpoints ✅
- ✅ Endpoint `/upload/v2` pour upload via API
- ✅ Support multipart/form-data
- ✅ Sélection de stratégie de parsing (query param)
- ✅ Upload via interface web (frontend)
- ✅ Authentification API Key

#### 2.7 Documentation ✅
- ✅ Guide complet : INGESTION_V2.md
- ✅ Changelog détaillé : CHANGELOG_INGESTION_V2.md
- ✅ Guide développement : DEV_WORKFLOW.md
- ✅ Exemples d'utilisation CLI et API
- ✅ README.md mis à jour avec nouveautés v2

---

### 3. Tests 🚧
**Statut :** 🚧 En cours (infrastructure créée le 21 décembre 2025)
**Répertoire :** `tests/`

#### 3.1 Tests unitaires 🚧
- ✅ Tests pour `app/ingest_v2.py` (test_ingest_v2.py créé avec 408 lignes)
  - ✅ Fonction `load_document()` pour tous les formats
  - ✅ Fonction `chunk_text()` avec chunking sémantique
  - ✅ Fonction `extract_metadata()`
  - ✅ Fonction `generate_document_hash()`
  - ✅ Tests de déduplication
  - ✅ Tests OCR pour images
- 🚧 Tests pour `app/main.py` (test_api_endpoints.py refonte en cours)
  - 🚧 Endpoints `/chat`, `/assistant`, `/chat/stream`
  - 🚧 Endpoint `/upload/v2`
  - ⏳ Fonction `verify_api_key()`
  - ⏳ Fonction `get_embeddings()`
  - ⏳ Fonction `search_context()`
  - ⏳ Fonction `generate_response()`
- ❌ Tests pour `app/ingest.py` (ancien système supprimé)

#### 3.2 Tests d'intégration ⏳
- ⏳ Test end-to-end du workflow complet :
  - Ingestion v2 → ChromaDB → Requête API → Réponse
- ⏳ Test d'intégration avec Ollama
- ⏳ Test d'intégration avec ChromaDB
- ⏳ Test des workflows N8N

#### 3.3 Tests de performance ⏳
- ⏳ Tests de charge sur les endpoints API
- ⏳ Benchmarking du temps de réponse
- ⏳ Tests de stress sur ChromaDB
- ⏳ Tests de concurrence (multi-requêtes simultanées)

#### 3.4 Infrastructure de tests ✅
- ✅ Configuration pytest (pytest.ini mis à jour)
- ✅ Fixtures complètes pour tous les formats (conftest.py refonte)
- ✅ Données de test dédiées (15+ fichiers de test dans tests/fixtures/)
  - ✅ Documents : PDF, DOCX, XLSX, PPTX, TXT, MD, HTML, JSONL, CSV
  - ✅ Images : PNG avec texte pour OCR
  - ✅ Tests Unicode et documents longs
- ✅ Script de génération de fichiers de test (generate_test_files.py)
- ✅ Requirements de test mis à jour (requirements-test.txt)
- ⏳ Coverage reports

---

### 4. Monitoring ⏳
**Statut :** ⏳ À faire
**Répertoire :** `monitoring/` (actuellement vide)

#### 4.1 Dashboard Grafana
- ⏳ Configuration Grafana dans docker-compose.yml
- ⏳ Connexion à Prometheus pour scraper les métriques
- ⏳ Dashboard pour :
  - Nombre de requêtes par endpoint
  - Temps de réponse moyen/médian/p95/p99
  - Taux d'erreur
  - Utilisation CPU/RAM des containers
  - Nombre de documents dans ChromaDB
  - Statut des services (health checks)

#### 4.2 Alerting
- ⏳ Configuration d'Alertmanager
- ⏳ Alertes critiques :
  - API down
  - Ollama non disponible
  - ChromaDB non disponible
  - Temps de réponse > seuil
  - Taux d'erreur > seuil
  - Espace disque < 10%
- ⏳ Canaux de notification (email, Slack, etc.)

#### 4.3 Logs centralisés
- ⏳ Configuration ELK Stack ou Loki + Promtail
- ⏳ Agrégation des logs de tous les services
- ⏳ Dashboard de visualisation des logs
- ⏳ Recherche et filtrage des logs
- ⏳ Retention policy pour les logs

---

### 5. Gestion de la mémoire conversationnelle ⏳
**Statut :** ⏳ À faire (session_id existe mais non utilisé)

#### 5.1 Stockage des conversations
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

#### 5.2 Intégration dans les endpoints
- ⏳ Modifier `/chat` pour inclure l'historique dans le prompt
- ⏳ Modifier `/assistant` pour inclure l'historique
- ⏳ Limiter la taille de l'historique (ex: 10 derniers messages)
- ⏳ Format de l'historique : User/Assistant alternés

#### 5.3 Gestion avancée
- ⏳ Résumé automatique des anciennes conversations (> N messages)
- ⏳ TTL pour les sessions inactives (ex: 24h)
- ⏳ Endpoint pour reset/supprimer une session
- ⏳ Endpoint pour lister les sessions d'un utilisateur

---

## PRIORITÉ MOYENNE

### 6. Sécurité en production ⏳
**Statut :** ⏳ À faire

#### 6.1 Variables d'environnement
- ⏳ Créer un fichier `.env` pour les secrets
- ⏳ Retirer les mots de passe du `docker-compose.yml`
- ⏳ Documentation sur la configuration des variables
- ⏳ Validation des variables au démarrage

#### 6.2 HTTPS/TLS
- ⏳ Configuration reverse proxy (Nginx ou Traefik)
- ⏳ Certificats SSL/TLS (Let's Encrypt)
- ⏳ Redirection HTTP → HTTPS
- ⏳ Configuration HSTS

#### 6.3 Authentification améliorée
- ⏳ Remplacer API Key par JWT
- ⏳ Système de users/tokens
- ⏳ Refresh tokens
- ⏳ Révocation de tokens
- ⏳ Rate limiting par utilisateur

#### 6.4 Hardening
- ⏳ Scan de vulnérabilités des images Docker
- ⏳ User non-root dans les containers
- ⏳ Network policies plus restrictives
- ⏳ Secrets management (Vault, Docker secrets)

---

### 7. Optimisations 🚧
**Statut :** 🚧 En cours (chunking sémantique terminé)

#### 7.1 Cache Redis ⏳
- ⏳ Ajout de Redis dans docker-compose.yml
- ⏳ Cache des embeddings pour requêtes identiques
- ⏳ Cache des réponses fréquentes
- ⏳ TTL configurable
- ⏳ Invalidation du cache lors de réindexation

#### 7.2 File d'attente asynchrone ⏳
- ⏳ Ajout de Celery + RabbitMQ ou Redis
- ⏳ Traitement asynchrone des requêtes longues
- ⏳ Endpoint pour soumettre une tâche
- ⏳ Endpoint pour récupérer le résultat
- ⏳ Webhook de notification de fin de traitement

#### 7.3 Amélioration du chunking ✅
- ✅ Remplacer chunking fixe par semantic chunking (ingest_v2.py avec RecursiveCharacterTextSplitter)
- ✅ Utiliser LangChain pour le chunking (intégré dans ingest_v2.py)
- ✅ Chunking basé sur les paragraphes/sections (via Unstructured.io)
- ✅ Overlap intelligent basé sur le contexte (chunk_overlap=200)
- ✅ Support des métadonnées enrichies (11 champs : titre, section, page, type, source, timestamp, etc.)

#### 7.4 Optimisation des requêtes ⏳
- ⏳ Batch processing pour l'ingestion
- ⏳ Parallélisation des embeddings
- ⏳ Compression des embeddings
- ⏳ Index HNSW optimisé dans ChromaDB

---

### 8. Workflows N8N ⏳
**Statut :** ⏳ À faire (1 exemple existe)

#### 8.1 Templates de workflows
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

#### 8.2 Documentation des workflows
- ⏳ Guide pas-à-pas pour chaque workflow
- ⏳ Screenshots des configurations
- ⏳ Variables d'environnement nécessaires
- ⏳ Exemples de payloads

---

## PRIORITÉ BASSE

### 9. Features additionnelles 🚧
**Statut :** 🚧 En cours (formats de fichiers terminés)

#### 9.1 Multi-utilisateurs ⏳
- ⏳ Système d'authentification multi-users
- ⏳ Isolation des données par utilisateur
- ⏳ Collections ChromaDB par utilisateur ou tenant
- ⏳ Quotas par utilisateur
- ⏳ Tableau de bord administrateur

#### 9.2 Interface web ✅
- ✅ Frontend HTML/CSS/JS vanilla (décision finale)
- ✅ Chat interface moderne type ChatGPT
- ✅ Upload de documents via UI (13 formats supportés)
- ✅ Visualisation des sources RAG
- ✅ Historique des conversations (localStorage)
- ✅ Settings utilisateur (modèle, TOP_K, thème)

#### 9.3 Support de nouveaux formats ✅
- ✅ CSV (avec détection de colonnes pertinentes via Unstructured.io)
- ✅ DOCX (Microsoft Word via Unstructured.io)
- ✅ XLSX (Excel via Unstructured.io)
- ✅ PPTX (PowerPoint via Unstructured.io)
- ✅ Images avec OCR (PNG, JPG via Tesseract)
- ⏳ Audio/Video avec transcription

#### 9.4 Feedback système ⏳
- ⏳ Thumbs up/down sur les réponses
- ⏳ Stockage des feedbacks
- ⏳ Utilisation des feedbacks pour améliorer le RAG
- ⏳ Fine-tuning basé sur les feedbacks
- ⏳ Analytics des feedbacks

#### 9.5 Features avancées RAG ⏳
- ⏳ Reranking des résultats de recherche
- ⏳ Hybrid search (dense + sparse)
- ⏳ Multi-query retrieval
- ⏳ Parent document retrieval
- ⏳ Query expansion/rephrasing

---

### 10. DevOps ⏳
**Statut :** ⏳ À faire

#### 10.1 CI/CD ⏳
- ⏳ GitHub Actions pour :
  - Linting (flake8, black)
  - Tests automatiques
  - Build des images Docker
  - Push vers Docker Hub/Registry
  - Déploiement automatique
- ⏳ Environnements multiples (dev, staging, prod)
- ⏳ Rollback automatique en cas d'échec

#### 10.2 Kubernetes ⏳
- ⏳ Manifests K8s (Deployments, Services, ConfigMaps, Secrets)
- ⏳ Helm charts
- ⏳ Horizontal Pod Autoscaling
- ⏳ Persistent Volumes pour les données
- ⏳ Ingress configuration
- ⏳ Service Mesh (Istio/Linkerd) optionnel

#### 10.3 Scripts de migration ⏳
- ⏳ Migration de données ChromaDB (upgrade versions)
- ⏳ Migration de schéma PostgreSQL (Alembic)
- ⏳ Scripts de rollback
- ⏳ Scripts de seed data pour dev/test

#### 10.4 Documentation DevOps ⏳
- ⏳ Guide de déploiement production
- ⏳ Architecture de haute disponibilité
- ⏳ Disaster recovery plan
- ⏳ Scaling guide

---

## BACKLOG (Idées futures)

### 11. Fonctionnalités avancées ⏳
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

**Dernière révision :** 21 décembre 2025

## 🎉 Réalisations récentes (20-21 décembre 2025)

### Système d'ingestion v2 ✅
- ✅ **Parsing intelligent** : Unstructured.io avec 3 stratégies (fast/auto/hi_res)
- ✅ **13 formats supportés** : PDF, DOCX, XLSX, PPTX, TXT, MD, HTML, JSONL, CSV, images avec OCR
- ✅ **Chunking sémantique** : RecursiveCharacterTextSplitter de LangChain
- ✅ **Métadonnées enrichies** : 11 champs vs 1 auparavant
- ✅ **Déduplication** : Hash SHA256 automatique
- ✅ **OCR intégré** : Tesseract pour images et PDFs scannés
- ✅ **Upload via API et UI** : Endpoint /upload/v2 + interface web
- ✅ **Documentation complète** : 3 nouveaux guides (INGESTION_V2.md, CHANGELOG_INGESTION_V2.md, DEV_WORKFLOW.md)

### Infrastructure de tests 🚧
- ✅ **Tests unitaires pour ingest_v2** : 408 lignes de tests (test_ingest_v2.py)
- ✅ **Fixtures complètes** : 15+ fichiers de test pour tous les formats
- ✅ **Configuration pytest** : pytest.ini et requirements-test.txt mis à jour
- ✅ **Script de génération** : generate_test_files.py pour créer des fichiers de test
- 🚧 **Tests API** : test_api_endpoints.py en cours de refonte
- ⏳ **Tests d'intégration** : À venir

### Refactoring et nettoyage
- ✅ **Suppression de l'ancien système** : ingest.py (207 lignes) retiré
- ✅ **Suppression des anciens tests** : test_ingest.py, test_integration.py, test_utility_functions.py
- ✅ **Refonte de conftest.py** : Fixtures modernisées et simplifiées
- ✅ **Hot reload activé** : Développement rapide sans rebuild Docker
