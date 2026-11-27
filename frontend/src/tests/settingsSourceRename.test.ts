import { describe, expect, it, vi } from 'vitest'
import { reactive } from 'vue'

const { call } = vi.hoisted(() => ({ call: vi.fn(() => Promise.resolve()) }))

vi.mock('frappe-ui', () => ({
	call,
	createDocumentResource: vi.fn(),
	toast: {},
}))

import { useSettingsSource } from '@/composables/useSettingsSource'

// A badge autonames from `title`, so the rename also writes that field.
const badge = () =>
	reactive({
		name: 'Champion',
		doc: { name: 'Champion', title: 'Course Champion' } as Record<string, any>,
		originalDoc: { name: 'Champion', title: 'Champion' },
		isDirty: true,
		save: { submit: vi.fn(() => Promise.resolve()) },
		reload: vi.fn(),
	})

describe('renaming a record through its name field', () => {
	it('leaves nothing unsaved once the rename lands', async () => {
		const resource = badge()
		const source = useSettingsSource(
			{ doctype: 'LMS Badge', name: 'Champion' },
			{ resource, renameField: 'title' }
		)

		await source.save()

		expect(call).toHaveBeenCalledWith('frappe.client.rename_doc', {
			doctype: 'LMS Badge',
			old_name: 'Champion',
			new_name: 'Course Champion',
		})
		expect(resource.isDirty).toBe(false)
	})
})
