#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh <backup_directory>"
    echo "Example: ./restore.sh ./backups/20240115-143022"
    exit 1
fi

BACKUP_DIR="$1"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "🔄 Restoration depuis: $BACKUP_DIR"
echo "⚠️  Cette opération va écraser les données actuelles!"
read -p "Continuer? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restauration annulée."
    exit 0
fi

# Arrêter les services
echo "⏸️  Arrêt des services..."
docker compose down

# Restaurer ChromaDB
if [ -f "$BACKUP_DIR/chroma.tar.gz" ]; then
    echo "📦 Restauration ChromaDB..."
    docker compose up -d chroma
    sleep 5
    docker compose cp "$BACKUP_DIR/chroma.tar.gz" chroma:/tmp/
    docker compose exec chroma tar -xzf /tmp/chroma.tar.gz -C /
    docker compose restart chroma
fi

# Restaurer Ollama
if [ -f "$BACKUP_DIR/ollama.tar.gz" ]; then
    echo "📦 Restauration Ollama..."
    docker compose up -d ollama
    sleep 5
    docker compose cp "$BACKUP_DIR/ollama.tar.gz" ollama:/tmp/
    docker compose exec ollama tar -xzf /tmp/ollama.tar.gz -C /
    docker compose restart ollama
fi

# Restaurer PostgreSQL
if [ -f "$BACKUP_DIR/postgres-n8n.sql.gz" ]; then
    echo "📦 Restauration PostgreSQL..."
    docker compose up -d postgres
    sleep 10
    gunzip -c "$BACKUP_DIR/postgres-n8n.sql.gz" | docker compose exec -T postgres psql -U n8n n8n
fi

# Restaurer N8N
if [ -f "$BACKUP_DIR/n8n.tar.gz" ]; then
    echo "📦 Restauration N8N..."
    docker compose up -d n8n
    sleep 5
    docker compose cp "$BACKUP_DIR/n8n.tar.gz" n8n:/tmp/
    docker compose exec n8n tar -xzf /tmp/n8n.tar.gz -C /
    docker compose restart n8n
fi

# Restaurer datasets
if [ -f "$BACKUP_DIR/datasets.tar.gz" ]; then
    echo "📦 Restauration datasets..."
    tar -xzf "$BACKUP_DIR/datasets.tar.gz"
fi

# Redémarrer tous les services
echo "🔄 Redémarrage de tous les services..."
docker compose up -d

echo ""
echo "✅ Restauration terminée!"
echo "⏳ Attendez 30 secondes que les services démarrent..."
sleep 30

# Vérifier
./scripts/test.sh
