// Configuration par defaut pour le developpement
// En production, ce fichier est genere automatiquement par Docker
window.ENV_CONFIG = {
    apiUrl: "http://localhost:8080",
    debug: true  // Passer a false en production
};

// Mode debug centralise - tous les modules utilisent cette variable
window.DEBUG = window.ENV_CONFIG.debug || false;
