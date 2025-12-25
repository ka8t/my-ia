#!/bin/sh
# Génère le fichier config.js avec les variables d'environnement

cat > /usr/share/nginx/html/js/config.js << EOF
// Configuration générée automatiquement au démarrage du container
// NE PAS MODIFIER - Ce fichier est écrasé à chaque redémarrage
window.ENV_CONFIG = {
    apiUrl: "${API_URL:-http://localhost:8080}",
    apiKey: "${API_KEY:-change-me-in-production}"
};
EOF

echo "Config.js generated with API_URL=${API_URL:-http://localhost:8080}"

# Démarrer nginx
exec nginx -g "daemon off;"
