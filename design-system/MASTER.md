# Design System — SaaS Admin Panel (Seguros BK)

> Generado con UI/UX Pro Max skill | Product: SaaS Admin Dashboard | Industry: Insurance/Fintech

---

## 1. Product Type & Style

| Attribute | Value | Reasoning |
|-----------|-------|-----------|
| **Product type** | SaaS Admin Dashboard (B2B) | Data-dense, multi-tenant management |
| **Primary style** | Minimalism + Flat Design | Insurance/fintech demands trust, clarity, and professionalism. Minimalism reduces cognitive load in data-heavy interfaces |
| **Secondary style** | Subtle Neumorphism (cards only) | Soft elevation for cards gives depth without distraction |
| **Density** | Comfortable (not compact) | Admins spend long sessions; avoid eye fatigue |
| **Mode** | Light (default) + Dark mode | `dark-mode-pairing`: design both together |
| **Icon set** | Lucide Icons (SVG, consistent 1.5px stroke) | `no-emoji-icons`, `icon-style-consistent`, `stroke-consistency` |

### Anti-patterns to avoid
- NO glassmorphism (blur = decorative in admin context, violates `blur-purpose`)
- NO brutalism (inappropriate for fintech trust)
- NO emoji as icons (`no-emoji-icons`)
- NO mixed icon styles (`filled-vs-outline-discipline`)

---

## 2. Color System

Based on fintech/insurance industry: trustworthy blues + neutral grays.

### Semantic Tokens (`color-semantic`)

| Token | Light Mode | Dark Mode | Usage |
|-------|-----------|-----------|-------|
| `--color-primary` | `#2563EB` (blue-600) | `#3B82F6` (blue-500) | Primary actions, active nav |
| `--color-primary-hover` | `#1D4ED8` (blue-700) | `#60A5FA` (blue-400) | Hover state |
| `--color-secondary` | `#64748B` (slate-500) | `#94A3B8` (slate-400) | Secondary text, labels |
| `--color-surface` | `#FFFFFF` | `#1E293B` (slate-800) | Cards, panels |
| `--color-surface-alt` | `#F8FAFC` (slate-50) | `#0F172A` (slate-900) | Page background |
| `--color-border` | `#E2E8F0` (slate-200) | `#334155` (slate-700) | Dividers, borders |
| `--color-text-primary` | `#0F172A` (slate-900) | `#F1F5F9` (slate-100) | Headings, body |
| `--color-text-secondary` | `#64748B` (slate-500) | `#94A3B8` (slate-400) | Descriptions, meta |
| `--color-success` | `#16A34A` (green-600) | `#4ADE80` (green-400) | Active, paid, healthy |
| `--color-warning` | `#D97706` (amber-600) | `#FBBF24` (amber-400) | Past due, attention |
| `--color-danger` | `#DC2626` (red-600) | `#F87171` (red-400) | Errors, cancel, delete |
| `--color-info` | `#0891B2` (cyan-600) | `#22D3EE` (cyan-400) | Info badges, tooltips |

### Contrast verification (`color-accessible-pairs`)
- Primary text on surface: >= 14:1 (light), >= 13:1 (dark) — WCAG AAA
- Secondary text on surface: >= 4.6:1 — WCAG AA
- All functional colors include icon + text, not color alone (`color-not-only`)

---

## 3. Typography

### Font Pairing

| Role | Font | Weight | Reasoning |
|------|------|--------|-----------|
| **Headings** | Inter | 600 (SemiBold) | Professional, highly legible, variable font. Excellent for data-dense UIs |
| **Body** | Inter | 400 (Regular) | Same family for consistency; great readability at small sizes |
| **Monospace** | JetBrains Mono | 400 | For IDs, codes, technical data |

### Type Scale (`font-scale`)

| Level | Size | Line Height | Usage |
|-------|------|-------------|-------|
| `display` | 30px | 1.2 | Page titles (Organizations, Users) |
| `heading-1` | 24px | 1.3 | Section headers |
| `heading-2` | 20px | 1.4 | Card headers |
| `heading-3` | 16px | 1.5 | Subsection headers |
| `body` | 14px | 1.6 | Default text |
| `body-sm` | 13px | 1.5 | Table cells, secondary info |
| `caption` | 12px | 1.4 | Labels, badges, meta |
| `mono` | 13px | 1.5 | UUIDs, slugs, IDs |

> `readable-font-size`: Minimum 14px body, `line-height` 1.5+

---

## 4. Spacing System (`spacing-scale`)

Base unit: **4px**. All spacing uses multiples of 4.

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Icon-text gap, tight padding |
| `--space-2` | 8px | Input padding, badge padding |
| `--space-3` | 12px | List item padding |
| `--space-4` | 16px | Card padding, section gap |
| `--space-5` | 20px | Group separator |
| `--space-6` | 24px | Card internal sections |
| `--space-8` | 32px | Page section gap |
| `--space-10` | 40px | Major section separator |
| `--space-12` | 48px | Page top/bottom padding |

---

## 5. Layout

### Navigation (`adaptive-navigation`, `nav-hierarchy`)
- **Desktop (>=1024px)**: Fixed sidebar (240px) + top bar
- **Tablet (768-1023px)**: Collapsible sidebar (icon-only 64px)
- **Mobile (<768px)**: Hidden sidebar with hamburger toggle

### Breakpoints (`breakpoint-consistency`)
| Name | Width | Behavior |
|------|-------|----------|
| `sm` | 640px | Stack cards vertically |
| `md` | 768px | 2-column grids, collapse sidebar |
| `lg` | 1024px | Full sidebar, 3-column grids |
| `xl` | 1280px | Max content width |
| `2xl` | 1440px | Center content, max-w-7xl |

### Content Area
- Max content width: `max-w-7xl` (1280px) centered
- Page padding: 24px (desktop), 16px (mobile)
- Card grid gap: 16px (desktop), 12px (mobile)

### Z-index Scale (`z-index-management`)
| Layer | Value |
|-------|-------|
| Base content | 0 |
| Sticky header | 10 |
| Sidebar | 20 |
| Dropdown/Popover | 30 |
| Modal backdrop | 40 |
| Modal content | 50 |
| Toast | 100 |

---

## 6. Components

### Cards
- Background: `--color-surface`
- Border: 1px solid `--color-border`
- Border radius: 8px
- Shadow: `0 1px 3px rgba(0,0,0,0.08)` (light), none (dark)
- Padding: `--space-6` (24px)

### Buttons

| Variant | Background | Text | Border |
|---------|-----------|------|--------|
| Primary | `--color-primary` | white | none |
| Secondary | transparent | `--color-primary` | 1px `--color-primary` |
| Danger | `--color-danger` | white | none |
| Ghost | transparent | `--color-text-secondary` | none |

- Height: 36px (default), 32px (compact/table)
- Border radius: 6px
- Transition: 150ms ease-out (`duration-timing`)
- `loading-buttons`: spinner + disabled during async

### Tables (`sortable-table`, `virtualize-lists`)
- Header: `--color-surface-alt`, font-weight 500, uppercase caption size
- Rows: alternating subtle stripe (`surface` / `surface-alt`)
- Hover: subtle highlight
- Pagination: bottom, 10/25/50 per page
- IDs shown in `mono` font
- Status columns: colored badge (icon + text, `color-not-only`)

### Forms (`input-labels`, `error-placement`, `inline-validation`)
- Labels: above field, font-weight 500, `body-sm` size
- Input height: 36px
- Border: 1px `--color-border`, focus: 2px `--color-primary`
- Error: red border + error icon + message below field
- Required: asterisk after label
- Validate on blur (`inline-validation`)

### Badges / Status
| Status | Color | Icon |
|--------|-------|------|
| Active | green | check-circle |
| Trialing | blue | clock |
| Past due | amber | alert-triangle |
| Cancelled | red | x-circle |
| Pending | gray | loader |

### Toast (`toast-dismiss`, `toast-accessibility`)
- Position: top-right
- Auto-dismiss: 4s
- aria-live="polite"
- Variants: success (green), error (red), warning (amber), info (blue)

---

## 7. Animation (`duration-timing`, `easing`)

| Type | Duration | Easing |
|------|----------|--------|
| Button hover/press | 150ms | ease-out |
| Modal enter | 250ms | ease-out |
| Modal exit | 180ms | ease-in |
| Sidebar toggle | 200ms | ease-in-out |
| Toast enter | 300ms | ease-out |
| Toast exit | 200ms | ease-in |
| Page transition | 200ms | ease-out |

- `transform-performance`: Only animate transform + opacity
- `reduced-motion`: Respect `prefers-reduced-motion`
- `loading-states`: Skeleton shimmer for >300ms loads
- `exit-faster-than-enter`: Exit ~70% of enter duration

---

## 8. Accessibility Checklist (`color-contrast`, `focus-states`, `keyboard-nav`)

- [ ] All text meets WCAG AA (4.5:1 normal, 3:1 large)
- [ ] Focus rings: 2px `--color-primary` offset 2px
- [ ] Tab order matches visual order
- [ ] Skip-to-main-content link
- [ ] All icon buttons have aria-label
- [ ] Status conveyed by icon + text + color (not color alone)
- [ ] Forms: label + for attribute, error near field
- [ ] Modals: focus trap, Escape to close (`modal-escape`)
- [ ] Heading hierarchy: h1 > h2 > h3 sequential

---

## 9. Charts (Dashboard) (`chart-type`, `legend-visible`, `tooltip-on-interact`)

| Data | Chart type | Library |
|------|-----------|---------|
| Revenue over time | Line chart | Chart.js or Svelte chart |
| Plan distribution | Donut (max 4 segments) | Chart.js |
| Monthly payments | Bar chart | Chart.js |
| Usage vs limits | Progress bar (custom) | Native Svelte |

- Accessible colors (no red/green only pairs)
- Legend visible, not below fold
- Tooltips on hover with exact values
- Empty state: "No hay datos disponibles" + guidance
- `responsive-chart`: simplify on mobile

---

## 10. Admin Panel Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/admin` | KPIs, charts, recent activity |
| Organizations | `/admin/organizations` | List + CRUD de tenants |
| Users | `/admin/users` | Lista global de usuarios |
| Subscriptions | `/admin/subscriptions` | Estado de todas las suscripciones |
| Payments | `/admin/payments` | Historial global de pagos |
| Metrics | `/admin/metrics` | Métricas del sistema |
| Impersonate | `/admin/impersonate/{user}` | Login como cualquier usuario |
