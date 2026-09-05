/**
 * Where tailwind's scan of `@framework/ui` points, per machine shape.
 *
 * Pinned because getting it wrong does not fail locally, it fails on a build
 * server, after a push, with a path that exists on nobody's disk. The Frappe
 * Cloud build broke exactly that way: the resolver preferred a local git
 * worktree of apps/frappe and built the same worktree suffix into its fallback,
 * so `apps/frappe/ui/src` was never tried and rollup was handed
 * `apps/frappe/.claude/worktrees/condition-builder-drag/ui/src`. The preference
 * is gone now that ConditionBuilder ships in the framework, and these cases are
 * what stop it coming back.
 *
 * Real directories rather than a mocked `node:fs`: the whole behaviour under
 * test is "which of these paths exists", so a mock would be asserting the
 * fixture rather than the resolver.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { mkdirSync, mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { resolveFrameworkUi } from '../../resolveFrameworkUi.js'

let bench: string

/** `apps/frappe/ui/src`, what a plain checkout of the framework has. */
function plainCheckout(): string {
	const dir = path.join(bench, 'apps', 'frappe', 'ui', 'src')
	mkdirSync(dir, { recursive: true })
	return dir
}

/** The frontend of the app doing the resolving, at one of two depths. */
function frontend(inWorktree: boolean): string {
	const dir = inWorktree
		? path.join(bench, 'apps', 'lms', '.lms-worktrees', 'feature', 'frontend')
		: path.join(bench, 'apps', 'lms', 'frontend')
	mkdirSync(dir, { recursive: true })
	return dir
}

beforeEach(() => {
	bench = mkdtempSync(path.join(tmpdir(), 'framework-ui-'))
})

afterEach(() => {
	rmSync(bench, { recursive: true, force: true })
})

describe('resolveFrameworkUi', () => {
	it('resolves the plain checkout', () => {
		const plain = plainCheckout()
		expect(resolveFrameworkUi(frontend(false))).toBe(plain)
	})

	it('finds it from a worktree of the app itself, which sits deeper', () => {
		// apps/lms/.lms-worktrees/<name>/frontend is two levels below the depth a
		// plain checkout has, which is why the lookup walks up instead of counting.
		const plain = plainCheckout()
		expect(resolveFrameworkUi(frontend(true))).toBe(plain)
	})

	it('ignores a worktree of the framework, however tempting', () => {
		// A .claude/worktrees copy of apps/frappe is a local artefact. Preferring it
		// is what handed the build server a path nothing there had ever created.
		mkdirSync(
			path.join(
				bench,
				'apps',
				'frappe',
				'.claude',
				'worktrees',
				'cb',
				'ui',
				'src'
			),
			{ recursive: true }
		)
		const plain = plainCheckout()
		const resolved = resolveFrameworkUi(frontend(false))
		expect(resolved).toBe(plain)
		expect(resolved).not.toContain('.claude')
	})

	it('returns the canonical location when nothing was found', () => {
		// With no frappe beside us the caller gets the canonical location, so a
		// glob that matches nothing names a path someone could plausibly create.
		expect(resolveFrameworkUi(frontend(false))).toBe(
			path.join(bench, 'apps', 'frappe', 'ui', 'src')
		)
	})
})
