# Workflow de Développement - MY-IA

## 🚀 Démarrage rapide

### Premier lancement (avec build)
```bash
# Build des images (5-10 min la première fois)
docker compose build

# Démarrer tous les services
docker compose up -d

# Vérifier que tout fonctionne
docker compose ps
docker compose logs -f app
```

### Accès aux services
- **Frontend** : http://localhost:3000
- **API** : http://localhost:8080/docs
- **N8N** : http://localhost:5678
- **ChromaDB** : http://localhost:8000

---

## ⚡ Développement avec Hot Reload (PAS DE REBUILD)

### Configuration actuelle
✅ **Hot reload activé** : Les changements de code Python sont détectés automatiquement !

```yaml
# docker-compose.yml
volumes:
  - ./app:/app  # Code monté en volume

# Dockerfile
CMD ["uvicorn", "--reload"]  # Auto-redémarrage
```

### Workflow de développement

1. **Modifier le code Python**
   ```bash
   # Éditez n'importe quel fichier dans app/
   nano app/main.py
   nano app/ingest_v2.py
   ```

2. **Les changements sont automatiques !**
   ```bash
   # Regardez les logs pour voir le reload
   docker compose logs -f app

   # Vous verrez :
   # INFO: Will watch for changes in these directories: ['/app']
   # WARNING: Detected file change in '/app/main.py'. Reloading...
   # INFO: Application startup complete.
   ```

3. **Tester immédiatement**
   - Rafraîchir le frontend : http://localhost:3000
   - Tester l'API : http://localhost:8080/docs

### Temps de réponse
- **Modification code** → **Application redémarrée** : ~2-3 secondes ⚡

---

## 🔨 Quand faut-il rebuild ?

### ❌ PAS besoin de rebuild pour :
- ✅ Modifications de fichiers Python (.py)
- ✅ Modifications de prompts (.md dans app/prompts/)
- ✅ Ajout de nouveaux fichiers Python
- ✅ Modifications du frontend (HTML/CSS/JS)

### ✅ Rebuild NÉCESSAIRE pour :
- 📦 Nouvelles dépendances Python (`requirements.txt`)
- 🐳 Modifications du `Dockerfile`
- 🔧 Modifications du `docker-compose.yml`

```bash
# Rebuild seulement le service modifié
docker compose build app

# Rebuild avec cache
docker compose build app

# Rebuild from scratch (si problèmes)
docker compose build --no-cache app

# Redémarrer après rebuild
docker compose up -d
```

---

## 🛠️ Commandes utiles

### Logs et debugging
```bash
# Logs en temps réel de l'app
docker compose logs -f app

# Logs de tous les services
docker compose logs -f

# Logs des dernières 100 lignes
docker compose logs --tail=100 app

# Filtrer les erreurs
docker compose logs app | grep ERROR
```

### Restart rapide
```bash
# Redémarrer uniquement l'app (2 secondes)
docker compose restart app

# Redémarrer tous les services
docker compose restart

# Forcer le rebuild et redémarrer
docker compose up -d --build app
```

### Shell dans le container
```bash
# Accéder au shell du container
docker compose exec app bash

# Lancer Python interactif
docker compose exec app python

# Tester ingest_v2 manuellement
docker compose exec app python ingest_v2.py
```

### Nettoyage
```bash
# Arrêter les services
docker compose down

# Arrêter et supprimer les volumes
docker compose down -v

# Supprimer les images
docker compose down --rmi all
```

---

## 📝 Développement frontend

### Hot reload frontend
Le frontend (Nginx) ne supporte PAS le hot reload par défaut.

**Option 1 : Serveur de dev local**
```bash
cd frontend
python -m http.server 3001
# Accéder à http://localhost:3001
```

**Option 2 : Rebuild rapide**
```bash
# Le frontend build est très rapide (~5 secondes)
docker compose build frontend
docker compose up -d frontend
```

---

## 🧪 Tests et validation

### Tester l'endpoint d'upload v2
```bash
# Préparer un fichier test
echo "Test document" > /tmp/test.txt

# Upload via curl
curl -X POST http://localhost:8080/upload/v2 \
  -H "X-API-Key: change-me-in-production" \
  -F "file=@/tmp/test.txt"
```

### Tester le chat
```bash
curl -X POST http://localhost:8080/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-in-production" \
  -d '{"query": "test", "session_id": "123"}'
```

### Health check
```bash
curl http://localhost:8080/health
```

---

## 🐛 Troubleshooting

### L'app ne redémarre pas après modification
```bash
# Vérifier que le volume est bien monté
docker compose exec app ls -la /app

# Vérifier les logs
docker compose logs -f app

# Redémarrer manuellement
docker compose restart app
```

### Erreurs d'import après ajout de dépendance
```bash
# Rebuild nécessaire !
docker compose down
docker compose build app
docker compose up -d
```

### Port déjà utilisé
```bash
# Trouver le processus
lsof -i :8080
lsof -i :3000

# Tuer le processus
kill -9 <PID>
```

### Problèmes de permissions
```bash
# Voir les permissions
docker compose exec app ls -la /app

# Fixer les permissions (si nécessaire)
sudo chown -R $USER:$USER app/
```

---

## 📚 Structure des fichiers montés

```
Hôte                    → Container
./app/                  → /app/              (CODE - Hot reload ✅)
./datasets/             → /app/datasets      (DATA)
./frontend/             → /usr/share/nginx/  (STATIC)
chroma-data volume      → /chroma/chroma     (PERSISTED)
```

---

## 🎯 Workflow recommandé

### Pour une nouvelle feature
1. ✏️ Modifier le code dans `app/`
2. 👀 Surveiller les logs : `docker compose logs -f app`
3. ⚡ Tester (reload auto en 2-3s)
4. 🔄 Itérer jusqu'à satisfaction
5. 📝 Commit les changements

### Pour debugging
1. 🔍 Ajouter des `logger.info()` dans le code
2. 👀 `docker compose logs -f app`
3. 🧪 Tester la requête
4. 📊 Voir les logs en temps réel

### Pour tester de nouvelles dépendances
1. 📦 Ajouter dans `requirements.txt`
2. 🔨 `docker compose build app`
3. 🚀 `docker compose up -d`
4. ✅ Vérifier : `docker compose exec app pip list`

---

## 💡 Astuces Pro

### Alias utiles (ajoutez dans ~/.bashrc ou ~/.zshrc)
```bash
alias dcup='docker compose up -d'
alias dcdown='docker compose down'
alias dclogs='docker compose logs -f'
alias dcrestart='docker compose restart app'
alias dcexec='docker compose exec app'
```

### Watch mode pour les logs
```bash
# Terminal 1 : logs
docker compose logs -f app

# Terminal 2 : développement
nano app/main.py
```

### Validation rapide après changement
```bash
# Script one-liner
docker compose restart app && \
  sleep 3 && \
  curl -s http://localhost:8080/health | jq
```

---

**Dernière mise à jour** : Décembre 2025
**Maintenu par** : MY-IA Team
