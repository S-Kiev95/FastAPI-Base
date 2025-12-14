"""
Routes for role and permission management (RBAC).
Protected by role/permission-based authorization.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.database import get_session
from app.models.role import (
    RoleCreate, RoleRead, RoleReadWithPermissions, RoleUpdate,
    PermissionCreate, PermissionRead,
    AssignRoleRequest, AssignPermissionsRequest
)
from app.models.user import UserRead
from app.services.role_service import role_service, permission_service
from app.core.permissions import require_admin, require_role, require_permission

router = APIRouter(prefix="/roles", tags=["roles & permissions"])


# ==================== ROLES ====================

@router.post("/", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_admin)
):
    """
    Create a new role.
    Requires admin or superadmin role.
    """
    # Check if role already exists
    existing = role_service.get_role_by_name(session, role_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role_data.name}' already exists"
        )

    role = role_service.create_role(session, role_data, is_system=False)
    return RoleRead.model_validate(role)


@router.get("/", response_model=List[RoleRead])
async def get_all_roles(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_permission("read", "roles"))
):
    """
    Get all roles.
    Requires read:roles permission.
    """
    roles = role_service.get_all_roles(session, skip, limit)
    return [RoleRead.model_validate(role) for role in roles]


@router.get("/{role_id}", response_model=RoleReadWithPermissions)
async def get_role(
    role_id: int,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_permission("read", "roles"))
):
    """
    Get role by ID with its permissions.
    Requires read:roles permission.
    """
    role = role_service.get_role_by_id(session, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Get permissions for this role
    permissions = role_service.get_role_permissions(session, role_id)

    role_dict = RoleRead.model_validate(role).model_dump()
    role_dict["permissions"] = [
        PermissionRead.model_validate(perm) for perm in permissions
    ]

    return role_dict


@router.patch("/{role_id}", response_model=RoleRead)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_admin)
):
    """
    Update role.
    Requires admin or superadmin role.
    System roles cannot be modified.
    """
    try:
        role = role_service.update_role(
            session,
            role_id,
            role_data.model_dump(exclude_unset=True)
        )

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        return RoleRead.model_validate(role)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_role("superadmin"))
):
    """
    Delete role.
    Requires superadmin role.
    System roles cannot be deleted.
    """
    try:
        success = role_service.delete_role(session, role_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== PERMISSIONS ====================

@router.post("/permissions", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
async def create_permission(
    perm_data: PermissionCreate,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_admin)
):
    """
    Create a new permission.
    Requires admin or superadmin role.
    """
    # Check if permission already exists
    perm_name = f"{perm_data.action}:{perm_data.resource}"
    existing = permission_service.get_permission_by_name(session, perm_name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Permission '{perm_name}' already exists"
        )

    permission = permission_service.create_permission(session, perm_data)
    return PermissionRead.model_validate(permission)


@router.get("/permissions", response_model=List[PermissionRead])
async def get_all_permissions(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_permission("read", "permissions"))
):
    """
    Get all permissions.
    Requires read:permissions permission.
    """
    permissions = permission_service.get_all_permissions(session, skip, limit)
    return [PermissionRead.model_validate(perm) for perm in permissions]


@router.delete("/permissions/{perm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    perm_id: int,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_admin)
):
    """
    Delete permission.
    Requires admin or superadmin role.
    """
    success = permission_service.delete_permission(session, perm_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )


# ==================== ROLE-PERMISSION ASSIGNMENT ====================

@router.post("/{role_id}/permissions", status_code=status.HTTP_200_OK)
async def assign_permissions_to_role(
    role_id: int,
    request: AssignPermissionsRequest,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_admin)
):
    """
    Assign permissions to a role.
    Requires admin or superadmin role.
    """
    success = role_service.assign_permissions_to_role(
        session,
        role_id,
        request.permission_ids
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    return {"message": "Permissions assigned successfully"}


# ==================== USER-ROLE ASSIGNMENT ====================

@router.post("/assign-to-user", status_code=status.HTTP_200_OK)
async def assign_role_to_user(
    request: AssignRoleRequest,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_permission("manage", "users"))
):
    """
    Assign a role to a user.
    Requires manage:users permission.
    """
    success = role_service.assign_role_to_user(
        session,
        request.user_id,
        request.role_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User or role not found"
        )

    return {"message": "Role assigned to user successfully"}


@router.delete("/remove-from-user", status_code=status.HTTP_200_OK)
async def remove_role_from_user(
    request: AssignRoleRequest,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_permission("manage", "users"))
):
    """
    Remove a role from a user.
    Requires manage:users permission.
    """
    success = role_service.remove_role_from_user(
        session,
        request.user_id,
        request.role_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    return {"message": "Role removed from user successfully"}


# ==================== USER INFO ====================

@router.get("/users/{user_id}/roles", response_model=List[RoleRead])
async def get_user_roles(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_permission("read", "users"))
):
    """
    Get all roles for a user.
    Requires read:users permission.
    """
    roles = role_service.get_user_roles(session, user_id)
    return [RoleRead.model_validate(role) for role in roles]


@router.get("/users/{user_id}/permissions", response_model=List[PermissionRead])
async def get_user_permissions(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: UserRead = Depends(require_permission("read", "users"))
):
    """
    Get all permissions for a user (through their roles).
    Requires read:users permission.
    """
    permissions = role_service.get_user_permissions(session, user_id)
    return [PermissionRead.model_validate(perm) for perm in permissions]
