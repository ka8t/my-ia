# Guide de Dépannage MY-IA

Solutions aux problèmes courants rencontrés avec MY-IA.

## Table des Matières

- [Problèmes de Démarrage](#problèmes-de-démarrage)
- [Problèmes de Performance](#problèmes-de-performance)
- [Erreurs API](#erreurs-api)
- [Problèmes Docker](#problèmes-docker)
- [Problèmes ChromaDB](#problèmes-chromadb)
- [Problèmes Ollama](#problèmes-ollama)

---

## Problèmes de Démarrage

### Les conteneurs ne démarrent pas

**Symptômes** :
```bash
docker compose ps
# Certains conteneurs sont "Exit" ou "Restarting"
```

**Solutions** :

1. **Vérifier les logs** :
```bash
docker compose logs
```

2. **Ports déjà utilisés** :
```bash
# Vérifier si les ports sont occupés
lsof -i :8080  # FastAPI
lsof -i :8000  # ChromaDB
lsof -i :11434 # Ollama
lsof -i :5678  # N8N
```

Solution : Arrêter le processus ou changer le port dans `docker-compose.yml`.

3. **Manque de ressources** :
```bash
# Vérifier l'espace disque
df -h

# Vérifier la RAM
free -h  # Linux
vm_stat  # Mac
```

Solution : Libérer de l'espace ou fermer d'autres applications.

---

### ChromaDB ne démarre pas

**Symptômes** :
```
Error: Cannot connect to ChromaDB
```

**Solutions** :

1. **Vérifier les permissions du volume** :
```bash
ls -la ./chroma-data
# Le dossier doit être accessible en écriture
```

2. **Recréer le volume** :
```bash
docker compose down
docker volume rm my-ia_chroma-data
docker compose up -d
```

3. **Vérifier les logs** :
```bash
docker logs my-ia-chroma
```

---

## Problèmes de Performance

### Réponses très lentes (>5 minutes)

**Causes** :
- Modèle trop gros pour votre CPU
- Pas assez de RAM
- Swap intensif

**Solutions** :

1. **Utiliser un modèle plus petit** :

Dans `docker-compose.yml` :
```yaml
app:
  environment:
    - MODEL_NAME=llama3.2:1b  # Au lieu de mistral:7b
```

```bash
docker exec my-ia-ollama ollama pull llama3.2:1b
docker compose restart app
```

2. **Augmenter la RAM Docker** (Mac/Windows) :

Docker Desktop → Settings → Resources → Memory : 8 GB minimum

3. **Activer le GPU** (si disponible) :

Voir [INSTALLATION.md - Activer le GPU](INSTALLATION.md#activer-le-gpu)

---

### Timeouts fréquents

**Symptômes** :
```json
{
  "detail": "Error generating response: TimeoutError"
}
```

**Solution** : Les timeouts sont déjà à 600s (10 min). Si encore insuffisant :

Éditez `app/main.py` :
```python
async with httpx.AsyncClient(timeout=1200.0) as client:  # 20 minutes
```

Puis :
```bash
docker compose build app
docker compose up -d app
```

---

## Erreurs API

### 401 Unauthorized

**Symptômes** :
```json
{
  "detail": "Invalid API key"
}
```

**Solution** :

Vérifier la clé API :
```bash
# Voir la clé dans docker-compose.yml
grep API_KEY docker-compose.yml

# Tester avec la bonne clé
curl -X POST http://localhost:8080/chat \
  -H 'X-API-Key: change-me-in-production' \
  -d '{"query":"test"}'
```

---

### 500 Internal Server Error

**Symptômes** :
```json
{
  "detail": "Error generating embeddings"
}
```

**Causes possibles** :

1. **Ollama n'est pas démarré** :
```bash
docker ps | grep ollama
# Doit être "Up"
```

Solution :
```bash
docker start my-ia-ollama
```

2. **Modèle non téléchargé** :
```bash
docker exec my-ia-ollama ollama list
# Vérifier que nomic-embed-text est présent
```

Solution :
```bash
docker exec my-ia-ollama ollama pull nomic-embed-text
```

3. **ChromaDB inaccessible** :
```bash
curl http://localhost:8000/api/v1/heartbeat
# Doit retourner 200
```

Solution :
```bash
docker restart my-ia-chroma
```

---

### 429 Too Many Requests

**Symptômes** :
```json
{
  "detail": "Rate limit exceeded"
}
```

**Solution temporaire** :

Attendre 1 minute avant de réessayer.

**Solution permanente** :

Augmenter le rate limit dans `app/main.py` :
```python
@limiter.limit("60/minute")  # Au lieu de 30/minute
async def chat(...):
```

---

## Problèmes Docker

### "Cannot connect to Docker daemon"

**Solution** :

```bash
# Linux
sudo systemctl start docker

# Mac/Windows
# Ouvrir Docker Desktop
```

---

### Volumes Docker pleins

**Symptômes** :
```
no space left on device
```

**Solution** :

```bash
# Nettoyer les volumes inutilisés
docker system prune -a --volumes

# ⚠️ ATTENTION: Cela supprime TOUS les volumes non utilisés
```

---

### Conteneur redémarre en boucle

**Diagnostic** :
```bash
docker logs my-ia-app --tail 50
```

**Solutions courantes** :

1. **Erreur Python** :
```bash
# Rebuild l'image
docker compose build app --no-cache
docker compose up -d app
```

2. **Port conflit** :
Changer le port dans `docker-compose.yml`.

---

## Problèmes ChromaDB

### Collection not found

**Symptômes** :
```
Collection 'knowledge_base' not found
```

**Solution** :

Réindexer les données :
```bash
docker compose exec app python ingest.py
```

---

### Pas de résultats dans les recherches

**Symptômes** :
Les requêtes ne retournent aucun contexte (sources vides).

**Solutions** :

1. **Vérifier le nombre de documents** :
```bash
docker compose exec app python -c "
import chromadb
client = chromadb.PersistentClient(path='/chroma/chroma')
collection = client.get_collection('knowledge_base')
print(f'Documents: {collection.count()}')
"
```

Si 0 documents → Réindexer :
```bash
docker compose exec app python ingest.py
```

2. **Vérifier les données sources** :
```bash
ls -lh datasets/
# Doit contenir des fichiers .md, .txt ou .jsonl
```

3. **Problème d'embeddings** :

Vérifier que `nomic-embed-text` fonctionne :
```bash
docker exec my-ia-ollama ollama run nomic-embed-text "test"
```

---

## Problèmes Ollama

### Modèle non trouvé

**Symptômes** :
```
Error: model 'mistral:7b' not found
```

**Solution** :
```bash
# Lister les modèles installés
docker exec my-ia-ollama ollama list

# Télécharger le modèle manquant
docker exec my-ia-ollama ollama pull mistral:7b
```

---

### Ollama crash / OOM

**Symptômes** :
```
Ollama killed by signal 9
```

**Cause** : Pas assez de RAM.

**Solutions** :

1. **Utiliser un modèle plus petit** :
```bash
docker exec my-ia-ollama ollama pull llama3.2:1b
```

Puis dans `docker-compose.yml` :
```yaml
- MODEL_NAME=llama3.2:1b
```

2. **Augmenter la RAM Docker** :

Docker Desktop → Resources → Memory : 12 GB+

---

## Commandes de Diagnostic Utiles

### Vérifier l'état complet

```bash
# Status de tous les services
docker compose ps

# Logs de tous les services
docker compose logs --tail=50

# Health check
curl http://localhost:8080/health
```

### Redémarrage complet

```bash
# Redémarrer tous les services
docker compose restart

# Ou arrêt/démarrage propre
docker compose down
docker compose up -d
```

### Reset complet (⚠️ perte de données)

```bash
# Arrêter et supprimer tout
docker compose down -v

# Relancer l'installation
./scripts/setup.sh
```

---

## Problèmes Connus

### Mac M1/M2 : Performance lente

**Cause** : Rosetta 2 émulation.

**Solution** : Utiliser des images ARM64 natives (déjà configuré dans docker-compose.yml).

### Windows : Chemins de volumes

**Cause** : Problèmes de permissions sous Windows.

**Solution** : Utiliser WSL2 :
```powershell
wsl --install
```

Puis lancer MY-IA dans WSL2.

---

## Obtenir de l'Aide

Si le problème persiste :

1. **Collecter les informations** :
```bash
# Versions
docker --version
docker compose version

# Logs
docker compose logs > logs.txt

# Status
docker compose ps > status.txt
```

2. **Créer une Issue GitHub** :

https://github.com/votre-repo/my-ia/issues

Inclure :
- Description du problème
- Logs (`logs.txt`)
- Votre configuration (OS, RAM, CPU)
- Étapes pour reproduire

---

## Voir Aussi

- [Guide d'Installation](INSTALLATION.md)
- [Documentation API](API.md)
- [Guide de Contribution](CONTRIBUTING.md)
