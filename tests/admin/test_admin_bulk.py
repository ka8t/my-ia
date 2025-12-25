"""
Tests pour Admin Bulk Operations

Tests des operations en masse.
Execution: docker-compose exec app python -m pytest tests/admin/test_admin_bulk.py -v
"""
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.features.admin.bulk.service import BulkService
from app.models import User


# =============================================================================
# TESTS BULK USERS - ACTIVATE/DEACTIVATE
# =============================================================================

class TestBulkUserActivation:
    """Tests activation/desactivation en masse"""

    @pytest.mark.asyncio
    async def test_bulk_activate_empty_list(
        self,
        db_session: AsyncSession,
        admin_user: User
    ):
        """Test activation liste vide"""
        result = await BulkService.activate_users(
            db=db_session,
            user_ids=[],
            admin_user_id=admin_user.id
        )

        assert result.success_count == 0
        assert result.failed_count == 0

    @pytest.mark.asyncio
    async def test_bulk_activate_invalid_ids(
        self,
        db_session: AsyncSession,
        admin_user: User
    ):
        """Test activation avec IDs invalides"""
        fake_ids = [uuid.uuid4() for _ in range(3)]

        result = await BulkService.activate_users(
            db=db_session,
            user_ids=fake_ids,
            admin_user_id=admin_user.id
        )

        assert result.success_count == 0
        assert result.failed_count == 3

    @pytest.mark.asyncio
    async def test_bulk_deactivate_valid_users(
        self,
        db_session: AsyncSession,
        multiple_users: list,
        admin_user: User
    ):
        """Test desactivation d'utilisateurs valides"""
        user_ids = [u.id for u in multiple_users[:2]]

        result = await BulkService.deactivate_users(
            db=db_session,
            user_ids=user_ids,
            admin_user_id=admin_user.id
        )

        assert result.success_count == 2


# =============================================================================
# TESTS BULK ROLE CHANGE
# =============================================================================

class TestBulkRoleChange:
    """Tests changement de role en masse"""

    @pytest.mark.asyncio
    async def test_bulk_change_role_valid(
        self,
        db_session: AsyncSession,
        multiple_users: list,
        admin_user: User,
        test_roles
    ):
        """Test changement de role valide"""
        user_ids = [u.id for u in multiple_users[:2]]

        result = await BulkService.change_users_role(
            db=db_session,
            user_ids=user_ids,
            new_role_id=2,
            admin_user_id=admin_user.id
        )

        assert result.success_count == 2


# =============================================================================
# TESTS BULK DELETE
# =============================================================================

class TestBulkDelete:
    """Tests suppression en masse"""

    @pytest.mark.asyncio
    async def test_bulk_delete_requires_confirm(
        self,
        db_session: AsyncSession,
        admin_user: User,
        sample_user_data: dict,
        test_roles
    ):
        """Test suppression sans confirmation"""
        from app.features.admin.users.service import AdminUserService

        # Creer un user a supprimer
        user = await AdminUserService.create_user(
            db=db_session,
            email=sample_user_data["email"],
            username=sample_user_data["username"],
            password=sample_user_data["password"]
        )

        with pytest.raises(HTTPException) as exc_info:
            await BulkService.delete_users(
                db=db_session,
                user_ids=[user.id],
                admin_user_id=admin_user.id,
                confirm=False
            )

        assert exc_info.value.status_code == 400

        # Cleanup
        await db_session.delete(user)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_bulk_delete_with_confirm(
        self,
        db_session: AsyncSession,
        admin_user: User,
        sample_user_data: dict,
        test_roles
    ):
        """Test suppression avec confirmation"""
        from app.features.admin.users.service import AdminUserService

        # Creer un user a supprimer
        user = await AdminUserService.create_user(
            db=db_session,
            email=sample_user_data["email"],
            username=sample_user_data["username"],
            password=sample_user_data["password"]
        )
        user_id = user.id

        result = await BulkService.delete_users(
            db=db_session,
            user_ids=[user_id],
            admin_user_id=admin_user.id,
            confirm=True
        )

        assert result.success_count == 1

    @pytest.mark.asyncio
    async def test_bulk_delete_prevents_self_deletion(
        self,
        db_session: AsyncSession,
        admin_user: User
    ):
        """Test que l'admin ne peut pas se supprimer via bulk"""
        result = await BulkService.delete_users(
            db=db_session,
            user_ids=[admin_user.id],
            admin_user_id=admin_user.id,
            confirm=True
        )

        # L'admin doit etre dans les echecs
        assert admin_user.id in result.failed_ids


# =============================================================================
# TESTS BULK CONVERSATIONS
# =============================================================================

class TestBulkConversations:
    """Tests operations bulk sur conversations"""

    @pytest.mark.asyncio
    async def test_bulk_delete_conversations_requires_confirm(
        self,
        db_session: AsyncSession
    ):
        """Test suppression conversations sans confirmation"""
        fake_ids = [uuid.uuid4() for _ in range(2)]

        with pytest.raises(HTTPException) as exc_info:
            await BulkService.delete_conversations(
                db=db_session,
                conversation_ids=fake_ids,
                confirm=False
            )

        assert exc_info.value.status_code == 400
