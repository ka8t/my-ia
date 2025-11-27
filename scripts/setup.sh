#!/bin/bash
set -e

echo "🚀 Configuration initiale du projet my-ia"
echo "================================================"

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Installez-le d'abord."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ docker compose n'est pas installé. Installez-le d'abord."
    exit 1
fi

echo "✅ Docker est installé"

# Démarrer les services
echo "📦 Démarrage des services..."
docker compose up -d

echo "⏳ Attente du démarrage de ChromaDB..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/heartbeat > /dev/null 2>&1; then
        echo "✅ ChromaDB est prêt!"
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

echo "⏳ Attente du démarrage de PostgreSQL..."
for i in {1..20}; do
    if docker compose exec -T postgres pg_isready -U n8n > /dev/null 2>&1; then
        echo "✅ PostgreSQL est prêt!"
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

echo "⏳ Attente du démarrage de l'API..."
for i in {1..30}; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "✅ API est prête!"
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

# Télécharger les modèles
echo "📥 Téléchargement des modèles Ollama..."
docker exec $(docker ps -qf name=ollama) ollama pull llama3.1:8b || echo "⚠️  Erreur téléchargement modèle principal"
docker exec $(docker ps -qf name=ollama) ollama pull nomic-embed-text || echo "⚠️  Erreur téléchargement modèle embeddings"

# Ingestion des données
echo "📊 Ingestion des données d'exemple..."
docker compose exec app python ingest.py || echo "⚠️  Erreur lors de l'ingestion"

# Test de santé
echo "🏥 Vérification de la santé du système..."
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ API fonctionne correctement!"
else
    echo "⚠️  L'API ne répond pas correctement, vérifiez les logs:"
    echo "   docker compose logs app"
fi

echo ""
echo "✅ Configuration terminée!"
echo ""
echo "📝 Services disponibles:"
echo "  🤖 API IA:        http://localhost:8080"
echo "  🔄 N8N:           http://localhost:5678 (admin / change-me-in-production)"
echo "  📊 Ollama:        http://localhost:11434"
echo "  🗄️  ChromaDB:      http://localhost:8000"
echo "  🐘 PostgreSQL:    localhost:5432"
echo ""
echo "📚 Prochaines étapes:"
echo "  1. Ajouter vos propres données dans ./datasets/"
echo "  2. Relancer l'ingestion: docker compose exec app python ingest.py"
echo "  3. Créer des workflows dans N8N"
echo "  4. Consulter ./n8n/README.md pour des exemples"
echo ""
echo "🔐 IMPORTANT: Changez les mots de passe par défaut en production!"
echo ""
echo "🐛 En cas de problème:"
echo "  - Logs: docker compose logs -f"
echo "  - Status: docker compose ps"
echo "  - Tests: ./scripts/test.sh"
