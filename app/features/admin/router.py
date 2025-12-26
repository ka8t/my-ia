"""
Router Admin

Endpoints d'administration pour gérer les utilisateurs, rôles, audit, etc.
Tous les endpoints nécessitent le rôle admin.
"""
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.deps import get_current_admin_user, get_db
from app.models import User, Role, ConversationMode, ResourceType, AuditAction, UserPreference, Document, Message
from app.common.schemas import (
    RoleRead, RoleCreate, RoleUpdate,
    ConversationModeRead, ConversationModeCreate, ConversationModeUpdate,
    ResourceTypeRead, ResourceTypeCreate, ResourceTypeUpdate,
    AuditActionRead, AuditActionCreate, AuditActionUpdate,
    UserPreferenceRead, UserPreferenceUpdate,
    ConversationRead, MessageRead, DocumentRead, SessionRead
)
from app.features.admin.repository import AdminRepository
from app.features.admin.service import AdminService
from app.features.audit.service import AuditService
from app.common.metrics import REQUEST_COUNT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# =============================================================================
# AUDIT LOGS & STATS
# =============================================================================

@router.get("/audit")
async def get_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupère les logs d'audit avec filtres

    Query Parameters:
    - user_id: Filtrer par utilisateur (UUID)
    - action: Filtrer par nom d'action
    - limit: Nombre de résultats (max 200)
    - offset: Pagination

    Requires: Admin role
    """
    try:
        limit = min(limit, 200)

        user_uuid = None
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid user_id format")

        audit_logs = await AdminRepository.get_audit_logs(
            db, user_uuid, action, limit, offset
        )

        # Enrichir les données (jointures manuelles pour simplifier)
        # Note: Dans une vraie app, utiliser eager loading avec joinedload()
        logs_data = []
        for log in audit_logs:
            logs_data.append({
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action_id": log.action_id,
                "resource_type_id": log.resource_type_id,
                "resource_id": str(log.resource_id) if log.resource_id else None,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat()
            })

        REQUEST_COUNT.labels(endpoint="/admin/audit", method="GET", status="200").inc()

        return {
            "total": len(logs_data),
            "limit": limit,
            "offset": offset,
            "logs": logs_data
        }

    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/audit", method="GET", status="500").inc()
        logger.error(f"Error fetching audit logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_admin_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupère les statistiques globales du système

    Requires: Admin role
    """
    try:
        stats = await AdminService.get_stats(db)

        REQUEST_COUNT.labels(endpoint="/admin/stats", method="GET", status="200").inc()

        return stats

    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/stats", method="GET", status="500").inc()
        logger.error(f"Error fetching admin stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ROLES CRUD
# =============================================================================

@router.get("/roles", response_model=list[RoleRead])
async def get_roles(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Récupère tous les rôles - Requires: Admin role"""
    try:
        roles = await AdminRepository.get_all(db, Role, order_by=Role.id)

        REQUEST_COUNT.labels(endpoint="/admin/roles", method="GET", status="200").inc()
        return roles
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/roles", method="GET", status="500").inc()
        logger.error(f"Error fetching roles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roles", response_model=RoleRead, status_code=201)
async def create_role(
    role_data: RoleCreate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Crée un nouveau rôle - Requires: Admin role"""
    try:
        new_role = await AdminService.create_role(db, role_data.model_dump())

        # Audit log
        await AuditService.log_action(
            db=db,
            action_name='role_created',
            user_id=admin_user.id,
            resource_type_name='role',
            resource_id=None,
            details={'role_name': new_role.name, 'role_id': new_role.id},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/roles", method="POST", status="201").inc()
        return new_role
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/roles", method="POST", status="500").inc()
        logger.error(f"Error creating role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/roles/{role_id}", response_model=RoleRead)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Met à jour un rôle - Requires: Admin role"""
    try:
        role = await AdminService.update_role(db, role_id, role_data.model_dump(exclude_unset=True))

        # Audit log
        await AuditService.log_action(
            db=db,
            action_name='role_updated',
            user_id=admin_user.id,
            resource_type_name='role',
            resource_id=None,
            details={'role_id': role.id, 'updates': role_data.model_dump(exclude_unset=True)},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/roles", method="PATCH", status="200").inc()
        return role
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/roles", method="PATCH", status="500").inc()
        logger.error(f"Error updating role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/roles/{role_id}", status_code=204)
async def delete_role(
    role_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Supprime un rôle - Requires: Admin role"""
    try:
        role = await AdminRepository.get_by_id(db, Role, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        role_name = role.name
        await AdminService.delete_role(db, role_id)

        # Audit log
        await AuditService.log_action(
            db=db,
            action_name='role_deleted',
            user_id=admin_user.id,
            resource_type_name='role',
            resource_id=None,
            details={'role_id': role_id, 'role_name': role_name},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/roles", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/roles", method="DELETE", status="500").inc()
        logger.error(f"Error deleting role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CONVERSATION MODES CRUD
# =============================================================================

@router.get("/conversation-modes", response_model=list[ConversationModeRead])
async def get_conversation_modes(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Récupère tous les modes de conversation"""
    try:
        modes = await AdminRepository.get_all(db, ConversationMode, order_by=ConversationMode.id)

        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="GET", status="200").inc()
        return modes
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="GET", status="500").inc()
        logger.error(f"Error fetching conversation modes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversation-modes", response_model=ConversationModeRead, status_code=201)
async def create_conversation_mode(
    mode_data: ConversationModeCreate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Crée un nouveau mode de conversation"""
    try:
        new_mode = await AdminService.create_conversation_mode(db, mode_data.model_dump())

        await AuditService.log_action(
            db=db,
            action_name='conversation_mode_created',
            user_id=admin_user.id,
            resource_type_name='conversation_mode',
            resource_id=None,
            details={'mode_name': new_mode.name, 'mode_id': new_mode.id},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="POST", status="201").inc()
        return new_mode
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="POST", status="500").inc()
        logger.error(f"Error creating conversation mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/conversation-modes/{mode_id}", response_model=ConversationModeRead)
async def update_conversation_mode(
    mode_id: int,
    mode_data: ConversationModeUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Met à jour un mode de conversation"""
    try:
        mode = await AdminService.update_conversation_mode(
            db, mode_id, mode_data.model_dump(exclude_unset=True)
        )

        await AuditService.log_action(
            db=db,
            action_name='conversation_mode_updated',
            user_id=admin_user.id,
            resource_type_name='conversation_mode',
            resource_id=None,
            details={'mode_id': mode.id, 'updates': mode_data.model_dump(exclude_unset=True)},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="PATCH", status="200").inc()
        return mode
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="PATCH", status="500").inc()
        logger.error(f"Error updating conversation mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversation-modes/{mode_id}", status_code=204)
async def delete_conversation_mode(
    mode_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Supprime un mode de conversation"""
    try:
        mode = await AdminRepository.get_by_id(db, ConversationMode, mode_id)
        if not mode:
            raise HTTPException(status_code=404, detail="Conversation mode not found")

        mode_name = mode.name
        await AdminService.delete_conversation_mode(db, mode_id)

        await AuditService.log_action(
            db=db,
            action_name='conversation_mode_deleted',
            user_id=admin_user.id,
            resource_type_name='conversation_mode',
            resource_id=None,
            details={'mode_id': mode_id, 'mode_name': mode_name},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="DELETE", status="500").inc()
        logger.error(f"Error deleting conversation mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RESOURCE TYPES & AUDIT ACTIONS CRUD (Simplified - same pattern as above)
# =============================================================================

@router.get("/resource-types", response_model=list[ResourceTypeRead])
async def get_resource_types(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Récupère tous les types de ressources"""
    try:
        types = await AdminRepository.get_all(db, ResourceType, order_by=ResourceType.id)
        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="GET", status="200").inc()
        return types
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="GET", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-actions", response_model=list[AuditActionRead])
async def get_audit_actions(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Récupère toutes les actions d'audit"""
    try:
        actions = await AdminRepository.get_all(db, AuditAction, order_by=AuditAction.id)
        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="GET", status="200").inc()
        return actions
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="GET", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RESOURCE TYPES CRUD (POST, PATCH, DELETE)
# =============================================================================

@router.post("/resource-types", response_model=ResourceTypeRead, status_code=201)
async def create_resource_type(
    type_data: ResourceTypeCreate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Crée un nouveau type de ressource - Requires: Admin role"""
    try:
        new_type = await AdminService.create_resource_type(db, type_data.model_dump())

        await AuditService.log_action(
            db=db,
            action_name='resource_type_created',
            user_id=admin_user.id,
            resource_type_name='resource_type',
            resource_id=None,
            details={'type_name': new_type.name, 'type_id': new_type.id},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="POST", status="201").inc()
        return new_type
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="POST", status="500").inc()
        logger.error(f"Error creating resource type: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/resource-types/{type_id}", response_model=ResourceTypeRead)
async def update_resource_type(
    type_id: int,
    type_data: ResourceTypeUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Met à jour un type de ressource - Requires: Admin role"""
    try:
        updated_type = await AdminService.update_resource_type(
            db, type_id, type_data.model_dump(exclude_unset=True)
        )

        await AuditService.log_action(
            db=db,
            action_name='resource_type_updated',
            user_id=admin_user.id,
            resource_type_name='resource_type',
            resource_id=None,
            details={'type_id': type_id, 'updates': type_data.model_dump(exclude_unset=True)},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="PATCH", status="200").inc()
        return updated_type
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="PATCH", status="500").inc()
        logger.error(f"Error updating resource type: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/resource-types/{type_id}", status_code=204)
async def delete_resource_type(
    type_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Supprime un type de ressource - Requires: Admin role"""
    try:
        resource_type = await AdminRepository.get_by_id(db, ResourceType, type_id)
        if not resource_type:
            raise HTTPException(status_code=404, detail="Resource type not found")

        type_name = resource_type.name
        await AdminService.delete_resource_type(db, type_id)

        await AuditService.log_action(
            db=db,
            action_name='resource_type_deleted',
            user_id=admin_user.id,
            resource_type_name='resource_type',
            resource_id=None,
            details={'type_id': type_id, 'type_name': type_name},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="DELETE", status="500").inc()
        logger.error(f"Error deleting resource type: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AUDIT ACTIONS CRUD (POST, PATCH, DELETE)
# =============================================================================

@router.post("/audit-actions", response_model=AuditActionRead, status_code=201)
async def create_audit_action(
    action_data: AuditActionCreate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Crée une nouvelle action d'audit - Requires: Admin role"""
    try:
        new_action = await AdminService.create_audit_action(db, action_data.model_dump())

        await AuditService.log_action(
            db=db,
            action_name='audit_action_created',
            user_id=admin_user.id,
            resource_type_name='audit_action',
            resource_id=None,
            details={'action_name': new_action.name, 'action_id': new_action.id},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="POST", status="201").inc()
        return new_action
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="POST", status="500").inc()
        logger.error(f"Error creating audit action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/audit-actions/{action_id}", response_model=AuditActionRead)
async def update_audit_action(
    action_id: int,
    action_data: AuditActionUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Met à jour une action d'audit - Requires: Admin role"""
    try:
        updated_action = await AdminService.update_audit_action(
            db, action_id, action_data.model_dump(exclude_unset=True)
        )

        await AuditService.log_action(
            db=db,
            action_name='audit_action_updated',
            user_id=admin_user.id,
            resource_type_name='audit_action',
            resource_id=None,
            details={'action_id': action_id, 'updates': action_data.model_dump(exclude_unset=True)},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="PATCH", status="200").inc()
        return updated_action
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="PATCH", status="500").inc()
        logger.error(f"Error updating audit action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/audit-actions/{action_id}", status_code=204)
async def delete_audit_action(
    action_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Supprime une action d'audit - Requires: Admin role"""
    try:
        audit_action = await AdminRepository.get_by_id(db, AuditAction, action_id)
        if not audit_action:
            raise HTTPException(status_code=404, detail="Audit action not found")

        action_name = audit_action.name
        await AdminService.delete_audit_action(db, action_id)

        await AuditService.log_action(
            db=db,
            action_name='audit_action_deleted',
            user_id=admin_user.id,
            resource_type_name='audit_action',
            resource_id=None,
            details={'action_id': action_id, 'action_name': action_name},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="DELETE", status="500").inc()
        logger.error(f"Error deleting audit action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# USER PREFERENCES
# =============================================================================

@router.get("/user-preferences/{user_id}", response_model=UserPreferenceRead)
async def get_user_preferences(
    user_id: uuid.UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Récupère les préférences d'un utilisateur"""
    try:
        preferences = await AdminRepository.get_by_id(db, UserPreference, user_id)
        if not preferences:
            raise HTTPException(status_code=404, detail="User preferences not found")

        REQUEST_COUNT.labels(endpoint="/admin/user-preferences", method="GET", status="200").inc()
        return preferences
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/user-preferences", method="GET", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CONVERSATIONS, MESSAGES, DOCUMENTS, SESSIONS
# =============================================================================

@router.get("/conversations", response_model=list[ConversationRead])
async def get_conversations(
    user_id: Optional[uuid.UUID] = None,
    mode_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Récupère toutes les conversations avec filtres"""
    try:
        limit = min(limit, 200)
        conversations = await AdminRepository.get_conversations(db, user_id, mode_id, limit, offset)

        REQUEST_COUNT.labels(endpoint="/admin/conversations", method="GET", status="200").inc()
        return conversations
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/conversations", method="GET", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=list[MessageRead])
async def get_messages(
    conversation_id: Optional[uuid.UUID] = None,
    sender_type: Optional[str] = None,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupère tous les messages avec filtres.

    Query Parameters:
    - conversation_id: Filtrer par conversation
    - sender_type: Filtrer par type (user/assistant)
    - include_deleted: Inclure les messages supprimés (soft delete)
    - limit: Nombre de résultats (max 200)
    - offset: Pagination
    """
    try:
        limit = min(limit, 200)
        messages = await AdminRepository.get_messages(
            db, conversation_id, sender_type,
            include_deleted=include_deleted,
            limit=limit, offset=offset
        )

        REQUEST_COUNT.labels(endpoint="/admin/messages", method="GET", status="200").inc()
        return messages
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/messages", method="GET", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/deleted", response_model=list[MessageRead])
async def get_deleted_messages(
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupère uniquement les messages supprimés (soft delete).

    Query Parameters:
    - conversation_id: Filtrer par conversation
    - limit: Nombre de résultats (max 200)
    - offset: Pagination
    """
    try:
        limit = min(limit, 200)
        messages = await AdminRepository.get_messages(
            db, conversation_id, sender_type=None,
            deleted_only=True,
            limit=limit, offset=offset
        )

        REQUEST_COUNT.labels(endpoint="/admin/messages/deleted", method="GET", status="200").inc()
        return messages
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/messages/deleted", method="GET", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages/{message_id}", status_code=204)
async def hard_delete_message(
    message_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Supprime physiquement un message (hard delete).

    Cette action est irréversible. Seuls les admins peuvent effectuer cette opération.
    """
    try:
        message = await AdminRepository.get_by_id(db, Message, message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        message_info = {
            'conversation_id': str(message.conversation_id),
            'sender_type': message.sender_type,
            'content_preview': message.content[:100] if message.content else None,
            'was_soft_deleted': message.deleted_at is not None
        }

        deleted = await AdminRepository.hard_delete_message(db, message_id)
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete message")

        await AuditService.log_action(
            db=db,
            action_name='message_hard_deleted',
            user_id=admin_user.id,
            resource_type_name='message',
            resource_id=message_id,
            details=message_info,
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/messages", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/messages", method="DELETE", status="500").inc()
        logger.error(f"Error hard deleting message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages/{message_id}/restore", response_model=MessageRead)
async def restore_message(
    message_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Restaure un message supprimé (soft delete).

    Annule le soft delete d'un message.
    """
    try:
        message = await AdminRepository.restore_message(db, message_id)

        if not message:
            raise HTTPException(
                status_code=404,
                detail="Message not found or not deleted"
            )

        await AuditService.log_action(
            db=db,
            action_name='message_restored',
            user_id=admin_user.id,
            resource_type_name='message',
            resource_id=message_id,
            details={'conversation_id': str(message.conversation_id)},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/messages/restore", method="POST", status="200").inc()
        return message
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/messages/restore", method="POST", status="500").inc()
        logger.error(f"Error restoring message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=list[DocumentRead])
async def get_documents(
    user_id: Optional[uuid.UUID] = None,
    file_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Récupère tous les documents avec filtres"""
    try:
        limit = min(limit, 200)
        documents = await AdminRepository.get_documents(db, user_id, file_type, limit, offset)

        REQUEST_COUNT.labels(endpoint="/admin/documents", method="GET", status="200").inc()
        return documents
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/documents", method="GET", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Supprime un document (aussi dans ChromaDB si possible)"""
    try:
        document = await AdminRepository.get_by_id(db, Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        document_info = {
            'filename': document.filename,
            'file_hash': document.file_hash,
            'user_id': str(document.user_id)
        }

        await AdminService.delete_document(db, document_id)

        await AuditService.log_action(
            db=db,
            action_name='document_deleted',
            user_id=admin_user.id,
            resource_type_name='document',
            resource_id=document_id,
            details=document_info,
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/documents", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/documents", method="DELETE", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{document_id}/deindex", response_model=DocumentRead)
async def deindex_document(
    document_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Désindexe un document du RAG

    Le document reste dans la base mais n'apparaîtra plus dans les recherches RAG.
    Requires: Admin role
    """
    try:
        document = await AdminService.deindex_document(db, document_id)

        await AuditService.log_action(
            db=db,
            action_name='document_deindexed',
            user_id=admin_user.id,
            resource_type_name='document',
            resource_id=document_id,
            details={
                'filename': document.filename,
                'file_hash': document.file_hash
            },
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/documents/deindex", method="POST", status="200").inc()
        return document
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/documents/deindex", method="POST", status="500").inc()
        logger.error(f"Error deindexing document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{document_id}/reindex", response_model=DocumentRead)
async def reindex_document(
    document_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Réindexe un document dans le RAG

    Le document sera à nouveau visible dans les recherches RAG.
    Requires: Admin role
    """
    try:
        document = await AdminService.reindex_document(db, document_id)

        await AuditService.log_action(
            db=db,
            action_name='document_reindexed',
            user_id=admin_user.id,
            resource_type_name='document',
            resource_id=document_id,
            details={
                'filename': document.filename,
                'file_hash': document.file_hash
            },
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/documents/reindex", method="POST", status="200").inc()
        return document
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/documents/reindex", method="POST", status="500").inc()
        logger.error(f"Error reindexing document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/documents/{document_id}/visibility")
async def update_document_visibility_admin(
    document_id: uuid.UUID,
    visibility: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Met à jour la visibilité d'un document (admin)

    Args:
        visibility: 'public' ou 'private'

    Requires: Admin role
    """
    try:
        document = await AdminService.update_document_visibility(
            db=db,
            document_id=document_id,
            visibility=visibility,
            user_id=admin_user.id,
            is_admin=True
        )

        await AuditService.log_action(
            db=db,
            action_name='document_visibility_updated',
            user_id=admin_user.id,
            resource_type_name='document',
            resource_id=document_id,
            details={
                'filename': document.filename,
                'new_visibility': visibility
            },
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/documents/visibility", method="PATCH", status="200").inc()
        return {
            "success": True,
            "document_id": str(document_id),
            "visibility": visibility
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/documents/visibility", method="PATCH", status="500").inc()
        logger.error(f"Error updating document visibility: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=list[SessionRead])
async def get_sessions(
    user_id: Optional[uuid.UUID] = None,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Récupère toutes les sessions avec filtres"""
    try:
        limit = min(limit, 200)
        sessions = await AdminRepository.get_sessions(db, user_id, active_only, limit, offset)

        REQUEST_COUNT.labels(endpoint="/admin/sessions", method="GET", status="200").inc()
        return sessions
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/sessions", method="GET", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/user/{user_id}", status_code=204)
async def revoke_all_user_sessions(
    user_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Révoque toutes les sessions d'un utilisateur"""
    try:
        user = await AdminRepository.get_by_id(db, User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        count = await AdminRepository.revoke_all_user_sessions(db, user_id)

        await AuditService.log_action(
            db=db,
            action_name='all_sessions_revoked',
            user_id=admin_user.id,
            resource_type_name='session',
            resource_id=user_id,
            details={'target_user_id': str(user_id), 'sessions_revoked': count},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/sessions", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/sessions", method="DELETE", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# INCLUSION DES SUB-ROUTERS
# =============================================================================

from app.features.admin.users.router import router as users_router
from app.features.admin.dashboard.router import router as dashboard_router
from app.features.admin.bulk.router import router as bulk_router
from app.features.admin.export.router import router as export_router
from app.features.admin.conversations.router import router as conversations_admin_router
from app.features.admin.config.router import router as config_router
from app.features.admin.password_policy.router import router as password_policy_router
from app.features.admin.geo.router import router as geo_admin_router

router.include_router(users_router, prefix="/users", tags=["Admin - Users"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["Admin - Dashboard"])
router.include_router(bulk_router, prefix="/bulk", tags=["Admin - Bulk"])
router.include_router(export_router, prefix="/export", tags=["Admin - Export"])
router.include_router(conversations_admin_router, prefix="/conversations-admin", tags=["Admin - Conversations"])
router.include_router(config_router, prefix="/config", tags=["Admin - Config"])
router.include_router(password_policy_router, prefix="/password-policies", tags=["Admin - Password Policies"])
router.include_router(geo_admin_router, prefix="/geo", tags=["Admin - Geo"])
