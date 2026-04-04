# Organizations — Page Override

> Overrides MASTER.md for `/admin/organizations` page

## Layout

- **Top bar**: Page title + "Nueva Organización" button (primary)
- **Filters bar**: Search input + plan filter (select) + status filter (active/inactive)
- **Table**: Full width, paginated
- `progressive-disclosure`: Filters collapsed by default on mobile, expandable

## Table Columns

| Column | Type | Sortable | Notes |
|--------|------|----------|-------|
| Nombre | text + slug below (caption, mono) | yes | Primary column, clickable to detail |
| Plan | badge (colored by tier) | yes | free=gray, starter=blue, pro=purple, enterprise=amber |
| Miembros | number / max | no | "3/10" format, red if >= 90% |
| Estado | badge (Active/Inactive) | yes | green / gray |
| Creada | relative date | yes | "hace 3 días" with tooltip showing ISO date |
| Acciones | icon buttons | no | Edit (pencil), View (eye), Deactivate (ban) |

- `sortable-table`: aria-sort on active column
- `confirmation-dialogs`: Confirm before deactivate
- `empty-states`: "No hay organizaciones" + create button

## Detail View (modal or slide-over)

- Organization info (name, slug, plan, created, is_active)
- Members list (compact table)
- Subscription status
- Recent payments (last 5)
- Actions: Edit, Change Plan, Deactivate, Impersonate Owner
- `sheet-dismiss-confirm`: Confirm if unsaved changes on edit
