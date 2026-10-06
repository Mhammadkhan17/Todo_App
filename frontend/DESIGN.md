# TodoFlow Design System

Source of truth for the TodoFlow UI. Code (`src/app/globals.css` `@theme` + component classes) is the code-level mirror; if they disagree, this file wins — regenerate code from it.

## Overview

TodoFlow is a task-execution dashboard with a **Luxury/terminal identity**: hairline borders, monospace micro-labels, a single confident emerald accent, and near-sharp 4px radii. It reads like a precision instrument, not a consumer app.

**Key characteristics:**
- One brand hue — emerald `#059669` (emerald-600) — reserved for CTAs, active states, focus rings, status dots, and key accents; never smeared across large backgrounds.
- Terminal micro-typography: 10–11px uppercase monospace labels with wide tracking (`IDENTITY_USER`, `// Execution Mode`) carry the personality.
- Radius discipline: 4px everywhere (`radius-sm` 2px only for tiny badges, `radius-xl` 6px rare). No pill shapes, no `rounded-2xl`.
- Shadows are for floating layers only (widget, dropdowns); static cards use border + luminance.
- Dark mode is a designed surface ladder (stone-black stack), not an inversion. Auth pages are intentionally always-dark; everything else follows the theme.

## Colors

Values are defined in `globals.css` (`:root` / `.dark`) and exposed via `@theme`.

### Brand & Accent
| Token | Light | Dark | Use |
|---|---|---|---|
| `{colors.brand}` (`--primary`) | `#059669` | `#059669` | Primary buttons, active nav, focus rings, emerald accents |
| `{colors.brand-foreground}` | `#0a0a0a` | `#0a0a0a` | Text/icon on solid emerald fills (5.25:1 — do not use white on emerald for normal-size text) |
| `{colors.brand-tint}` | `bg-emerald-50` | `bg-emerald-500/10` | Tinted brand surfaces (user bubbles, active nav wash) |
| `{colors.brand-text}` | `#047857` (emerald-700) | `#34d399` (emerald-400) | Emerald text on neutral surfaces (labels, links, strong) |

### Surface
| Token | Light | Dark | Use |
|---|---|---|---|
| `{colors.background}` | `#fafaf9` (stone-50) | `#0a0a0a` | Page canvas |
| `{colors.surface}` (card/panel) | `#ffffff` | `#0f0f0f` | Cards, sidebar, chat shell, widget shell |
| `{colors.surface-inset}` | `#fafaf9` | `#0a0a0a` | Recessed regions inside a card (message log, widget log) |
| `{colors.surface-interactive}` | `#f5f5f4` (stone-100) | `#141414` | Inputs, code blocks, user bubbles (dark), headers of panels |
| `{colors.surface-active}` | `#e7e5e4` (stone-200) | `#1a1a1a` | Hover/pressed fills, skeletons |

### Borders
| Token | Light | Dark | Use |
|---|---|---|---|
| `{colors.border-subtle}` (`--border`) | `#e7e5e4` (stone-200) | `#1c1917` (stone-800) | Default hairline: card outlines, dividers, inputs |
| `{colors.border-strong}` | `#a8a29e` (stone-400) | `#44403c` (stone-700) | Emphasized outlines only (rare) |

### Text (3+ levels, all ≥4.5:1 on their surfaces)
| Token | Light | Dark | Use |
|---|---|---|---|
| `{colors.text-primary}` | `#0c0a09` (stone-950) | `#fafaf9` | Headings, body |
| `{colors.text-secondary}` | `#57534e` (stone-600) | `#d6d3d1` (stone-300) | Supporting copy, role labels |
| `{colors.text-muted}` | `#78716c` (stone-500) | `#a8a29e` (stone-400) | Micro-labels, timestamps, placeholders |
| `{colors.text-inverse}` | `#0a0a0a` | `#ffffff` | Text on emerald fills / on emerald logo boxes |

### Semantic
| Token | Value | Use |
|---|---|---|
| `{colors.danger}` | `#ef4444` | Errors, destructive actions (light text: `text-red-600` on light, `text-red-400` on dark) |

## Typography

- **Sans:** Inter (`--font-inter`) → ui-sans-serif fallback. Body 15px / 1.6.
- **Mono:** Geist Mono (`--font-geist-mono`) → ui-monospace fallback. Carries the terminal identity.

| Token | Size | Weight | Tracking | Use |
|---|---|---|---|---|
| `{type.display}` | 3xl (30px) | 700 | tight, uppercase | Page titles (`KNOWLEDGE ASSISTANT`) |
| `{type.heading}` | lg–xl | 600–700 | tight | Card/section titles |
| `{type.body}` | 15px | 400 | normal | Body copy, chat messages (markdown) |
| `{type.micro}` | 11px | 700 | `tracking-widest`, uppercase, mono | Section eyebrows, nav group labels |
| `{type.mono-label}` | 10px | 500–700 | `tracking-widest`, uppercase, mono | Role labels, timestamps, status, placeholders |
| `{type.button}` | 14px | 500–700 | normal | Button labels (mono uppercase for terminal CTAs) |

**Principles:** hierarchy comes from weight + tracking + case, not size inflation; micro text never below 10px; body line-height ≥ 1.6; markdown body 14px / 1.65.

## Layout

- Shell: fixed sidebar 256px (`lg:` breakpoint) + sticky 64px header + padded main (`p-6` / `lg:p-10`) + footer.
- Spacing rhythm: 4px base; component internals use 8/12/16px; section gaps 24px (`gap-6`).
- Full-height chat pages: shell height `calc(100dvh - 11rem)` mobile, `- 13rem` on `lg` (header + footer + main padding), `min-height: 24rem`.
- Whitespace: dashboard content breathes; chat/log surfaces are dense (terminals are dense).

## Elevation & Depth

| Level | Treatment | Use |
|---|---|---|
| Flat + hairline | `{colors.border-subtle}`, no shadow | All static cards, panels, chat shell |
| Floating | `0 20px 50px rgba(0,0,0,0.12)` light / `0 20px 60px rgba(0,0,0,0.6)` dark | CompactChatWidget shell |
| Brand glow | `0 0 30px rgba(16,185,129,0.3)` | Emerald FAB (chat launcher) only |

## Shapes

| Token | Value | Use |
|---|---|---|
| `{radius.sm}` | 2px | Tiny badges, status pip containers |
| `{radius.md}` / `{radius.lg}` | 4px | Everything: buttons, inputs, cards, bubbles, panels |
| `{radius.xl}` | 6px | Rare large wrappers |
| `{radius.full}` | 9999px | Dots/pills only (status pips) |

Rule: no in-between values (no 8/12px). If a component needs softness, it gets 4px.

## Components

### Buttons
- **`button-primary`**: `{colors.brand}` bg, `{colors.brand-foreground}` text, `{radius.md}`, min-h 44px for icon/text CTAs. Disabled: `bg-stone-200 text-stone-400` / `dark:bg-stone-900 dark:text-stone-700`.
- **`button-ghost-icon`**: transparent, `{colors.text-muted}` → hover `{colors.text-primary}`, min 44×44 hit area (header/sidebar controls).
- Focus: 2px `{colors.brand}` outline, offset 2px (global `*:focus-visible`).

### Inputs
- **`input-terminal`**: `{colors.surface-interactive}` bg, `{colors.border-subtle}` border, `{radius.md}`, min-h 44px, focus `border-emerald-600/60` + global ring. Placeholder: mono, 10px, uppercase, `tracking-widest`, `{colors.text-muted}`.

### Chat & Assistant (see entries added 2026-10-06)
- **`chat-shell`**: `{colors.surface}` card, `{colors.border-subtle}`, `{radius.md}`, flex column, full height; thin header bar (`{colors.surface-inset}`-ish via `bg-white dark:bg-[#141414]`… use `{colors.surface}` + border) with mono title `// KNOWLEDGE_ASSISTANT`, emerald status pip, `[DOCS]` toggle.
- **`message-log`**: recessed `{colors.surface-inset}` region, custom scrollbar, `role="log" aria-live="polite"`.
- **`message-row`**: mono role label `{type.mono-label}` `{colors.text-secondary}` + timestamp `{colors.text-muted}`; label variants `IDENTITY_USER` / `CORE_ASSISTANT`.
- **`message-bubble-user`**: `{colors.brand-tint}` bg, emerald border with `border-l-2 border-l-emerald-600`, `{radius.md}`, `{colors.text-primary}` (dark: stone-100), max-w 85%, right-aligned.
- **`message-bubble-assistant`**: `{colors.surface}` (light) / `#141414` (dark) bg, `{colors.border-subtle}`, `{radius.md}`, `{colors.text-secondary}`-to-primary body, max-w 85%, left-aligned. No shadow (in-flow).
- **`source-ref`**: inside assistant bubble, top hairline divider; mono uppercase emerald header `SOURCES [n]`; each source `{colors.surface-inset}` box, `{colors.border-subtle}`, `{radius.md}`, 12px text, line-clamped excerpt, mono file name in `{colors.brand-text}`.
- **`chat-composer`**: bottom bar, top hairline; terminal input (see `input-terminal`) + `button-primary` send (44px square, emerald, `text-[#0a0a0a]` icon).
- **`chat-empty-state`**: centered emerald-tinted icon box (48px, `{radius.md}`) + mono `AWAITING_INPUT` `{type.micro}` + muted mono sub-line.
- **`chat-loading`**: mono `PROCESSING...` label in `{colors.brand-text}` + emerald spinner + inset box.
- **`docs-panel`**: right panel 340px (`lg:` static, expands chat shell; below `lg` it overlays from the right with backdrop); `{colors.surface}`, left hairline, contains `DocumentUploader` + compact how-it-works list.
- **`compact-chat-widget`**: floating 320px / 450px expanded; shell = `chat-shell` + Floating elevation; log = `message-log`; bubbles = same pairs as page chat; terminal labels preserved in both themes. Collapsed launcher: `button-primary` square with brand glow.
- **`markdown-content`**: shared markdown typography (defined in `globals.css`) used by page chat and widget: neutral body, emerald `strong`/links, mono code on `{colors.surface-interactive}`, hairline tables.

### Navigation
- **`nav-item`**: `{radius.md}`, 4px emerald indicator bar when active, `{brand-tint}` wash + emerald icon/text; inactive `{colors.text-muted}` → hover `{colors.text-primary}` on `stone-100`/`dark:#1c1917`.

## Do's and Don'ts

- DO keep all radii at 2/4/6px; DON'T introduce 8px+ or pill buttons.
- DO put text on emerald fills as `#0a0a0a`; DON'T use white on emerald for body-size text.
- DO use mono uppercase micro-labels for roles/status/meta; DON'T use emoji as icons (lucide/heroicons only).
- DO reserve shadows for floating layers; DON'T shadow static cards.
- DO keep hue budget: stone ramp + emerald + red (danger) only; DON'T add a third accent hue.
- DO ensure every text level hits ≥4.5:1 in BOTH themes; when in doubt, bump a step (stone-500 → stone-600).

## Responsive Behavior

| Breakpoint | Width | Changes |
|---|---|---|
| (mobile) | <1024px | Sidebar → overlay drawer; chat docs panel → right overlay with backdrop; header keeps menu button |
| `lg` | ≥1024px | Persistent sidebar; docs panel static right column; `[DOCS]` collapses it |

Touch targets: min 44×44 (`min-h-11 min-w-11`) for all icon buttons and the composer send button.

## Iteration Guide

1. Reference tokens by the names above; the code mirror lives in `globals.css`.
2. New component states get their own entries (`button-primary-disabled`), not edits to base descriptions.
3. Hard checks before adding anything: hue budget (stone + emerald + red), 4.5:1 contrast in both themes, radius ∈ {2,4,6}, shadows floating-only.
4. Terminal micro-labels are the identity — new UI surfaces get a mono label, not a bigger heading.

## Known Gaps

- `AppButton` uses white text on emerald-600 (~3.8:1) — passes only for large/bold labels; new solid-emerald controls must use `{colors.brand-foreground}` (#0a0a0a). Migration of existing buttons pending.
- No `warning`/`info` semantic tokens yet (unused in UI; add via §Colors when needed).
- `@tailwindcss/typography` is NOT installed — `prose*` classes are dead; use `markdown-content` instead.
- Auth pages are always-dark by design (not theme-following); documented exception, not a gap.
