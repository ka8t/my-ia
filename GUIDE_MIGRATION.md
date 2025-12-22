# Guide de Migration - Architecture Modulaire

## 📁 Nouvelle Structure

```
app/
├── main_new.py              # ✅ Nouveau point d'entrée (<50 lignes)
├── main.py.old              # ✅ Sauvegarde de l'ancien main
│
├── core/                    # ✅ Configuration & Dépendances
│   ├── config.py            # Settings avec pydantic-settings
│   └── deps.py              # Dépendances injectables
│
├── common/                  # ✅ Code partagé
│   ├── utils/
│   │   ├── ollama.py        # Fonctions Ollama (embeddings, génération)
│   │   └── chroma.py        # Fonctions ChromaDB (search_context)
│   ├── exceptions/
│   │   └── http.py          # Exceptions HTTP personnalisées
│   └── schemas/
│       └── base.py          # Schémas Pydantic de base
│
└── features/                # Architecture par features
    ├── health/              # ✅ MIGRÉ
    │   ├── router.py        # GET /health, /metrics, /
    │   └── service.py       # Logique health check
    │
    ├── chat/                # ✅ MIGRÉ
    │   ├── router.py        # POST /chat, /assistant, /test, /chat/stream
    │   ├── service.py       # Logique RAG et génération
    │   └── schemas.py       # ChatRequest, ChatResponse
    │
    ├── ingestion/           # 🔄 À MIGRER
    │   ├── router.py        # POST /upload
    │   ├── service.py       # Pipeline d'ingestion
    │   └── schemas.py       # UploadResponse
    │
    ├── admin/               # 🔄 À MIGRER (grosse feature)
    │   ├── router.py        # Tous les /admin/*
    │   ├── service.py       # Logique métier admin
    │   └── repository.py    # Opérations DB
    │
    └── audit/               # 🔄 À MIGRER
        ├── service.py       # Depuis audit_service.py
        └── repository.py    # Opérations DB audit
```

---

## 🎯 Exemple : Migrer une Feature (Template)

### Étape 1 : Créer les Schémas (si nécessaire)

```python
# app/features/ma_feature/schemas.py
from pydantic import BaseModel, Field
from typing import Optional

class MaFeatureRequest(BaseModel):
    """Requête pour ma feature"""
    param: str = Field(..., description="Un paramètre")

class MaFeatureResponse(BaseModel):
    """Réponse de ma feature"""
    result: str
    success: bool = True
```

### Étape 2 : Créer le Service (Logique Métier)

```python
# app/features/ma_feature/service.py
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MaFeatureService:
    """Service pour ma feature"""

    @staticmethod
    async def faire_quelque_chose(param: str) -> Dict[str, Any]:
        """
        Fait quelque chose d'utile

        Args:
            param: Le paramètre

        Returns:
            Résultat du traitement
        """
        try:
            # Logique métier ici
            result = f"Traité: {param}"

            return {
                "result": result,
                "success": True
            }
        except Exception as e:
            logger.error(f"Erreur: {e}")
            raise
```

### Étape 3 : Créer le Repository (si opérations DB)

```python
# app/features/ma_feature/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import MonModele

class MaFeatureRepository:
    """Repository pour les opérations DB"""

    @staticmethod
    async def get_by_id(db: AsyncSession, id: int) -> MonModele:
        """Récupère un élément par ID"""
        result = await db.execute(
            select(MonModele).where(MonModele.id == id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> MonModele:
        """Crée un nouvel élément"""
        item = MonModele(**data)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item
```

### Étape 4 : Créer le Router (Endpoints SEULEMENT)

```python
# app/features/ma_feature/router.py
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, verify_api_key
from app.features.ma_feature.schemas import MaFeatureRequest, MaFeatureResponse
from app.features.ma_feature.service import MaFeatureService
from app.features.ma_feature.repository import MaFeatureRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ma-feature", tags=["ma-feature"])

@router.post("", response_model=MaFeatureResponse)
async def endpoint_ma_feature(
    request: MaFeatureRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_api_key)
):
    """
    Endpoint de ma feature

    Args:
        request: Requête
        db: Session DB
        _: Vérification API key

    Returns:
        Réponse
    """
    try:
        # Utiliser le service (logique métier)
        result = await MaFeatureService.faire_quelque_chose(request.param)

        # Utiliser le repository (si besoin DB)
        # item = await MaFeatureRepository.create(db, {"param": request.param})

        return MaFeatureResponse(**result)

    except Exception as e:
        logger.error(f"Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Étape 5 : Intégrer dans main_new.py

```python
# Dans app/main_new.py
from app.features.ma_feature.router import router as ma_feature_router

# ...

# Dans la section ROUTERS
app.include_router(ma_feature_router)
```

---

## 🔍 Règles Strictes

### ❌ NE JAMAIS faire
1. **Logique métier dans router.py**
   ```python
   # ❌ MAUVAIS
   @router.post("/chat")
   async def chat(request: ChatRequest):
       context = await search_context(request.query)  # ❌ Logique dans router
       response = await generate_response(...)        # ❌ Logique dans router
   ```

2. **Opérations DB dans service.py**
   ```python
   # ❌ MAUVAIS - Service ne doit PAS faire de DB directement
   class ChatService:
       async def save_message(self, db: AsyncSession, message: str):
           db.execute(...)  # ❌ DB dans service
   ```

3. **Import circulaires**
   ```python
   # ❌ MAUVAIS
   # service.py importe repository.py
   # repository.py importe service.py
   ```

### ✅ TOUJOURS faire

1. **Router → Service → Repository**
   ```python
   # ✅ BON
   @router.post("/chat")
   async def chat(request: ChatRequest):
       result = await ChatService.chat_with_rag(request.query)  # ✅ Appel service
       return ChatResponse(**result)
   ```

2. **Service utilise Repository pour DB**
   ```python
   # ✅ BON
   class ChatService:
       @staticmethod
       async def save_conversation(db: AsyncSession, data: dict):
           return await ChatRepository.create(db, data)  # ✅ Délègue à repository
   ```

3. **Type hints partout**
   ```python
   # ✅ BON
   async def get_user(db: AsyncSession, user_id: int) -> User:
       ...
   ```

4. **Docstrings**
   ```python
   # ✅ BON
   async def create_user(db: AsyncSession, email: str) -> User:
       """
       Crée un nouvel utilisateur

       Args:
           db: Session de base de données
           email: Email de l'utilisateur

       Returns:
           L'utilisateur créé

       Raises:
           HTTPException: Si l'email existe déjà
       """
   ```

---

## 🚀 Comment Continuer la Migration

### 1. Migrer Ingestion (Facile - ~100 lignes)

```bash
# Créer les fichiers
touch app/features/ingestion/router.py
touch app/features/ingestion/service.py
touch app/features/ingestion/schemas.py
```

**Code source :** Lignes 505-610 de `main.py.old`

**Extraire :**
- `UploadResponse` → `schemas.py`
- Logique upload → `service.py`
- Endpoint `/upload` → `router.py`

### 2. Migrer Audit (Moyen - ~300 lignes)

```bash
touch app/features/audit/service.py
touch app/features/audit/repository.py
```

**Code source :** `app/audit_service.py`

**Déplacer :**
- Classe `AuditService` → `service.py`
- Opérations DB → `repository.py`

### 3. Migrer Admin (Difficile - ~1500 lignes)

Diviser en sous-features :

```bash
mkdir -p app/features/admin/{roles,conversations,documents,sessions}

# Ou tout mettre dans admin/ avec des fichiers séparés
touch app/features/admin/router_roles.py
touch app/features/admin/router_conversations.py
touch app/features/admin/router_documents.py
touch app/features/admin/service.py
touch app/features/admin/repository.py
```

**Code source :** Lignes 612-2086 de `main.py.old`

---

## 📝 Checklist Finale

Avant de remplacer `main.py` par `main_new.py` :

- [ ] Toutes les features migrées
- [ ] Tous les endpoints testés
- [ ] Aucune régression fonctionnelle
- [ ] Tests unitaires passent
- [ ] Configuration dans `.env` correcte
- [ ] `pydantic-settings` ajouté à `requirements.txt`
- [ ] Documentation mise à jour
- [ ] CLAUDE.md respecté :
  - [ ] Structure features/ ✅
  - [ ] main.py <50 lignes ✅
  - [ ] Type hints partout
  - [ ] Docstrings présentes
  - [ ] Logger utilisé (pas print)
  - [ ] Dependencies injectées

---

## 🎓 Ressources

- **CLAUDE.md** : Référence absolue du projet
- **MIGRATION_STATUS.md** : État actuel de la migration
- **main.py.old** : Code source original (2102 lignes)
- **main_new.py** : Nouveau point d'entrée (<50 lignes)

---

Bon courage pour la suite de la migration ! 🚀
