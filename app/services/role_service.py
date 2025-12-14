"""
Service for managing roles and permissions (RBAC).
"""
from typing import List, Optional
from sqlmodel import Session, select, or_
from datetime import datetime

from app.models.role import (
    Role, Permission, RolePermission, UserRole,
    RoleCreate, PermissionCreate, RoleRead, PermissionRead
)
from app.models.user import User


class RoleService:
    """Service for managing roles"""

    def create_role(
        self,
        session: Session,
        role_data: RoleCreate,
        is_system: bool = False
    ) -> Role:
        """Create a new role"""
        # Generate permission name from action:resource
        role = Role(
            name=role_data.name,
            display_name=role_data.display_name,
            description=role_data.description,
            is_system=is_system
        )

        session.add(role)
        session.commit()
        session.refresh(role)

        # Assign permissions if provided
        if role_data.permission_ids:
            self.assign_permissions_to_role(
                session,
                role.id,
                role_data.permission_ids
            )
            session.refresh(role)

        return role

    def get_role_by_id(self, session: Session, role_id: int) -> Optional[Role]:
        """Get role by ID"""
        return session.get(Role, role_id)

    def get_role_by_name(self, session: Session, name: str) -> Optional[Role]:
        """Get role by name"""
        statement = select(Role).where(Role.name == name)
        return session.exec(statement).first()

    def get_all_roles(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False
    ) -> List[Role]:
        """Get all roles"""
        statement = select(Role).offset(skip).limit(limit)

        if not include_inactive:
            statement = statement.where(Role.is_active == True)

        return list(session.exec(statement).all())

    def update_role(
        self,
        session: Session,
        role_id: int,
        role_data: dict
    ) -> Optional[Role]:
        """Update role"""
        role = self.get_role_by_id(session, role_id)
        if not role:
            return None

        # System roles cannot be modified
        if role.is_system:
            raise ValueError("System roles cannot be modified")

        for key, value in role_data.items():
            if value is not None and hasattr(role, key):
                setattr(role, key, value)

        role.updated_at = datetime.utcnow()
        session.add(role)
        session.commit()
        session.refresh(role)

        return role

    def delete_role(self, session: Session, role_id: int) -> bool:
        """Delete role"""
        role = self.get_role_by_id(session, role_id)
        if not role:
            return False

        # System roles cannot be deleted
        if role.is_system:
            raise ValueError("System roles cannot be deleted")

        # Remove all user-role assignments
        statement = select(UserRole).where(UserRole.role_id == role_id)
        user_roles = session.exec(statement).all()
        for user_role in user_roles:
            session.delete(user_role)

        # Remove all role-permission assignments
        statement = select(RolePermission).where(RolePermission.role_id == role_id)
        role_perms = session.exec(statement).all()
        for role_perm in role_perms:
            session.delete(role_perm)

        session.delete(role)
        session.commit()

        return True

    def get_role_permissions(self, session: Session, role_id: int) -> List[Permission]:
        """Get all permissions for a role"""
        statement = (
            select(Permission)
            .join(RolePermission)
            .where(RolePermission.role_id == role_id)
        )
        return list(session.exec(statement).all())

    def assign_permissions_to_role(
        self,
        session: Session,
        role_id: int,
        permission_ids: List[int]
    ) -> bool:
        """Assign permissions to a role"""
        role = self.get_role_by_id(session, role_id)
        if not role:
            return False

        # Remove existing permissions
        statement = select(RolePermission).where(RolePermission.role_id == role_id)
        existing = session.exec(statement).all()
        for rp in existing:
            session.delete(rp)

        # Add new permissions
        for perm_id in permission_ids:
            role_perm = RolePermission(role_id=role_id, permission_id=perm_id)
            session.add(role_perm)

        session.commit()
        return True

    def assign_role_to_user(
        self,
        session: Session,
        user_id: int,
        role_id: int
    ) -> bool:
        """Assign a role to a user"""
        # Check if user exists
        user = session.get(User, user_id)
        if not user:
            return False

        # Check if role exists
        role = self.get_role_by_id(session, role_id)
        if not role:
            return False

        # Check if already assigned
        statement = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
        existing = session.exec(statement).first()

        if existing:
            return True  # Already assigned

        # Create assignment
        user_role = UserRole(user_id=user_id, role_id=role_id)
        session.add(user_role)
        session.commit()

        return True

    def remove_role_from_user(
        self,
        session: Session,
        user_id: int,
        role_id: int
    ) -> bool:
        """Remove a role from a user"""
        statement = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
        user_role = session.exec(statement).first()

        if not user_role:
            return False

        session.delete(user_role)
        session.commit()

        return True

    def get_user_roles(self, session: Session, user_id: int) -> List[Role]:
        """Get all roles for a user"""
        statement = (
            select(Role)
            .join(UserRole)
            .where(UserRole.user_id == user_id)
        )
        return list(session.exec(statement).all())

    def get_user_permissions(self, session: Session, user_id: int) -> List[Permission]:
        """Get all permissions for a user (through their roles)"""
        statement = (
            select(Permission)
            .join(RolePermission)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
            .distinct()
        )
        return list(session.exec(statement).all())

    def user_has_permission(
        self,
        session: Session,
        user_id: int,
        action: str,
        resource: str
    ) -> bool:
        """Check if user has a specific permission"""
        permission_name = f"{action}:{resource}"

        # Check for exact permission
        statement = (
            select(Permission)
            .join(RolePermission)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(
                UserRole.user_id == user_id,
                or_(
                    Permission.name == permission_name,
                    Permission.name == f"manage:{resource}",
                    Permission.name == "manage:all"
                )
            )
        )

        permission = session.exec(statement).first()
        return permission is not None

    def user_has_role(
        self,
        session: Session,
        user_id: int,
        role_name: str
    ) -> bool:
        """Check if user has a specific role"""
        statement = (
            select(Role)
            .join(UserRole)
            .where(
                UserRole.user_id == user_id,
                Role.name == role_name
            )
        )

        role = session.exec(statement).first()
        return role is not None


class PermissionService:
    """Service for managing permissions"""

    def create_permission(
        self,
        session: Session,
        perm_data: PermissionCreate
    ) -> Permission:
        """Create a new permission"""
        # Generate name from action:resource
        name = f"{perm_data.action}:{perm_data.resource}"

        permission = Permission(
            name=name,
            action=perm_data.action,
            resource=perm_data.resource,
            description=perm_data.description
        )

        session.add(permission)
        session.commit()
        session.refresh(permission)

        return permission

    def get_permission_by_id(self, session: Session, perm_id: int) -> Optional[Permission]:
        """Get permission by ID"""
        return session.get(Permission, perm_id)

    def get_permission_by_name(self, session: Session, name: str) -> Optional[Permission]:
        """Get permission by name"""
        statement = select(Permission).where(Permission.name == name)
        return session.exec(statement).first()

    def get_all_permissions(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[Permission]:
        """Get all permissions"""
        statement = select(Permission).offset(skip).limit(limit)
        return list(session.exec(statement).all())

    def delete_permission(self, session: Session, perm_id: int) -> bool:
        """Delete permission"""
        permission = self.get_permission_by_id(session, perm_id)
        if not permission:
            return False

        # Remove from all roles
        statement = select(RolePermission).where(RolePermission.permission_id == perm_id)
        role_perms = session.exec(statement).all()
        for rp in role_perms:
            session.delete(rp)

        session.delete(permission)
        session.commit()

        return True


# Singleton instances
role_service = RoleService()
permission_service = PermissionService()
