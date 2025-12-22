# Plan de Démarrage - Implémentation Authentification

**Date :** 21 décembre 2025
**Objectif :** Démarrer l'implémentation du système d'authentification de manière progressive et testable

---

## 🎯 Approche Recommandée

**Stratégie : "Backend-First, Iterate Fast"**

Commencer par les fondations backend puis ajouter progressivement les couches :
1. ✅ Base de données + Migrations
2. ✅ Backend Auth (modèles + endpoints de base)
3. ✅ Tests backend
4. ✅ Frontend minimal (login page)
5. ✅ Intégration complète

**Avantages :**
- Validation rapide de l'architecture
- Tests possibles à chaque étape (via curl/Postman)
- Détection précoce des problèmes
- Déploiement incrémental

---

## 📅 Phase 1 : Fondations Backend (Jour 1-2)

### Étape 1.1 : Setup Infrastructure Base de Données (2h)

**Objectif :** Créer la base de données `myia_auth` et configurer les connexions

**Actions :**

1. **Créer le script d'initialisation PostgreSQL**
```bash
# Créer le fichier
touch scripts/init-multiple-databases.sh
chmod +x scripts/init-multiple-databases.sh
```

Contenu :
```bash
#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE myia_auth;
    GRANT ALL PRIVILEGES ON DATABASE myia_auth TO n8n;
EOSQL

echo "Database myia_auth created successfully!"
```

2. **Modifier docker-compose.yml**
```yaml
# Ajouter au service postgres:
environment:
  - POSTGRES_MULTIPLE_DATABASES=n8n,myia_auth
volumes:
  - ./scripts/init-multiple-databases.sh:/docker-entrypoint-initdb.d/init-multiple-databases.sh
```

3. **Créer fichier .env**
```bash
# Créer .env à la racine du projet
touch .env
```

Contenu :
```env
# PostgreSQL
POSTGRES_PASSWORD=n8n_password

# JWT
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# N8N
N8N_PASSWORD=change-me-in-production

# Environment
ENVIRONMENT=development
```

4. **Tester la création de la BDD**
```bash
# Arrêter les containers existants
docker compose down

# Supprimer le volume postgres (attention : perte de données N8N !)
# Faire un backup d'abord si N8N est en production
docker volume rm my-ia_postgres-data

# Relancer
docker compose up -d postgres

# Vérifier que la BDD est créée
docker compose exec postgres psql -U n8n -l
# Doit afficher : myia_auth
```

**Critère de succès :** ✅ Base de données `myia_auth` créée et accessible

---

### Étape 1.2 : Setup Alembic pour Migrations (1h)

**Objectif :** Initialiser Alembic pour gérer les migrations de schéma

**Actions :**

1. **Ajouter dépendances dans app/requirements.txt**
```txt
# Ajouter ces lignes
fastapi-users[sqlalchemy]==12.1.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
alembic==1.13.1
asyncpg==0.29.0
python-multipart==0.0.6
email-validator==2.1.0
```

2. **Rebuild le container app**
```bash
docker compose build app
docker compose up -d app
```

3. **Initialiser Alembic dans le container**
```bash
docker compose exec app alembic init alembic
```

4. **Configurer alembic.ini**
```bash
# Éditer app/alembic.ini
# Modifier la ligne sqlalchemy.url
```

Remplacer par :
```ini
# Ne pas mettre l'URL ici, elle sera dans env.py
# sqlalchemy.url = driver://user:pass@localhost/dbname
```

5. **Configurer alembic/env.py**
```python
# Ajouter en haut du fichier
import os
from app.database import Base
from app.models import *  # Import tous les modèles

# Dans run_migrations_offline() et run_migrations_online()
# Remplacer target_metadata = None par :
target_metadata = Base.metadata

# Dans run_migrations_online(), config la connexion :
config.set_main_option(
    'sqlalchemy.url',
    os.getenv('DATABASE_URL', 'postgresql+asyncpg://n8n:n8n_password@postgres:5432/myia_auth')
)
```

**Critère de succès :** ✅ Alembic initialisé et configuré

---

### Étape 1.3 : Créer les Modèles SQLAlchemy (3h)

**Objectif :** Créer tous les modèles de tables (11 tables)

**Actions :**

1. **Créer la structure des fichiers**
```bash
mkdir -p app/models
touch app/models/__init__.py
touch app/models/user.py
touch app/models/conversation.py
touch app/models/reference.py
touch app/models/audit.py
touch app/database.py
```

2. **Créer app/database.py** (configuration DB)
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://n8n:n8n_password@postgres:5432/myia_auth"
)

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_async_session():
    async with async_session_maker() as session:
        yield session
```

3. **Créer app/models/reference.py** (tables de référence)
```python
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

class ConversationMode(Base):
    __tablename__ = "conversation_modes"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    system_prompt = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

class ResourceType(Base):
    __tablename__ = "resource_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class AuditAction(Base):
    __tablename__ = "audit_actions"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    severity = Column(String(20), default='info', nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
```

4. **Créer app/models/user.py** (utilisateurs)
```python
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, TIMESTAMP, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role_id = Column(Integer, ForeignKey('roles.id'), default=1)
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    last_login = Column(TIMESTAMP)

    # Relations
    role = relationship("Role", lazy="joined")
    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    conversations = relationship("Conversation", back_populates="user")

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    top_k = Column(Integer, default=4)
    show_sources = Column(Boolean, default=True)
    theme = Column(String(20), default='light')
    default_mode_id = Column(Integer, ForeignKey('conversation_modes.id'), default=1)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relations
    user = relationship("User", back_populates="preferences")
    default_mode = relationship("ConversationMode")
```

5. **Créer app/models/conversation.py**
```python
from sqlalchemy import Column, String, Integer, Text, ForeignKey, TIMESTAMP, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(500), nullable=False)
    mode_id = Column(Integer, ForeignKey('conversation_modes.id'), default=1)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relations
    user = relationship("User", back_populates="conversations")
    mode = relationship("ConversationMode")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    sender_type = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    sources = Column(JSONB)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    # Relations
    conversation = relationship("Conversation", back_populates="messages")
```

6. **Créer app/models/audit.py** (sessions, documents, audit)
```python
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, TIMESTAMP, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    refresh_token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(TIMESTAMP, nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    user_agent = Column(String(500))
    ip_address = Column(String(45))

    # Relations
    user = relationship("User")

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    filename = Column(String(500), nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False, index=True)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(50), nullable=False)
    chunk_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relations
    user = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    action_id = Column(Integer, ForeignKey('audit_actions.id'), nullable=False)
    resource_type_id = Column(Integer, ForeignKey('resource_types.id'))
    resource_id = Column(UUID(as_uuid=True))
    details = Column(JSONB)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    # Relations
    user = relationship("User")
    action = relationship("AuditAction")
    resource_type = relationship("ResourceType")
```

7. **Créer app/models/__init__.py**
```python
from app.models.reference import Role, ConversationMode, ResourceType, AuditAction
from app.models.user import User, UserPreference
from app.models.conversation import Conversation, Message
from app.models.audit import Session, Document, AuditLog

__all__ = [
    "Role", "ConversationMode", "ResourceType", "AuditAction",
    "User", "UserPreference",
    "Conversation", "Message",
    "Session", "Document", "AuditLog"
]
```

**Critère de succès :** ✅ Tous les modèles créés sans erreur d'import

---

### Étape 1.4 : Créer la Migration Initiale (1h)

**Objectif :** Générer et appliquer la migration pour créer toutes les tables

**Actions :**

1. **Générer la migration automatiquement**
```bash
docker compose exec app alembic revision --autogenerate -m "Initial migration - auth tables"
```

2. **Vérifier le fichier de migration généré**
```bash
# Regarder dans app/alembic/versions/xxxxx_initial_migration.py
# Vérifier que toutes les tables sont présentes
```

3. **Appliquer la migration**
```bash
docker compose exec app alembic upgrade head
```

4. **Vérifier que les tables sont créées**
```bash
docker compose exec postgres psql -U n8n -d myia_auth -c "\dt"
```

Doit afficher :
```
 roles
 conversation_modes
 resource_types
 audit_actions
 users
 user_preferences
 conversations
 messages
 sessions
 documents
 audit_logs
```

**Critère de succès :** ✅ 11 tables créées dans la BDD `myia_auth`

---

### Étape 1.5 : Seed Data (Tables de Référence) (30min)

**Objectif :** Insérer les données de référence (roles, modes, etc.)

**Actions :**

1. **Créer script de seed**
```bash
touch app/seed_data.py
```

Contenu :
```python
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_maker
from app.models import Role, ConversationMode, ResourceType, AuditAction

async def seed_data():
    async with async_session_maker() as session:
        # Rôles
        roles = [
            Role(name='user', display_name='Utilisateur', description='Accès basique'),
            Role(name='contributor', display_name='Contributeur', description='Peut uploader des documents'),
            Role(name='admin', display_name='Administrateur', description='Accès complet')
        ]
        session.add_all(roles)

        # Modes de conversation
        modes = [
            ConversationMode(name='chatbot', display_name='ChatBot', description='Mode conversationnel'),
            ConversationMode(name='assistant', display_name='Assistant', description='Mode orienté tâches')
        ]
        session.add_all(modes)

        # Types de ressources
        resource_types = [
            ResourceType(name='user', display_name='Utilisateur'),
            ResourceType(name='conversation', display_name='Conversation'),
            ResourceType(name='document', display_name='Document'),
            ResourceType(name='preference', display_name='Préférence'),
            ResourceType(name='config', display_name='Configuration')
        ]
        session.add_all(resource_types)

        # Actions d'audit
        actions = [
            AuditAction(name='login_success', display_name='Connexion réussie', severity='info'),
            AuditAction(name='login_failed', display_name='Échec de connexion', severity='warning'),
            AuditAction(name='logout', display_name='Déconnexion', severity='info'),
            AuditAction(name='user_created', display_name='Utilisateur créé', severity='info'),
            AuditAction(name='role_changed', display_name='Rôle modifié', severity='warning'),
            # ... (ajouter toutes les actions du cahier des charges)
        ]
        session.add_all(actions)

        await session.commit()
        print("✅ Seed data inserted successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
```

2. **Exécuter le seed**
```bash
docker compose exec app python seed_data.py
```

3. **Vérifier les données**
```bash
docker compose exec postgres psql -U n8n -d myia_auth -c "SELECT * FROM roles;"
docker compose exec postgres psql -U n8n -d myia_auth -c "SELECT * FROM conversation_modes;"
```

**Critère de succès :** ✅ Données de référence insérées (3 roles, 2 modes, 5 resource types, ~20 actions)

---

## ✅ Checkpoint Jour 1

À ce stade, vous devriez avoir :
- ✅ Base de données `myia_auth` créée
- ✅ Alembic configuré
- ✅ 11 modèles SQLAlchemy créés
- ✅ Migration appliquée (11 tables)
- ✅ Seed data inséré

**Test de validation :**
```bash
# Compter les tables
docker compose exec postgres psql -U n8n -d myia_auth -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
# Résultat attendu : 11

# Compter les rôles
docker compose exec postgres psql -U n8n -d myia_auth -c "SELECT count(*) FROM roles;"
# Résultat attendu : 3
```

---

## 📅 Prochaines Étapes (Jour 2)

Une fois le Checkpoint Jour 1 validé, voici ce que je recommande :

### Option A : Continuer Backend Auth (Recommandé)
- Étape 2.1 : Setup FastAPI-Users (2h)
- Étape 2.2 : Endpoints /auth/register et /auth/login (2h)
- Étape 2.3 : Middleware JWT (1h)
- Étape 2.4 : Tests avec curl/Postman (1h)

### Option B : Frontend Login Minimal (Alternatif)
- Créer login.html de base
- Tester l'inscription/connexion visuelle
- Revenir au backend ensuite

**Je recommande Option A** car :
- Backend d'abord = fondations solides
- Tests plus faciles (curl)
- Détection précoce des problèmes
- Frontend ensuite = intégration fluide

---

## 🚀 Commande Rapide pour Démarrer

Voici la commande pour tout démarrer aujourd'hui :

```bash
# 1. Créer la structure
mkdir -p scripts app/models app/alembic

# 2. Créer .env
cat > .env << 'EOF'
POSTGRES_PASSWORD=n8n_password
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
N8N_PASSWORD=change-me-in-production
ENVIRONMENT=development
EOF

# 3. Créer script init DB
cat > scripts/init-multiple-databases.sh << 'EOF'
#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE myia_auth;
    GRANT ALL PRIVILEGES ON DATABASE myia_auth TO n8n;
EOSQL
echo "Database myia_auth created!"
EOF

chmod +x scripts/init-multiple-databases.sh

# 4. Continuer avec les étapes ci-dessus...
```

---

## ❓ Questions avant de commencer

Avant de démarrer l'implémentation, confirmez :

1. **Êtes-vous d'accord pour commencer par le backend ?** (Recommandé)
2. **Voulez-vous que je crée les fichiers un par un ou tous d'un coup ?**
3. **Avez-vous des données N8N importantes à sauvegarder** avant de recréer le volume PostgreSQL ?
4. **Préférez-vous un rythme rapide (tout en 1 jour) ou progressif (étape par étape) ?**

---

**Prêt à commencer ? Dites-moi et je lance l'Étape 1.1 ! 🚀**
