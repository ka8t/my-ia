IMPORTANT : SUIT CES RÈGLES À CHAQUE ÉTAPE DE GÉNÉRATION DE CODE. Relis ce fichier au début de chaque session. Appliquez systématiquement cette structure modulaire, scalable et maintenable pour tous les projets Python/FastAPI.

# Context : Projet "MY-IA API"
Je suis sous Macos Monterey. MacBook Pro 2015.
Intel core I5 2,7 
256 Go SSD interne
1 Go SSD externe
Je veux utiliser le minimum de ressources pour créer l'application et doit donc optimiser les ressources.

## Interaction
Tu dois toujours t'adresser à moi en Français

## Description
Application de Chatbot RAG avec gestion administrative poussée, authentification et observabilité.

## Stack Technique
- **Framework :** FastAPI (Python 3.10+)
- **Database (Relationnelle) :** PostgreSQL (via SQLAlchemy 2.0 + AsyncPG)
- **Database (Vectorielle) :** ChromaDB (HttpClient)
- **LLM / Embeddings :** Ollama (Mistral, Nomic-embed-text)
- **Auth :** FastAPI Users (JWT Strategy)
- **Ingestion :** Pipeline personnalisé (Unstructured.io + LangChain semantic chunking)
- **Monitoring :** Prometheus Client, SlowAPI (Rate Limiting)


NE JAMais mettre de logique métier dans main.py ou router.py.

Ce projet a migré d'un `main.py` monolithique vers une architecture modulaire.
Chaque feature est découpée comme suit
exemple dans le dossier `/app`
```
app/
├── main.py                        # Point d'entrée minimal
├── core/                          # Configuration centralisée
│   ├── config.py                  # pydantic-settings
│   └── deps.py                    # Injection de dépendances
├── common/                        # Code partagé
│   ├── utils/
│   │   ├── chroma.py              # search_context()
│   │   └── ollama.py              # get_embeddings(), generate_response()
│   ├── exceptions/http.py         # Custom HTTP exceptions
│   ├── schemas/base.py            # Base Pydantic models
│   └── metrics.py                 # Métriques Prometheus centralisées
└── features/                      # 🎯 Architecture modulaire
    ├── health/                    # ✅ Health check & metrics
    │   ├── router.py
    │   └── service.py
    ├── chat/                      # ✅ Chat conversationnel RAG
    │   ├── router.py
    │   ├── service.py
    │   └── schemas.py
    ├── ingestion/                 # ✅ Upload documents
    │   ├── router.py
    │   ├── service.py
    │   └── schemas.py
    ├── audit/                     # ✅ Audit logs
    │   ├── service.py
    │   └── repository.py
    └── admin/                     # ✅ CRUD admin (20+ endpoints)
        ├── router.py
        ├── service.py
        └── repository.py
```

### Pattern Feature (Standard Appliqué)

Chaque feature suit le pattern **Router → Service → Repository** :

```python
features/[nom]/
├── router.py       # FastAPI endpoints ONLY (GET/POST/PATCH/DELETE)
├── service.py      # Business logic (async)
├── repository.py   # Database operations (optionnel)
└── schemas.py      # Pydantic DTOs (optionnel)
```

Les documents Markdown (sauf README) doivent être stockés dans le dossier /docs
à la racine et organisés par type de documentation
- Générale
    - cahier des charges
    - évolutions
    - todos ...
- technique
    - installation
    - déploiement
    - maintenance ...

Les tests doivent être stockés dans le dossier /tests
à la racine et organisés de manière à pouvoir les exécuter individuellement ou tout l'ensemble.


Vérification Finale
À CHAQUE réponse de code, confirmer :
✅ Structure features/ respectée
✅ main.py minimal 
✅ Type hints partout
✅ Tests unitaires écrits
✅ Docstrings présentes
✅ Logger utilisé (pas print)
✅ Dependencies injectées (si utilisée)

## Améliorations : Modulaire, Scalable, Maintenable
1. Découpage des Routes (Modularité)
Actuellement, plus de 60% de ton fichier main.py est occupé par les routes /admin. Action : Crée un dossier routers/ et déplace le code.
2. Injection de Dépendances (Scalabilité & Testabilité)
Tu utilises des variables globales comme chroma_client ou ingestion_pipeline initialisées au début du fichier. Problème : Si la connexion échoue au démarrage, toute l'app plante. Difficile à tester (mocker). Solution : Utilise lru_cache ou le système de dépendance FastAPI.
3. Gestion asynchrone de l'ingestion (Performance)
La route /upload fait : await ingestion_pipeline.ingest_file(...). Problème : Si le fichier est gros, la requête HTTP va timeout (le client attendra indéfiniment). Cela bloque un "worker" FastAPI. Solution : Utiliser BackgroundTasks de FastAPI (simple) ou Celery (robuste).
4. Generic Repository Pattern (Maintenabilité)
Les routes Admin (get_roles, create_role, update_role, etc.) répètent la même logique CRUD 10 fois. Solution : Crée une classe générique.

## Directives de Code
1. **DRY** Pas de duplication de code qui viole le principe DRY (Don't Repeat Yourself).
2. **Asynchronisme :** Tout doit être `async/await`, surtout les appels DB et HTTP (Ollama).
3. **Typage :** Utiliser `typing` (List, Optional, Dict) et Pydantic strictement.
4. **Erreurs :** Toujours wrapper les appels externes dans des `try/except` avec logging approprié.
5. **Dépendances :** Utiliser l'injection de dépendance de FastAPI (`Depends()`) plutôt que des imports globaux.
6. **Admin :** Les routes admin doivent toujours vérifier le rôle `superuser` ou `admin`.
7. **Commit :** Indiquer KL comme auteur. Ne JAMAIS ajouter de références à Claude, Claude Code, ou Co-Authored-By dans les messages de commit.

## Conventions de Nommage
- Variables/Fonctions : `snake_case`
- Classes : `PascalCase`
- Constantes : `UPPER_CASE`

Pour les containers docker, on ne doit pas redémarrer ou les reconstruire si il y a un changement de code mais uniquement si cela est nécessaire, ajout/modification de libs systèmes, dépendances ....

Ne prends jamais d'initiatives d'optimisatations sans me présenter le pour et le contre. Sachant que le plus important est la maintenabilité, la clarté, la scalabilité.

Tu dois toujoujours suggérer les meilleurs pratiques de codage.

Tu dois toujours vérifier les dépendances et les conflits possibles entre elles.

Tu dois à chaque création ou modification de fichier que les lines-ending ne sont pas au format Windows.


Ce fichier CLAUDE.md doit être la référence ABSOLUE pour tous vos projets Python. Relisez-le systématiquement au début de chaque génération de code.