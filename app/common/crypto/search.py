"""
Service d'indexation pour la recherche sur données chiffrées.

Fournit:
- Blind Index (HMAC-SHA256) pour la recherche exacte
- Trigrammes hashés pour la recherche partielle (LIKE)
"""
import hashlib
import hmac
import logging
import re
import unicodedata
from typing import Optional, Set

from app.common.crypto.key_manager import get_key_manager

logger = logging.getLogger(__name__)


class SearchIndexService:
    """
    Service de création d'index de recherche pour données chiffrées.

    Deux types d'index sont supportés:

    1. Blind Index (HMAC-SHA256):
       - Pour la recherche EXACTE (WHERE blind_index = ?)
       - Déterministe: même valeur → même hash
       - Impossible de retrouver la valeur originale

    2. Trigrammes hashés:
       - Pour la recherche PARTIELLE (LIKE %valeur%)
       - Découpe en fragments de 3 caractères
       - Chaque trigramme est hashé individuellement
       - Stocké comme JSON array de hashes
    """

    TRIGRAM_SIZE = 3
    # Préfixe pour distinguer les types d'index
    BLIND_INDEX_PREFIX = "bi:"
    TRIGRAM_PREFIX = "tg:"

    def __init__(self, hmac_key: Optional[bytes] = None):
        """
        Initialise le service d'indexation.

        Args:
            hmac_key: Clé HMAC de 32 bytes. Si None, utilise KeyManager.
        """
        if hmac_key is None:
            hmac_key = get_key_manager().hmac_key

        self._hmac_key = hmac_key

    def _normalize(self, value: str) -> str:
        """
        Normalise une valeur pour l'indexation.

        - Convertit en minuscules
        - Supprime les accents
        - Supprime les espaces multiples
        - Supprime la ponctuation

        Args:
            value: Valeur à normaliser

        Returns:
            Valeur normalisée
        """
        if not value:
            return ""

        # Minuscules
        normalized = value.lower()

        # Supprime les accents (NFD décompose, on filtre les diacritiques)
        normalized = unicodedata.normalize('NFD', normalized)
        normalized = ''.join(
            char for char in normalized
            if unicodedata.category(char) != 'Mn'
        )

        # Supprime la ponctuation et caractères spéciaux
        normalized = re.sub(r'[^\w\s]', '', normalized)

        # Normalise les espaces
        normalized = ' '.join(normalized.split())

        return normalized

    def _hmac_hash(self, value: str) -> str:
        """
        Calcule le HMAC-SHA256 d'une valeur.

        Args:
            value: Valeur à hasher

        Returns:
            Hash hexadécimal de 64 caractères
        """
        return hmac.new(
            self._hmac_key,
            value.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def create_blind_index(self, value: str) -> str:
        """
        Crée un blind index pour la recherche exacte.

        Le blind index permet de chercher une valeur exacte sans
        pouvoir la retrouver. Utile pour: email, téléphone, etc.

        Args:
            value: Valeur à indexer

        Returns:
            Hash HMAC-SHA256 hexadécimal (64 caractères)
        """
        if not value:
            return ""

        normalized = self._normalize(value)
        return self._hmac_hash(normalized)

    def create_trigrams(self, value: str) -> Set[str]:
        """
        Génère les trigrammes d'une valeur.

        Un trigramme est une séquence de 3 caractères consécutifs.
        Exemple: "paris" → {"par", "ari", "ris"}

        Args:
            value: Valeur à découper

        Returns:
            Ensemble de trigrammes
        """
        if not value or len(value) < self.TRIGRAM_SIZE:
            return set()

        normalized = self._normalize(value)

        if len(normalized) < self.TRIGRAM_SIZE:
            return set()

        trigrams = set()
        for i in range(len(normalized) - self.TRIGRAM_SIZE + 1):
            trigram = normalized[i:i + self.TRIGRAM_SIZE]
            # Ignore les trigrammes avec espaces
            if ' ' not in trigram:
                trigrams.add(trigram)

        return trigrams

    def create_trigram_index(self, value: str) -> str:
        """
        Crée un index de trigrammes hashés pour la recherche partielle.

        Chaque trigramme est hashé individuellement puis concaténé
        avec un séparateur. Permet la recherche LIKE sur données chiffrées.

        Args:
            value: Valeur à indexer

        Returns:
            Trigrammes hashés séparés par des virgules
        """
        if not value:
            return ""

        trigrams = self.create_trigrams(value)

        if not trigrams:
            return ""

        # Hash chaque trigramme (on utilise un hash court pour économiser l'espace)
        hashed_trigrams = sorted([
            self._hmac_hash(tg)[:16]  # 16 premiers caractères suffisent
            for tg in trigrams
        ])

        return ','.join(hashed_trigrams)

    def match_trigrams(self, query: str, stored_index: str) -> bool:
        """
        Vérifie si une requête correspond à un index de trigrammes.

        Tous les trigrammes de la requête doivent être présents
        dans l'index stocké pour que la correspondance soit validée.

        Args:
            query: Terme de recherche
            stored_index: Index de trigrammes stocké

        Returns:
            True si tous les trigrammes de la requête sont trouvés
        """
        if not query or not stored_index:
            return False

        # Génère les trigrammes hashés de la requête
        query_trigrams = self.create_trigrams(query)

        if not query_trigrams:
            # Requête trop courte, pas de trigrammes
            return False

        query_hashes = {
            self._hmac_hash(tg)[:16]
            for tg in query_trigrams
        }

        # Parse l'index stocké
        stored_hashes = set(stored_index.split(','))

        # Vérifie que TOUS les trigrammes de la requête sont présents
        return query_hashes.issubset(stored_hashes)

    def search_score(self, query: str, stored_index: str) -> float:
        """
        Calcule un score de pertinence pour une recherche.

        Le score est le ratio de trigrammes de la requête trouvés
        dans l'index stocké.

        Args:
            query: Terme de recherche
            stored_index: Index de trigrammes stocké

        Returns:
            Score entre 0.0 (aucune correspondance) et 1.0 (correspondance parfaite)
        """
        if not query or not stored_index:
            return 0.0

        query_trigrams = self.create_trigrams(query)

        if not query_trigrams:
            return 0.0

        query_hashes = {
            self._hmac_hash(tg)[:16]
            for tg in query_trigrams
        }

        stored_hashes = set(stored_index.split(','))

        # Calcule le ratio de correspondance
        matches = len(query_hashes.intersection(stored_hashes))
        return matches / len(query_hashes)


# Instance singleton pour usage courant
_search_index_service: Optional[SearchIndexService] = None


def get_search_index_service() -> SearchIndexService:
    """
    Retourne l'instance singleton du service d'indexation.

    Returns:
        Instance de SearchIndexService
    """
    global _search_index_service
    if _search_index_service is None:
        _search_index_service = SearchIndexService()
    return _search_index_service
