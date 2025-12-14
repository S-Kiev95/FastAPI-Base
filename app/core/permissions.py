"""
Permission-based authorization dependencies.
Used to protect endpoints based on user roles and permissions.
"""
from fastapi import Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.database import get_session
from app.core.dependencies import get_current_active_user
from app.models.user import UserRead
from app.services.role_service import role_service


def require_permission(action: str, resource: str):
    """
    Dependency factory to require a specific permission.

    Usage:
        @router.post("/users/")
        async def create_user(
            current_user: UserRead = Depends(require_permission("create", "users"))
        ):
            ...
    """
    async def permission_checker(
        current_user: UserRead = Depends(get_current_active_user),
        session: Session = Depends(get_session)
    ) -> UserRead:
        # Check if user has permission
        has_permission = role_service.user_has_permission(
            session,
            current_user.id,
            action,
            resource
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {action}:{resource}"
            )

        return current_user

    return permission_checker


def require_role(role_name: str):
    """
    Dependency factory to require a specific role.

    Usage:
        @router.get("/admin/dashboard")
        async def admin_dashboard(
            current_user: UserRead = Depends(require_role("admin"))
        ):
            ...
    """
    async def role_checker(
        current_user: UserRead = Depends(get_current_active_user),
        session: Session = Depends(get_session)
    ) -> UserRead:
        # Check if user has role
        has_role = role_service.user_has_role(
            session,
            current_user.id,
            role_name
        )

        if not has_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role_name}"
            )

        return current_user

    return role_checker


def require_any_role(role_names: List[str]):
    """
    Dependency factory to require any of the specified roles.

    Usage:
        @router.get("/moderate")
        async def moderate(
            current_user: UserRead = Depends(require_any_role(["admin", "moderator"]))
        ):
            ...
    """
    async def role_checker(
        current_user: UserRead = Depends(get_current_active_user),
        session: Session = Depends(get_session)
    ) -> UserRead:
        # Check if user has any of the roles
        for role_name in role_names:
            if role_service.user_has_role(session, current_user.id, role_name):
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"One of these roles required: {', '.join(role_names)}"
        )

    return role_checker


def require_all_permissions(permissions: List[tuple]):
    """
    Dependency factory to require multiple permissions.

    Usage:
        @router.post("/admin/users/bulk-delete")
        async def bulk_delete(
            current_user: UserRead = Depends(require_all_permissions([
                ("delete", "users"),
                ("manage", "users")
            ]))
        ):
            ...
    """
    async def permissions_checker(
        current_user: UserRead = Depends(get_current_active_user),
        session: Session = Depends(get_session)
    ) -> UserRead:
        for action, resource in permissions:
            has_permission = role_service.user_has_permission(
                session,
                current_user.id,
                action,
                resource
            )

            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required: {action}:{resource}"
                )

        return current_user

    return permissions_checker


# Common permission dependencies (shortcuts)
require_superadmin = require_role("superadmin")
require_admin = require_any_role(["superadmin", "admin"])
require_moderator = require_any_role(["superadmin", "admin", "moderator"])


# Resource-specific permission dependencies
def require_users_create(): return require_permission("create", "users")
def require_users_read(): return require_permission("read", "users")
def require_users_update(): return require_permission("update", "users")
def require_users_delete(): return require_permission("delete", "users")
def require_users_manage(): return require_permission("manage", "users")

def require_roles_manage(): return require_permission("manage", "roles")
def require_media_create(): return require_permission("create", "media")
def require_media_delete(): return require_permission("delete", "media")
