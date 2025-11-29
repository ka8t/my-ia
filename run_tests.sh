#!/bin/bash
# Script pour lancer les tests MY-IA

set -e

echo "🧪 MY-IA Test Runner"
echo "===================="
echo ""

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Vérifier si pytest est installé
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest n'est pas installé${NC}"
    echo "Installez les dépendances de test avec:"
    echo "  pip install -r requirements-test.txt"
    exit 1
fi

# Parse arguments
MODE=${1:-"all"}

case $MODE in
    "unit")
        echo -e "${BLUE}🔬 Lancement des tests unitaires...${NC}"
        pytest -m unit -v
        ;;

    "integration")
        echo -e "${BLUE}🔗 Lancement des tests d'intégration...${NC}"
        pytest -m integration -v
        ;;

    "api")
        echo -e "${BLUE}🌐 Lancement des tests API...${NC}"
        pytest -m api -v
        ;;

    "ingest")
        echo -e "${BLUE}📥 Lancement des tests d'ingestion...${NC}"
        pytest -m ingest -v
        ;;

    "coverage")
        echo -e "${BLUE}📊 Lancement des tests avec coverage...${NC}"
        pytest --cov=app --cov-report=html --cov-report=term-missing
        echo ""
        echo -e "${GREEN}✅ Rapport de coverage généré dans htmlcov/index.html${NC}"
        ;;

    "fast")
        echo -e "${BLUE}⚡ Lancement des tests rapides (sans les lents)...${NC}"
        pytest -m "not slow" -v
        ;;

    "watch")
        echo -e "${BLUE}👀 Mode watch (relance auto)...${NC}"
        if ! command -v ptw &> /dev/null; then
            echo -e "${RED}❌ pytest-watch n'est pas installé${NC}"
            echo "Installez avec: pip install pytest-watch"
            exit 1
        fi
        ptw
        ;;

    "clean")
        echo -e "${BLUE}🧹 Nettoyage des fichiers de test...${NC}"
        rm -rf .pytest_cache htmlcov .coverage
        find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
        echo -e "${GREEN}✅ Nettoyage terminé${NC}"
        ;;

    "help"|"-h"|"--help")
        echo "Usage: ./run_tests.sh [MODE]"
        echo ""
        echo "Modes disponibles:"
        echo "  all          - Tous les tests (défaut)"
        echo "  unit         - Tests unitaires seulement"
        echo "  integration  - Tests d'intégration seulement"
        echo "  api          - Tests des endpoints API"
        echo "  ingest       - Tests du système d'ingestion"
        echo "  coverage     - Tests avec rapport de coverage"
        echo "  fast         - Tests rapides (exclut les lents)"
        echo "  watch        - Mode watch (relance automatique)"
        echo "  clean        - Nettoyer les fichiers de test"
        echo "  help         - Afficher cette aide"
        echo ""
        echo "Exemples:"
        echo "  ./run_tests.sh              # Tous les tests"
        echo "  ./run_tests.sh unit         # Tests unitaires"
        echo "  ./run_tests.sh coverage     # Avec coverage"
        ;;

    "all"|*)
        echo -e "${BLUE}🧪 Lancement de tous les tests...${NC}"
        pytest -v
        ;;
esac

echo ""
echo -e "${GREEN}✅ Tests terminés${NC}"
