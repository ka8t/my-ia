"""
Tests pour le validateur de mot de passe.

Execution: docker-compose exec app python -m pytest tests/admin/password_policy/ -v
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PasswordPolicy
from app.features.admin.password_policy.validator import PasswordValidator


# =============================================================================
# TESTS VALIDATION LOCALE (sans DB)
# =============================================================================

class TestPasswordValidatorLocal:
    """Tests de validation sans acces a la DB."""

    def test_validate_against_policy_valid(self):
        """Test validation reussie."""
        policy = PasswordPolicy(
            name="test",
            min_length=8,
            max_length=128,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=True,
            special_characters="!@#$%^&*()"
        )

        is_valid, errors = PasswordValidator.validate_against_policy(
            "SecureP@ss123", policy
        )

        assert is_valid is True
        assert errors == []

    def test_validate_against_policy_too_short(self):
        """Test mot de passe trop court."""
        policy = PasswordPolicy(
            name="test",
            min_length=8,
            max_length=128,
            require_uppercase=False,
            require_lowercase=False,
            require_digit=False,
            require_special=False,
            special_characters="!@#$%^&*()"
        )

        is_valid, errors = PasswordValidator.validate_against_policy(
            "short", policy
        )

        assert is_valid is False
        assert len(errors) == 1
        assert "au moins 8 caracteres" in errors[0]

    def test_validate_against_policy_too_long(self):
        """Test mot de passe trop long."""
        policy = PasswordPolicy(
            name="test",
            min_length=8,
            max_length=20,
            require_uppercase=False,
            require_lowercase=False,
            require_digit=False,
            require_special=False,
            special_characters="!@#$%^&*()"
        )

        is_valid, errors = PasswordValidator.validate_against_policy(
            "a" * 25, policy
        )

        assert is_valid is False
        assert len(errors) == 1
        assert "depasser 20 caracteres" in errors[0]

    def test_validate_against_policy_missing_uppercase(self):
        """Test majuscule manquante."""
        policy = PasswordPolicy(
            name="test",
            min_length=8,
            max_length=128,
            require_uppercase=True,
            require_lowercase=False,
            require_digit=False,
            require_special=False,
            special_characters="!@#$%^&*()"
        )

        is_valid, errors = PasswordValidator.validate_against_policy(
            "lowercase123", policy
        )

        assert is_valid is False
        assert any("majuscule" in e for e in errors)

    def test_validate_against_policy_missing_lowercase(self):
        """Test minuscule manquante."""
        policy = PasswordPolicy(
            name="test",
            min_length=8,
            max_length=128,
            require_uppercase=False,
            require_lowercase=True,
            require_digit=False,
            require_special=False,
            special_characters="!@#$%^&*()"
        )

        is_valid, errors = PasswordValidator.validate_against_policy(
            "UPPERCASE123", policy
        )

        assert is_valid is False
        assert any("minuscule" in e for e in errors)

    def test_validate_against_policy_missing_digit(self):
        """Test chiffre manquant."""
        policy = PasswordPolicy(
            name="test",
            min_length=8,
            max_length=128,
            require_uppercase=False,
            require_lowercase=False,
            require_digit=True,
            require_special=False,
            special_characters="!@#$%^&*()"
        )

        is_valid, errors = PasswordValidator.validate_against_policy(
            "NoDigitsHere", policy
        )

        assert is_valid is False
        assert any("chiffre" in e for e in errors)

    def test_validate_against_policy_missing_special(self):
        """Test caractere special manquant."""
        policy = PasswordPolicy(
            name="test",
            min_length=8,
            max_length=128,
            require_uppercase=False,
            require_lowercase=False,
            require_digit=False,
            require_special=True,
            special_characters="!@#$%^&*()"
        )

        is_valid, errors = PasswordValidator.validate_against_policy(
            "NoSpecialChars123", policy
        )

        assert is_valid is False
        assert any("special" in e for e in errors)

    def test_validate_against_policy_multiple_errors(self):
        """Test plusieurs erreurs en meme temps."""
        policy = PasswordPolicy(
            name="test",
            min_length=12,
            max_length=128,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=True,
            special_characters="!@#$%^&*()"
        )

        is_valid, errors = PasswordValidator.validate_against_policy(
            "short", policy
        )

        assert is_valid is False
        assert len(errors) >= 4  # Trop court + manque maj, chiffre, special


# =============================================================================
# TESTS STRENGTH SCORE
# =============================================================================

class TestPasswordStrength:
    """Tests du calcul de robustesse."""

    def test_strength_weak_password(self):
        """Test mot de passe faible."""
        policy = PasswordPolicy(
            name="test",
            min_length=8,
            max_length=128,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=True,
            special_characters="!@#$%^&*()"
        )

        score = PasswordValidator.calculate_strength("abc", policy)
        assert score < 30

    def test_strength_medium_password(self):
        """Test mot de passe moyen."""
        policy = PasswordPolicy(
            name="test",
            min_length=8,
            max_length=128,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=True,
            special_characters="!@#$%^&*()"
        )

        score = PasswordValidator.calculate_strength("Password1", policy)
        assert 30 <= score < 70

    def test_strength_strong_password(self):
        """Test mot de passe fort."""
        policy = PasswordPolicy(
            name="test",
            min_length=8,
            max_length=128,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=True,
            special_characters="!@#$%^&*()"
        )

        score = PasswordValidator.calculate_strength("SecureP@ss123!XYZ", policy)
        assert score >= 70


# =============================================================================
# TESTS SUGGESTIONS
# =============================================================================

class TestPasswordSuggestions:
    """Tests des suggestions d'amelioration."""

    def test_suggestions_too_short(self):
        """Test suggestion pour mot de passe trop court."""
        policy = PasswordPolicy(
            name="test",
            min_length=12,
            max_length=128,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=True,
            special_characters="!@#$%^&*()"
        )

        suggestions = PasswordValidator.get_suggestions(
            "short", policy, ["trop court"]
        )

        assert any("Ajoutez" in s for s in suggestions)

    def test_suggestions_repeated_chars(self):
        """Test detection des caracteres repetes."""
        policy = PasswordPolicy(
            name="test",
            min_length=8,
            max_length=128,
            require_uppercase=False,
            require_lowercase=False,
            require_digit=False,
            require_special=False,
            special_characters="!@#$%^&*()"
        )

        suggestions = PasswordValidator.get_suggestions(
            "passsword111", policy, []
        )

        assert any("repetes" in s.lower() for s in suggestions)

    def test_suggestions_sequential_numbers(self):
        """Test detection des suites de chiffres."""
        policy = PasswordPolicy(
            name="test",
            min_length=8,
            max_length=128,
            require_uppercase=False,
            require_lowercase=False,
            require_digit=False,
            require_special=False,
            special_characters="!@#$%^&*()"
        )

        suggestions = PasswordValidator.get_suggestions(
            "password123", policy, []
        )

        assert any("suites de chiffres" in s for s in suggestions)


# =============================================================================
# TESTS AVEC DB
# =============================================================================

class TestPasswordValidatorWithDB:
    """Tests de validation avec acces a la DB."""

    @pytest.mark.asyncio
    async def test_validate_password_with_default_policy(
        self, db_session: AsyncSession
    ):
        """Test validation avec politique par defaut."""
        result = await PasswordValidator.validate_password(
            db_session, "SecureP@ss123", "default"
        )

        assert result.is_valid is True
        assert result.errors == []
        assert result.strength_score > 0

    @pytest.mark.asyncio
    async def test_validate_password_invalid(
        self, db_session: AsyncSession
    ):
        """Test validation echec."""
        result = await PasswordValidator.validate_password(
            db_session, "weak", "default"
        )

        assert result.is_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_get_requirements(self, db_session: AsyncSession):
        """Test recuperation des exigences."""
        requirements = await PasswordValidator.get_requirements(
            db_session, "default"
        )

        assert "min_length" in requirements
        assert "require_uppercase" in requirements
        assert "require_special" in requirements
        assert requirements["min_length"] >= 4
