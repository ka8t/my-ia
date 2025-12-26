# 🚀 Des nouvelles de mon IA personnelle !

Après plusieurs semaines de développement, voici **MY-IA**, ma plateforme d'IA conversationnelle construite from scratch.

**🎯 Le défi** : faire tourner une IA complète sur un MacBook Pro 2015.
**💡 La solution** : un petit modèle LLM local via Ollama et une architecture modulaire.

---

## 🤔 Pourquoi ce projet ?

Après **+20 ans** dans la tech (développeur puis chef de projet technique), j'avais envie de :

- 🎓 **Apprendre** les nouvelles technos IA/LLM qui transforment notre métier
- 🔄 **Capitaliser** sur mon expérience en architecture, sécurité et gestion de projet
- 🧩 **Combiner** le tout dans un projet concret et ambitieux

Mon parcours (INRAP, Ministère de l'Intérieur, Publicis, Numéricable...) m'a appris à structurer des projets complexes. Ce side project était l'occasion parfaite d'appliquer ces compétences tout en montant en compétence sur FastAPI, les LLM locaux et le RAG.

---

## 📚 Ce que j'ai appris

- 🧙‍♂️ **Piloter une IA pour coder** : utiliser un LLM comme assistant de développement en lui imposant mes contraintes (architecture modulaire, patterns, conventions) issues de 20 ans d'expérience — l'IA génère, je valide et je guide 🤖✨
- 🏗️ Architecture modulaire et scalable avec FastAPI
- 🔐 Chiffrement AES-256-GCM en production
- 🔍 Recherche sur données chiffrées (blind index, trigrammes)
- ⚡ Async de bout en bout avec SQLAlchemy 2.0
- 🤖 Pipeline RAG avec ChromaDB et embeddings locaux
- 🧪 Tests d'intégration robustes avec PostgreSQL
- 🎨 Frontend modulaire sans framework

---

## ⚙️ Ce que ça fait

### 💬 Chat IA avec RAG
- Streaming temps réel des réponses
- Mode RAG (enrichi par vos documents) ou Assistant (libre)
- Régénération, sources citées, historique archivable

### 📄 Gestion des Documents
- Upload multi-format : PDF, DOCX, XLSX, TXT, Markdown, HTML, CSV
- Chunking sémantique + embeddings locaux
- Visibilité public/privé avec isolation dans le RAG
- Versioning et quotas par utilisateur

### 🛠️ Administration complète
- Dashboard avec statistiques
- CRUD utilisateurs (rôles, activation, reset password)
- Gestion documents et conversations
- Export CSV/JSON, opérations bulk
- Politique de mot de passe configurable
- Audit logs complet

### 🖥️ Interface utilisateur
- Sidebar repliable, thème clair/sombre
- Modal profil avec validation et autocomplétion pays/ville
- Tooltips, toasts, confirmations

---

## 🏛️ Architecture

```
┌─────────────────────┐
│      FRONTEND       │
│  Vanilla JS modulaire│
│                     │
│  📁 services/       │
│  📁 modules/        │
│  📁 components/     │
│  📁 utils/          │
└──────────┬──────────┘
           │
      REST API
           │
┌──────────┴──────────┐
│      BACKEND        │
│      FastAPI        │
│                     │
│  📁 features/       │
│    └─ router.py     │
│    └─ service.py    │
│    └─ repository.py │
│                     │
│  📁 common/         │
│  📁 core/           │
└──────────┬──────────┘
           │
     ┌─────┼─────┐
     ▼     ▼     ▼
   🗄️     🔢     🤖
PostgreSQL ChromaDB Ollama
```

**🔒 Sécurité** : AES-256-GCM, blind index, JWT, audit, rate limiting

---

## 📊 Chiffres

| | |
|---|---|
| 🧪 Tests | 200+ |
| 🔌 Endpoints | 60+ |
| 🐍 Fichiers Python | 100+ |
| 🏙️ Villes importées | 35 000+ |

---

🎬 **Nouvelle vidéo de démonstration à venir !**

👉 **Suivez mon profil et commentez "MY-IA-STATUS" pour obtenir une version plus détaillée. Je vous enverrai le lien en DM.**

---

#FastAPI #Python #RAG #LLM #Ollama #PostgreSQL #IA #Architecture #Security #Docker #FullStack

*📅 26 décembre 2025*
