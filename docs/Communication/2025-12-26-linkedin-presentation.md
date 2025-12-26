# 🚀 MY-IA - Document de Communication LinkedIn

---

# Des nouvelles de mon IA personnelle !

Après plusieurs semaines de développement intensif, je suis ravi de partager l'avancement de **MY-IA**, ma plateforme d'IA conversationnelle construite entièrement from scratch.

## 🎯 Le défi

Faire tourner une IA complète et fonctionnelle sur un MacBook Pro 2015 avec des ressources limitées. La solution ? Un petit modèle LLM local via Ollama et une architecture soigneusement pensée pour la performance.

## ✨ Le résultat

Une application full-stack complète intégrant :
- 🤖 Un système RAG (Retrieval Augmented Generation) pour enrichir les réponses avec vos propres documents
- 🖥️ Une interface utilisateur moderne avec streaming temps réel
- 🛠️ Un panneau d'administration complet
- 🔐 Une sécurité de niveau entreprise

---

# 🤔 Pourquoi ce projet ?

Après **plus de 20 ans** dans la tech, d'abord développeur puis chef de projet technique, j'avais envie de me lancer un nouveau défi.

## 🎓 Apprendre de nouvelles technologies

L'IA générative et les LLM transforment notre métier. Je voulais comprendre en profondeur comment fonctionnent ces technologies, pas juste les utiliser via des API cloud. D'où le choix d'Ollama pour faire tourner un modèle en local, et de ChromaDB pour gérer les embeddings.

## 🔄 Capitaliser sur mon expérience

Mon parcours m'a permis d'acquérir une solide expérience en :
- **Architecture applicative** : structurer des systèmes complexes (Publicis, Numéricable, Telecom Italia)
- **Sécurité** : certification ANSSI, projets au Ministère de l'Intérieur sur l'infrastructure de gestion de clés
- **Gestion de projet** : coordination multi-équipes, documentation, qualité de service (INRAP, Prodigious)
- **Interface métiers-IT** : traduire les besoins fonctionnels en solutions techniques

## 🧩 Combiner le tout

Ce side project était l'occasion parfaite de mettre en pratique ces compétences tout en montant en compétence sur :
- FastAPI et l'architecture modulaire Python
- SQLAlchemy 2.0 async
- Les pipelines RAG (chunking, embeddings, recherche vectorielle)
- Le chiffrement de données sensibles en production
- Les tests d'intégration robustes

Le résultat : une application complète que je peux montrer, pas juste un POC.

---

# 📚 Ce que j'ai appris

Ce projet m'a permis d'approfondir de nombreux sujets :

- 🧙‍♂️ **Piloter une IA pour générer du code de qualité** : j'ai utilisé un LLM comme assistant de développement en lui imposant un fichier de contraintes strict regroupant mes exigences issues de 20 ans d'expérience et les meilleures pratiques actuelles — architecture modulaire, patterns, conventions de code, sécurité. L'IA génère, je valide, je corrige, je guide. Résultat : productivité décuplée tout en gardant le contrôle total sur la qualité 🤖✨
- 🏗️ Concevoir une **architecture modulaire et scalable** avec FastAPI
- 🔐 Implémenter le **chiffrement de données sensibles** en production (AES-256-GCM)
- 🔍 Effectuer des **recherches sur données chiffrées** (blind index, trigrammes hashés)
- ⚡ Gérer l'**asynchrone de bout en bout** avec SQLAlchemy 2.0
- 🤖 Construire un **pipeline RAG** avec ChromaDB et embeddings locaux
- 🧪 Écrire des **tests d'intégration robustes** avec PostgreSQL
- 🎨 Développer un **frontend modulaire** performant sans framework
- 💻 Travailler efficacement avec des **contraintes de ressources limitées**

---

# 💬 Fonctionnalités Backend

## 🔑 Authentification et Gestion des Utilisateurs

L'authentification repose sur **FastAPI-Users** avec une stratégie JWT robuste. Chaque utilisateur dispose d'un profil complet dont les données personnelles sensibles (nom, prénom, téléphone, adresse) sont chiffrées en base de données avec **AES-256-GCM**.

Le système gère les sessions via des refresh tokens avec expiration configurable. Le changement de mot de passe intègre une validation de l'ancien mot de passe et respecte une politique de complexité paramétrable par l'administrateur.

Pour la localisation, j'ai implémenté un système d'autocomplétion permettant de sélectionner son pays parmi 250+ options et sa ville parmi plus de 35 000 communes françaises importées avec leurs codes postaux.

## 🤖 Chat RAG (Retrieval Augmented Generation)

Le cœur de l'application est le système de chat avec RAG. Les réponses de l'IA s'affichent en **streaming temps réel**, mot par mot, offrant une expérience fluide et réactive.

Deux modes de conversation sont disponibles :
- **Mode RAG** : l'IA enrichit ses réponses avec le contexte des documents uploadés par l'utilisateur
- **Mode Assistant** : conversation libre sans contexte documentaire

L'utilisateur peut régénérer une réponse s'il n'est pas satisfait. Chaque réponse en mode RAG affiche les sources utilisées, permettant de vérifier l'origine des informations. Toutes les conversations sont sauvegardées et peuvent être archivées.

## 📄 Gestion des Documents

Le système accepte de nombreux formats : PDF, DOCX, XLSX, TXT, Markdown, HTML, CSV et JSONL. Chaque document uploadé passe par un pipeline d'ingestion qui effectue :

1. 📝 **Extraction du texte** via Unstructured.io
2. ✂️ **Chunking sémantique** intelligent avec LangChain
3. 🔢 **Génération des embeddings** avec Nomic-embed-text
4. 💾 **Stockage vectoriel** dans ChromaDB

Les documents peuvent être configurés en visibilité **publique** (accessibles à tous les utilisateurs dans le RAG) ou **privée** (visibles uniquement par leur propriétaire). Cette isolation garantit que les documents privés ne "polluent" pas les réponses des autres utilisateurs.

Le système intègre également :
- 📚 Un **versioning** avec historique des modifications
- 📊 Des **quotas de stockage** par utilisateur
- 🔗 Une **déduplication** automatique par hash SHA-256

## 🛠️ Administration Complète

Le panneau d'administration offre plus de 20 endpoints pour gérer l'ensemble de la plateforme.

### 📊 Dashboard
Un tableau de bord affiche les statistiques globales : nombre d'utilisateurs, documents uploadés, conversations créées. Les métriques sont exposées via Prometheus pour un monitoring temps réel.

### 👥 Gestion des Utilisateurs
L'administrateur dispose d'un CRUD complet pour gérer les utilisateurs : création de comptes, modification des informations, changement de rôle (user vers admin), activation/désactivation, et reset de mot de passe. Un système de recherche avec filtres avancés (par rôle, statut, date de création) facilite la navigation.

### 📁 Gestion des Documents
Vue globale de tous les documents du système avec possibilité de désindexer/réindexer un document du RAG, modifier sa visibilité, et consulter les statistiques par utilisateur.

### 💬 Gestion des Conversations
Consultation de l'historique des conversations de tous les utilisateurs avec possibilité de soft delete (suppression logique) des messages.

### 📤 Export de Données
Export des données au format CSV ou JSON : liste des utilisateurs, logs d'audit.

### ⚡ Opérations en Masse
Actions bulk pour activer/désactiver plusieurs utilisateurs simultanément ou effectuer des suppressions en masse.

### 🔒 Politique de Mot de Passe
Configuration complète des règles de mot de passe : longueur minimale/maximale, exigence de majuscules, chiffres, caractères spéciaux. Option d'expiration des mots de passe et historique pour empêcher la réutilisation. La validation s'effectue en temps réel avec un score de robustesse et des suggestions d'amélioration.

### 📋 Audit Logs
Traçabilité complète de toutes les actions : qui a fait quoi, quand, depuis quelle adresse IP. Chaque action est catégorisée par niveau de sévérité (info, warning, critical).

### 🌍 Données Géographiques
Import et gestion des pays (250+ avec drapeaux et préfixes téléphoniques) et des villes (35 000+ communes françaises). Possibilité d'activer/désactiver sélectivement des pays selon les besoins.

---

# 🖥️ Fonctionnalités Frontend

## 💬 Interface de Chat

L'interface principale est centrée sur l'expérience de conversation. Une **sidebar repliable** à gauche affiche l'historique des conversations. Le contenu principal présente la conversation active avec les messages utilisateur et les réponses de l'IA.

Le **streaming temps réel** affiche les réponses progressivement, créant une sensation de dialogue naturel. Un bouton **Stop** permet d'interrompre la génération à tout moment.

Les anciennes conversations peuvent être **archivées** pour désencombrer la liste. Pour les réponses en mode RAG, les **sources citées** sont affichées, permettant de tracer l'origine des informations.

Des **boutons de suggestions** proposent des questions prédéfinies pour aider l'utilisateur à démarrer.

## 👤 Gestion du Profil Utilisateur

Une **modal de profil** complète permet d'éditer toutes ses informations personnelles. Chaque champ fait l'objet d'une validation côté client (minimum 4 caractères pour les champs obligatoires) avec mise en évidence visuelle des erreurs.

La sélection du pays et de la ville s'effectue via des champs avec **autocomplétion**. Le pays affiche son drapeau, la ville propose les résultats filtrés au fur et à mesure de la saisie.

Le **thème clair/sombre** est persisté dans le localStorage et s'applique instantanément.

## 📄 Gestion des Documents

L'upload de fichiers supporte le **drag & drop** ou la sélection classique. La liste des documents affiche leur visibilité (public/privé) avec possibilité de basculer. La suppression requiert une confirmation.

## ✨ Expérience Utilisateur

L'interface intègre plusieurs éléments d'UX soignés :
- 💡 **Tooltips stylisés** avec icônes explicatives
- 🔔 **Toasts de notification** pour les retours utilisateur (succès, erreur, info)
- ⚠️ **Modales de confirmation** pour les actions critiques
- 📱 **Design responsive** adapté aux différentes tailles d'écran
- 🎨 **Système d'icônes centralisé** facilitant la maintenance et la cohérence visuelle

---

# 🏛️ Architecture Technique

## Vue d'ensemble

```
┌───────────────────────────────────┐
│            🖥️ FRONTEND            │
│        Vanilla JS modulaire       │
│                                   │
│   📁 services/    (auth, api)     │
│   📁 modules/     (chat, profile) │
│   📁 components/  (toast, modal)  │
│   📁 utils/       (dom, format)   │
│   📁 config/      (icons)         │
│                                   │
│   🎨 CSS : base/ components/ layout/
└─────────────────┬─────────────────┘
                  │
             REST API
                  │
┌─────────────────┴─────────────────┐
│          ⚡ BACKEND FastAPI        │
│                                   │
│   📄 main.py (minimal)            │
│                                   │
│   📁 features/                    │
│      ├─ auth/                     │
│      ├─ chat/                     │
│      ├─ documents/                │
│      ├─ conversations/            │
│      ├─ admin/ (10 sous-modules)  │
│      ├─ geo/                      │
│      └─ ...                       │
│                                   │
│      Chaque feature :             │
│        📄 router.py               │
│        📄 service.py              │
│        📄 repository.py           │
│        📄 schemas.py              │
│                                   │
│   📁 common/                      │
│      ├─ crypto/   (AES-256)       │
│      ├─ storage/  (local)         │
│      └─ utils/    (chroma, ollama)│
│                                   │
│   📁 core/                        │
│      ├─ config.py (settings)      │
│      └─ deps.py   (DI)            │
└─────────────────┬─────────────────┘
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │   🗄️    │ │   🔢    │ │   🤖    │
   │PostgreSQL│ │ChromaDB │ │ Ollama  │
   │   SQL   │ │ Vectors │ │   LLM   │
   │  + ORM  │ │Embeddings│ │  Local  │
   └─────────┘ └─────────┘ └─────────┘
```

---

# 🧩 Structure Modulaire et Scalable

## ⚙️ Backend : Pattern Feature

L'architecture backend suit un pattern modulaire strict où chaque fonctionnalité est isolée dans son propre dossier. Ce découpage garantit :

- 🔧 **Maintenabilité** : chaque feature peut évoluer indépendamment
- 🧪 **Testabilité** : les tests sont organisés par feature
- 📈 **Scalabilité** : ajout de nouvelles features sans impacter l'existant

Chaque feature contient :
- `router.py` : définition des endpoints HTTP (aucune logique métier)
- `service.py` : logique métier, orchestration
- `repository.py` : accès aux données, requêtes SQL
- `schemas.py` : DTOs Pydantic pour validation et sérialisation

Le fichier `main.py` reste minimal : uniquement les imports et la configuration FastAPI. Toute la logique est déléguée aux features.

L'injection de dépendances FastAPI (`Depends()`) permet de découpler les composants et facilite les tests unitaires.

Le code partagé (chiffrement, stockage, utilitaires) est centralisé dans `common/` pour éviter la duplication.

## 🎨 Frontend : Architecture Modulaire

Le frontend est développé en **Vanilla JavaScript** sans framework. Ce choix, volontaire, offre :

- ⚡ **Performance** : pas de surcharge liée à un framework
- 🎯 **Contrôle total** : maîtrise complète du code
- 📖 **Maintenabilité** : structure claire et lisible

L'organisation suit une séparation par responsabilité :
- `services/` : communication avec l'API (auth, appels HTTP)
- `modules/` : fonctionnalités (messages, conversations, streaming, upload, profil)
- `components/` : éléments réutilisables (toast, modal, markdown)
- `utils/` : fonctions utilitaires (DOM, formatage)
- `config/` : configuration centralisée (icônes SVG, paramètres)

Le CSS est organisé en couches :
- `base/` : variables CSS, reset
- `components/` : styles des composants (boutons, formulaires, toast)
- `layout/` : mise en page (chat, sidebar, login)

---

# 🔐 Sécurité

La sécurité est une priorité de l'application :

| Aspect | Implémentation |
|--------|----------------|
| 🔒 **Chiffrement PII** | AES-256-GCM pour les données personnelles (nom, téléphone, adresse) |
| 🔍 **Blind Index** | Hash HMAC pour recherche sur données chiffrées sans déchiffrement |
| 🔤 **Trigrammes hashés** | Recherche floue sécurisée sur les noms |
| 🎫 **JWT** | Tokens signés avec expiration courte et refresh automatique |
| 📋 **Audit complet** | Logs de toutes les actions avec IP et user-agent |
| 🚦 **Rate limiting** | Protection contre les abus via SlowAPI |
| ✅ **Validation** | Schemas Pydantic stricts sur toutes les entrées |

---

# 🧪 Tests

Le projet compte plus de **200 tests unitaires** organisés par module. Les tests s'exécutent dans Docker avec une vraie base PostgreSQL (pas de SQLite en mémoire qui causerait des incompatibilités UUID).

Les fixtures génèrent les tokens JWT directement sans passer par l'API d'authentification, évitant les conflits de connexion base de données. L'utilisation de NullPool garantit l'isolation entre les tests.

| Métrique | Valeur |
|----------|--------|
| 🧪 Tests unitaires | 200+ |
| 📁 Organisation | Par module (tests/admin/, tests/user/, tests/geo/...) |
| 🐳 Exécution | Dans Docker avec PostgreSQL réel |
| 🔌 Couverture | Endpoints HTTP + Services + Repositories |

---

# 📈 Évolution du Projet

Le projet a évolué significativement depuis sa création :

| Étape | Description |
|-------|-------------|
| 1️⃣ | **Commit initial** : plateforme RAG basique |
| 2️⃣ | **Interface chat** : ajout de l'UI avec streaming |
| 3️⃣ | **Upload de fichiers** : intégration dans le chat |
| 4️⃣ | **Authentification** : mise en place de FastAPI-Users avec ORM |
| 5️⃣ | **Audit** : traçabilité des actions utilisateurs |
| 6️⃣ | **Refactoring majeur** : migration vers l'architecture modulaire par features |
| 7️⃣ | **Backend admin** : 10 sous-modules avec 93 tests |
| 8️⃣ | **Backend utilisateur** : conversations, documents, préférences |
| 9️⃣ | **Frontend modulaire** : refactoring en modules JS séparés |
| 🔟 | **Storage et versioning** : gestion avancée des documents |
| 1️⃣1️⃣ | **Visibilité et isolation** : documents privés isolés dans le RAG |
| 1️⃣2️⃣ | **Profil utilisateur** : chiffrement PII, données géographiques, modal frontend |

---

# 🛠️ Stack Technique

| Couche | Technologies |
|--------|--------------|
| ⚙️ Backend | FastAPI, Python 3.10+, SQLAlchemy 2.0 async |
| 🗄️ Base de données | PostgreSQL |
| 🔢 Base vectorielle | ChromaDB |
| 🤖 LLM | Ollama (local) |
| 📊 Embeddings | Nomic-embed-text (local) |
| 🔑 Authentification | FastAPI-Users, JWT |
| 🖥️ Frontend | Vanilla JavaScript modulaire |
| 🎨 Styles | CSS en architecture couches |
| 🐳 Conteneurisation | Docker Compose |
| 📈 Monitoring | Prometheus |
| 🚦 Rate limiting | SlowAPI |

---

🎬 **Nouvelle vidéo de démonstration à venir !**

---

# 🏷️ Hashtags

#FastAPI #Python #RAG #LLM #Ollama #PostgreSQL #ChromaDB #IA #AI #MachineLearning #SideProject #Architecture #Security #Encryption #Docker #FullStack #CleanCode #ModularArchitecture

---

*📅 Document rédigé le 26 décembre 2025*
