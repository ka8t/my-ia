# Plan : Gestion des Documents (Frontend - Utilisateur & Admin)

## Objectif
Permettre à l'utilisateur ET à l'administrateur de gérer les documents (lister, voir, télécharger, rechercher, remplacer, modifier la visibilité) via une interface dédiée dans le frontend.

**Scope :**
- **Utilisateur** : Gère ses propres documents uniquement
- **Admin** : Gère tous les documents de tous les utilisateurs + actions supplémentaires (deindex/reindex)

---

## 1. État Actuel

### Backend (API existante)

#### Endpoints Utilisateur (`/documents`)
| Endpoint | Méthode | Description | Status |
|----------|---------|-------------|--------|
| `/documents/` | GET | Lister ses documents (pagination) | ✅ Existe |
| `/documents/{id}` | GET | Détails d'un document | ✅ Existe |
| `/documents/{id}` | DELETE | Supprimer un document | ✅ Existe |
| `/documents/{id}/visibility` | PATCH | Modifier visibilité (public/private) | ✅ Existe |
| `/upload/v2` | POST | Upload avec visibilité | ✅ Existe |
| `/documents/{id}/download` | GET | Télécharger le fichier | ❌ À créer |
| `/documents/search` | GET | Rechercher par nom/type | ❌ À créer |
| `/documents/{id}` | PUT | Remplacer un document | ❌ À créer |

#### Endpoints Admin (`/admin/documents`)
| Endpoint | Méthode | Description | Status |
|----------|---------|-------------|--------|
| `/admin/documents` | GET | Lister TOUS les documents (filtres user_id, file_type) | ✅ Existe |
| `/admin/documents/{id}` | DELETE | Supprimer n'importe quel document | ✅ Existe |
| `/admin/documents/{id}/visibility` | PATCH | Modifier visibilité (tout document) | ✅ Existe |
| `/admin/documents/{id}/deindex` | POST | Désactiver du RAG (garder en DB) | ✅ Existe |
| `/admin/documents/{id}/reindex` | POST | Réactiver dans le RAG | ✅ Existe |
| `/admin/bulk/documents` | DELETE | Suppression en masse (max 100) | ✅ Existe |
| `/admin/documents/{id}/download` | GET | Télécharger n'importe quel fichier | ❌ À créer |
| `/admin/documents/search` | GET | Rechercher dans tous les documents | ❌ À créer |

### Frontend (État actuel)
- Upload via modal existant (`js/modules/upload.js`)
- Liste des documents dans le modal d'upload (basique)
- Aucune page dédiée à la gestion des documents
- Aucune fonctionnalité de recherche/filtrage

---

## 2. Couche d'Abstraction Storage (Nouveau)

### 2.1 Architecture StorageService

```
┌─────────────────────────────────────────────────────────────┐
│                      APPLICATION                             │
│   DocumentService / IngestionService / AdminService          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE SERVICE                           │
│         (Façade avec quotas, validations, stats)            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   STORAGE BACKEND                            │
│                  (Interface abstraite)                       │
└─────────┬───────────────────┬───────────────────┬───────────┘
          │                   │                   │
          ▼                   ▼                   ▼
   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
   │LocalBackend │     │MinIOBackend │     │  S3Backend  │
   │  (actuel)   │     │  (futur)    │     │  (futur)    │
   └─────────────┘     └─────────────┘     └─────────────┘
```

### 2.2 Structure des fichiers

```
app/
└── common/
    └── storage/
        ├── __init__.py           # Exports publics
        ├── base.py               # StorageBackend (interface ABC)
        ├── service.py            # StorageService (façade)
        ├── schemas.py            # FileInfo, StorageStats, QuotaInfo
        ├── exceptions.py         # StorageError, QuotaExceeded, FileNotFound
        └── backends/
            ├── __init__.py
            ├── local.py          # LocalStorageBackend (implémentation)
            ├── minio.py          # MinIOStorageBackend (futur)
            └── s3.py             # S3StorageBackend (futur)
```

### 2.3 Interface StorageBackend

```python
# base.py
from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional, AsyncIterator
from .schemas import FileInfo, StorageStats, UserStorageStats

class StorageBackend(ABC):
    """Interface abstraite pour les backends de stockage."""

    # === CRUD Fichiers ===
    @abstractmethod
    async def save(self, user_id: UUID, filename: str, content: bytes) -> str:
        """Sauvegarde un fichier. Retourne le chemin relatif."""
        pass

    @abstractmethod
    async def get(self, file_path: str) -> bytes:
        """Récupère le contenu d'un fichier."""
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """Supprime un fichier. Retourne True si supprimé."""
        pass

    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """Vérifie si un fichier existe."""
        pass

    # === Métadonnées ===
    @abstractmethod
    async def get_file_info(self, file_path: str) -> FileInfo:
        """Retourne les métadonnées d'un fichier."""
        pass

    @abstractmethod
    async def list_user_files(self, user_id: UUID) -> list[str]:
        """Liste les chemins des fichiers d'un utilisateur."""
        pass

    # === Statistiques ===
    @abstractmethod
    async def get_storage_stats(self) -> StorageStats:
        """Statistiques globales du storage."""
        pass

    @abstractmethod
    async def get_user_stats(self, user_id: UUID) -> UserStorageStats:
        """Statistiques d'un utilisateur."""
        pass

    # === Téléchargement ===
    @abstractmethod
    async def get_download_path(self, file_path: str) -> str:
        """Retourne le chemin absolu ou URL pour téléchargement."""
        pass

    @abstractmethod
    async def stream_file(self, file_path: str) -> AsyncIterator[bytes]:
        """Stream le fichier par chunks (pour gros fichiers)."""
        pass
```

### 2.4 Schemas Storage

```python
# schemas.py
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional

@dataclass
class FileInfo:
    """Métadonnées d'un fichier stocké."""
    path: str
    filename: str
    size: int                    # bytes
    mime_type: str
    created_at: datetime
    modified_at: datetime

@dataclass
class StorageStats:
    """Statistiques globales du storage."""
    total_bytes: int             # Espace total
    used_bytes: int              # Espace utilisé
    free_bytes: int              # Espace libre
    file_count: int              # Nombre de fichiers
    user_count: int              # Nombre d'utilisateurs avec fichiers

@dataclass
class UserStorageStats:
    """Statistiques de stockage d'un utilisateur."""
    user_id: UUID
    used_bytes: int              # Espace utilisé
    file_count: int              # Nombre de fichiers
    quota_bytes: Optional[int]   # Quota (None = illimité)
    quota_used_percent: float    # % du quota utilisé (0-100)

@dataclass
class QuotaConfig:
    """Configuration des quotas."""
    default_quota_bytes: int         # Quota par défaut (ex: 100 MB)
    max_file_size_bytes: int         # Taille max par fichier (ex: 50 MB)
    allowed_mime_types: list[str]    # Types autorisés (ex: ["application/pdf", ...])
    blocked_extensions: list[str]    # Extensions bloquées (ex: [".exe", ".bat"])
```

### 2.5 StorageService (Façade)

```python
# service.py
from uuid import UUID
from typing import Optional
from .base import StorageBackend
from .schemas import StorageStats, UserStorageStats, QuotaConfig, FileInfo
from .exceptions import QuotaExceededError, InvalidFileTypeError, FileTooLargeError

class StorageService:
    """
    Service de haut niveau pour la gestion du stockage.
    Gère les quotas, validations et statistiques.
    """

    def __init__(self, backend: StorageBackend, quota_config: QuotaConfig):
        self.backend = backend
        self.config = quota_config

    # === Upload avec validations ===
    async def upload(
        self,
        user_id: UUID,
        filename: str,
        content: bytes,
        mime_type: str,
        check_quota: bool = True
    ) -> str:
        """
        Upload un fichier avec vérifications.

        Raises:
            QuotaExceededError: Si quota dépassé
            InvalidFileTypeError: Si type MIME non autorisé
            FileTooLargeError: Si fichier trop gros
        """
        # Vérifier taille max
        if len(content) > self.config.max_file_size_bytes:
            raise FileTooLargeError(len(content), self.config.max_file_size_bytes)

        # Vérifier type MIME
        if mime_type not in self.config.allowed_mime_types:
            raise InvalidFileTypeError(mime_type, self.config.allowed_mime_types)

        # Vérifier extension
        ext = Path(filename).suffix.lower()
        if ext in self.config.blocked_extensions:
            raise InvalidFileTypeError(ext, reason="extension bloquée")

        # Vérifier quota utilisateur
        if check_quota and self.config.default_quota_bytes:
            user_stats = await self.backend.get_user_stats(user_id)
            new_total = user_stats.used_bytes + len(content)
            quota = user_stats.quota_bytes or self.config.default_quota_bytes
            if new_total > quota:
                raise QuotaExceededError(user_id, quota, new_total)

        return await self.backend.save(user_id, filename, content)

    # === Download ===
    async def download(self, file_path: str) -> bytes:
        """Télécharge un fichier."""
        return await self.backend.get(file_path)

    async def get_download_path(self, file_path: str) -> str:
        """Retourne le chemin/URL de téléchargement."""
        return await self.backend.get_download_path(file_path)

    # === Suppression ===
    async def delete(self, file_path: str) -> bool:
        """Supprime un fichier."""
        return await self.backend.delete(file_path)

    # === Statistiques ===
    async def get_global_stats(self) -> StorageStats:
        """Stats globales pour dashboard admin."""
        return await self.backend.get_storage_stats()

    async def get_user_stats(self, user_id: UUID) -> UserStorageStats:
        """Stats d'un utilisateur avec quota."""
        stats = await self.backend.get_user_stats(user_id)
        quota = stats.quota_bytes or self.config.default_quota_bytes
        if quota:
            stats.quota_used_percent = (stats.used_bytes / quota) * 100
        return stats

    # === Quota Admin ===
    async def check_user_can_upload(self, user_id: UUID, file_size: int) -> bool:
        """Vérifie si l'utilisateur peut uploader (sans lever d'exception)."""
        try:
            user_stats = await self.backend.get_user_stats(user_id)
            quota = user_stats.quota_bytes or self.config.default_quota_bytes
            return (user_stats.used_bytes + file_size) <= quota
        except Exception:
            return False

    async def get_user_remaining_quota(self, user_id: UUID) -> int:
        """Retourne l'espace restant pour un utilisateur (bytes)."""
        user_stats = await self.backend.get_user_stats(user_id)
        quota = user_stats.quota_bytes or self.config.default_quota_bytes
        return max(0, quota - user_stats.used_bytes)
```

### 2.6 Versioning des Documents

#### Stratégie ChromaDB : Option A (Version courante uniquement)

**Décision :** Seule la version courante est indexée dans ChromaDB.
- Les anciennes versions restent téléchargeables sur le disque
- Le RAG retourne toujours des informations à jour
- Pas de pollution avec des données obsolètes

```
Workflow de remplacement (PUT /documents/{id})
    │
    ├─→ 1. Sauvegarder nouveau fichier (v2) sur disque
    ├─→ 2. Créer entrée dans document_versions (v1 archivé)
    ├─→ 3. SUPPRIMER chunks v1 dans ChromaDB
    ├─→ 4. Parser et chunker v2
    ├─→ 5. Embedder et INSÉRER chunks v2 dans ChromaDB
    └─→ 6. Mettre à jour document.chunk_count en DB
```

#### Table document_versions

```python
class DocumentVersion(Base):
    """Historique des versions d'un document."""
    __tablename__ = "document_versions"

    id: UUID (PK)
    document_id: UUID (FK -> documents.id)
    version_number: int                    # 1, 2, 3...
    file_path: str                         # Chemin du fichier versionné
    file_size: int
    file_hash: str                         # Pour détecter les vrais changements
    chunk_count: int                       # Nombre de chunks (pour info)
    created_at: datetime
    created_by: UUID (FK -> users.id)      # Qui a fait le remplacement
    comment: Optional[str]                 # Note optionnelle
```

#### Structure de stockage

```
/data/uploads/
├── {user_id}/
│   ├── {document_id}/
│   │   ├── v1_{filename}                  # Version 1 (originale, archivée)
│   │   ├── v2_{filename}                  # Version 2 (courante)
│   │   └── current -> v2_{filename}       # Lien symbolique vers version active
```

#### Endpoints versioning

```python
GET  /documents/{id}/versions              # Liste des versions
GET  /documents/{id}/versions/{version}    # Télécharger une version spécifique
POST /documents/{id}/versions/{version}/restore  # Restaurer une ancienne version
```

#### Restauration d'une ancienne version

```
POST /documents/{id}/versions/1/restore
    │
    ├─→ 1. Copier v1 comme nouvelle version (v3)
    ├─→ 2. Créer entrée document_versions pour v3
    ├─→ 3. SUPPRIMER chunks v2 dans ChromaDB
    ├─→ 4. Parser et chunker v3 (copie de v1)
    ├─→ 5. Embedder et INSÉRER chunks v3 dans ChromaDB
    └─→ 6. Mettre à jour document (file_path, chunk_count)
```

**Note :** La restauration crée une nouvelle version (pas de réécriture de l'historique).

### 2.7 Partage de Documents (Préparé pour le futur)

```python
# Enum avec 3 valeurs dès le départ
class DocumentVisibility(str, enum.Enum):
    PUBLIC = "public"      # Visible par tous dans le RAG
    PRIVATE = "private"    # Visible uniquement par le propriétaire
    SHARED = "shared"      # Visible par les utilisateurs spécifiés (futur)

# Table pour les partages (créée maintenant, utilisée plus tard)
class DocumentShare(Base):
    """Partage d'un document avec un utilisateur spécifique."""
    __tablename__ = "document_shares"

    id: UUID (PK)
    document_id: UUID (FK -> documents.id)
    shared_with_user_id: UUID (FK -> users.id)
    permission: str = "read"               # "read" | "write" (futur)
    created_at: datetime
    created_by: UUID (FK -> users.id)      # Qui a partagé

    # Contrainte unique
    __table_args__ = (
        UniqueConstraint('document_id', 'shared_with_user_id'),
    )
```

**Note :** La fonctionnalité de partage ne sera pas implémentée dans cette itération, mais l'enum et la table sont prêts pour éviter des migrations complexes plus tard.

### 2.8 Exceptions Storage

```python
# exceptions.py
from uuid import UUID

class StorageError(Exception):
    """Erreur de base pour le storage."""
    pass

class FileNotFoundError(StorageError):
    """Fichier non trouvé."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"Fichier non trouvé: {file_path}")

class QuotaExceededError(StorageError):
    """Quota utilisateur dépassé."""
    def __init__(self, user_id: UUID, quota: int, requested: int):
        self.user_id = user_id
        self.quota = quota
        self.requested = requested
        super().__init__(
            f"Quota dépassé pour {user_id}: {requested} > {quota} bytes"
        )

class FileTooLargeError(StorageError):
    """Fichier trop volumineux."""
    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(f"Fichier trop gros: {size} > {max_size} bytes")

class InvalidFileTypeError(StorageError):
    """Type de fichier non autorisé."""
    def __init__(self, file_type: str, allowed: list = None, reason: str = None):
        self.file_type = file_type
        self.allowed = allowed
        self.reason = reason
        msg = f"Type non autorisé: {file_type}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)
```

### 2.7 Configuration Settings

```python
# core/config.py (ajouts)
class Settings(BaseSettings):
    # ... existant ...

    # === Storage ===
    storage_backend: str = "local"                    # "local" | "minio" | "s3"
    storage_local_path: str = "/data/uploads"         # Chemin pour LocalBackend

    # === Quotas ===
    storage_default_quota_mb: int = 100               # Quota par défaut (MB)
    storage_max_file_size_mb: int = 50                # Taille max fichier (MB)
    storage_allowed_mime_types: str = "application/pdf,text/plain,text/csv,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    storage_blocked_extensions: str = ".exe,.bat,.sh,.cmd,.ps1,.dll"

    # === MinIO (futur) ===
    storage_minio_endpoint: Optional[str] = None
    storage_minio_access_key: Optional[str] = None
    storage_minio_secret_key: Optional[str] = None
    storage_minio_bucket: str = "documents"

    # === S3 (futur) ===
    storage_s3_bucket: Optional[str] = None
    storage_s3_region: Optional[str] = None
```

### 2.8 Injection de dépendance

```python
# core/deps.py (ajouts)
from functools import lru_cache
from app.common.storage import StorageService, StorageBackend, LocalStorageBackend
from app.common.storage.schemas import QuotaConfig

@lru_cache
def get_quota_config() -> QuotaConfig:
    """Configuration des quotas depuis settings."""
    return QuotaConfig(
        default_quota_bytes=settings.storage_default_quota_mb * 1024 * 1024,
        max_file_size_bytes=settings.storage_max_file_size_mb * 1024 * 1024,
        allowed_mime_types=settings.storage_allowed_mime_types.split(","),
        blocked_extensions=settings.storage_blocked_extensions.split(",")
    )

@lru_cache
def get_storage_backend() -> StorageBackend:
    """Factory pour le backend de stockage."""
    if settings.storage_backend == "local":
        return LocalStorageBackend(settings.storage_local_path)
    elif settings.storage_backend == "minio":
        # Futur: return MinIOStorageBackend(...)
        raise NotImplementedError("MinIO backend not implemented yet")
    elif settings.storage_backend == "s3":
        # Futur: return S3StorageBackend(...)
        raise NotImplementedError("S3 backend not implemented yet")
    raise ValueError(f"Unknown storage backend: {settings.storage_backend}")

def get_storage_service() -> StorageService:
    """Service de stockage avec quotas."""
    return StorageService(
        backend=get_storage_backend(),
        quota_config=get_quota_config()
    )
```

### 2.9 Endpoints Storage (Admin)

```python
# Nouveaux endpoints admin pour gérer le storage
GET  /admin/storage/stats          # Stats globales (espace, fichiers)
GET  /admin/storage/users          # Liste utilisateurs avec leur usage
GET  /admin/storage/users/{id}     # Stats d'un utilisateur spécifique
PUT  /admin/storage/users/{id}/quota  # Modifier quota d'un utilisateur
```

### 2.10 Frontend - Affichage Quota Utilisateur

```
┌─────────────────────────────────────────────────────────┐
│ MES DOCUMENTS                                    [×]    │
├─────────────────────────────────────────────────────────┤
│ Espace utilisé: 45.2 MB / 100 MB                       │
│ [████████████████░░░░░░░░░░░░░░] 45%                   │
├─────────────────────────────────────────────────────────┤
│ [Rechercher...        ] [Type ▼] [Visibilité ▼]        │
...
```

### 2.11 Frontend - Dashboard Admin Storage

```
┌──────────────────────────────────────────────────────────────────┐
│ STOCKAGE (Admin)                                                  │
├──────────────────────────────────────────────────────────────────┤
│ Espace total: 50 GB | Utilisé: 12.4 GB | Libre: 37.6 GB         │
│ [████████░░░░░░░░░░░░░░░░░░░░░░░] 25%                            │
│                                                                   │
│ 156 fichiers | 23 utilisateurs                                   │
├──────────────────────────────────────────────────────────────────┤
│ Top utilisateurs:                                                 │
│ 1. admin@example.com     4.2 GB / 100 MB  [Modifier quota]       │
│ 2. user1@example.com     2.1 GB / 100 MB  [Modifier quota]       │
│ 3. user2@example.com     890 MB / 100 MB  [Modifier quota]       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Modifications Backend - Endpoints Documents

### 3.1 Endpoints Utilisateur (à créer)

#### Download
**Fichier:** `app/features/documents/router.py`

```python
@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> FileResponse:
    """Télécharge le fichier original du document (owner only)."""
```

#### Recherche
```python
@router.get("/search")
async def search_documents(
    query: str = Query(..., min_length=1),
    file_type: Optional[str] = None,
    visibility: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> DocumentListResponse:
    """Recherche dans les documents de l'utilisateur."""
```

#### Remplacement
```python
@router.put("/{document_id}")
async def replace_document(
    document_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> DocumentRead:
    """Remplace le contenu d'un document existant (owner only)."""
```

### 3.2 Endpoints Admin (à créer)

#### Download Admin
**Fichier:** `app/features/admin/router.py`

```python
@router.get("/documents/{document_id}/download")
async def admin_download_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
) -> FileResponse:
    """Télécharge n'importe quel fichier (admin only)."""
```

#### Recherche Admin
```python
@router.get("/documents/search")
async def admin_search_documents(
    query: str = Query(..., min_length=1),
    user_id: Optional[UUID] = None,  # Filtre par propriétaire
    file_type: Optional[str] = None,
    visibility: Optional[str] = None,
    is_indexed: Optional[bool] = None,  # Filtre par statut indexation
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
) -> DocumentListResponse:
    """Recherche dans TOUS les documents du système."""
```

---

## 4. Modifications Frontend

### 4.1 Structure des fichiers à créer/modifier

```
frontend/
├── css/
│   └── components/
│       └── documents.css      # ✨ À CRÉER (styles partagés user/admin)
├── js/
│   ├── services/
│   │   └── api.js             # ⚙️ À MODIFIER (méthodes user + admin)
│   └── modules/
│       ├── documents.js       # ✨ À CRÉER (module utilisateur)
│       ├── admin-documents.js # ✨ À CRÉER (module admin)
│       └── upload.js          # ⚙️ À MODIFIER (intégration)
└── index.html                 # ⚙️ À MODIFIER (ajouter sections user + admin)
```

### 4.2 API Service - Nouvelles méthodes
**Fichier:** `frontend/js/services/api.js`

```javascript
// === Documents Utilisateur ===
async listDocuments(limit = 50, offset = 0) { ... }
async getDocument(documentId) { ... }
async deleteDocument(documentId) { ... }
async updateDocumentVisibility(documentId, visibility) { ... }
async downloadDocument(documentId) { ... }
async searchDocuments(query, filters = {}) { ... }
async replaceDocument(documentId, file) { ... }

// === Documents Admin ===
async adminListDocuments(filters = {}) { ... }  // user_id, file_type, is_indexed
async adminDeleteDocument(documentId) { ... }
async adminUpdateDocumentVisibility(documentId, visibility) { ... }
async adminDownloadDocument(documentId) { ... }
async adminSearchDocuments(query, filters = {}) { ... }
async adminDeindexDocument(documentId) { ... }
async adminReindexDocument(documentId) { ... }
async adminBulkDeleteDocuments(documentIds) { ... }
```

### 4.3 Module Documents Utilisateur
**Fichier:** `frontend/js/modules/documents.js`

**Fonctionnalités:**
1. **Liste des documents** avec pagination
2. **Barre de recherche** (filtre par nom, type)
3. **Actions par document:**
   - Voir les détails
   - Télécharger
   - Remplacer
   - Toggle visibilité (public/privé)
   - Supprimer
4. **Upload** intégré avec sélection de visibilité
5. **Tri** par date, nom, taille

### 4.4 Module Documents Admin
**Fichier:** `frontend/js/modules/admin-documents.js`

**Fonctionnalités supplémentaires (en plus de celles utilisateur):**
1. **Vue de tous les documents** (tous utilisateurs)
2. **Filtres avancés:**
   - Par utilisateur (dropdown)
   - Par statut indexation (indexé/désindexé)
   - Par type de fichier
   - Par visibilité
3. **Actions admin:**
   - Deindex/Reindex (activer/désactiver du RAG)
   - Suppression en masse (sélection multiple)
   - Voir le propriétaire du document
4. **Indicateurs visuels:**
   - Badge "Désindexé" pour documents hors RAG
   - Nom/email du propriétaire affiché

### 4.5 Interface Utilisateur

#### Vue Utilisateur (Panel latéral)
```
┌─────────────────────────────────────────────────────────┐
│ MES DOCUMENTS                                    [×]    │
├─────────────────────────────────────────────────────────┤
│ [Rechercher...        ] [Type ▼] [Visibilité ▼]        │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ rapport.pdf                              [Public]   │ │
│ │ PDF | 2.4 MB | 12 chunks | 25/12/2024              │ │
│ │ [Voir] [Telecharger] [Remplacer] [Prive] [Suppr]   │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ notes.txt                                [Prive]    │ │
│ │ TXT | 156 KB | 3 chunks | 24/12/2024               │ │
│ │ [Voir] [Telecharger] [Remplacer] [Public] [Suppr]  │ │
│ └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│ 1-10 sur 42                        [< Prec] [Suiv >]   │
│                        [+ Ajouter un document]          │
└─────────────────────────────────────────────────────────┘
```

#### Vue Admin (Panel étendu)
```
┌──────────────────────────────────────────────────────────────────┐
│ GESTION DES DOCUMENTS (Admin)                             [×]    │
├──────────────────────────────────────────────────────────────────┤
│ [Rechercher...    ] [User ▼] [Type ▼] [Visib ▼] [Index ▼]       │
│                                        [Supprimer selection]     │
├──────────────────────────────────────────────────────────────────┤
│ [ ] rapport.pdf                    user@ex.com    [Public]       │
│     PDF | 2.4 MB | 12 chunks | 25/12/2024        [Indexe]        │
│     [Voir] [DL] [Visib] [Deindexer] [Suppr]                      │
├──────────────────────────────────────────────────────────────────┤
│ [ ] data.csv                       admin@ex.com   [Prive]        │
│     CSV | 890 KB | 8 chunks | 24/12/2024         [Desindexe]     │
│     [Voir] [DL] [Visib] [Reindexer] [Suppr]                      │
├──────────────────────────────────────────────────────────────────┤
│ 1-10 sur 156                                   [< Prec] [Suiv >] │
└──────────────────────────────────────────────────────────────────┘
```

### 4.6 Composants UI à créer

1. **DocumentCard** - Affichage d'un document (partagé user/admin)
2. **DocumentFilters** - Barre de recherche + filtres (version simple/avancée)
3. **DocumentActions** - Boutons d'action (user: 5, admin: 6)
4. **VisibilityBadge** - Badge public/privé
5. **IndexStatusBadge** - Badge indexé/désindexé (admin only)
6. **OwnerInfo** - Affichage propriétaire (admin only)
7. **Pagination** - Navigation pages
8. **BulkActions** - Actions en masse avec checkboxes (admin only)
9. **UploadDropzone** - Zone de drop améliorée

---

## 5. Étapes d'Implémentation

### Phase 0 : Backend - Couche Storage (Prérequis)
1. [ ] Créer `app/common/storage/` (structure dossiers)
2. [ ] Implémenter `base.py` (interface StorageBackend)
3. [ ] Implémenter `schemas.py` (FileInfo, StorageStats, QuotaConfig, etc.)
4. [ ] Implémenter `exceptions.py` (StorageError, QuotaExceeded, etc.)
5. [ ] Implémenter `backends/local.py` (LocalStorageBackend avec support versioning)
6. [ ] Implémenter `service.py` (StorageService avec quotas)
7. [ ] Ajouter settings dans `core/config.py`
8. [ ] Ajouter dépendances dans `core/deps.py`
9. [ ] Créer migration : table `document_versions`
10. [ ] Créer migration : table `document_shares` (préparation futur)
11. [ ] Créer migration : ajouter `shared` à l'enum `DocumentVisibility`
12. [ ] Écrire les tests unitaires Storage
13. [ ] Valider les tests

### Phase 1 : Backend - Endpoints Storage Admin
1. [ ] Créer `GET /admin/storage/stats` (stats globales)
2. [ ] Créer `GET /admin/storage/users` (liste users + usage)
3. [ ] Créer `GET /admin/storage/users/{id}` (stats user)
4. [ ] Créer `PUT /admin/storage/users/{id}/quota` (modifier quota)
5. [ ] Écrire les tests unitaires
6. [ ] Valider les tests

### Phase 2 : Backend - Endpoints Documents Utilisateur
1. [ ] Créer endpoint `/documents/{id}/download` (user)
2. [ ] Créer endpoint `/documents/search` (user, full-text + métadonnées)
3. [ ] Créer endpoint `/documents/{id}` PUT (remplacement avec versioning)
4. [ ] Créer endpoint `/documents/{id}/versions` GET (liste versions)
5. [ ] Créer endpoint `/documents/{id}/versions/{v}` GET (télécharger version)
6. [ ] Créer endpoint `/documents/{id}/versions/{v}/restore` POST (restaurer)
7. [ ] Créer endpoint `/documents/storage` (stats quota user)
8. [ ] Intégrer StorageService dans DocumentService
9. [ ] Écrire les tests unitaires
10. [ ] Valider les tests

### Phase 3 : Backend - Endpoints Documents Admin
1. [ ] Créer endpoint `/admin/documents/{id}/download`
2. [ ] Créer endpoint `/admin/documents/search`
3. [ ] Ajouter les filtres avancés à `/admin/documents` (is_indexed)
4. [ ] Écrire les tests unitaires admin
5. [ ] Valider les tests

### Phase 4 : Frontend - Base (User)
1. [ ] Créer `css/components/documents.css`
2. [ ] Ajouter méthodes API utilisateur dans `api.js`
3. [ ] Créer `js/modules/documents.js` (structure de base)
4. [ ] Ajouter section HTML utilisateur dans `index.html`
5. [ ] Intégrer le script dans la page

### Phase 5 : Frontend - Fonctionnalités User
1. [ ] Implémenter la liste des documents avec quota (barre de progression)
2. [ ] Ajouter la pagination
3. [ ] Implémenter la recherche/filtres (full-text + métadonnées)
4. [ ] Ajouter les actions (voir, télécharger, supprimer)
5. [ ] Implémenter le toggle visibilité
6. [ ] Ajouter la fonctionnalité de remplacement (avec versioning)
7. [ ] Ajouter vue historique des versions
8. [ ] Ajouter action restaurer une version
9. [ ] Afficher erreur si quota dépassé lors de l'upload

### Phase 6 : Frontend - Module Admin
1. [ ] Ajouter méthodes API admin dans `api.js`
2. [ ] Créer `js/modules/admin-documents.js`
3. [ ] Ajouter section HTML admin dans `index.html`
4. [ ] Implémenter filtres avancés (user, indexation)
5. [ ] Implémenter actions admin (deindex/reindex)
6. [ ] Implémenter sélection multiple + suppression en masse
7. [ ] Afficher propriétaire + badges statut
8. [ ] Dashboard storage (stats globales + top users)
9. [ ] Modifier quota utilisateur

### Phase 7 : Intégration & Polish
1. [ ] Intégrer avec le modal d'upload existant
2. [ ] Ajouter les notifications toast
3. [ ] Gérer les états de chargement
4. [ ] Ajouter les confirmations de suppression
5. [ ] Responsive design (mobile)
6. [ ] Tests manuels (user + admin)

---

## 6. Schémas Pydantic (Backend)

### DocumentSearchParams
```python
class DocumentSearchParams(BaseModel):
    query: str = Field(..., min_length=1, max_length=100)
    file_type: Optional[str] = None
    visibility: Optional[DocumentVisibility] = None
    sort_by: str = Field(default="created_at", pattern="^(created_at|filename|file_size)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
```

### DocumentReplace
```python
class DocumentReplace(BaseModel):
    """Réponse après remplacement"""
    old_document: DocumentRead
    new_document: DocumentRead
    message: str
```

---

## 7. Points d'Attention

### Sécurité
- Vérifier l'ownership avant chaque opération (user)
- Admin peut accéder à tous les documents (vérifier rôle)
- Valider les types MIME pour l'upload/remplacement
- Limiter la taille des fichiers
- Sanitizer les noms de fichiers
- Audit log pour les actions admin sensibles (deindex, bulk delete)

### Performance
- Pagination obligatoire (max 50 items)
- Debounce sur la recherche (300ms)
- Cache côté client pour les listes
- Lazy loading des détails

### UX
- Feedback visuel immédiat (loading states)
- Confirmations avant actions destructives
- Messages d'erreur clairs
- Accessibilité (ARIA labels)

### Stockage Fichiers
**DÉCIDÉ:** Système de fichiers local avec couche d'abstraction (StorageService)
- Backend actuel : `LocalStorageBackend` (`/data/uploads/{user_id}/`)
- Évolutif vers MinIO/S3 sans changer le code métier
- Quotas intégrés dès le départ

---

## 8. Estimation des Efforts

| Phase | Description | Complexité | Fichiers |
|-------|-------------|------------|----------|
| Phase 0 | Couche Storage + migrations (versions, shares) | Haute | 10-12 fichiers |
| Phase 1 | Backend Storage Admin | Faible | 2-3 fichiers |
| Phase 2 | Backend Documents User (+ versioning) | Haute | 4-5 fichiers |
| Phase 3 | Backend Documents Admin | Faible | 2 fichiers |
| Phase 4 | Frontend Base User (modal fullscreen) | Moyenne | 4 fichiers |
| Phase 5 | Frontend Fonctionnalités User (+ versions) | Haute | 2-3 fichiers |
| Phase 6 | Frontend Module Admin | Haute | 3-4 fichiers |
| Phase 7 | Polish & Intégration | Moyenne | Existants |

---

## 9. Questions Clarifiées

| # | Question | Décision |
|---|----------|----------|
| 1 | Stockage des fichiers | ✅ Local avec abstraction (StorageService) |
| 2 | Historique des versions | ✅ Oui, on conserve les versions sur disque |
| 3 | Interface | ✅ Modal fullscreen pour l'utilisateur |
| 4 | Recherche | ✅ Full-text + métadonnées |
| 5 | Partage (futur) | ✅ Prévoir enum `shared` + table `document_shares` |
| 6 | Versioning ChromaDB | ✅ Option A : seule la version courante dans le RAG |

---

## 10. Comparatif Fonctionnalités User vs Admin

| Fonctionnalité | Utilisateur | Admin |
|----------------|-------------|-------|
| Lister ses documents | Oui | Oui |
| Lister tous les documents | Non | Oui |
| Filtrer par utilisateur | Non | Oui |
| Filtrer par type/visibilité | Oui | Oui |
| Filtrer par statut indexation | Non | Oui |
| Voir détails | Oui | Oui |
| Télécharger | Oui (ses docs) | Oui (tous) |
| Modifier visibilité | Oui (ses docs) | Oui (tous) |
| Remplacer | Oui (ses docs) | Non* |
| Supprimer | Oui (ses docs) | Oui (tous) |
| Deindex/Reindex | Non | Oui |
| Suppression en masse | Non | Oui |
| Voir propriétaire | Non | Oui |

*Le remplacement admin n'est pas prévu car cela modifierait les documents d'autres utilisateurs sans leur consentement.

| **Fonctionnalités Storage** | Utilisateur | Admin |
|-----------------------------|-------------|-------|
| Voir son quota/usage | Oui | Oui |
| Voir stats globales storage | Non | Oui |
| Voir usage de tous les users | Non | Oui |
| Modifier quota d'un user | Non | Oui |

---

## Prochaines Actions

**Toutes les questions sont clarifiées. Plan prêt pour implémentation.**

1. Commencer par **Phase 0** : Couche Storage + migrations
2. Procéder séquentiellement phase par phase
3. Tests unitaires à chaque phase avant de passer à la suivante
