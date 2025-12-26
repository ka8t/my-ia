"""
Service Admin Users

Logique métier pour la gestion des utilisateurs par les administrateurs.
"""
import uuid
import logging
from typing import Optional, Tuple, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from passlib.context import CryptContext

from app.models import User, Role, UserPreference
from app.features.admin.users.repository import AdminUserRepository

logger = logging.getLogger(__name__)

# Context pour le hashing des mots de passe (compatible avec FastAPI-Users)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminUserService:
    """Service pour les opérations utilisateurs admin"""

    # ========================================================================
    # LECTURE
    # ========================================================================

    @staticmethod
    async def get_users(
        db: AsyncSession,
        role_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        search: Optional[str] = None,
        created_after=None,
        created_before=None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[dict], int]:
        """
        Récupère la liste des utilisateurs avec filtres et pagination.

        Returns:
            Tuple (liste d'utilisateurs, total)
        """
        return await AdminUserRepository.get_users_with_stats(
            db=db,
            role_id=role_id,
            is_active=is_active,
            is_verified=is_verified,
            search=search,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            offset=offset
        )

    @staticmethod
    async def get_user_details(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> dict:
        """
        Récupère les détails complets d'un utilisateur.

        Args:
            db: Session de base de données
            user_id: UUID de l'utilisateur

        Returns:
            Dictionnaire avec les données utilisateur enrichies

        Raises:
            HTTPException 404 si l'utilisateur n'existe pas
        """
        user_data = await AdminUserRepository.get_user_by_id_with_stats(db, user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        return user_data

    # ========================================================================
    # CRÉATION
    # ========================================================================

    @staticmethod
    async def create_user(
        db: AsyncSession,
        email: str,
        username: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role_id: int = 2,
        is_active: bool = True,
        is_verified: bool = False
    ) -> User:
        """
        Crée un nouvel utilisateur.

        Args:
            db: Session de base de données
            email: Adresse email
            username: Nom d'utilisateur
            password: Mot de passe en clair
            first_name: Prénom (optionnel)
            last_name: Nom de famille (optionnel)
            role_id: ID du rôle (défaut: 2 = user)
            is_active: Compte actif (défaut: True)
            is_verified: Email vérifié (défaut: False)

        Returns:
            Utilisateur créé

        Raises:
            HTTPException 409 si email ou username existe déjà
            HTTPException 400 si le rôle n'existe pas
        """
        # Vérifier l'email
        existing_email = await AdminUserRepository.get_user_by_email(db, email)
        if existing_email:
            raise HTTPException(
                status_code=409,
                detail=f"User with email '{email}' already exists"
            )

        # Vérifier le username
        existing_username = await AdminUserRepository.get_user_by_username(db, username)
        if existing_username:
            raise HTTPException(
                status_code=409,
                detail=f"User with username '{username}' already exists"
            )

        # Vérifier que le rôle existe
        role_result = await db.execute(select(Role).where(Role.id == role_id))
        if not role_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Role with id {role_id} does not exist"
            )

        # Hasher le mot de passe
        hashed_password = pwd_context.hash(password)

        # Créer l'utilisateur
        new_user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            role_id=role_id,
            is_active=is_active,
            is_verified=is_verified,
            is_superuser=(role_id == 1)  # Superuser si admin
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Créer les préférences par défaut
        preferences = UserPreference(user_id=new_user.id)
        db.add(preferences)
        await db.commit()

        logger.info(f"User created by admin: {new_user.email} (id={new_user.id})")
        return new_user

    # ========================================================================
    # MISE À JOUR
    # ========================================================================

    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        email: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        address_line1: Optional[str] = None,
        address_line2: Optional[str] = None,
        city_id: Optional[int] = None,
        country_code: Optional[str] = None,
        is_verified: Optional[bool] = None
    ) -> User:
        """
        Met à jour les informations d'un utilisateur.

        Args:
            db: Session de base de données
            user_id: UUID de l'utilisateur
            email: Nouvelle adresse email (optionnel)
            username: Nouveau nom d'utilisateur (optionnel)
            first_name: Nouveau prénom (optionnel)
            last_name: Nouveau nom de famille (optionnel)
            phone: Numéro de téléphone (optionnel)
            address_line1: Adresse ligne 1 (optionnel)
            address_line2: Adresse ligne 2 (optionnel)
            city_id: ID de la ville (optionnel)
            country_code: Code pays ISO (optionnel)
            is_verified: Nouveau statut de vérification (optionnel)

        Returns:
            Utilisateur mis à jour

        Raises:
            HTTPException 404 si l'utilisateur n'existe pas
            HTTPException 409 si email/username existe déjà
        """
        user = await AdminUserRepository.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Vérifier l'unicité de l'email si modifié
        if email and email != user.email:
            existing = await AdminUserRepository.get_user_by_email(db, email)
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"User with email '{email}' already exists"
                )
            user.email = email

        # Vérifier l'unicité du username si modifié
        if username and username != user.username:
            existing = await AdminUserRepository.get_user_by_username(db, username)
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"User with username '{username}' already exists"
                )
            user.username = username

        # Mettre à jour les champs identité
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if is_verified is not None:
            user.is_verified = is_verified

        # Mettre à jour les champs profil
        if phone is not None:
            user.phone = phone
        if address_line1 is not None:
            user.address_line1 = address_line1
        if address_line2 is not None:
            user.address_line2 = address_line2
        if city_id is not None:
            user.city_id = city_id
        if country_code is not None:
            user.country_code = country_code.upper() if country_code else None

        await db.commit()
        await db.refresh(user)

        logger.info(f"User updated by admin: {user.email} (id={user.id})")
        return user

    @staticmethod
    async def change_role(
        db: AsyncSession,
        user_id: uuid.UUID,
        new_role_id: int,
        admin_user_id: uuid.UUID
    ) -> User:
        """
        Change le rôle d'un utilisateur.

        Args:
            db: Session de base de données
            user_id: UUID de l'utilisateur cible
            new_role_id: ID du nouveau rôle
            admin_user_id: UUID de l'admin effectuant l'action

        Returns:
            Utilisateur mis à jour

        Raises:
            HTTPException 404 si utilisateur ou rôle n'existe pas
            HTTPException 403 si l'admin essaie de se rétrograder
            HTTPException 409 si c'est le dernier admin
        """
        user = await AdminUserRepository.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Vérifier que le rôle existe
        role_result = await db.execute(select(Role).where(Role.id == new_role_id))
        role = role_result.scalar_one_or_none()
        if not role:
            raise HTTPException(
                status_code=404,
                detail=f"Role with id {new_role_id} does not exist"
            )

        # Empêcher un admin de se rétrograder lui-même
        if user_id == admin_user_id and new_role_id != 1:
            raise HTTPException(
                status_code=403,
                detail="Cannot demote yourself from admin role"
            )

        # Si on rétrograde un admin, vérifier qu'il reste au moins un admin
        if user.role_id == 1 and new_role_id != 1:
            admin_count = await AdminUserRepository.count_admins(db)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot demote the last admin user"
                )

        old_role_id = user.role_id
        user.role_id = new_role_id
        user.is_superuser = (new_role_id == 1)

        await db.commit()
        await db.refresh(user)

        logger.info(
            f"User role changed: {user.email} from role {old_role_id} to {new_role_id}"
        )
        return user

    @staticmethod
    async def change_status(
        db: AsyncSession,
        user_id: uuid.UUID,
        is_active: bool,
        admin_user_id: uuid.UUID
    ) -> User:
        """
        Active ou désactive un utilisateur.

        Args:
            db: Session de base de données
            user_id: UUID de l'utilisateur cible
            is_active: Nouveau statut
            admin_user_id: UUID de l'admin effectuant l'action

        Returns:
            Utilisateur mis à jour

        Raises:
            HTTPException 404 si l'utilisateur n'existe pas
            HTTPException 403 si l'admin essaie de se désactiver
        """
        user = await AdminUserRepository.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Empêcher un admin de se désactiver lui-même
        if user_id == admin_user_id and not is_active:
            raise HTTPException(
                status_code=403,
                detail="Cannot deactivate your own account"
            )

        user.is_active = is_active
        await db.commit()
        await db.refresh(user)

        status_str = "activated" if is_active else "deactivated"
        logger.info(f"User {status_str}: {user.email} (id={user.id})")
        return user

    @staticmethod
    async def reset_password(
        db: AsyncSession,
        user_id: uuid.UUID,
        new_password: str
    ) -> User:
        """
        Réinitialise le mot de passe d'un utilisateur.

        Args:
            db: Session de base de données
            user_id: UUID de l'utilisateur
            new_password: Nouveau mot de passe en clair

        Returns:
            Utilisateur mis à jour

        Raises:
            HTTPException 404 si l'utilisateur n'existe pas
        """
        user = await AdminUserRepository.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.hashed_password = pwd_context.hash(new_password)
        await db.commit()
        await db.refresh(user)

        logger.info(f"Password reset by admin for user: {user.email} (id={user.id})")
        return user

    # ========================================================================
    # SUPPRESSION
    # ========================================================================

    @staticmethod
    async def delete_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        admin_user_id: uuid.UUID
    ) -> bool:
        """
        Supprime un utilisateur.

        Args:
            db: Session de base de données
            user_id: UUID de l'utilisateur à supprimer
            admin_user_id: UUID de l'admin effectuant l'action

        Returns:
            True si supprimé

        Raises:
            HTTPException 404 si l'utilisateur n'existe pas
            HTTPException 403 si l'admin essaie de se supprimer
            HTTPException 409 si c'est le dernier admin
        """
        user = await AdminUserRepository.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Empêcher un admin de se supprimer lui-même
        if user_id == admin_user_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot delete your own account"
            )

        # Si c'est un admin, vérifier qu'il reste au moins un admin
        if user.role_id == 1:
            admin_count = await AdminUserRepository.count_admins(db)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot delete the last admin user"
                )

        email = user.email
        await db.delete(user)
        await db.commit()

        logger.info(f"User deleted by admin: {email} (id={user_id})")
        return True
