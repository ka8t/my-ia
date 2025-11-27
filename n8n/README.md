# Workflows N8N

Ce dossier contient des exemples de workflows N8N pour automatiser des tâches avec l'IA.

## Configuration

1. Accéder à N8N : http://localhost:5678
2. Se connecter avec les identifiants configurés dans docker-compose.yml
3. Importer les workflows depuis ce dossier

## Exemples de workflows

### 1. AI Document Processor (example-ai-processor.json)
Webhook qui reçoit une question et retourne une réponse de l'IA.

**Usage :**
```bash
curl -X POST http://localhost:5678/webhook/ai-process \
  -H 'Content-Type: application/json' \
  -d '{"question":"Comment déployer l'app?"}'
```

### 2. Créer vos propres workflows

Idées de workflows :
- **Email Auto-responder** : Répondre automatiquement aux emails avec l'IA
- **Document Summarizer** : Résumer des documents PDF/Word automatiquement
- **Slack Bot** : Bot Slack qui répond aux questions de l'équipe
- **Daily Report** : Générer un rapport quotidien basé sur vos données
- **Customer Support** : Traiter automatiquement les tickets de support
- **Content Generator** : Générer du contenu pour les réseaux sociaux

## Endpoints de l'API disponibles

- `POST /chat` - ChatBot conversationnel
- `POST /assistant` - Assistant orienté tâches
- `POST /chat/stream` - Streaming des réponses
- `GET /health` - Vérifier l'état de l'API

## Exemple de node HTTP Request dans N8N

```json
{
  "method": "POST",
  "url": "http://app:8080/chat",
  "body": {
    "query": "{{$json.question}}",
    "session_id": "n8n-workflow"
  }
}
```

## Bonnes pratiques

1. **Gestion des sessions** : Utilisez des session_id uniques pour chaque conversation
2. **Timeout** : Configurez un timeout de 120s minimum pour les requêtes IA
3. **Error handling** : Ajoutez des nodes de gestion d'erreur dans vos workflows
4. **Logging** : Activez les logs N8N pour déboguer vos workflows

## Ressources

- [Documentation N8N](https://docs.n8n.io/)
- [Community Workflows](https://n8n.io/workflows/)
- [API Documentation](http://localhost:8080/docs)
