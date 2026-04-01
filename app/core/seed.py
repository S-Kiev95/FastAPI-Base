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
from app.models.organization import Organization, Membership, MembershipRole
from app.models.user import User
from app.core.security import get_password_hash
from app.config import settings


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


def seed_system_organization(session: Session) -> None:
    """
    Crea la organización sistema para datos compartidos (ej: aseguradoras).
    También crea el superadmin si SYSTEM_ADMIN_EMAIL está configurado.
    Idempotente: seguro de ejecutar múltiples veces.
    """
    slug = settings.SYSTEM_ORG_SLUG

    # Verificar si ya existe
    stmt = select(Organization).where(Organization.slug == slug)
    existing = session.exec(stmt).first()

    if existing:
        print(f"  [OK] System organization already exists: {slug}")
        system_org = existing
    else:
        system_org = Organization(
            name="Sistema",
            slug=slug,
            plan="system",
            is_system=True,
            is_active=True,
        )
        session.add(system_org)
        session.flush()
        print(f"  + Created system organization: {slug}")

    # Crear superadmin si está configurado
    admin_email = settings.SYSTEM_ADMIN_EMAIL
    admin_password = settings.SYSTEM_ADMIN_PASSWORD

    if admin_email and admin_password:
        stmt = select(User).where(User.email == admin_email)
        existing_user = session.exec(stmt).first()

        if existing_user:
            print(f"  [OK] System admin already exists: {admin_email}")
            admin_user = existing_user
        else:
            admin_user = User(
                email=admin_email,
                name="System Admin",
                provider="local",
                hashed_password=get_password_hash(admin_password),
                is_active=True,
                is_verified=True,
                is_superadmin=True,
            )
            session.add(admin_user)
            session.flush()
            print(f"  + Created system admin: {admin_email}")

        # Crear membership owner en la org sistema
        stmt = select(Membership).where(
            Membership.user_id == admin_user.id,
            Membership.organization_id == system_org.id,
        )
        existing_membership = session.exec(stmt).first()

        if not existing_membership:
            membership = Membership(
                user_id=admin_user.id,
                organization_id=system_org.id,
                role=MembershipRole.owner,
            )
            session.add(membership)
            print(f"  + Assigned admin as owner of system org")


def seed_all():
    """
    Seed completo: RBAC + organización sistema.
    Seguro de ejecutar múltiples veces (idempotente).
    """
    print("\n" + "="*60)
    print("SEEDING DATA")
    print("="*60 + "\n")

    with Session(engine) as session:
        print("Creating permissions...")
        permissions_map = seed_permissions(session)

        print("\nCreating roles and assigning permissions...")
        roles_map = seed_roles(session, permissions_map)

        print("\nCreating system organization...")
        seed_system_organization(session)

        session.commit()

        print("\n" + "="*60)
        print("[SUCCESS] Seeding complete!")
        print("="*60 + "\n")


if __name__ == "__main__":
    seed_all()
