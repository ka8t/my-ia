# 🐳 Processus de Mise à Jour Docker - Architecture Modulaire

**Date** : 22 décembre 2024
**Version** : 1.0.0 (Architecture Features/)

---

## 📋 Résumé des Changements

L'application a migré vers une architecture modulaire. Voici ce qui a changé pour Docker :

### Changements Dockerfile

| Avant | Après | Raison |
|-------|-------|--------|
| Python 3.11 | Python 3.12 | Compatibilité `unstructured` |
| `main:app` | `app.main:app` | Nouveau structure modulaire |
| WORKDIR `/app` | WORKDIR `/code` + PYTHONPATH | Meilleure organisation |
| requirements.txt | requirements-docker.txt | Fusion core + ingestion |

### Fichiers Modifiés

- ✅ `app/Dockerfile` - Mise à jour Python 3.12 + nouveau CMD
- ✅ `app/requirements-docker.txt` - Fusion de toutes les dépendances
- ⚠️ `docker-compose.yml` - Aucun changement nécessaire (hot reload fonctionne)

---

## 🚀 Processus de Mise à Jour (Étape par Étape)

### Méthode 1 : Mise à Jour avec Downtime Minimal (Recommandée)

Cette méthode reconstruit seulement le container `app` sans toucher aux données.

```bash
# 1. Aller dans le répertoire du projet
cd /Users/k/Documents/Documents\ -\ MacBook\ Pro\ de\ k/Code/Ollama/my-ia

# 2. Arrêter uniquement le container app
docker compose stop app

# 3. Rebuild le container app avec la nouvelle image
docker compose build app

# 4. Redémarrer le container app
docker compose up -d app

# 5. Vérifier les logs
docker compose logs -f app

# 6. Tester l'application
curl http://localhost:8080/health
curl http://localhost:8080/docs
```

**Durée** : ~3-5 minutes (selon vitesse connexion)

**Downtime** : ~2-3 minutes (seulement l'API)

---

### Méthode 2 : Rebuild Complet (Si Problèmes)

Si la Méthode 1 échoue, rebuild complet de tous les services.

```bash
# 1. Arrêter tous les containers
docker compose down

# 2. Rebuild tous les containers
docker compose build

# 3. Relancer tous les services
docker compose up -d

# 4. Vérifier que tout fonctionne
docker compose ps
docker compose logs -f app
```

**Durée** : ~5-10 minutes

**Downtime** : ~5-10 minutes (tous les services)

---

### Méthode 3 : Mise à Jour Sans Downtime (Avancée)

Utilise un container temporaire pour tester avant de switcher.

```bash
# 1. Construire la nouvelle image avec un tag différent
docker compose build app

# 2. Lancer un container temporaire sur un autre port
docker run -d \
  --name my-ia-app-test \
  --network my-ia_internal \
  -p 8081:8080 \
  -e OLLAMA_HOST=http://ollama:11434 \
  -e CHROMA_HOST=http://chroma:8000 \
  -e DATABASE_URL=$DATABASE_URL \
  my-ia-app:latest

# 3. Tester le nouveau container
curl http://localhost:8081/health

# 4. Si OK, switcher
docker compose stop app
docker rm my-ia-app
docker rename my-ia-app-test my-ia-app
docker network connect my-ia_external my-ia-app

# 5. Mettre à jour docker-compose pour pointer vers la bonne image
docker compose up -d app
```

**Durée** : ~10 minutes

**Downtime** : 0 (si tout se passe bien)

---

## 🧪 Tests Post-Déploiement

### 1. Vérifier que tous les containers tournent

```bash
docker compose ps
```

**Attendu** :
```
NAME                IMAGE                   STATUS
my-ia-app           my-ia-app               Up
my-ia-chroma        chromadb/chroma:latest  Up
my-ia-frontend      my-ia-frontend          Up
my-ia-ollama        ollama/ollama:latest    Up
my-ia-postgres      postgres:16-alpine      Up (healthy)
```

### 2. Tester les endpoints de base

```bash
# Health check
curl http://localhost:8080/health
# → {"status":"healthy","ollama":true,"chroma":true}

# Root endpoint
curl http://localhost:8080/
# → {"name":"MY-IA API","version":"1.0.0"}

# Swagger UI
curl -I http://localhost:8080/docs
# → HTTP/1.1 200 OK

# Metrics
curl http://localhost:8080/metrics | grep myia_requests
# → myia_requests_total{...}
```

### 3. Tester les features principales

```bash
# Test Chat (nécessite Ollama)
curl -X POST http://localhost:8080/test \
  -H 'Content-Type: application/json' \
  -d '{"query":"Hello, test!"}'

# Test Upload (nécessite clé API)
curl -X POST http://localhost:8080/upload \
  -H "X-API-Key: change-me-in-production" \
  -F "file=@test.pdf"
```

### 4. Vérifier les logs

```bash
# Logs en temps réel
docker compose logs -f app

# Logs des dernières 50 lignes
docker compose logs --tail=50 app
```

**Rechercher** :
- ✅ "MY-IA API initialized successfully"
- ✅ "Application startup complete"
- ✅ "ChromaDB initialized successfully"
- ❌ Pas d'erreurs Python (Traceback)

---

## 🐛 Dépannage

### Problème 1 : Container app ne démarre pas

**Symptômes** :
```
docker compose ps
# → my-ia-app    Exit 1
```

**Solution** :
```bash
# Voir les logs d'erreur
docker compose logs app

# Erreurs communes :
# - ModuleNotFoundError → Vérifier PYTHONPATH dans Dockerfile
# - Import Error → Vérifier requirements-docker.txt
# - Database connection → Vérifier DATABASE_URL
```

### Problème 2 : Erreur "No module named 'app'"

**Cause** : PYTHONPATH mal configuré

**Solution** :
```dockerfile
# Dans Dockerfile, vérifier :
ENV PYTHONPATH=/code
CMD ["uvicorn", "app.main:app", ...]
```

### Problème 3 : Hot Reload ne fonctionne pas

**Cause** : Volume mount incorrect

**Solution** :
```yaml
# Dans docker-compose.yml, vérifier :
volumes:
  - ./app:/code/app  # Monter le code source
```

### Problème 4 : Dépendances manquantes

**Symptômes** :
```
ModuleNotFoundError: No module named 'pydantic_settings'
```

**Solution** :
```bash
# Rebuild avec --no-cache
docker compose build --no-cache app
```

### Problème 5 : ChromaDB ou Ollama non accessibles

**Symptômes** :
```
ERROR - Failed to initialize ChromaDB client
```

**Solution** :
```bash
# Vérifier que les services tournent
docker compose ps chroma ollama

# Vérifier les networks
docker network ls | grep my-ia

# Tester la connectivité
docker compose exec app curl http://chroma:8000
docker compose exec app curl http://ollama:11434/api/tags
```

---

## 📊 Checklist de Validation

Avant de déclarer la mise à jour réussie, vérifier :

### Infrastructure
- [ ] Tous les containers sont `Up` (docker compose ps)
- [ ] PostgreSQL est `healthy`
- [ ] Pas d'erreurs dans les logs (docker compose logs)

### Endpoints API
- [ ] GET / → 200 OK
- [ ] GET /health → 200 OK (status: healthy ou degraded)
- [ ] GET /docs → 200 OK (Swagger accessible)
- [ ] GET /metrics → 200 OK (Prometheus metrics)

### Features Principales
- [ ] Chat fonctionne (POST /chat ou /test)
- [ ] Upload fonctionne (POST /upload)
- [ ] Auth fonctionne (POST /auth/register)
- [ ] Admin accessible (GET /admin/roles avec token)

### Monitoring
- [ ] Métriques Prometheus visibles
- [ ] Logs structurés (JSON format)
- [ ] Pas de memory leaks (docker stats)

---

## 🔄 Rollback (En Cas de Problème)

Si la mise à jour échoue, revenir à l'ancienne version :

### Option 1 : Utiliser l'Ancien main.py

```bash
# 1. Restaurer l'ancien main.py
cd app
mv main.py main.py.modular_backup
mv main.py.monolithic_backup main.py

# 2. Rebuild
docker compose build app
docker compose up -d app
```

### Option 2 : Utiliser une Image Sauvegardée

```bash
# 1. Tag l'image actuelle avant upgrade
docker tag my-ia-app:latest my-ia-app:v0.9-monolithic

# 2. En cas de problème, revenir
docker compose stop app
docker tag my-ia-app:v0.9-monolithic my-ia-app:latest
docker compose up -d app
```

### Option 3 : Restore depuis Git

```bash
# 1. Vérifier l'état actuel
git status

# 2. Annuler les modifications
git checkout app/main.py
git checkout app/Dockerfile

# 3. Rebuild
docker compose build app
docker compose up -d app
```

---

## 📈 Performance et Optimisation

### Cache Docker

Pour accélérer les builds futurs :

```dockerfile
# Dans Dockerfile, ordre optimisé :
COPY requirements.txt ./          # Change rarement
RUN pip install -r requirements.txt  # Layer mis en cache
COPY . /code/app/                 # Change souvent
```

### Multi-Stage Build (Optionnel)

Pour réduire la taille de l'image :

```dockerfile
# Stage 1: Builder
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . /code/app/
CMD ["uvicorn", "app.main:app", ...]
```

### Healthcheck Optimisé

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:8080/health || exit 1
```

---

## 📝 Changelog Docker

### v1.0.0 - 22 décembre 2024

**✨ Features**
- Python 3.12 (upgrade depuis 3.11)
- Architecture modulaire `app.main:app`
- PYTHONPATH configuré pour imports absolus
- requirements-docker.txt fusionné

**🐛 Fixes**
- Import paths corrigés (app.xxx)
- WORKDIR optimisé (/code au lieu de /app)
- Hot reload préservé avec volume mount

**🔧 Improvements**
- Build time réduit (cache Docker)
- Image size optimisée
- Healthcheck amélioré

---

## 🎯 Prochaines Étapes

1. **Tests automatisés** : Ajouter tests dans CI/CD
2. **Multi-stage build** : Réduire taille image
3. **Docker Compose v2** : Utiliser profiles pour dev/prod
4. **Kubernetes** : Préparer manifests K8s (optionnel)

---

## 📞 Support

Si vous rencontrez des problèmes :

1. Consulter ce fichier (DOCKER_UPDATE_PROCESS.md)
2. Vérifier les logs : `docker compose logs app`
3. Consulter MIGRATION_SUCCESS.md
4. Tester en environnement virtuel d'abord

---

**Processus validé** : 22 décembre 2024
**Testé sur** : macOS 12.7.6, Docker 24.0+
**Statut** : ✅ Production Ready
