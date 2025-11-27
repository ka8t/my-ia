#!/bin/bash
set -e

BACKUP_DIR="./backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "🔄 Backup en cours..."

# Backup ChromaDB
echo "📦 Backup ChromaDB..."
docker compose exec -T chroma tar -czf - /chroma/index > "$BACKUP_DIR/chroma.tar.gz"

# Backup Ollama models
echo "📦 Backup Ollama models..."
docker compose exec -T ollama tar -czf - /root/.ollama > "$BACKUP_DIR/ollama.tar.gz"

# Backup PostgreSQL (N8N)
echo "📦 Backup PostgreSQL (N8N)..."
docker compose exec -T postgres pg_dump -U n8n n8n | gzip > "$BACKUP_DIR/postgres-n8n.sql.gz"

# Backup N8N data
echo "📦 Backup N8N data..."
docker compose exec -T n8n tar -czf - /home/node/.n8n > "$BACKUP_DIR/n8n.tar.gz"

# Backup datasets
echo "📦 Backup datasets..."
tar -czf "$BACKUP_DIR/datasets.tar.gz" ./datasets

# Backup workflows
echo "📦 Backup N8N workflows..."
tar -czf "$BACKUP_DIR/n8n-workflows.tar.gz" ./n8n/workflows

# Backup config
echo "📦 Backup configuration..."
cp docker-compose.yml "$BACKUP_DIR/"
cp -r app "$BACKUP_DIR/" 2>/dev/null || true

echo "✅ Backup completed: $BACKUP_DIR"
echo "📊 Taille du backup:"
du -sh "$BACKUP_DIR"

# Nettoyer les backups > 30 jours
echo "🧹 Nettoyage des anciens backups..."
find ./backups -type d -mtime +30 -exec rm -rf {} + 2>/dev/null || true

echo "✅ Terminé!"
