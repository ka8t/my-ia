"""
Repository Audit

Opérations de base de données pour l'audit.
"""
import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import AuditLog, AuditAction, ResourceType

logger = logging.getLogger(__name__)


class AuditRepository:
    """Repository pour les opérations d'audit en base de données"""

    @staticmethod
    async def get_action_by_name(db: AsyncSession, action_name: str) -> Optional[AuditAction]:
        """
        Récupère une action d'audit par son nom

        Args:
            db: Session de base de données
            action_name: Nom de l'action

        Returns:
            AuditAction ou None si non trouvée
        """
        result = await db.execute(
            select(AuditAction).where(AuditAction.name == action_name)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_resource_type_by_name(
        db: AsyncSession,
        resource_type_name: str
    ) -> Optional[ResourceType]:
        """
        Récupère un type de ressource par son nom

        Args:
            db: Session de base de données
            resource_type_name: Nom du type de ressource

        Returns:
            ResourceType ou None si non trouvé
        """
        result = await db.execute(
            select(ResourceType).where(ResourceType.name == resource_type_name)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_audit_log(
        db: AsyncSession,
        user_id: Optional[uuid.UUID],
        action_id: int,
        resource_type_id: Optional[int],
        resource_id: Optional[uuid.UUID],
        details: Optional[dict],
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> Optional[AuditLog]:
        """
        Crée un log d'audit

        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            action_id: ID de l'action
            resource_type_id: ID du type de ressource
            resource_id: ID de la ressource
            details: Détails additionnels
            ip_address: Adresse IP
            user_agent: User agent

        Returns:
            AuditLog créé ou None si erreur
        """
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action_id=action_id,
                resource_type_id=resource_type_id,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address[:45] if ip_address else None,  # Limite DB
                user_agent=user_agent[:500] if user_agent else None  # Limite DB
            )

            db.add(audit_log)
            await db.commit()
            await db.refresh(audit_log)

            return audit_log

        except Exception as e:
            logger.error(f"Error creating audit log: {e}", exc_info=True)
            await db.rollback()
            return None
