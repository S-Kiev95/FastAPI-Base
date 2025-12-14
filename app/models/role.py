"""
Role and Permission models for RBAC (Role-Based Access Control).
Supports flexible role management with custom permissions.
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum


# Junction tables for many-to-many relationships
class UserRole(SQLModel, table=True):
    """Junction table for User-Role many-to-many relationship"""
    __tablename__ = "user_roles"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    role_id: int = Field(foreign_key="roles.id", primary_key=True)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)


class RolePermission(SQLModel, table=True):
    """Junction table for Role-Permission many-to-many relationship"""
    __tablename__ = "role_permissions"

    role_id: int = Field(foreign_key="roles.id", primary_key=True)
    permission_id: int = Field(foreign_key="permissions.id", primary_key=True)


# Enums for default roles and permissions
class DefaultRole(str, Enum):
    """Default system roles"""
    SUPERADMIN = "superadmin"  # Full system access
    ADMIN = "admin"            # Administrative access
    MODERATOR = "moderator"    # Content moderation
    USER = "user"              # Regular user
    GUEST = "guest"            # Limited access


class PermissionAction(str, Enum):
    """CRUD actions for permissions"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"  # Full CRUD + special actions


class PermissionResource(str, Enum):
    """Resources that can be protected"""
    USERS = "users"
    ROLES = "roles"
    PERMISSIONS = "permissions"
    MEDIA = "media"
    ALL = "all"  # Superadmin permission


# Main models
class Role(SQLModel, table=True):
    """
    Role model for RBAC.
    Can be system-defined (superadmin, admin, etc.) or user-created.
    """
    __tablename__ = "roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)  # e.g., "admin", "editor", "viewer"
    display_name: str  # Human-readable name
    description: Optional[str] = None

    # System roles cannot be deleted or modified
    is_system: bool = Field(default=False)
    is_active: bool = Field(default=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships (defined with strings to avoid circular imports)
    # permissions: List["Permission"] = Relationship(back_populates="roles", link_model=RolePermission)


class Permission(SQLModel, table=True):
    """
    Permission model for granular access control.
    Format: {action}:{resource} (e.g., "create:users", "read:media")
    """
    __tablename__ = "permissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)  # e.g., "create:users", "read:media"
    action: str  # create, read, update, delete, manage
    resource: str  # users, roles, media, etc.
    description: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    # roles: List[Role] = Relationship(back_populates="permissions", link_model=RolePermission)


# Schemas for API

class RoleCreate(SQLModel):
    """Schema for creating a role"""
    name: str
    display_name: str
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = []


class RoleRead(SQLModel):
    """Schema for reading a role"""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    is_system: bool
    is_active: bool
    created_at: datetime


class RoleReadWithPermissions(RoleRead):
    """Schema for reading a role with its permissions"""
    permissions: List["PermissionRead"] = []


class RoleUpdate(SQLModel):
    """Schema for updating a role"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionCreate(SQLModel):
    """Schema for creating a permission"""
    action: str
    resource: str
    description: Optional[str] = None


class PermissionRead(SQLModel):
    """Schema for reading a permission"""
    id: int
    name: str
    action: str
    resource: str
    description: Optional[str]
    created_at: datetime


class PermissionUpdate(SQLModel):
    """Schema for updating a permission"""
    description: Optional[str] = None


class AssignRoleRequest(SQLModel):
    """Schema for assigning role to user"""
    user_id: int
    role_id: int


class AssignPermissionsRequest(SQLModel):
    """Schema for assigning permissions to role"""
    role_id: int
    permission_ids: List[int]
