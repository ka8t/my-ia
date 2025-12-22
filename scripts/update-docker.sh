#!/bin/bash
# Script de mise à jour Docker - Architecture Modulaire
# Version: 1.0.0
# Date: 22 décembre 2024

set -e  # Arrêter en cas d'erreur

echo "🐳 MY-IA - Mise à Jour Docker vers Architecture Modulaire"
echo "============================================================"
echo ""

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonction de log
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "docker-compose.yml" ]; then
    log_error "Fichier docker-compose.yml non trouvé. Exécutez ce script depuis la racine du projet."
    exit 1
fi

log_info "Répertoire de travail : $(pwd)"
echo ""

# Étape 1 : Vérifier l'état actuel
echo "📊 Étape 1/6 : Vérification de l'état actuel"
echo "-------------------------------------------"
docker compose ps
echo ""

# Étape 2 : Sauvegarder l'image actuelle (optionnel)
echo "💾 Étape 2/6 : Sauvegarde de l'image actuelle"
echo "-------------------------------------------"
if docker images | grep -q "my-ia-app"; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    docker tag my-ia-app:latest my-ia-app:backup_$TIMESTAMP || true
    log_success "Image sauvegardée : my-ia-app:backup_$TIMESTAMP"
else
    log_info "Aucune image existante à sauvegarder"
fi
echo ""

# Étape 3 : Arrêter le container app
echo "⏸️  Étape 3/6 : Arrêt du container app"
echo "-------------------------------------------"
docker compose stop app
log_success "Container app arrêté"
echo ""

# Étape 4 : Rebuild l'image
echo "🔨 Étape 4/6 : Rebuild de l'image Docker"
echo "-------------------------------------------"
log_info "Cela peut prendre 3-5 minutes..."
docker compose build app
log_success "Image reconstruite avec succès"
echo ""

# Étape 5 : Redémarrer le container
echo "🚀 Étape 5/6 : Redémarrage du container app"
echo "-------------------------------------------"
docker compose up -d app
log_success "Container app redémarré"
echo ""

# Étape 6 : Tests de validation
echo "🧪 Étape 6/6 : Tests de validation"
echo "-------------------------------------------"

# Attendre que le container soit prêt
log_info "Attente du démarrage (10 secondes)..."
sleep 10

# Test 1 : Container running
if docker compose ps app | grep -q "Up"; then
    log_success "Container app est UP"
else
    log_error "Container app n'est pas démarré"
    docker compose logs --tail=20 app
    exit 1
fi

# Test 2 : Health endpoint
log_info "Test de l'endpoint /health..."
if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
    HEALTH_RESPONSE=$(curl -s http://localhost:8080/health)
    log_success "Endpoint /health répond : $HEALTH_RESPONSE"
else
    log_error "Endpoint /health ne répond pas"
    docker compose logs --tail=20 app
    exit 1
fi

# Test 3 : Root endpoint
log_info "Test de l'endpoint /..."
if curl -s -f http://localhost:8080/ > /dev/null 2>&1; then
    ROOT_RESPONSE=$(curl -s http://localhost:8080/ | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data.get('name')} v{data.get('version')}\")" 2>/dev/null || echo "OK")
    log_success "Endpoint / répond : $ROOT_RESPONSE"
else
    log_error "Endpoint / ne répond pas"
fi

# Test 4 : Swagger docs
log_info "Test de l'endpoint /docs..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/docs | grep -q "200"; then
    log_success "Swagger UI accessible"
else
    log_error "Swagger UI non accessible"
fi

echo ""
echo "============================================================"
log_success "🎉 Mise à jour Docker terminée avec succès !"
echo ""
echo "📝 Prochaines étapes :"
echo "  1. Vérifier les logs : docker compose logs -f app"
echo "  2. Accéder à Swagger : http://localhost:8080/docs"
echo "  3. Tester les endpoints principaux"
echo ""
echo "📊 État des services :"
docker compose ps
echo ""
echo "🔗 URLs utiles :"
echo "  - API Swagger : http://localhost:8080/docs"
echo "  - Health Check : http://localhost:8080/health"
echo "  - Métriques : http://localhost:8080/metrics"
echo "  - Frontend : http://localhost:3000"
echo ""
log_info "En cas de problème, consulter DOCKER_UPDATE_PROCESS.md"
