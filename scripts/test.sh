#!/bin/bash
set -e

echo "🧪 Tests du système"
echo "=================="

BASE_URL="http://localhost:8080"
N8N_URL="http://localhost:5678"

# Test 1: Health check API
echo "✓ Test 1: Health check API..."
curl -f "$BASE_URL/health" > /dev/null 2>&1 || {
    echo "❌ Health check API échoué"
    exit 1
}
echo "  ✅ Health check API OK"

# Test 2: Chat endpoint
echo "✓ Test 2: Chat endpoint..."
RESPONSE=$(curl -s -X POST "$BASE_URL/chat" \
  -H 'Content-Type: application/json' \
  -d '{"query":"test"}')

if [ -z "$RESPONSE" ]; then
    echo "❌ Chat endpoint ne répond pas"
    exit 1
fi
echo "  ✅ Chat endpoint OK"

# Test 3: Assistant endpoint
echo "✓ Test 3: Assistant endpoint..."
RESPONSE=$(curl -s -X POST "$BASE_URL/assistant" \
  -H 'Content-Type: application/json' \
  -d '{"query":"test"}')

if [ -z "$RESPONSE" ]; then
    echo "❌ Assistant endpoint ne répond pas"
    exit 1
fi
echo "  ✅ Assistant endpoint OK"

# Test 4: Metrics endpoint
echo "✓ Test 4: Metrics endpoint..."
curl -f "$BASE_URL/metrics" > /dev/null 2>&1 || {
    echo "❌ Metrics endpoint échoué"
    exit 1
}
echo "  ✅ Metrics endpoint OK"

# Test 5: N8N disponible
echo "✓ Test 5: N8N disponibilité..."
curl -f "$N8N_URL" > /dev/null 2>&1 || {
    echo "❌ N8N n'est pas accessible"
    exit 1
}
echo "  ✅ N8N OK"

# Test 6: PostgreSQL
echo "✓ Test 6: PostgreSQL..."
docker compose exec -T postgres pg_isready -U n8n > /dev/null 2>&1 || {
    echo "❌ PostgreSQL n'est pas prêt"
    exit 1
}
echo "  ✅ PostgreSQL OK"

echo ""
echo "✅ Tous les tests sont passés avec succès!"
echo ""
echo "📊 État des services:"
docker compose ps
