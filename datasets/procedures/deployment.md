# Procédure de Déploiement en Production

## Pré-requis
- Docker et docker-compose installés
- Accès SSH au serveur de production
- Variables d'environnement configurées
- Certificats SSL pour N8N (recommandé en production)

## Étapes de déploiement

### 1. Préparation
```bash
# Se connecter au serveur
ssh user@production-server

# Naviguer vers le répertoire du projet
cd /opt/my-ia

# Faire un backup
./scripts/backup.sh
```

### 2. Mise à jour du code
```bash
# Récupérer les dernières modifications
git pull origin main

# Vérifier la version
git log -1
```

### 3. Configuration sécurité
```bash
# Modifier les mots de passe par défaut dans docker-compose.yml
# - POSTGRES_PASSWORD
# - N8N_BASIC_AUTH_PASSWORD
# - API_KEY
```

### 4. Déploiement
```bash
# Reconstruire les images
docker compose build

# Démarrer les services
docker compose up -d

# Vérifier les logs
docker compose logs -f
```

### 5. Validation
```bash
# Tester le health check de l'API
curl http://localhost:8080/health

# Vérifier N8N
curl http://localhost:5678

# Tester une requête à l'IA
curl -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{"query":"test de déploiement"}'
```

## Services déployés
- **API FastAPI** : Port 8080 - Interface IA avec RAG
- **N8N** : Port 5678 - Automatisation de workflows
- **Ollama** : Port 11434 - Serveur LLM
- **ChromaDB** : Port 8000 - Base de données vectorielle
- **PostgreSQL** : Port 5432 - Base de données N8N

## Rollback en cas de problème
```bash
# Arrêter les services
docker compose down

# Revenir à la version précédente
git checkout <previous-tag>

# Redéployer
docker compose up -d
```

## Points de vigilance
- Vérifier l'espace disque avant le déploiement (20 GB minimum)
- S'assurer que les modèles Ollama sont téléchargés
- Monitorer les métriques après le déploiement
- Vérifier que tous les services sont "healthy"
- Changer tous les mots de passe par défaut en production
