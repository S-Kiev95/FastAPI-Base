# Dashboard — Page Override

> Overrides MASTER.md for `/admin` dashboard page

## Layout Override

- **Grid**: 4 KPI cards top row (1 column on mobile, 2 on tablet, 4 on desktop)
- **Charts section**: 2-column grid below KPIs (stack on mobile)
- **Activity feed**: Right sidebar on xl+, below charts on smaller screens
- `content-priority`: KPIs first, then charts, then activity feed

## KPI Cards

| Metric | Icon | Format |
|--------|------|--------|
| Total Organizations | building-2 | Number |
| Active Users | users | Number |
| MRR (Monthly Recurring Revenue) | dollar-sign | Currency ($X,XXX) |
| Active Subscriptions | credit-card | Number + % change |

- Each card shows: value, label, trend indicator (arrow up/down + %)
- `number-tabular`: Use tabular figures for KPI values
- Background: `--color-surface`, left accent border (4px) using semantic color

## Charts

| Chart | Type | Data |
|-------|------|------|
| Revenue (30d) | Line | Daily MRR from payments |
| Plan distribution | Donut | Count per plan tier (4 segments max, `no-pie-overuse`) |
| New orgs (30d) | Bar | Weekly new organization signups |

- `responsive-chart`: On mobile, show only Revenue chart; others collapse to summary numbers
- `legend-visible`: Inline legend, not detached
- `gridline-subtle`: Use `--color-border` at 50% opacity

## Activity Feed

- Last 10 events (new org, plan change, payment, user registration)
- Each item: icon + description + relative timestamp ("hace 2h")
- `virtualize-lists`: Not needed (max 10 items)
- Empty state: "No hay actividad reciente"
