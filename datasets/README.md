# Datasets MY-IA

Ce dossier contient les données utilisées par le système RAG (Retrieval-Augmented Generation).

## Formats Supportés

MY-IA supporte 3 formats de documents :

### 1. Markdown (`.md`) - Recommandé

**Avantages** :
- Structuré et lisible
- Supporte les titres, listes, code blocks
- Facile à maintenir

**Exemple** :
```markdown
# Ma Documentation

## Installation

Pour installer...

## Configuration

Les paramètres sont...
```

### 2. Texte Brut (`.txt`)

**Avantages** :
- Simple et universel
- Pas de formatage nécessaire

**Exemple** :
```
Documentation MY-IA

Installation:
1. Télécharger...
2. Configurer...
```

### 3. JSONL (`.jsonl`) - Format Structuré

**Avantages** :
- Métadonnées riches
- Tags et catégories
- Traçabilité

**Exemple** :
```jsonl
{"text": "Pour installer MY-IA, suivez ces étapes...", "metadata": {"source": "installation.md", "tags": ["installation", "setup"]}}
{"text": "La configuration se fait via...", "metadata": {"source": "config.md", "tags": ["configuration"]}}
```

**Format** :
- 1 document JSON par ligne
- Champs requis : `text`
- Champs optionnels : `metadata` (dict), `id` (string)

---

## Structure Recommandée

```
datasets/
├── README.md                 # Ce fichier
│
├── exemple.md                # Documentation d'exemple
│
├── examples/                 # Données d'exemple
│   └── faq.jsonl            # FAQ au format JSONL
│
└── procedures/               # Procédures et guides
    └── deployment.md        # Guide de déploiement
```

**Organisation suggérée** :
- **`docs/`** : Documentation générale
- **`faq/`** : Questions fréquentes
- **`procedures/`** : Guides pas-à-pas
- **`api/`** : Documentation API
- **`examples/`** : Exemples de code

---

## Ajouter des Documents

### Méthode 1 : Fichier Markdown

```bash
# Créer votre fichier
cat > datasets/mon-guide.md << 'EOF'
# Guide MY-IA

## Introduction
Ce guide explique...

## Étapes
1. Première étape
2. Deuxième étape
EOF

# Réindexer
docker compose exec app python ingest.py
```

### Méthode 2 : Fichier JSONL

```bash
# Créer le fichier
cat > datasets/ma-faq.jsonl << 'EOF'
{"text": "Q: Comment installer MY-IA?\nR: Utilisez docker compose up -d", "metadata": {"source": "faq", "tags": ["installation"]}}
{"text": "Q: Quel modèle choisir?\nR: llama3.2:1b pour CPU, mistral:7b pour GPU", "metadata": {"source": "faq", "tags": ["modeles"]}}
EOF

# Réindexer
docker compose exec app python ingest.py
```

### Méthode 3 : Copier depuis un autre emplacement

```bash
# Copier vos fichiers
cp /chemin/vers/mes-docs/*.md datasets/

# Réindexer
docker compose exec app python ingest.py
```

---

## Bonnes Pratiques

### Contenu

✅ **À FAIRE** :
- Écrire dans un langage clair et concis
- Structurer avec des titres (#, ##, ###)
- Inclure des exemples concrets
- Mettre à jour régulièrement
- Supprimer les informations obsolètes

❌ **À ÉVITER** :
- Texte non structuré trop long
- Informations confidentielles (mots de passe, clés)
- Fichiers binaires (images, PDF) - pas encore supportés
- Duplicatas de contenu

### Taille des Documents

- **Optimal** : 200-1000 mots par document
- **Maximum** : 2000 mots (sera découpé en chunks de 900 caractères)
- **Trop court** : <50 mots (contexte insuffisant)
- **Trop long** : >5000 mots (morceler en plusieurs fichiers)

### Chunking

Le système découpe automatiquement les documents :
- **Taille chunk** : 900 caractères
- **Overlap** : 150 caractères
- **Stratégie** : Sliding window

**Exemple** :
```
Document (2000 caractères)
  ↓
Chunk 1 (0-900)
Chunk 2 (750-1650)  ← overlap de 150
Chunk 3 (1500-2400)
```

### Métadonnées JSONL

**Champs utiles** :
```jsonl
{
  "text": "Contenu du document...",
  "metadata": {
    "source": "guide-api.md",      # Source d'origine
    "title": "Guide API REST",     # Titre
    "tags": ["api", "rest"],       # Tags pour filtrage
    "author": "John Doe",          # Auteur
    "date": "2024-11-27",         # Date de création
    "version": "1.0"              # Version
  }
}
```

---

## Gestion des Données

### Vérifier les Données Indexées

```bash
# Nombre de documents
docker compose exec app python -c "
import chromadb
client = chromadb.PersistentClient(path='/chroma/chroma')
collection = client.get_collection('knowledge_base')
print(f'Documents: {collection.count()}')
"
```

### Réindexer Complètement

```bash
# Supprimer l'ancienne collection
docker compose exec app python -c "
import chromadb
client = chromadb.PersistentClient(path='/chroma/chroma')
try:
    client.delete_collection('knowledge_base')
    print('Collection supprimée')
except:
    print('Collection inexistante')
"

# Réindexer
docker compose exec app python ingest.py
```

### Backup des Données

```bash
# Backup du dossier datasets
tar -czf datasets-backup-$(date +%Y%m%d).tar.gz datasets/

# Backup du volume ChromaDB
docker run --rm -v my-ia_chroma-data:/data -v $(pwd):/backup alpine tar czf /backup/chroma-backup-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore

```bash
# Restore datasets
tar -xzf datasets-backup-20241127.tar.gz

# Restore ChromaDB
docker run --rm -v my-ia_chroma-data:/data -v $(pwd):/backup alpine tar xzf /backup/chroma-backup-20241127.tar.gz -C /data
```

---

## Exemples de Données

### FAQ

```jsonl
{"text": "Q: Quelle est la configuration minimale?\nR: 4 CPU cores, 8 GB RAM, 20 GB disque", "metadata": {"source": "faq", "tags": ["requirements"]}}
{"text": "Q: Comment changer de modèle LLM?\nR: Modifier MODEL_NAME dans docker-compose.yml", "metadata": {"source": "faq", "tags": ["configuration"]}}
```

### Documentation API

```markdown
# Endpoint /chat

## Description
ChatBot conversationnel avec RAG.

## Requête
POST /chat

## Headers
- X-API-Key: votre-cle-api
- Content-Type: application/json

## Body
{
  "query": "Ma question",
  "session_id": "user-123"
}

## Réponse
{
  "response": "La réponse...",
  "sources": [{"source": "doc.md"}]
}
```

### Guide Pas-à-Pas

```markdown
# Déployer MY-IA en Production

## Prérequis
- Serveur Linux avec Docker
- Nom de domaine
- Certificat SSL

## Étape 1 : Cloner le Projet
\`\`\`bash
git clone https://github.com/repo/my-ia
cd my-ia
\`\`\`

## Étape 2 : Configuration
Créer le fichier \`.env\`:
\`\`\`env
API_KEY=secret-production-key
MODEL_NAME=mistral:7b
\`\`\`

## Étape 3 : Lancer
\`\`\`bash
docker compose up -d
\`\`\`
```

---

## Performance et Optimisation

### Nombre de Documents

- **<100 docs** : Très rapide (<1s recherche)
- **100-1000 docs** : Rapide (1-2s recherche)
- **1000-10000 docs** : Moyen (2-5s recherche)
- **>10000 docs** : Considérer le partitionnement

### TOP_K (nombre de résultats)

Configurable dans `docker-compose.yml` :
```yaml
environment:
  - TOP_K=4  # Défaut : 4 documents
```

- **TOP_K=2** : Contexte minimal, réponses rapides
- **TOP_K=4** : Équilibré (recommandé)
- **TOP_K=8** : Contexte riche, mais plus lent

---

## Dépannage

### Aucun résultat dans les recherches

**Cause** : Pas de documents indexés.

**Solution** :
```bash
# Vérifier
ls -la datasets/

# Réindexer
docker compose exec app python ingest.py
```

### Résultats non pertinents

**Causes** :
- Documents trop génériques
- Manque de structure
- Embeddings de mauvaise qualité

**Solutions** :
- Ajouter plus de contexte spécifique
- Structurer avec des titres clairs
- Utiliser des mots-clés pertinents

---

## Voir Aussi

- [Documentation API](../docs/API.md)
- [Guide d'Installation](../docs/INSTALLATION.md)
- [Guide de Contribution](../docs/CONTRIBUTING.md)
