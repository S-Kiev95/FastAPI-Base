# Subscriptions — Page Override

> Overrides MASTER.md for `/admin/subscriptions` page

## Layout

- **Summary cards**: 4 cards showing count by status (active, trialing, past_due, cancelled)
- **Table**: Below cards, full width, paginated

## Table Columns

| Column | Type | Sortable |
|--------|------|----------|
| Organización | link to org detail | yes |
| Plan | badge (colored by tier) | yes |
| Estado | status badge (icon + text) | yes |
| Pasarela | text (Stripe/MercadoPago/Polar/None) | yes |
| Período actual | date range | yes |
| Creada | relative date | yes |

## Status Badges (override from MASTER)

- Active: green badge, check-circle icon
- Trialing: blue badge, clock icon
- Past Due: amber badge, alert-triangle icon — **row highlight** with subtle amber background
- Cancelled: red badge, x-circle icon — text-secondary styling

## Actions

- Quick plan change (dropdown on row)
- Cancel subscription (with `confirmation-dialogs`)
- View payment history (link)
- `destructive-emphasis`: Cancel is visually separated, uses danger variant
