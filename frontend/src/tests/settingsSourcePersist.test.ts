import { describe, expect, it, vi, beforeEach } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'

const { call, createDocumentResource } = vi.hoisted(() => ({
	call: vi.fn(),
	createDocumentResource: vi.fn(),
}))

vi.mock('frappe-ui', () => ({ call, createDocumentResource, toast: {} }))
vi.mock('@/utils/dialogs', () => ({ createDialog: vi.fn() }))
vi.mock('@/utils', () => ({ cleanError: (m: string) => m }))
vi.mock('@/components/Settings/Members/Members.vue', () => ({ default: {} }))

import { NEW_RECORD, useSettingsSource } from '@/composables/useSettingsSource'
import { memberDetails } from '@/components/Settings/Members/members'
import type { SettingsListRow } from '@/types'

const sourceFor = (
	record: string,
	persist: (doc: SettingsListRow, isNew: boolean) => Promise<unknown>
) =>
	effectScope().run(() =>
		useSettingsSource(
			{ doctype: 'User', record: 'route' },
			{ record: ref(record), persist }
		)
	)!

describe('useSettingsSource persist', () => {
	beforeEach(() => {
		call.mockReset()
		createDocumentResource.mockReset()
	})

	it('creates through persist, never frappe.client.insert', async () => {
		const persist = vi.fn().mockResolvedValue({ name: 'a@b.c' })
		const source = sourceFor(NEW_RECORD, persist)
		source.doc!.email = 'a@b.c'

		expect(await source.save()).toEqual({ name: 'a@b.c' })
		expect(persist).toHaveBeenCalledWith({ email: 'a@b.c' }, true)
		expect(call).not.toHaveBeenCalled()
		expect(source.isDirty).toBe(false)
	})

	it('updates through persist and reloads instead of saving the resource', async () => {
		const resource = {
			name: 'a@b.c',
			doc: { name: 'a@b.c', first_name: 'A' },
			save: { submit: vi.fn() },
			reload: vi.fn().mockResolvedValue(undefined),
		}
		createDocumentResource.mockReturnValue(resource)
		const persist = vi.fn().mockResolvedValue({ name: 'a@b.c' })
		const source = sourceFor('a@b.c', persist)
		await nextTick()

		await source.save()
		expect(persist).toHaveBeenCalledWith(resource.doc, false)
		expect(resource.reload).toHaveBeenCalled()
		expect(resource.save.submit).not.toHaveBeenCalled()
	})
})

describe('memberDetails', () => {
	const doc = {
		name: 'a@b.c',
		email: 'a@b.c',
		first_name: 'Ada',
		bio: null,
		roles: [{ role: 'System Manager' }],
		new_password: 'x',
		enabled: 1,
		user_type: 'System User',
	}

	it('sends only the profile fields, plus email when creating', () => {
		const created = memberDetails(doc, true)
		const updated = memberDetails(doc, false)

		expect(created.email).toBe('a@b.c')
		expect(updated).not.toHaveProperty('email')
		for (const details of [created, updated]) {
			expect(details.first_name).toBe('Ada')
			expect(details.bio).toBeNull()
			for (const field of ['roles', 'new_password', 'enabled', 'user_type'])
				expect(details).not.toHaveProperty(field)
		}
	})
})
