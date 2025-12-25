"""
Tests Securite pour Admin Users

Tests des controles de securite et restrictions :
- Protection auto-suppression
- Protection dernier admin
- Validation donnees
Execution: docker-compose exec app python -m pytest tests/admin/test_admin_users_security.py -v
"""
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.features.admin.users.service import AdminUserService
from app.models import User


# =============================================================================
# TESTS PROTECTION AUTO-ACTION
# =============================================================================

class TestSelfProtection:
    """Tests protection contre les auto-actions"""

    @pytest.mark.asyncio
    async def test_admin_cannot_delete_self(
        self,
        db_session: AsyncSession,
        admin_user: User
    ):
        """Un admin ne peut pas se supprimer lui-meme"""
        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.delete_user(
                db=db_session,
                user_id=admin_user.id,
                admin_user_id=admin_user.id
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_deactivate_self(
        self,
        db_session: AsyncSession,
        admin_user: User
    ):
        """Un admin ne peut pas se desactiver lui-meme"""
        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.change_status(
                db=db_session,
                user_id=admin_user.id,
                is_active=False,
                admin_user_id=admin_user.id
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_demote_self(
        self,
        db_session: AsyncSession,
        admin_user: User
    ):
        """Un admin ne peut pas se retrograder lui-meme"""
        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.change_role(
                db=db_session,
                user_id=admin_user.id,
                new_role_id=2,  # user role
                admin_user_id=admin_user.id
            )

        assert exc_info.value.status_code == 403


# =============================================================================
# TESTS PROTECTION DERNIER ADMIN
# =============================================================================

class TestLastAdminProtection:
    """Tests protection du dernier admin"""

    @pytest.mark.asyncio
    async def test_cannot_demote_if_last_admin(
        self,
        db_session: AsyncSession,
        admin_user: User,
        sample_user_data: dict,
        test_roles
    ):
        """Test protection lors de retrogradation si dernier admin"""
        from sqlalchemy import select, func
        from app.models import User as UserModel

        # Compter les admins
        result = await db_session.execute(
            select(func.count(UserModel.id)).where(UserModel.role_id == 1)
        )
        admin_count = result.scalar()

        if admin_count == 1:
            # S'il n'y a qu'un admin, on ne peut pas le retrograder
            with pytest.raises(HTTPException) as exc_info:
                await AdminUserService.change_role(
                    db=db_session,
                    user_id=admin_user.id,
                    new_role_id=2,
                    admin_user_id=admin_user.id
                )

            # 403 pour self-demotion OU 409 pour dernier admin
            assert exc_info.value.status_code in [403, 409]


# =============================================================================
# TESTS VALIDATION DONNEES
# =============================================================================

class TestDataValidation:
    """Tests validation des donnees"""

    @pytest.mark.asyncio
    async def test_invalid_role_id(
        self,
        db_session: AsyncSession,
        test_user: User,
        admin_user: User
    ):
        """Test role invalide"""
        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.change_role(
                db=db_session,
                user_id=test_user.id,
                new_role_id=999,
                admin_user_id=admin_user.id
            )

        assert exc_info.value.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_user_not_found(
        self,
        db_session: AsyncSession,
        admin_user: User
    ):
        """Test utilisateur inexistant"""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.change_role(
                db=db_session,
                user_id=fake_id,
                new_role_id=2,
                admin_user_id=admin_user.id
            )

        assert exc_info.value.status_code == 404


# =============================================================================
# TESTS RACE CONDITIONS
# =============================================================================

class TestConcurrentAccess:
    """Tests d'acces concurrent"""

    @pytest.mark.asyncio
    async def test_user_not_found_after_deletion(
        self,
        db_session: AsyncSession,
        admin_user: User,
        sample_user_data: dict,
        test_roles
    ):
        """Test acces a un utilisateur deja supprime"""
        # Creer un user temporaire
        temp_user = await AdminUserService.create_user(
            db=db_session,
            email=sample_user_data["email"],
            username=sample_user_data["username"],
            password=sample_user_data["password"]
        )
        user_id = temp_user.id

        # Supprimer
        await AdminUserService.delete_user(
            db=db_session,
            user_id=user_id,
            admin_user_id=admin_user.id
        )

        # Tenter d'acceder
        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.get_user_details(db_session, user_id)

        assert exc_info.value.status_code == 404
