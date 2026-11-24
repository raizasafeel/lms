/**
 * Billing and the other Frappe Cloud pages are offered only when the server
 * reports Cloud Settings enabled, which it does only on a Frappe Cloud v2 site.
 */
import { describe, expect, it, vi } from 'vitest'

vi.hoisted(() => {
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
})

vi.stubGlobal('__', (s: string) => s)
vi.mock('@framework/ui/telemetry/index', () => ({}))
vi.mock('@framework/ui/components/Onboarding/index', () => ({}))

const user = vi.hoisted(() => ({ data: {} as Record<string, unknown> }))
vi.mock('@/stores/user', () => ({
	usersStore: () => ({ userResource: user }),
}))

import { isGroupVisible, settingsTree } from '@/components/Settings/settings'

const visibleSlugs = () =>
	settingsTree
		.filter(isGroupVisible)
		.flatMap((group) => group.items.map((item) => item.slug))

describe('the Frappe Cloud settings group', () => {
	it('hides billing when the site is not on Frappe Cloud v2', () => {
		user.data = {
			is_moderator: true,
			is_system_manager: true,
			cloud_settings: { enabled: false },
		}
		expect(visibleSlugs()).not.toContain('cloud-billing')
	})

	it('hides billing when user info carries no cloud settings', () => {
		user.data = { is_moderator: true, is_system_manager: true }
		expect(visibleSlugs()).not.toContain('cloud-billing')
	})

	it('shows billing when the server enables cloud settings', () => {
		user.data = {
			is_moderator: true,
			is_system_manager: true,
			cloud_settings: { enabled: true },
		}
		expect(visibleSlugs()).toContain('cloud-billing')
	})
})
