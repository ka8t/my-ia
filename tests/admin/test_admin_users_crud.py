"""
Tests CRUD pour Admin Users

Tests des operations Create, Read, Update, Delete sur les utilisateurs.
Execution: docker-compose exec app python -m pytest tests/admin/test_admin_users_crud.py -v
"""
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.features.admin.users.service import AdminUserService
from app.models import User


# =============================================================================
# TESTS SERVICE - GET USERS
# =============================================================================

class TestAdminUserService:
    """Tests pour le service AdminUser"""

    @pytest.mark.asyncio
    async def test_get_users_returns_tuple(self, db_session: AsyncSession):
        """Test que get_users retourne (liste, total)"""
        users, total = await AdminUserService.get_users(
            db=db_session,
            limit=10,
            offset=0
        )

        assert isinstance(users, list)
        assert isinstance(total, int)
        assert total >= 0

    @pytest.mark.asyncio
    async def test_get_users_pagination(
        self,
        db_session: AsyncSession,
        multiple_users: list
    ):
        """Test pagination des utilisateurs"""
        # Page 1
        users_p1, total = await AdminUserService.get_users(
            db=db_session,
            limit=2,
            offset=0
        )

        # Page 2
        users_p2, _ = await AdminUserService.get_users(
            db=db_session,
            limit=2,
            offset=2
        )

        if total > 2 and len(users_p1) > 0 and len(users_p2) > 0:
            # Extraire les IDs (dict ou objet)
            def get_id(u):
                return u.get("id") if isinstance(u, dict) else u.id

            ids_p1 = {get_id(u) for u in users_p1}
            ids_p2 = {get_id(u) for u in users_p2}
            assert ids_p1.isdisjoint(ids_p2), "Pages should have different users"

    @pytest.mark.asyncio
    async def test_get_users_filter_by_role(
        self,
        db_session: AsyncSession,
        test_roles
    ):
        """Test filtre par role"""
        users, total = await AdminUserService.get_users(
            db=db_session,
            role_id=1,  # admin
            limit=50,
            offset=0
        )

        for user in users:
            role_id = user.get("role_id") if isinstance(user, dict) else user.role_id
            assert role_id == 1

    @pytest.mark.asyncio
    async def test_get_users_filter_by_active(self, db_session: AsyncSession):
        """Test filtre par statut actif"""
        users, total = await AdminUserService.get_users(
            db=db_session,
            is_active=True,
            limit=50,
            offset=0
        )

        for user in users:
            is_active = user.get("is_active") if isinstance(user, dict) else user.is_active
            assert is_active is True

    @pytest.mark.asyncio
    async def test_get_users_search(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test recherche utilisateur"""
        users, total = await AdminUserService.get_users(
            db=db_session,
            search=test_user.username[:5],
            limit=50,
            offset=0
        )

        assert total >= 1


# =============================================================================
# TESTS GET USER DETAILS
# =============================================================================

class TestAdminUserDetails:
    """Tests get_user_details"""

    @pytest.mark.asyncio
    async def test_get_user_details_success(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test recuperation details utilisateur"""
        details = await AdminUserService.get_user_details(
            db=db_session,
            user_id=test_user.id
        )

        assert details is not None

    @pytest.mark.asyncio
    async def test_get_user_details_not_found(self, db_session: AsyncSession):
        """Test 404 si utilisateur inexistant"""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.get_user_details(
                db=db_session,
                user_id=fake_id
            )

        assert exc_info.value.status_code == 404


# =============================================================================
# TESTS CREATE USER
# =============================================================================

class TestAdminUserCreate:
    """Tests creation utilisateur"""

    @pytest.mark.asyncio
    async def test_create_user_success(
        self,
        db_session: AsyncSession,
        test_roles,
        sample_user_data: dict
    ):
        """Test creation utilisateur reussie"""
        user = await AdminUserService.create_user(
            db=db_session,
            email=sample_user_data["email"],
            username=sample_user_data["username"],
            password=sample_user_data["password"],
            full_name=sample_user_data["full_name"],
            role_id=sample_user_data["role_id"]
        )

        assert user is not None
        assert user.email == sample_user_data["email"]
        assert user.username == sample_user_data["username"]

        # Cleanup
        await db_session.delete(user)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test 409 si email existe deja"""
        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.create_user(
                db=db_session,
                email=test_user.email,
                username=f"unique_{uuid.uuid4().hex[:8]}",
                password="Password123!"
            )

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test 409 si username existe deja"""
        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.create_user(
                db=db_session,
                email=f"unique_{uuid.uuid4().hex[:8]}@test.local",
                username=test_user.username,
                password="Password123!"
            )

        assert exc_info.value.status_code == 409


# =============================================================================
# TESTS UPDATE USER
# =============================================================================

class TestAdminUserUpdate:
    """Tests mise a jour utilisateur"""

    @pytest.mark.asyncio
    async def test_update_user_email(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test mise a jour email"""
        original_email = test_user.email
        new_email = f"updated_{uuid.uuid4().hex[:8]}@test.local"

        updated_user = await AdminUserService.update_user(
            db=db_session,
            user_id=test_user.id,
            email=new_email
        )

        assert updated_user.email == new_email

        # Remettre l'email original
        await AdminUserService.update_user(
            db=db_session,
            user_id=test_user.id,
            email=original_email
        )

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, db_session: AsyncSession):
        """Test 404 si utilisateur inexistant"""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.update_user(
                db=db_session,
                user_id=fake_id,
                email="newemail@test.local"
            )

        assert exc_info.value.status_code == 404


# =============================================================================
# TESTS CHANGE ROLE
# =============================================================================

class TestAdminUserChangeRole:
    """Tests changement de role"""

    @pytest.mark.asyncio
    async def test_change_role_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        admin_user: User,
        test_roles
    ):
        """Test changement de role reussi"""
        original_role = test_user.role_id

        # Passer en contributeur (role 3) si existe, sinon role 1
        new_role = 3 if len(test_roles) > 2 else 1

        updated_user = await AdminUserService.change_role(
            db=db_session,
            user_id=test_user.id,
            new_role_id=new_role,
            admin_user_id=admin_user.id
        )

        assert updated_user.role_id == new_role

        # Remettre le role original
        await AdminUserService.change_role(
            db=db_session,
            user_id=test_user.id,
            new_role_id=original_role,
            admin_user_id=admin_user.id
        )

    @pytest.mark.asyncio
    async def test_change_role_invalid_role(
        self,
        db_session: AsyncSession,
        test_user: User,
        admin_user: User
    ):
        """Test 404 si role inexistant"""
        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.change_role(
                db=db_session,
                user_id=test_user.id,
                new_role_id=9999,
                admin_user_id=admin_user.id
            )

        assert exc_info.value.status_code == 404


# =============================================================================
# TESTS CHANGE STATUS
# =============================================================================

class TestAdminUserChangeStatus:
    """Tests changement de statut"""

    @pytest.mark.asyncio
    async def test_toggle_status(
        self,
        db_session: AsyncSession,
        test_user: User,
        admin_user: User
    ):
        """Test activation/desactivation utilisateur"""
        original_status = test_user.is_active

        # Basculer le statut
        updated_user = await AdminUserService.change_status(
            db=db_session,
            user_id=test_user.id,
            is_active=not original_status,
            admin_user_id=admin_user.id
        )

        assert updated_user.is_active is not original_status

        # Remettre le statut original
        await AdminUserService.change_status(
            db=db_session,
            user_id=test_user.id,
            is_active=original_status,
            admin_user_id=admin_user.id
        )


# =============================================================================
# TESTS RESET PASSWORD
# =============================================================================

class TestAdminUserResetPassword:
    """Tests reset mot de passe"""

    @pytest.mark.asyncio
    async def test_reset_password_success(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test reset mot de passe reussi"""
        old_hash = test_user.hashed_password

        updated_user = await AdminUserService.reset_password(
            db=db_session,
            user_id=test_user.id,
            new_password="NewPassword123!"
        )

        assert updated_user.hashed_password != old_hash

    @pytest.mark.asyncio
    async def test_reset_password_not_found(self, db_session: AsyncSession):
        """Test 404 si utilisateur inexistant"""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.reset_password(
                db=db_session,
                user_id=fake_id,
                new_password="NewPassword123!"
            )

        assert exc_info.value.status_code == 404


# =============================================================================
# TESTS DELETE USER
# =============================================================================

class TestAdminUserDelete:
    """Tests suppression utilisateur"""

    @pytest.mark.asyncio
    async def test_delete_user_success(
        self,
        db_session: AsyncSession,
        admin_user: User,
        sample_user_data: dict,
        test_roles
    ):
        """Test suppression utilisateur reussie"""
        # Creer un user a supprimer
        user_to_delete = await AdminUserService.create_user(
            db=db_session,
            email=sample_user_data["email"],
            username=sample_user_data["username"],
            password=sample_user_data["password"]
        )
        user_id = user_to_delete.id

        # Supprimer
        result = await AdminUserService.delete_user(
            db=db_session,
            user_id=user_id,
            admin_user_id=admin_user.id
        )

        assert result is True

        # Verifier suppression
        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.get_user_details(
                db=db_session,
                user_id=user_id
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_user_not_found(
        self,
        db_session: AsyncSession,
        admin_user: User
    ):
        """Test 404 si utilisateur inexistant"""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await AdminUserService.delete_user(
                db=db_session,
                user_id=fake_id,
                admin_user_id=admin_user.id
            )

        assert exc_info.value.status_code == 404


# =============================================================================
# TESTS EDGE CASES
# =============================================================================

class TestAdminUserEdgeCases:
    """Tests cas limites"""

    @pytest.mark.asyncio
    async def test_pagination_beyond_total(self, db_session: AsyncSession):
        """Test pagination au-dela du total"""
        users, total = await AdminUserService.get_users(
            db=db_session,
            limit=10,
            offset=99999
        )

        assert users == []

    @pytest.mark.asyncio
    async def test_search_no_results(self, db_session: AsyncSession):
        """Test recherche sans resultats"""
        users, total = await AdminUserService.get_users(
            db=db_session,
            search="zzzznonexistent999xyz",
            limit=10,
            offset=0
        )

        assert users == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_filter_combination(self, db_session: AsyncSession):
        """Test combinaison de filtres"""
        users, total = await AdminUserService.get_users(
            db=db_session,
            is_active=True,
            is_verified=True,
            limit=10,
            offset=0
        )

        for user in users:
            is_active = user.get("is_active") if isinstance(user, dict) else user.is_active
            is_verified = user.get("is_verified") if isinstance(user, dict) else user.is_verified
            assert is_active is True
            assert is_verified is True
