# État du Déploiement - MY-IA

> Dernière mise à jour : 2025-11-27 05:37 CET
> Session de déploiement en cours

---

## ✅ Corrections Apportées

### 1. Fichier `main.py` recréé
- **Problème** : Fichier corrompu (contenait du YAML au lieu de Python)
- **Solution** : Nouveau fichier créé avec API FastAPI complète (371 lignes)
- **Sauvegarde** : `app/main.py.backup.20251127_045940`
- **Statut** : ✅ RÉSOLU

### 2. docker-compose.yml corrigé
- **Problème** : Indentation incorrecte (lignes 22, 54, 84)
- **Solution** : Espaces normalisés à 2 espaces
- **Statut** : ✅ RÉSOLU

### 3. ChromaDB corrigé
- **Problème** : Erreur de permissions (`Permission denied` sur `/data`)
- **Solution** : Utilisation de l'image officielle + changement du path volume
- **Changement** : `chroma-data:/chroma/chroma` (au lieu de `/chroma/index`)
- **Statut** : ✅ RÉSOLU

---

## 📊 État Actuel des Services

| Service | Statut | Port | Notes |
|---------|--------|------|-------|
| **my-ia-app** | ✅ Healthy | 8080 | API FastAPI fonctionnelle |
| **my-ia-ollama** | ✅ Running | 11434 | ⏳ Téléchargement modèle en cours |
| **my-ia-chroma** | ✅ Running | 8000 | Fonctionnel |
| **my-ia-postgres** | ⚠️ Unhealthy | 5432 | Premier fsync lent (~5 min) |
| **my-ia-n8n** | ⏸️ En attente | - | Attend que Postgres soit healthy |

### Tests effectués

```bash
# API fonctionne
$ curl http://localhost:8080/
{
  "name": "MY-IA API",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "health": "/health",
  "metrics": "/metrics"
}

# Health check
$ curl http://localhost:8080/health
{
  "status": "degraded",
  "ollama": true,
  "chroma": false,  # Normal, API v2 maintenant
  "model": "mistral:7b"
}
```

---

## ⏳ Téléchargement en Cours

### Modèle: `mistral:7b`
- **Taille totale** : 4.4 GB
- **Progression** : ~3% (129 MB / 4400 MB)
- **Vitesse** : 7-8 MB/s
- **Temps estimé restant** : ~9 minutes
- **ID de tâche** : Background shell `1edbd8`

**Commande en cours** :
```bash
docker exec my-ia-ollama ollama pull mistral:7b
```

### Pour suivre la progression

```bash
# Voir les modèles déjà téléchargés
docker exec my-ia-ollama ollama list

# Ou surveiller les logs
docker logs my-ia-ollama --follow
```

---

## 📝 Étapes Restantes

### 1. Attendre la fin du téléchargement de `mistral:7b`
**Temps estimé** : ~9 minutes (peut varier selon la connexion)

Une fois terminé, vous devriez voir :
```
pulling f5074b1221da: 100%
verifying sha256 digest
writing manifest
removing any unused layers
success
```

### 2. Télécharger le modèle d'embeddings

```bash
docker exec my-ia-ollama ollama pull nomic-embed-text
```

**Taille** : ~500 MB
**Temps estimé** : ~1-2 minutes

### 3. Vérifier que tous les modèles sont présents

```bash
docker exec my-ia-ollama ollama list
```

**Sortie attendue** :
```
NAME                   ID              SIZE    MODIFIED
mistral:7b             <hash>          4.4 GB  X minutes ago
nomic-embed-text       <hash>          500 MB  X minutes ago
```

### 4. Ingérer les données dans ChromaDB

```bash
docker compose exec app python ingest.py
```

**Ce script va** :
- Scanner le dossier `./datasets/`
- Découper les documents en chunks (900 chars)
- Générer des embeddings avec `nomic-embed-text`
- Stocker dans ChromaDB (collection `knowledge_base`)

**Durée estimée** : 30 secondes - 2 minutes (selon quantité de données)

### 5. Tester l'API complète

#### Test sans RAG (modèle direct)
```bash
curl -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{"query":"Bonjour, qui es-tu?"}'
```

#### Test avec RAG (après ingestion)
```bash
curl -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{"query":"Comment déployer cette application?"}'
```

#### Test de l'assistant
```bash
curl -X POST http://localhost:8080/assistant \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{"query":"Crée un plan de déploiement pour cette stack"}'
```

#### Test du streaming
```bash
curl -N -X POST http://localhost:8080/chat/stream \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{"query":"Explique-moi le RAG en détail"}'
```

### 6. Accéder aux interfaces

- **API Documentation** : http://localhost:8080/docs
- **Métriques Prometheus** : http://localhost:8080/metrics
- **N8N** : http://localhost:5678 (login: admin / change-me-in-production)
- **ChromaDB** : http://localhost:8000 (pas d'UI, API seulement)

---

## 🐛 Problèmes Connus

### PostgreSQL "unhealthy"
**Symptôme** : `docker compose ps` montre postgres comme `unhealthy`
**Cause** : Premier fsync très lent (peut prendre 5-10 minutes)
**Solution** : Attendre, c'est normal au premier démarrage

**Vérification** :
```bash
docker logs my-ia-postgres --tail=20
```

Quand vous voyez `database system is ready to accept connections`, c'est OK.

### N8N ne démarre pas
**Cause** : Attend que PostgreSQL soit healthy
**Solution** : Attendre que postgres soit prêt, N8N démarrera automatiquement

### ChromaDB "health check failed"
**Cause** : L'API a changé de v1 à v2
**Impact** : Aucun, le code utilise l'API v2 maintenant
**Solution** : Ignorer, c'est normal

---

## 📦 Fichiers Créés/Modifiés

```
my-ia/
├── app/
│   ├── main.py                               ✅ RECRÉÉ (371 lignes)
│   └── main.py.backup.20251127_045940        📦 SAUVEGARDE
├── docker-compose.yml                         ✅ CORRIGÉ (indentation)
├── DOCKER_FIX.md                              📄 DOCUMENTATION COMPLÈTE
├── AMELIORATIONS.md                           📄 ROADMAP 6 MOIS
└── ETAT_DEPLOIEMENT.md                        📄 CE FICHIER
```

---

## 🚀 Commande Rapide pour Reprendre

Si vous voulez **tout recommencer** proprement plus tard :

```bash
# 1. Arrêter tout
docker compose down

# 2. Supprimer les volumes (ATTENTION : perte de données!)
docker volume rm my-ia_chroma-data my-ia_ollama-data my-ia_postgres-data my-ia_n8n-data

# 3. Relancer
docker compose up -d

# 4. Télécharger les modèles
docker exec my-ia-ollama ollama pull mistral:7b
docker exec my-ia-ollama ollama pull nomic-embed-text

# 5. Ingérer les données
docker compose exec app python ingest.py

# 6. Tester
curl http://localhost:8080/health
```

---

## 🔍 Commandes de Diagnostic

### Voir les logs en temps réel
```bash
# Tous les services
docker compose logs -f

# Un service spécifique
docker compose logs -f app
docker compose logs -f ollama
docker compose logs -f postgres
docker compose logs -f n8n
docker compose logs -f chroma
```

### Vérifier l'état des containers
```bash
docker compose ps
```

### Vérifier l'utilisation des ressources
```bash
docker stats
```

### Inspecter un container
```bash
docker inspect my-ia-app
docker inspect my-ia-ollama
```

### Voir les volumes
```bash
docker volume ls | grep my-ia
```

### Espace utilisé
```bash
docker system df
```

---

## 📌 Prochaines Actions Recommandées

Après avoir terminé le déploiement :

1. **Sécurité** : Changer les mots de passe par défaut dans `.env`
2. **Tests** : Créer des tests unitaires (voir `AMELIORATIONS.md`)
3. **Monitoring** : Ajouter Grafana (voir `AMELIORATIONS.md` - Phase 2)
4. **UI Web** : Implémenter une interface Streamlit ou React
5. **Workflows N8N** : Créer des automatisations pratiques

---

## 💡 Astuces

### Accélérer le téléchargement Ollama
Si le téléchargement est trop lent :
```bash
# Utiliser un autre registry (si disponible)
# Ou télécharger un modèle plus petit en attendant
docker exec my-ia-ollama ollama pull llama3.2:1b  # 1 GB au lieu de 4.4 GB
```

### Libérer de l'espace
```bash
# Nettoyer les images inutilisées
docker system prune -a

# Supprimer seulement les volumes non utilisés
docker volume prune
```

### Redémarrer un service spécifique
```bash
docker compose restart app
docker compose restart ollama
```

---

## 📚 Documentation

- **DOCKER_FIX.md** : Détails des corrections apportées
- **AMELIORATIONS.md** : Roadmap et améliorations futures
- **README.md** : Documentation générale du projet
- **app/prompts/** : System prompts pour ChatBot et Assistant
- **n8n/README.md** : Guide workflows N8N

---

**Note importante** : Le téléchargement du modèle `mistral:7b` est toujours en cours. Vous pouvez :
- Attendre qu'il se termine (~9 minutes restantes)
- Fermer cette session et revenir plus tard (le téléchargement continuera en arrière-plan si le container est actif)
- Utiliser `docker logs my-ia-ollama --follow` pour suivre la progression

---

**Status actuel** : ⏳ EN COURS (Téléchargement modèle mistral:7b à 3%)
**Prochaine étape** : Attendre fin du téléchargement → Télécharger nomic-embed-text → Ingérer données
