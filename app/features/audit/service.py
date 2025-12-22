"""
Service Audit

Système de logging des actions utilisateurs.
Conforme au CAHIER_DES_CHARGES_AUTH.md
"""
import uuid
import logging
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from app.models import AuditLog
from app.features.audit.repository import AuditRepository

logger = logging.getLogger(__name__)


class AuditService:
    """Service pour le logging d'audit des actions utilisateurs"""

    @staticmethod
    async def log_action(
        db: AsyncSession,
        action_name: str,
        user_id: Optional[uuid.UUID] = None,
        resource_type_name: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> Optional[AuditLog]:
        """
        Log une action dans le système d'audit

        Args:
            db: Session de base de données async
            action_name: Nom de l'action (ex: 'login_success', 'user_created')
            user_id: ID de l'utilisateur effectuant l'action
            resource_type_name: Type de ressource concernée (ex: 'user', 'document')
            resource_id: ID de la ressource concernée
            details: Détails additionnels (dict converti en JSON)
            request: Requête FastAPI pour capturer IP et user_agent

        Returns:
            AuditLog créé ou None si erreur

        Example:
            await AuditService.log_action(
                db=db,
                action_name='role_changed',
                user_id=admin_uuid,
                resource_type_name='user',
                resource_id=target_user_uuid,
                details={
                    'old_role_id': 1,
                    'old_role_name': 'user',
                    'new_role_id': 2,
                    'new_role_name': 'contributor',
                    'reason': 'User request approved'
                },
                request=request
            )
        """
        try:
            # Récupérer l'action_id depuis audit_actions
            action = await AuditRepository.get_action_by_name(db, action_name)
            if not action:
                logger.error(f"Action '{action_name}' not found in audit_actions table")
                return None

            # Récupérer resource_type_id si fourni
            resource_type_id = None
            if resource_type_name:
                resource_type = await AuditRepository.get_resource_type_by_name(
                    db, resource_type_name
                )
                if resource_type:
                    resource_type_id = resource_type.id

            # Capturer IP et User-Agent depuis la requête
            ip_address = None
            user_agent = None
            if request:
                # Gérer les proxies (X-Forwarded-For)
                ip_address = request.headers.get("X-Forwarded-For")
                if ip_address:
                    # Prendre la première IP si plusieurs
                    ip_address = ip_address.split(",")[0].strip()
                else:
                    # Fallback sur l'IP directe
                    ip_address = request.client.host if request.client else None

                user_agent = request.headers.get("User-Agent")

            # Créer le log d'audit via repository
            audit_log = await AuditRepository.create_audit_log(
                db=db,
                user_id=user_id,
                action_id=action.id,
                resource_type_id=resource_type_id,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent
            )

            if audit_log:
                logger.info(
                    f"Audit log created: action={action_name}, user={user_id}, "
                    f"resource={resource_type_name}:{resource_id}, ip={ip_address}"
                )

            return audit_log

        except Exception as e:
            logger.error(f"Error in audit service: {e}", exc_info=True)
            return None

    # ========================================================================
    # Helper methods pour les actions courantes
    # ========================================================================

    @staticmethod
    async def log_login_success(
        db: AsyncSession,
        user_id: uuid.UUID,
        request: Optional[Request] = None
    ):
        """Log connexion réussie"""
        await AuditService.log_action(
            db=db,
            action_name='login_success',
            user_id=user_id,
            resource_type_name='user',
            resource_id=user_id,
            request=request
        )

    @staticmethod
    async def log_login_failed(
        db: AsyncSession,
        email: str,
        request: Optional[Request] = None
    ):
        """Log tentative de connexion échouée"""
        await AuditService.log_action(
            db=db,
            action_name='login_failed',
            details={'email': email, 'reason': 'Invalid credentials'},
            request=request
        )

    @staticmethod
    async def log_logout(
        db: AsyncSession,
        user_id: uuid.UUID,
        request: Optional[Request] = None
    ):
        """Log déconnexion"""
        await AuditService.log_action(
            db=db,
            action_name='logout',
            user_id=user_id,
            resource_type_name='user',
            resource_id=user_id,
            request=request
        )

    @staticmethod
    async def log_user_created(
        db: AsyncSession,
        admin_user_id: Optional[uuid.UUID],
        new_user_id: uuid.UUID,
        new_user_email: str,
        role_id: int,
        request: Optional[Request] = None
    ):
        """Log création d'utilisateur (par admin ou auto-registration)"""
        await AuditService.log_action(
            db=db,
            action_name='user_created',
            user_id=admin_user_id,  # None si auto-registration
            resource_type_name='user',
            resource_id=new_user_id,
            details={
                'email': new_user_email,
                'role_id': role_id,
                'created_by': 'admin' if admin_user_id else 'self-registration'
            },
            request=request
        )

    @staticmethod
    async def log_role_changed(
        db: AsyncSession,
        admin_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        target_user_email: str,
        old_role_id: int,
        old_role_name: str,
        new_role_id: int,
        new_role_name: str,
        reason: Optional[str] = None,
        request: Optional[Request] = None
    ):
        """Log changement de rôle"""
        await AuditService.log_action(
            db=db,
            action_name='role_changed',
            user_id=admin_user_id,
            resource_type_name='user',
            resource_id=target_user_id,
            details={
                'target_user_email': target_user_email,
                'old_role_id': old_role_id,
                'old_role_name': old_role_name,
                'new_role_id': new_role_id,
                'new_role_name': new_role_name,
                'reason': reason
            },
            request=request
        )

    @staticmethod
    async def log_document_uploaded(
        db: AsyncSession,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        filename: str,
        file_size: int,
        chunks_count: int,
        request: Optional[Request] = None
    ):
        """Log upload de document"""
        await AuditService.log_action(
            db=db,
            action_name='document_uploaded',
            user_id=user_id,
            resource_type_name='document',
            resource_id=document_id,
            details={
                'filename': filename,
                'file_size': file_size,
                'chunks_count': chunks_count
            },
            request=request
        )

    @staticmethod
    async def log_preferences_updated_by_admin(
        db: AsyncSession,
        admin_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        target_user_email: str,
        old_preferences: Dict[str, Any],
        new_preferences: Dict[str, Any],
        reason: Optional[str] = None,
        request: Optional[Request] = None
    ):
        """Log modification de préférences par un admin"""
        # Calculer les changements
        changes = {}
        for key in new_preferences:
            if key in old_preferences and old_preferences[key] != new_preferences[key]:
                changes[key] = {
                    'old': old_preferences[key],
                    'new': new_preferences[key]
                }

        await AuditService.log_action(
            db=db,
            action_name='preferences_updated_by_admin',
            user_id=admin_user_id,
            resource_type_name='preference',
            resource_id=target_user_id,  # On utilise user_id comme resource_id
            details={
                'target_user_id': str(target_user_id),
                'target_user_email': target_user_email,
                'changes': changes,
                'reason': reason
            },
            request=request
        )

    @staticmethod
    async def log_conversation_created(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        mode_name: str,
        request: Optional[Request] = None
    ):
        """Log création de conversation"""
        await AuditService.log_action(
            db=db,
            action_name='conversation_created',
            user_id=user_id,
            resource_type_name='conversation',
            resource_id=conversation_id,
            details={'mode': mode_name},
            request=request
        )


# Instance globale pour compatibilité avec le code existant
audit_service = AuditService()
