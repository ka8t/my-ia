# Documentation API MY-IA

Documentation complète des endpoints de l'API FastAPI de MY-IA.

## Base URL

```
http://localhost:8080
```

## Authentification

Toutes les requêtes aux endpoints protégés nécessitent une clé API dans le header :

```http
X-API-Key: votre-cle-api
```

Configuration dans `.env` :
```env
API_KEY=change-me-in-production
```

## Endpoints

### GET /

Endpoint racine - Informations sur l'API.

**Requête** :
```bash
curl http://localhost:8080/
```

**Réponse** :
```json
{
  "name": "MY-IA API",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "health": "/health",
  "metrics": "/metrics"
}
```

---

### GET /health

Health check de tous les services (Ollama, ChromaDB).

**Requête** :
```bash
curl http://localhost:8080/health
```

**Réponse** :
```json
{
  "status": "healthy",
  "ollama": true,
  "chroma": true,
  "model": "llama3.2:1b"
}
```

**Status** :
- `healthy` : Tous les services fonctionnent
- `degraded` : Au moins un service est hors ligne

---

### GET /metrics

Métriques Prometheus pour le monitoring.

**Requête** :
```bash
curl http://localhost:8080/metrics
```

**Réponse** : Format Prometheus (plain text)

**Métriques disponibles** :
- `myia_requests_total` : Nombre total de requêtes par endpoint
- `myia_request_duration_seconds` : Latence des requêtes

---

### POST /chat

ChatBot conversationnel avec RAG (Retrieval-Augmented Generation).

**Rate Limit** : 30 requêtes/minute

**Requête** :
```bash
curl -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{
    "query": "Comment installer MY-IA?",
    "session_id": "user-123"
  }'
```

**Paramètres** :
- `query` (string, requis) : Question de l'utilisateur
- `session_id` (string, optionnel) : ID de session pour le contexte

**Réponse** :
```json
{
  "response": "Pour installer MY-IA, suivez ces étapes...",
  "sources": [
    {"source": "exemple.md"},
    {"source": "exemple.md"},
    {"source": "exemple.md"}
  ],
  "session_id": "user-123"
}
```

**Comportement** :
1. Recherche de contexte dans ChromaDB via embeddings
2. Récupération des top-k documents pertinents (défaut: 4)
3. Génération de réponse avec le LLM + contexte
4. Retour de la réponse avec les sources utilisées

**Temps de réponse** :
- CPU : 2-5 minutes
- GPU : 10-30 secondes

---

### POST /assistant

Assistant orienté tâches avec RAG.

**Rate Limit** : 30 requêtes/minute

**Requête** :
```bash
curl -X POST http://localhost:8080/assistant \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{
    "query": "Crée un workflow N8N pour automatiser les emails",
    "session_id": "user-123"
  }'
```

**Paramètres** :
- `query` (string, requis) : Instruction/tâche pour l'assistant
- `session_id` (string, optionnel) : ID de session

**Réponse** :
```json
{
  "response": "Voici un workflow N8N pour automatiser les emails...",
  "sources": [
    {"source": "n8n-docs.md"},
    {"source": "automation-guide.md"}
  ],
  "session_id": "user-123"
}
```

**Différence avec /chat** :
- Utilise `assistant_system.md` comme prompt système
- Orienté vers l'exécution de tâches et l'action
- Ton plus direct et technique

---

### POST /chat/stream

ChatBot avec streaming des réponses (Server-Sent Events).

**Rate Limit** : 20 requêtes/minute

**Requête** :
```bash
curl -X POST http://localhost:8080/chat/stream \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{
    "query": "Explique le RAG",
    "session_id": "user-123"
  }' \
  --no-buffer
```

**Réponse** : Stream NDJSON (Newline Delimited JSON)

```json
{"response": "Le"}
{"response": " RAG"}
{"response": " (Retrieval"}
{"response": "-Augmented"}
...
{"done": true}
```

**Usage avec JavaScript** :
```javascript
const response = await fetch('http://localhost:8080/chat/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'change-me-in-production'
  },
  body: JSON.stringify({ query: 'Bonjour' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.trim()) {
      const data = JSON.parse(line);
      console.log(data.response);
    }
  }
}
```

---

### POST /test

Endpoint de test sans RAG - directement avec le LLM.

**Rate Limit** : 30 requêtes/minute

**Requête** :
```bash
curl -X POST http://localhost:8080/test \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{
    "query": "Bonjour, qui es-tu?"
  }'
```

**Réponse** :
```json
{
  "response": "Bonjour ! Je suis un assistant IA...",
  "sources": null,
  "session_id": null
}
```

**Usage** :
- Tester la connexion à Ollama
- Benchmark de performance (sans overhead du RAG)
- Debugging

---

## Codes d'Erreur

### 401 Unauthorized
```json
{
  "detail": "Invalid API key"
}
```

**Cause** : Clé API manquante ou incorrecte.

**Solution** : Vérifier le header `X-API-Key`.

---

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded"
}
```

**Cause** : Trop de requêtes (dépassement du rate limit).

**Solution** : Attendre avant de réessayer.

---

### 500 Internal Server Error
```json
{
  "detail": "Error generating response: TimeoutError"
}
```

**Causes possibles** :
- Ollama non démarré
- Modèle non téléchargé
- Timeout dépassé (>600s)

**Solution** : Consulter [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Exemples d'Intégration

### Python

```python
import requests

API_URL = "http://localhost:8080"
API_KEY = "change-me-in-production"

def chat(query: str) -> dict:
    response = requests.post(
        f"{API_URL}/chat",
        json={"query": query},
        headers={"X-API-Key": API_KEY}
    )
    response.raise_for_status()
    return response.json()

result = chat("Comment installer MY-IA?")
print(result["response"])
print("Sources:", result["sources"])
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8080';
const API_KEY = 'change-me-in-production';

async function chat(query) {
  const response = await axios.post(
    `${API_URL}/chat`,
    { query },
    { headers: { 'X-API-Key': API_KEY } }
  );
  return response.data;
}

chat('Comment installer MY-IA?').then(result => {
  console.log(result.response);
  console.log('Sources:', result.sources);
});
```

### cURL

```bash
# Variable pour la clé API
export API_KEY="change-me-in-production"

# Fonction helper
chat() {
  curl -X POST http://localhost:8080/chat \
    -H 'Content-Type: application/json' \
    -H "X-API-Key: $API_KEY" \
    -d "{\"query\":\"$1\"}"
}

# Usage
chat "Comment installer MY-IA?"
```

---

## Configuration Avancée

### Modifier le TOP_K (nombre de documents RAG)

Dans `docker-compose.yml` :

```yaml
app:
  environment:
    - TOP_K=8  # Défaut: 4
```

Plus de contexte = réponses plus précises mais plus lentes.

### Augmenter les Timeouts

Dans `app/main.py` :

```python
async with httpx.AsyncClient(timeout=900.0) as client:
```

### Désactiver le Rate Limiting

Commentez dans `app/main.py` :

```python
# @limiter.limit("30/minute")
async def chat(...):
```

---

## Documentation Interactive

Pour une documentation interactive complète avec interface Swagger :

```
http://localhost:8080/docs
```

Pour la documentation ReDoc :

```
http://localhost:8080/redoc
```

---

## Support

- [Guide d'Installation](INSTALLATION.md)
- [Dépannage](TROUBLESHOOTING.md)
- [Issues GitHub](https://github.com/votre-repo/my-ia/issues)
