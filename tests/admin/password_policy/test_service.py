"""
Tests pour le service Password Policy.

Execution: docker-compose exec app python -m pytest tests/admin/password_policy/ -v
"""
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.features.admin.password_policy.service import PasswordPolicyService


# =============================================================================
# TESTS CRUD POLICIES
# =============================================================================

class TestPasswordPolicyServiceCRUD:
    """Tests CRUD pour les politiques de mot de passe."""

    @pytest.mark.asyncio
    async def test_get_all_policies(self, db_session: AsyncSession):
        """Test liste des politiques."""
        policies = await PasswordPolicyService.get_all_policies(db_session)

        assert isinstance(policies, list)
        # Au moins la politique default doit exister
        assert len(policies) >= 1

    @pytest.mark.asyncio
    async def test_get_policy_by_name_default(self, db_session: AsyncSession):
        """Test recuperation politique par defaut."""
        policy = await PasswordPolicyService.get_policy_by_name(
            db_session, "default"
        )

        assert policy is not None
        assert policy.name == "default"
        assert policy.min_length >= 4

    @pytest.mark.asyncio
    async def test_get_policy_not_found(self, db_session: AsyncSession):
        """Test 404 si politique inexistante."""
        with pytest.raises(HTTPException) as exc_info:
            await PasswordPolicyService.get_policy_by_name(
                db_session, "nonexistent_policy"
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_policy(self, db_session: AsyncSession):
        """Test creation d'une politique."""
        unique_name = f"test_policy_{uuid.uuid4().hex[:8]}"

        policy = await PasswordPolicyService.create_policy(
            db=db_session,
            name=unique_name,
            min_length=10,
            max_length=64,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=False,
            history_count=3
        )

        assert policy is not None
        assert policy.name == unique_name
        assert policy.min_length == 10
        assert policy.require_special is False
        assert policy.history_count == 3

        # Cleanup
        await PasswordPolicyService.delete_policy(db_session, policy.id)

    @pytest.mark.asyncio
    async def test_create_policy_duplicate_name(self, db_session: AsyncSession):
        """Test 409 si nom existe deja."""
        with pytest.raises(HTTPException) as exc_info:
            await PasswordPolicyService.create_policy(
                db=db_session,
                name="default",  # Existe deja
                min_length=8
            )

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_update_policy(self, db_session: AsyncSession):
        """Test mise a jour d'une politique."""
        # Creer une politique de test
        unique_name = f"update_test_{uuid.uuid4().hex[:8]}"
        policy = await PasswordPolicyService.create_policy(
            db=db_session,
            name=unique_name,
            min_length=8
        )

        try:
            # Mettre a jour
            updated = await PasswordPolicyService.update_policy(
                db=db_session,
                policy_id=policy.id,
                min_length=12,
                require_special=False
            )

            assert updated.min_length == 12
            assert updated.require_special is False
        finally:
            # Cleanup
            await PasswordPolicyService.delete_policy(db_session, policy.id)

    @pytest.mark.asyncio
    async def test_delete_policy_default_forbidden(self, db_session: AsyncSession):
        """Test impossible de supprimer la politique default."""
        # Recuperer l'ID de default
        default_policy = await PasswordPolicyService.get_policy_by_name(
            db_session, "default"
        )

        with pytest.raises(HTTPException) as exc_info:
            await PasswordPolicyService.delete_policy(
                db_session, default_policy.id
            )

        assert exc_info.value.status_code == 403


# =============================================================================
# TESTS VALIDATION
# =============================================================================

class TestPasswordPolicyServiceValidation:
    """Tests de validation via le service."""

    @pytest.mark.asyncio
    async def test_validate_password_valid(self, db_session: AsyncSession):
        """Test validation reussie."""
        result = await PasswordPolicyService.validate_password(
            db_session,
            password="SecureP@ssword123",
            policy_name="default"
        )

        assert result.is_valid is True
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_validate_password_invalid(self, db_session: AsyncSession):
        """Test validation echec."""
        result = await PasswordPolicyService.validate_password(
            db_session,
            password="weak",
            policy_name="default"
        )

        assert result.is_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_get_requirements(self, db_session: AsyncSession):
        """Test recuperation des exigences."""
        requirements = await PasswordPolicyService.get_requirements(
            db_session, "default"
        )

        assert "min_length" in requirements
        assert "max_length" in requirements
        assert "require_uppercase" in requirements
        assert "require_lowercase" in requirements
        assert "require_digit" in requirements
        assert "require_special" in requirements
        assert "special_characters" in requirements
        assert "expire_days" in requirements
        assert "history_count" in requirements


# =============================================================================
# TESTS HISTORIQUE
# =============================================================================

class TestPasswordPolicyServiceHistory:
    """Tests de gestion de l'historique."""

    @pytest.mark.asyncio
    async def test_add_password_to_history(
        self, db_session: AsyncSession, admin_user_id: uuid.UUID
    ):
        """Test ajout a l'historique."""
        # Creer une politique avec history_count > 0
        unique_name = f"history_test_{uuid.uuid4().hex[:8]}"
        policy = await PasswordPolicyService.create_policy(
            db=db_session,
            name=unique_name,
            min_length=8,
            history_count=3
        )

        try:
            # Ajouter un mot de passe a l'historique
            await PasswordPolicyService.add_password_to_history(
                db=db_session,
                user_id=admin_user_id,
                hashed_password="$2b$12$test_hash_value",
                policy_name=unique_name
            )

            # Pas d'erreur = succes
        finally:
            # Cleanup
            await PasswordPolicyService.clear_password_history(
                db_session, admin_user_id
            )
            await PasswordPolicyService.delete_policy(db_session, policy.id)

    @pytest.mark.asyncio
    async def test_clear_password_history(
        self, db_session: AsyncSession, admin_user_id: uuid.UUID
    ):
        """Test suppression de l'historique."""
        count = await PasswordPolicyService.clear_password_history(
            db_session, admin_user_id
        )

        # Le count peut etre 0 si rien n'etait dans l'historique
        assert count >= 0
