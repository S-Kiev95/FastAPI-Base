"""
Seed data for default roles and permissions.
Run this script to initialize the database with default RBAC configuration.
"""
from datetime import datetime
from sqlmodel import Session, select

from app.database import engine
from app.models.role import (
    Role, Permission, RolePermission,
    DefaultRole, PermissionAction, PermissionResource
)


def seed_permissions(session: Session) -> dict[str, Permission]:
    """
    Create default permissions.
    Returns a dict mapping permission names to Permission objects.
    """
    permissions_data = [
        # User permissions
        ("create:users", "create", "users", "Create new users"),
        ("read:users", "read", "users", "View user information"),
        ("update:users", "update", "users", "Update user information"),
        ("delete:users", "delete", "users", "Delete users"),
        ("manage:users", "manage", "users", "Full user management"),

        # Role permissions
        ("create:roles", "create", "roles", "Create new roles"),
        ("read:roles", "read", "roles", "View roles"),
        ("update:roles", "update", "roles", "Update roles"),
        ("delete:roles", "delete", "roles", "Delete roles"),
        ("manage:roles", "manage", "roles", "Full role management"),

        # Permission permissions
        ("create:permissions", "create", "permissions", "Create new permissions"),
        ("read:permissions", "read", "permissions", "View permissions"),
        ("update:permissions", "update", "permissions", "Update permissions"),
        ("delete:permissions", "delete", "permissions", "Delete permissions"),
        ("manage:permissions", "manage", "permissions", "Full permission management"),

        # Media permissions
        ("create:media", "create", "media", "Upload media files"),
        ("read:media", "read", "media", "View media files"),
        ("update:media", "update", "media", "Update media information"),
        ("delete:media", "delete", "media", "Delete media files"),
        ("manage:media", "manage", "media", "Full media management"),

        # Superadmin permission
        ("manage:all", "manage", "all", "Full system access (superadmin)"),
    ]

    permissions_map = {}

    for name, action, resource, description in permissions_data:
        # Check if permission already exists
        stmt = select(Permission).where(Permission.name == name)
        existing = session.exec(stmt).first()

        if existing:
            permissions_map[name] = existing
            print(f"  [OK] Permission already exists: {name}")
        else:
            permission = Permission(
                name=name,
                action=action,
                resource=resource,
                description=description,
                created_at=datetime.utcnow()
            )
            session.add(permission)
            session.flush()  # Get the ID
            permissions_map[name] = permission
            print(f"  + Created permission: {name}")

    return permissions_map


def seed_roles(session: Session, permissions_map: dict[str, Permission]) -> dict[str, Role]:
    """
    Create default roles and assign permissions.
    Returns a dict mapping role names to Role objects.
    """
    roles_data = [
        (
            DefaultRole.SUPERADMIN,
            "Super Administrator",
            "Full system access with all permissions",
            ["manage:all"]
        ),
        (
            DefaultRole.ADMIN,
            "Administrator",
            "Administrative access to manage users, roles, and content",
            [
                "manage:users", "manage:roles", "manage:permissions",
                "manage:media"
            ]
        ),
        (
            DefaultRole.MODERATOR,
            "Moderator",
            "Can manage content and view users",
            [
                "read:users", "update:users",
                "manage:media",
                "read:roles"
            ]
        ),
        (
            DefaultRole.USER,
            "User",
            "Standard user with basic access",
            [
                "read:users",  # Can view their own profile
                "create:media", "read:media", "update:media", "delete:media"  # Own media only
            ]
        ),
        (
            DefaultRole.GUEST,
            "Guest",
            "Limited read-only access",
            [
                "read:media"  # Public media only
            ]
        ),
    ]

    roles_map = {}

    for role_name, display_name, description, permission_names in roles_data:
        # Check if role already exists
        stmt = select(Role).where(Role.name == role_name)
        existing_role = session.exec(stmt).first()

        if existing_role:
            role = existing_role
            roles_map[role_name] = role
            print(f"  [OK] Role already exists: {role_name}")
        else:
            role = Role(
                name=role_name,
                display_name=display_name,
                description=description,
                is_system=True,  # System roles cannot be deleted
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(role)
            session.flush()  # Get the ID
            roles_map[role_name] = role
            print(f"  + Created role: {role_name}")

        # Assign permissions to role
        for perm_name in permission_names:
            if perm_name not in permissions_map:
                print(f"  [WARNING] Permission '{perm_name}' not found for role '{role_name}'")
                continue

            permission = permissions_map[perm_name]

            # Check if role-permission assignment already exists
            stmt = select(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id
            )
            existing_assignment = session.exec(stmt).first()

            if not existing_assignment:
                role_perm = RolePermission(
                    role_id=role.id,
                    permission_id=permission.id
                )
                session.add(role_perm)
                print(f"    > Assigned permission: {perm_name}")

    return roles_map


def seed_rbac():
    """
    Main function to seed roles and permissions.
    Safe to run multiple times (idempotent).
    """
    print("\n" + "="*60)
    print("SEEDING RBAC DATA (Roles & Permissions)")
    print("="*60 + "\n")

    with Session(engine) as session:
        print("Creating permissions...")
        permissions_map = seed_permissions(session)

        print("\nCreating roles and assigning permissions...")
        roles_map = seed_roles(session, permissions_map)

        session.commit()

        print("\n" + "="*60)
        print(f"[SUCCESS] Seeding complete!")
        print(f"  - {len(permissions_map)} permissions")
        print(f"  - {len(roles_map)} roles")
        print("="*60 + "\n")


if __name__ == "__main__":
    seed_rbac()
