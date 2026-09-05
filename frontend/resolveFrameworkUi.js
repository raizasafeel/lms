import { existsSync } from 'node:fs'
import path from 'node:path'

/**
 * Where `@framework/ui`'s source lives, relative to this frontend.
 *
 * This is for tailwind's `content` globs, and only those. App code imports the
 * package by name and resolves through its `exports` map like any other
 * dependency; tailwind cannot, because `content` takes file globs rather than
 * module specifiers, so it is the one consumer that still needs a path.
 *
 * In a normal checkout that is `apps/frappe/ui/src`, two levels up from here. A
 * git worktree of this app sits deeper (`apps/lms/.lms-worktrees/<name>/frontend`)
 * and would resolve two levels up to a directory that does not exist, so the
 * lookup walks up until it finds the package rather than counting on one depth.
 *
 * This used to prefer a named worktree of apps/frappe, because the component
 * Settings > Raven reaches for did not exist in the framework yet. It does now,
 * so the preference is gone and this is the plain lookup it was always meant to
 * reduce to. Do not put it back: the Frappe Cloud build broke on exactly that,
 * with the worktree suffix baked into the fallback so `apps/frappe/ui/src` was
 * never tried and rollup was handed a path nothing on that machine had created.
 *
 * Falls back to the canonical `apps/frappe/ui/src` when nothing is found, so a
 * checkout without the frappe app beside it fails with vite's own "does the file
 * exist?" rather than with an alias pointing at the wrong tree.
 */
export function resolveFrameworkUi(from) {
	const suffix = path.join('ui', 'src')
	let dir = from
	for (let up = 0; up < 6; up += 1) {
		const candidate = path.resolve(dir, '../frappe', suffix)
		if (existsSync(candidate)) return candidate
		const parent = path.dirname(dir)
		if (parent === dir) break
		dir = parent
	}
	return path.resolve(from, '../../frappe', suffix)
}
