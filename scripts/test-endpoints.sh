#!/bin/bash

##############################################################################
#                        MY-IA API - Script de Test
##############################################################################
#
# DESCRIPTION
# -----------
# Script de test automatisé pour valider les endpoints de l'API MY-IA.
# Effectue des requêtes HTTP via curl et vérifie les codes de réponse.
#
# USAGE
# -----
#   ./scripts/test-endpoints.sh [SUITE]
#
#   SUITE (optionnel) :
#     base   - Endpoints publics (/, /health, /metrics, /docs)
#     auth   - Authentification (register, login, logout, forgot-password)
#     user   - Gestion utilisateur (requiert auth : /users/me, PATCH, GET by ID)
#     all    - Toutes les suites (défaut)
#
# EXEMPLES
# --------
#   ./scripts/test-endpoints.sh           # Exécute tous les tests
#   ./scripts/test-endpoints.sh base      # Teste uniquement les endpoints de base
#   ./scripts/test-endpoints.sh auth      # Teste l'authentification
#   ./scripts/test-endpoints.sh user      # Teste auth + endpoints utilisateur
#
# PRÉREQUIS
# ---------
#   - curl installé
#   - Fichier .env présent à la racine du projet
#   - API MY-IA en cours d'exécution (docker-compose up)
#
# VARIABLES D'ENVIRONNEMENT (depuis .env)
# ---------------------------------------
#   FRONTEND_HOST      - Hôte de l'API (ex: localhost)
#   APP_PORT           - Port de l'API (ex: 8080)
#   HTTP_TIMEOUT       - Timeout des requêtes en secondes (ex: 30.0)
#   TEST_USER_EMAIL    - Email pour les tests d'authentification
#   TEST_USER_PASSWORD - Mot de passe pour les tests d'authentification
#
# CODES DE SORTIE
# ---------------
#   0 - Tous les tests sont passés
#   1 - Au moins un test a échoué ou erreur de configuration
#
# SUITES DE TESTS
# ---------------
#
#   [base] Endpoints publics :
#     GET  /              → 200  Page d'accueil
#     GET  /health        → 200  Health check (Ollama + ChromaDB)
#     GET  /metrics       → 200  Métriques Prometheus
#     GET  /docs          → 200  Documentation Swagger UI
#     GET  /openapi.json  → 200  Schéma OpenAPI
#
#   [auth] Authentification :
#     POST /auth/register/register              → 201  Création utilisateur
#     POST /auth/jwt/login                      → 200  Connexion (retourne JWT)
#     POST /auth/jwt/logout                     → 200  Déconnexion
#     POST /auth/verify/request-verify-token   → 202  Demande vérification email
#     POST /auth/reset-password/forgot-password → 202  Mot de passe oublié
#
#   [user] Gestion utilisateur (authentifié) :
#     GET   /users/me      → 200  Récupérer profil courant
#     PATCH /users/me      → 200  Mettre à jour profil
#     GET   /users/{id}    → 200  Récupérer utilisateur par ID
#
#   [other] Vérification protection endpoints :
#     POST /chat                → 401  Chat sans auth
#     GET  /ingestion/documents → 401  Ingestion sans auth
#     GET  /admin/roles         → 401  Admin sans auth
#
# AUTEUR
# ------
#   KL - Projet MY-IA
#
##############################################################################

# Note: On n'utilise PAS "set -e" pour que le script continue même si un test échoue
# Le code de sortie final est géré par print_summary()

# Charger les variables depuis .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)
else
    echo "Erreur: Fichier .env introuvable: $ENV_FILE"
    exit 1
fi

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration depuis .env
API_URL="http://${FRONTEND_HOST}:${APP_PORT}"
TIMEOUT="${HTTP_TIMEOUT}"

# Compteurs
TOTAL=0
SUCCESS=0
FAILED=0

# Variables globales pour auth (depuis .env)
ACCESS_TOKEN=""
TEST_USER_EMAIL="${TEST_USER_EMAIL}"
TEST_USER_PASSWORD="${TEST_USER_PASSWORD}"
USER_ID=""

##############################################################################
# Fonctions utilitaires - Affichage
##############################################################################

# Affiche un en-tête de section
# Usage: print_header "Titre de la section"
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

# Affiche le nom du test en cours (jaune)
print_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

# Affiche un succès et incrémente les compteurs
print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((SUCCESS++))
    ((TOTAL++))
}

# Affiche une erreur et incrémente les compteurs
print_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((FAILED++))
    ((TOTAL++))
}

# Affiche une information (bleu)
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

##############################################################################
# Fonction principale de test HTTP
##############################################################################

# Effectue une requête HTTP et vérifie le code de réponse
#
# Arguments:
#   $1 method          - Méthode HTTP (GET, POST, PATCH, DELETE)
#   $2 endpoint        - Chemin de l'endpoint (ex: /health)
#   $3 expected_status - Code HTTP attendu (ex: 200, 201, 401)
#   $4 description     - Description du test pour l'affichage
#   $5 data (opt)      - Corps JSON de la requête
#   $6 headers (opt)   - En-têtes additionnels (ex: "Authorization: Bearer xxx")
#
# Retourne:
#   0 si le code HTTP correspond à expected_status
#   1 sinon
#
# Exemple:
#   test_endpoint "GET" "/health" 200 "Health check"
#   test_endpoint "POST" "/auth/login" 200 "Login" '{"email":"x","password":"y"}'
#
test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected_status=$3
    local description=$4
    local data=${5:-}
    local headers=${6:-}

    print_test "$description"

    # Construire la commande curl
    local url="${API_URL}${endpoint}"
    local curl_cmd="curl -s -w '\n%{http_code}' -X $method '$url' --max-time $TIMEOUT"

    # Afficher les détails de la requête
    echo -e "    ${BLUE}→ ${method}${NC} ${url}"

    # Ajouter les en-têtes si présents
    if [ -n "$headers" ]; then
        curl_cmd="$curl_cmd -H '$headers'"
        # Masquer le token dans l'affichage
        local display_headers=$(echo "$headers" | sed 's/Bearer [^ ]*/Bearer ***/')
        echo -e "    ${BLUE}→ Headers:${NC} ${display_headers}"
    fi

    # Ajouter le corps JSON si présent
    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
        # Masquer les mots de passe dans l'affichage
        local display_data=$(echo "$data" | sed 's/"password":"[^"]*"/"password":"***"/g')
        echo -e "    ${BLUE}→ Body:${NC} ${display_data:0:100}"
    fi

    # Exécuter la requête
    local response
    response=$(eval $curl_cmd 2>&1) || {
        print_error "$description - Connection failed"
        return 1
    }

    # Extraire le code HTTP (dernière ligne de la sortie curl -w)
    local http_code=$(echo "$response" | tail -n1)
    # Extraire le corps (tout sauf la dernière ligne)
    local body=$(echo "$response" | sed '$d')

    # Vérifier le code HTTP
    if [ "$http_code" = "$expected_status" ]; then
        print_success "$description (HTTP $http_code)"
        echo -e "    ${BLUE}← Response:${NC} ${body:0:100}..."
        echo ""
        return 0
    else
        print_error "$description - Expected $expected_status, got $http_code"
        echo -e "    ${BLUE}← Response:${NC} $body" | head -c 200
        echo ""
        return 1
    fi
}

##############################################################################
# SUITE: base - Endpoints publics
##############################################################################

# Teste les endpoints accessibles sans authentification
# - Page d'accueil, health check, métriques, documentation
test_basic_endpoints() {
    print_header "Tests des endpoints de base"

    test_endpoint "GET" "/" 200 "Root endpoint"
    test_endpoint "GET" "/health" 200 "Health check"
    test_endpoint "GET" "/metrics" 200 "Prometheus metrics"
    test_endpoint "GET" "/docs" 200 "OpenAPI documentation"
    test_endpoint "GET" "/openapi.json" 200 "OpenAPI schema"
}

##############################################################################
# SUITE: auth - Authentification
##############################################################################

# Teste le flux complet d'authentification :
# 1. Inscription d'un nouvel utilisateur (POST /auth/register/register)
# 2. Connexion et récupération du JWT (POST /auth/jwt/login)
# 3. Déconnexion (POST /auth/jwt/logout)
# 4. Demande de vérification email (POST /auth/verify/request-verify-token)
# 5. Mot de passe oublié (POST /auth/reset-password/forgot-password)
#
# Variables globales modifiées :
#   ACCESS_TOKEN - Token JWT récupéré après login
#   USER_ID      - UUID de l'utilisateur créé
test_auth_endpoints() {
    print_header "Tests des endpoints d'authentification"

    # 1. Register - Création d'un nouvel utilisateur
    local register_data="{\"email\":\"$TEST_USER_EMAIL\",\"password\":\"$TEST_USER_PASSWORD\",\"username\":\"testuser\",\"full_name\":\"Test User\"}"

    print_test "POST /auth/register/register - Création d'utilisateur"
    echo -e "    ${BLUE}→ POST${NC} ${API_URL}/auth/register/register"
    echo -e "    ${BLUE}→ Body:${NC} {\"email\":\"$TEST_USER_EMAIL\",\"password\":\"***\",\"username\":\"testuser\",\"full_name\":\"Test User\"}"
    local response=$(curl -s -w '\n%{http_code}' -X POST "$API_URL/auth/register/register" \
        -H 'Content-Type: application/json' \
        -d "$register_data" \
        --max-time $TIMEOUT 2>&1)

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "201" ]; then
        print_success "Utilisateur créé (HTTP 201)"
        # Extraire l'ID utilisateur
        USER_ID=$(echo "$body" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
        print_info "User ID: $USER_ID"
        echo "    Response: ${body:0:100}..."
    else
        print_error "Échec création utilisateur - Expected 201, got $http_code"
        echo "    Response: $body"
    fi
    echo ""

    # 2. Login
    print_test "POST /auth/jwt/login - Connexion utilisateur"
    local login_data="username=$TEST_USER_EMAIL&password=$TEST_USER_PASSWORD"

    response=$(curl -s -w '\n%{http_code}' -X POST "$API_URL/auth/jwt/login" \
        -H 'Content-Type: application/x-www-form-urlencoded' \
        -d "$login_data" \
        --max-time $TIMEOUT 2>&1)

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        print_success "Connexion réussie (HTTP 200)"
        # Extraire le token
        ACCESS_TOKEN=$(echo "$body" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
        print_info "Access Token: ${ACCESS_TOKEN:0:50}..."
        echo "    Response: ${body:0:100}..."
    else
        print_error "Échec connexion - Expected 200, got $http_code"
        echo "    Response: $body"
    fi
    echo ""

    # 3. Logout
    if [ -n "$ACCESS_TOKEN" ]; then
        test_endpoint "POST" "/auth/jwt/logout" 204 "POST /auth/jwt/logout - Déconnexion" "" "Authorization: Bearer $ACCESS_TOKEN"
    else
        print_error "POST /auth/jwt/logout - Pas de token disponible"
        ((FAILED++))
        ((TOTAL++))
    fi

    # 4. Request verify token (sans être connecté, devrait échouer ou réussir selon config)
    test_endpoint "POST" "/auth/verify/request-verify-token" 202 "POST /auth/verify/request-verify-token - Demande token vérification" "{\"email\":\"$TEST_USER_EMAIL\"}"

    # 5. Forgot password
    test_endpoint "POST" "/auth/reset-password/forgot-password" 202 "POST /auth/reset-password/forgot-password - Mot de passe oublié" "{\"email\":\"$TEST_USER_EMAIL\"}"
}

##############################################################################
# SUITE: user - Gestion utilisateur (authentifié)
##############################################################################

# Teste les endpoints de gestion utilisateur (requiert ACCESS_TOKEN)
# - Récupération du profil courant
# - Mise à jour du profil
# - Récupération par ID
#
# Prérequis : ACCESS_TOKEN doit être défini (exécuter test_auth_endpoints avant)
test_user_endpoints() {
    print_header "Tests des endpoints utilisateurs"

    # Vérifier que le token est disponible
    if [ -z "$ACCESS_TOKEN" ]; then
        print_error "Pas de token d'authentification - Login requis"
        ((FAILED++))
        ((TOTAL++))
        return 1
    fi

    # 1. Get current user
    print_test "GET /me - Récupérer l'utilisateur courant"
    local response=$(curl -s -w '\n%{http_code}' -X GET "$API_URL/me" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        --max-time $TIMEOUT 2>&1)

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        print_success "Utilisateur récupéré (HTTP 200)"
        echo "    Response: ${body:0:150}..."
    else
        print_error "Échec récupération utilisateur - Expected 200, got $http_code"
        echo "    Response: $body"
    fi
    echo ""

    # 2. Update current user
    print_test "PATCH /me - Mettre à jour l'utilisateur courant"
    local update_data='{"full_name":"Updated Test User"}'

    response=$(curl -s -w '\n%{http_code}' -X PATCH "$API_URL/me" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H 'Content-Type: application/json' \
        -d "$update_data" \
        --max-time $TIMEOUT 2>&1)

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        print_success "Utilisateur mis à jour (HTTP 200)"
        echo "    Response: ${body:0:150}..."
    else
        print_error "Échec mise à jour utilisateur - Expected 200, got $http_code"
        echo "    Response: $body"
    fi
    echo ""

    # 3. Get user by ID (requiert rôle admin - doit retourner 403 pour utilisateur standard)
    if [ -n "$USER_ID" ]; then
        print_test "GET /$USER_ID - Utilisateur par ID (attendu 403 sans rôle admin)"
        response=$(curl -s -w '\n%{http_code}' -X GET "$API_URL/$USER_ID" \
            -H "Authorization: Bearer $ACCESS_TOKEN" \
            --max-time $TIMEOUT 2>&1)

        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | sed '$d')

        if [ "$http_code" = "403" ]; then
            print_success "Accès refusé comme attendu (HTTP 403)"
            echo "    Response: ${body:0:150}..."
        else
            print_error "Attendu 403, reçu $http_code"
            echo "    Response: $body"
        fi
        echo ""
    fi
}

##############################################################################
# SUITE: other - Vérification protection des endpoints
##############################################################################

# Vérifie que les endpoints protégés retournent 401 sans authentification
# - Chat : requiert authentification
# - Ingestion : requiert authentification
# - Admin : requiert authentification + rôle admin
test_other_endpoints() {
    print_header "Tests des autres endpoints (non-authentifiés)"

    # Chat - doit refuser sans token
    test_endpoint "POST" "/chat" 401 "POST /chat - Sans authentification (attendu 401)" '{"query":"test"}'

    # Admin documents - doit refuser sans token
    test_endpoint "GET" "/admin/documents" 401 "GET /admin/documents - Sans authentification (attendu 401)"

    # Admin - doit refuser sans token (et sans rôle admin)
    test_endpoint "GET" "/admin/roles" 401 "GET /admin/roles - Sans authentification (attendu 401)"
}

##############################################################################
# Rapport final
##############################################################################

# Affiche le résumé des tests et retourne le code de sortie approprié
# - Calcule le taux de réussite
# - Exit 0 si tous les tests passent, 1 sinon
print_summary() {
    print_header "Résumé des tests"

    echo -e "${BLUE}Total de tests:${NC} $TOTAL"
    echo -e "${GREEN}Réussis:${NC} $SUCCESS"
    echo -e "${RED}Échecs:${NC} $FAILED"

    local success_rate=0
    if [ $TOTAL -gt 0 ]; then
        success_rate=$(awk "BEGIN {printf \"%.1f\", ($SUCCESS/$TOTAL)*100}")
    fi

    echo -e "\n${BLUE}Taux de réussite:${NC} $success_rate%"

    if [ $FAILED -eq 0 ]; then
        echo -e "\n${GREEN}✓ Tous les tests sont passés avec succès!${NC}\n"
        exit 0
    else
        echo -e "\n${RED}✗ Certains tests ont échoué${NC}\n"
        exit 1
    fi
}

##############################################################################
# Point d'entrée principal
##############################################################################

# Fonction principale - Parse les arguments et exécute les suites de tests
#
# Arguments:
#   $1 - Suite de tests à exécuter (base|auth|user|all)
#        Défaut: all
#
# Flux d'exécution:
#   1. Affiche la bannière et la configuration
#   2. Exécute la suite demandée
#   3. Affiche le résumé et retourne le code de sortie
main() {
    local test_suite=${1:-all}

    # Bannière
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║       MY-IA API - Script de test des endpoints        ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # Afficher la configuration chargée
    print_info "API URL: $API_URL"
    print_info "Timeout: ${TIMEOUT}s"
    echo ""

    # Exécuter la suite demandée
    case "$test_suite" in
        base|basic)
            # Endpoints publics uniquement
            test_basic_endpoints
            ;;
        auth)
            # Authentification uniquement
            test_auth_endpoints
            ;;
        user)
            # Auth + User (auth requis pour obtenir le token)
            test_auth_endpoints
            test_user_endpoints
            ;;
        all)
            # Toutes les suites
            test_basic_endpoints
            test_auth_endpoints
            test_user_endpoints
            test_other_endpoints
            ;;
        *)
            echo -e "${RED}Usage: $0 [base|auth|user|all]${NC}"
            exit 1
            ;;
    esac

    # Afficher le résumé et sortir
    print_summary
}

##############################################################################
# Exécution
##############################################################################
main "$@"
