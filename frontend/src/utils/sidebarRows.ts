import {
	hasBuiltInRow,
	isGuestAccessRevoked,
	isLinkEnabled,
	LOCKED_VISIBLE,
	type SidebarVisibility,
} from '@/utils/mobileNav'
import type {
	SidebarLink,
	SidebarRenderLink,
	SidebarRenderRow,
	SidebarRow,
} from '@/types/sidebar'

// The sidebar's render list, in one place, because it has to be built the same
// way whether the site has rows or not. Two render paths in the component would
// drift.

// `LOCKED_VISIBLE` lives in mobileNav.ts, because `isLinkEnabled` needs it too.
// Re-exported so importers of this module keep resolving it from this path.
export { LOCKED_VISIBLE }

/** The id convention the seven legacy Check fields already used, and the one
 * every built-in row's `name1` follows. */
export const sidebarKey = (label: string): string =>
	label.toLowerCase().split(' ').join('_')

interface SidebarGroup {
	items?: SidebarLink[]
}

const flatten = (links: SidebarGroup[]): SidebarLink[] =>
	(links ?? []).flatMap((group) => group.items ?? [])

// getSidebarItems() ships its built-ins in groups. The groups carry
// `hideLabel`, so they were never headings; they are the gaps the sidebar draws
// between the three.
const groupIndexes = (links: SidebarGroup[]): Map<string, number> => {
	const groups = new Map<string, number>()
	;(links ?? []).forEach((group, index) => {
		for (const item of group.items ?? [])
			groups.set(sidebarKey(item.label), index)
	})
	return groups
}

// A spacer wherever two consecutive built-in links come from different groups.
// Space, not a rule, and it is only ever inserted between two links, so it is
// never leading, trailing or doubled.
const withGroupGaps = (
	rows: SidebarRenderRow[],
	groups: Map<string, number>
): SidebarRenderRow[] => {
	const out: SidebarRenderRow[] = []
	let previous: number | undefined
	for (const row of rows) {
		if (row.kind !== 'link') {
			// The More group is a break in the built-in run all on its own.
			previous = undefined
			out.push(row)
			continue
		}
		const group = groups.get(sidebarKey(row.link.label))
		if (group !== undefined) {
			if (previous !== undefined && group !== previous)
				out.push({ kind: 'gap', key: `group-gap-${out.length}` })
			previous = group
		}
		out.push(row)
	}
	return out
}

const sidebarRowsIn = (visibility?: SidebarVisibility): SidebarRow[] => {
	if (!visibility || isGuestAccessRevoked(visibility)) return []
	const rows = (visibility as Record<string, unknown>).sidebar_rows
	return Array.isArray(rows) ? (rows as SidebarRow[]) : []
}

const isVisible = (row: SidebarRow): boolean =>
	LOCKED_VISIBLE.has(row.name1) || !row.hidden

// The web pages have always been drawn inside one collapsible "More" group
// rather than inline. The key is the group's own, not a row's, because rows come
// and go and the disclosure has to keep its open or closed state.
export const WEB_PAGE_GROUP_KEY = 'web_pages'
export const WEB_PAGE_GROUP_LABEL = 'More'

const renderLink = (row: SidebarRow): SidebarRenderLink => ({
	kind: 'link',
	key: row.name,
	link: {
		label: row.label ?? row.name1,
		// `||`, not `??`: a row stored before the server-side icon check renders
		// an empty string, and `icons['']` is undefined.
		icon: row.icon || 'Link',
		to: row.to ?? undefined,
		open_in_new_window: row.open_in_new_window,
	},
})

// Every non-built-in row, a web page or a link a moderator added, folds into
// the one "More" group, drawn where the first of them fell. Nothing outside the
// built-ins ever renders inline.
const foldMore = (
	rendered: SidebarRenderRow[],
	items: SidebarRenderLink[],
	at: number
): SidebarRenderRow[] => {
	if (!items.length) return rendered
	rendered.splice(at, 0, {
		kind: 'accordion',
		key: WEB_PAGE_GROUP_KEY,
		label: WEB_PAGE_GROUP_LABEL,
		items,
	})
	return rendered
}

/**
 * The list the sidebar draws. `links` has already had each item's `condition()`
 * applied, so a built-in row whose entry is absent is one this viewer cannot
 * have. A row is a second gate, never a way to switch a link back on.
 */
export function buildSidebarRows(
	links: SidebarGroup[],
	visibility?: SidebarVisibility
): SidebarRenderRow[] {
	const items = flatten(links)
	const groups = groupIndexes(links)

	// Built-ins render in getSidebarItems() order, always. A row decides whether
	// one shows, never where it sits, which is what keeps the sidebar looking as
	// it did before rows existed.
	const builtins: SidebarRenderRow[] = items
		.filter((item) => isLinkEnabled(item.label, visibility))
		.map((item) => ({
			kind: 'link' as const,
			key: sidebarKey(item.label),
			link: item,
		}))

	// Every non-built-in row folds into the one "More" group at the end, in the
	// order the rows carry, exactly as the web pages always have.
	const more = sidebarRowsIn(visibility)
		.filter((row) => row.item_type !== 'Built-in' && isVisible(row))
		.map(renderLink)

	return withGroupGaps(foldMore(builtins, more, builtins.length), groups)
}
