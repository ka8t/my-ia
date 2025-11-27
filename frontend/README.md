# MY-IA - Interface de Chat Web

Interface web moderne pour MY-IA, inspirée de ChatGPT/Claude, construite avec HTML/CSS/JavaScript vanilla.

## Fonctionnalités

### Interface utilisateur
- Design responsive moderne
- Mode clair/sombre
- Sidebar avec liste des conversations
- Zone de chat centrale avec messages
- Input avec auto-resize
- Support markdown avec syntax highlighting

### Gestion des conversations
- Créer nouvelle conversation
- Sauvegarder automatiquement les conversations (localStorage)
- Renommer les conversations automatiquement (basé sur le premier message)
- Supprimer les conversations
- Historique persistant

### Chat
- Streaming des réponses en temps réel
- Support markdown complet
- Syntax highlighting pour le code
- Copier le texte d'un message
- Affichage des sources RAG (optionnel)
- Bouton stop pour annuler la génération
- Compteur de caractères
- Suggestions de questions

### Modes
- **ChatBot** : Mode conversationnel (endpoint `/chat`)
- **Assistant** : Mode orienté tâches (endpoint `/assistant`)
- Toggle simple entre les deux modes

### Paramètres configurables
- URL de l'API
- Clé API
- Nombre de sources (TOP_K)
- Afficher/masquer les sources
- Thème (clair/sombre)

## Technologies

- **HTML5** : Structure
- **CSS3** : Styles avec variables CSS pour le theming
- **JavaScript** : Logique de l'application
- **Marked.js** : Parsing du markdown
- **Highlight.js** : Syntax highlighting du code
- **Nginx** : Serveur web

## Architecture

```
frontend/
├── index.html          # Page principale
├── css/
│   └── styles.css      # Styles CSS avec thème dark/light
├── js/
│   └── app.js          # Logique JavaScript
├── Dockerfile          # Image Docker avec Nginx
├── nginx.conf          # Configuration Nginx
└── README.md           # Cette documentation
```

## Utilisation

### Avec Docker (recommandé)

```bash
# Démarrer tous les services (depuis la racine du projet)
docker compose up -d

# L'interface sera accessible sur http://localhost:3000
```

### En local (développement)

```bash
# Servir les fichiers avec n'importe quel serveur HTTP
cd frontend
python3 -m http.server 3000

# Ou avec Node.js
npx http-server -p 3000

# Accéder à http://localhost:3000
```

## Configuration

Au premier lancement, cliquez sur "Paramètres" pour configurer :

1. **URL de l'API** : `http://localhost:8080` (par défaut)
2. **Clé API** : `change-me-in-production` (par défaut)
3. **TOP_K** : Nombre de documents à récupérer (4 par défaut)
4. **Afficher sources** : Cocher pour voir les sources RAG

Les paramètres sont sauvegardés dans le localStorage du navigateur.

## Raccourcis clavier

- `Enter` : Envoyer le message
- `Shift + Enter` : Nouvelle ligne dans le message

## Fonctionnalités à venir

- [ ] Régénération de réponse
- [ ] Éditer et renvoyer un message
- [ ] Export des conversations (JSON, Markdown, PDF)
- [ ] Upload de fichiers pour ingestion
- [ ] Recherche dans l'historique
- [ ] Partage de conversations
- [ ] Raccourcis clavier personnalisables
- [ ] Avatars personnalisés
- [ ] Synthèse vocale (Text-to-Speech)
- [ ] Reconnaissance vocale (Speech-to-Text)

## Compatibilité

- Chrome/Edge : ✅
- Firefox : ✅
- Safari : ✅
- Mobile : ✅ (responsive)

## Dépannage

### L'interface ne se connecte pas à l'API

1. Vérifier que l'API est bien accessible : `curl http://localhost:8080/health`
2. Vérifier les paramètres (icône engrenage)
3. Ouvrir la console du navigateur (F12) pour voir les erreurs

### Les messages ne s'affichent pas

1. Vérifier la console pour les erreurs JavaScript
2. Effacer le cache du navigateur
3. Effacer le localStorage : `localStorage.clear()` dans la console

### Le streaming ne fonctionne pas

1. Vérifier que l'endpoint `/chat/stream` fonctionne
2. Tester avec curl :
```bash
curl -N -X POST http://localhost:8080/chat/stream \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{"query":"Test"}'
```

## Contributions

Les contributions sont les bienvenues ! Voici quelques idées :
- Améliorer le design
- Ajouter des animations
- Optimiser les performances
- Ajouter des tests
- Traduire en d'autres langues

## Licence

MIT
