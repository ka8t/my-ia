@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Setup du projet my-ia
echo ========================================
echo.

REM Verifier Docker
where docker >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERREUR] Docker n'est pas installe ou n'est pas dans le PATH
    pause
    exit /b 1
)
echo [OK] Docker est installe

REM Demarrer les services
echo.
echo [1/5] Demarrage des services Docker...
docker compose up -d
if %ERRORLEVEL% neq 0 (
    echo [ERREUR] Echec du demarrage des services
    pause
    exit /b 1
)

REM Attendre ChromaDB
echo.
echo [2/5] Attente du demarrage de ChromaDB (30 secondes)...
timeout /t 30 /nobreak >nul

REM Verifier ChromaDB
echo Verification de ChromaDB...
curl -s http://localhost:8000/api/v1/heartbeat >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [OK] ChromaDB est pret
) else (
    echo [ATTENTION] ChromaDB ne repond pas encore, attente supplementaire...
    timeout /t 30 /nobreak >nul
)

REM Télécharger les modèles Ollama
echo.
echo [3/5] Telechargement des modeles Ollama...
echo Cela peut prendre 5-10 minutes selon votre connexion...

echo - Telechargement de llama3.1:8b...
docker exec my-ia-ollama ollama pull llama3.1:8b
if %ERRORLEVEL% neq 0 echo [ATTENTION] Erreur telechargement modele principal

echo - Telechargement de nomic-embed-text...
docker exec my-ia-ollama ollama pull nomic-embed-text
if %ERRORLEVEL% neq 0 echo [ATTENTION] Erreur telechargement modele embeddings

REM Ingestion des données
echo.
echo [4/5] Ingestion des donnees d'exemple...
docker compose exec app python ingest.py
if %ERRORLEVEL% neq 0 (
    echo [ATTENTION] Erreur lors de l'ingestion
    echo Verifiez les logs: docker compose logs app
)

REM Test de santé
echo.
echo [5/5] Verification de la sante du systeme...
curl -f http://localhost:8080/health >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [OK] API fonctionne correctement!
) else (
    echo [ATTENTION] L'API ne repond pas correctement
    echo Verifiez les logs: docker compose logs app
)

echo.
echo ========================================
echo Configuration terminee!
echo ========================================
echo.
echo Services disponibles:
echo   - API IA:       http://localhost:8080
echo   - N8N:          http://localhost:5678
echo   - Ollama:       http://localhost:11434
echo   - ChromaDB:     http://localhost:8000
echo   - PostgreSQL:   localhost:5432
echo.
echo Prochaines etapes:
echo   1. Ouvrir http://localhost:8080 dans votre navigateur
echo   2. Se connecter a N8N: http://localhost:5678
echo      (admin / change-me-in-production)
echo   3. Ajouter vos donnees dans ./datasets/
echo   4. Relancer ingestion: docker compose exec app python ingest.py
echo.
echo En cas de probleme:
echo   - Logs: docker compose logs -f
echo   - Status: docker compose ps
echo.
echo IMPORTANT: Changez les mots de passe par defaut en production!
echo.
pause
