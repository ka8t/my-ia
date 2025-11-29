#!/bin/bash
# Script pour lancer les tests MY-IA avec Docker

set -e

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 MY-IA Docker Test Runner${NC}"
echo "=============================="
echo ""

# Parse arguments
MODE=${1:-"unit"}
COMPOSE_FILE="docker-compose.test.yml"

# Fonction pour vérifier si les services sont prêts
wait_for_services() {
    echo -e "${YELLOW}⏳ Attente que les services soient prêts...${NC}"

    # Attendre ChromaDB
    timeout 30 bash -c 'until docker compose -f docker-compose.test.yml exec -T chroma curl -f http://localhost:8000/api/v1/heartbeat 2>/dev/null; do sleep 2; done' || {
        echo -e "${RED}❌ ChromaDB n'est pas accessible${NC}"
        exit 1
    }

    # Attendre Ollama
    timeout 30 bash -c 'until docker compose -f docker-compose.test.yml exec -T ollama curl -f http://localhost:11434/api/tags 2>/dev/null; do sleep 2; done' || {
        echo -e "${RED}❌ Ollama n'est pas accessible${NC}"
        exit 1
    }

    echo -e "${GREEN}✅ Services prêts${NC}"
}

# Fonction pour nettoyer
cleanup() {
    echo -e "${BLUE}🧹 Nettoyage...${NC}"
    docker compose -f $COMPOSE_FILE down -v 2>/dev/null || true
}

case $MODE in
    "build")
        echo -e "${BLUE}🔨 Build de l'image de test...${NC}"
        docker compose -f $COMPOSE_FILE build test
        echo -e "${GREEN}✅ Build terminé${NC}"
        ;;

    "setup")
        echo -e "${BLUE}🚀 Démarrage des services...${NC}"
        docker compose -f $COMPOSE_FILE up -d ollama chroma
        wait_for_services

        echo -e "${BLUE}📥 Téléchargement des modèles...${NC}"
        docker compose -f $COMPOSE_FILE exec ollama ollama pull mistral:7b || {
            echo -e "${YELLOW}⚠️  Échec du pull de mistral:7b, tentative avec tinyllama...${NC}"
            docker compose -f $COMPOSE_FILE exec ollama ollama pull tinyllama
        }
        docker compose -f $COMPOSE_FILE exec ollama ollama pull nomic-embed-text

        echo -e "${GREEN}✅ Setup terminé${NC}"
        ;;

    "unit")
        echo -e "${BLUE}🔬 Lancement des tests unitaires...${NC}"
        docker compose -f $COMPOSE_FILE run --rm test pytest -m unit -v --tb=short
        ;;

    "integration")
        echo -e "${BLUE}🔗 Lancement des tests d'intégration...${NC}"

        # Vérifier que les services sont démarrés
        if ! docker compose -f $COMPOSE_FILE ps | grep -q "my-ia-test-ollama"; then
            echo -e "${YELLOW}⚠️  Services non démarrés. Lancement avec 'setup' d'abord...${NC}"
            $0 setup
        fi

        wait_for_services
        docker compose -f $COMPOSE_FILE run --rm test pytest -m integration -v --tb=short --timeout=300
        ;;

    "all")
        echo -e "${BLUE}🧪 Lancement de tous les tests...${NC}"

        # Vérifier que les services sont démarrés
        if ! docker compose -f $COMPOSE_FILE ps | grep -q "my-ia-test-ollama"; then
            echo -e "${YELLOW}⚠️  Services non démarrés. Lancement avec 'setup' d'abord...${NC}"
            $0 setup
        fi

        wait_for_services
        docker compose -f $COMPOSE_FILE run --rm test pytest -v --tb=short
        ;;

    "coverage")
        echo -e "${BLUE}📊 Lancement des tests avec coverage...${NC}"
        docker compose -f $COMPOSE_FILE run --rm test \
            pytest -m "not integration" \
            --cov=app \
            --cov-report=html \
            --cov-report=term-missing \
            --cov-report=xml

        echo ""
        echo -e "${GREEN}✅ Rapport de coverage généré${NC}"
        echo -e "   HTML: htmlcov/index.html"
        echo -e "   XML:  coverage.xml"
        ;;

    "shell")
        echo -e "${BLUE}🐚 Ouverture d'un shell dans le conteneur de test...${NC}"
        docker compose -f $COMPOSE_FILE run --rm test /bin/bash
        ;;

    "logs")
        echo -e "${BLUE}📋 Logs des services...${NC}"
        docker compose -f $COMPOSE_FILE logs -f
        ;;

    "clean")
        echo -e "${BLUE}🧹 Nettoyage complet...${NC}"
        docker compose -f $COMPOSE_FILE down -v
        rm -rf htmlcov/ .pytest_cache/ .coverage coverage.xml
        echo -e "${GREEN}✅ Nettoyage terminé${NC}"
        ;;

    "down")
        echo -e "${BLUE}🛑 Arrêt des services de test...${NC}"
        docker compose -f $COMPOSE_FILE down
        echo -e "${GREEN}✅ Services arrêtés${NC}"
        ;;

    "help"|"-h"|"--help")
        echo "Usage: ./run_tests_docker.sh [MODE]"
        echo ""
        echo "Modes disponibles:"
        echo "  build        - Build l'image de test"
        echo "  setup        - Démarre les services et télécharge les modèles"
        echo "  unit         - Tests unitaires seulement (défaut)"
        echo "  integration  - Tests d'intégration seulement"
        echo "  all          - Tous les tests"
        echo "  coverage     - Tests avec rapport de coverage"
        echo "  shell        - Ouvrir un shell dans le conteneur"
        echo "  logs         - Afficher les logs des services"
        echo "  down         - Arrêter les services"
        echo "  clean        - Nettoyer tout (volumes, rapports, etc.)"
        echo "  help         - Afficher cette aide"
        echo ""
        echo "Workflow typique:"
        echo "  1. ./run_tests_docker.sh build    # Build l'image"
        echo "  2. ./run_tests_docker.sh setup    # Setup services + modèles"
        echo "  3. ./run_tests_docker.sh unit     # Lancer tests unitaires"
        echo "  4. ./run_tests_docker.sh coverage # Générer coverage"
        echo "  5. ./run_tests_docker.sh clean    # Nettoyer"
        echo ""
        echo "Exemples:"
        echo "  ./run_tests_docker.sh              # Tests unitaires"
        echo "  ./run_tests_docker.sh integration  # Tests d'intégration"
        echo "  ./run_tests_docker.sh all          # Tous les tests"
        ;;

    *)
        echo -e "${RED}❌ Mode inconnu: $MODE${NC}"
        echo "Utilisez './run_tests_docker.sh help' pour voir les modes disponibles"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Terminé${NC}"
