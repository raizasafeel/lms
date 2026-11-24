import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import type { PersonRow } from '@/types/lms/LMSRoleAssignment'

const { details, slotCounts, resourceParams } = vi.hoisted(() => {
	// @/utils pulls in plyr, which touches matchMedia at import time.
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
	return {
		details: {
			'owner@example.com': ['Course Creator'],
			'ash@example.com': ['Course Creator'],
			'eve@example.com': ['Batch Evaluator'],
			'both@example.com': ['Course Creator', 'Batch Evaluator'],
		} as Record<string, string[]>,
		slotCounts: { 'eve@example.com': 3 } as Record<string, number>,
		resourceParams: [] as unknown[],
	}
})

vi.mock('frappe-ui', async () => {
	const { reactive } = await import('vue')
	const passthrough = { template: '<div><slot /></div>' }
	return {
		call: vi.fn(async (_method: string, { users }: { users: string }) =>
			JSON.parse(users).map((name: string) => ({
				name,
				full_name: name.split('@')[0].toUpperCase(),
				roles: details[name] || [],
			}))
		),
		createResource: (options: { makeParams?: () => unknown }) => {
			resourceParams.push(options.makeParams?.())
			return reactive({ data: slotCounts, reload: vi.fn(), loading: false })
		},
		Avatar: { props: ['label'], template: '<span class="avatar" />' },
		Badge: {
			props: ['label'],
			template: '<span class="badge">{{ label }}</span>',
		},
		Button: {
			props: ['ariaLabel'],
			template:
				'<button :aria-label="ariaLabel" v-bind="$attrs"><slot /><slot name="icon" /></button>',
		},
		MultiSelect: {
			name: 'MultiSelect',
			props: ['modelValue', 'options'],
			emits: ['update:modelValue'],
			template: '<div class="roles"><slot name="summary" /></div>',
		},
		FormControl: {
			name: 'FormControl',
			props: ['modelValue', 'label', 'options'],
			template: '<div />',
		},
		Tooltip: passthrough,
		Dialog: passthrough,
	}
})
vi.mock('@/components/InlineEdit/SettingSwitch.vue', () => ({
	default: {
		name: 'SettingSwitch',
		props: ['modelValue', 'label', 'summary'],
		emits: ['update:modelValue'],
		template: '<div class="switch">{{ label }} {{ summary }}</div>',
	},
}))
vi.mock('@/components/Controls/MultiLink.vue', () => ({
	default: {
		name: 'MultiLink',
		props: ['modelValue', 'searchParams', 'allowSelectAll', 'clearable'],
		emits: ['update:modelValue'],
		template: '<div class="multilink"><slot name="summary" /></div>',
	},
}))

import ChangeOwnerDialog from '@/components/InlineEdit/People/ChangeOwnerDialog.vue'
import EvaluationGroup from '@/components/InlineEdit/People/EvaluationGroup.vue'
import PeopleGroup from '@/components/InlineEdit/People/PeopleGroup.vue'
import {
	eligibleRoles,
	withMembers,
} from '@/components/InlineEdit/People/people'

const global = { mocks: { __: globalThis.__ } }

function host(
	component: unknown,
	props: Record<string, unknown>,
	rows: PersonRow[],
	model = 'modelValue'
) {
	const people = ref<PersonRow[]>(rows)
	const wrapper = mount(
		defineComponent({
			setup: () => () =>
				h(component as never, {
					...props,
					[model]: people.value,
					[`onUpdate:${model}`]: (next: PersonRow[]) => (people.value = next),
				}),
		}),
		{ global }
	)
	return { wrapper, people }
}

describe('People roles', () => {
	it('offers each person only the roles their site roles allow', () => {
		expect(eligibleRoles('LMS Course', ['Course Creator'])).toEqual(['Editor'])
		expect(eligibleRoles('LMS Course', ['Batch Evaluator'])).toEqual(['Grader'])
		expect(eligibleRoles('LMS Batch', ['Batch Evaluator'])).toEqual([
			'Live class conductor',
			'Grader',
		])
		expect(eligibleRoles('LMS Batch', ['Moderator'])).toHaveLength(3)
	})

	it('sets one role and keeps the others in role order', () => {
		const rows: PersonRow[] = [
			{ member: 'eve@example.com', role: 'Grader' },
			{ member: 'ash@example.com', role: 'Editor' },
		]
		expect(
			withMembers('LMS Course', rows, 'Grader', ['both@example.com'])
		).toEqual([
			{ member: 'ash@example.com', role: 'Editor' },
			{ member: 'both@example.com', role: 'Grader' },
		])
	})
})

describe('PeopleGroup', () => {
	const mountPeople = (rows: PersonRow[], canChangeOwner = true) =>
		host(
			PeopleGroup,
			{
				doctype: 'LMS Course',
				name: 'c1',
				owner: 'owner@example.com',
				canChangeOwner,
			},
			rows
		)

	it('lists the owner first, then each person with what their role does', async () => {
		const { wrapper } = mountPeople([
			{ member: 'ash@example.com', role: 'Editor' },
			{ member: 'eve@example.com', role: 'Grader' },
		])
		await flushPromises()
		const rows = wrapper.findAll('li').map((row) => row.text())
		expect(rows[0]).toContain('OWNER')
		expect(rows[0]).toContain('Everything, including deleting the course')
		expect(rows[0]).toContain('Owner')
		expect(rows[0]).toContain('Change owner')
		expect(rows[1]).toContain('Edits content and settings')
		expect(rows[1]).not.toContain('schedules classes')
		expect(rows[2]).toContain('Grades work and answers questions')
	})

	it('hides Change owner from everyone but the owner and Moderators', () => {
		const { wrapper } = mountPeople([], false)
		expect(wrapper.text()).not.toContain('Change owner')
	})

	it('disables a role the person may not hold, saying why', async () => {
		const { wrapper } = mountPeople([
			{ member: 'ash@example.com', role: 'Editor' },
		])
		await flushPromises()
		const options = wrapper
			.findComponent({ name: 'MultiSelect' })
			.props('options')
		expect(options).toEqual([
			expect.objectContaining({ value: 'Editor', disabled: false }),
			expect.objectContaining({
				value: 'Grader',
				disabled: true,
				description: 'Only evaluators can grade',
			}),
		])
	})

	it('adds someone in the first role they may hold and removes them again', async () => {
		const { wrapper, people } = mountPeople([
			{ member: 'ash@example.com', role: 'Editor' },
		])
		await flushPromises()
		const picker = wrapper.findComponent({ name: 'MultiLink' })
		expect(picker.text()).toContain('Add someone')
		// Clear would drop everyone at once.
		expect(picker.props('clearable')).toBe(false)
		picker.vm.$emit('update:modelValue', ['ash@example.com', 'eve@example.com'])
		await flushPromises()
		expect(people.value).toEqual([
			{ member: 'ash@example.com', role: 'Editor' },
			{ member: 'eve@example.com', role: 'Grader' },
		])
		await wrapper.find('button[aria-label="Remove ASH"]').trigger('click')
		expect(people.value).toEqual([
			{ member: 'eve@example.com', role: 'Grader' },
		])
	})

	it('shows each person once with all their roles', async () => {
		const { wrapper, people } = mountPeople([
			{ member: 'both@example.com', role: 'Editor' },
			{ member: 'both@example.com', role: 'Grader' },
		])
		await flushPromises()
		const rows = wrapper.findAll('li')
		expect(rows).toHaveLength(2)
		expect(rows[1].find('.roles').text()).toBe('Editor, Grader')
		expect(rows[1].text()).toContain(
			'Edits content and settings · Grades work and answers questions'
		)

		const roles = wrapper.findComponent({ name: 'MultiSelect' })
		roles.vm.$emit('update:modelValue', ['Grader'])
		expect(people.value).toEqual([
			{ member: 'both@example.com', role: 'Grader' },
		])
		roles.vm.$emit('update:modelValue', [])
		expect(people.value).toEqual([])
	})

	it('describes a batch editor as scheduling classes', async () => {
		const { wrapper } = host(
			PeopleGroup,
			{
				doctype: 'LMS Batch',
				name: 'b1',
				owner: 'owner@example.com',
				canChangeOwner: true,
			},
			[{ member: 'ash@example.com', role: 'Editor' }]
		)
		await flushPromises()
		expect(wrapper.findAll('li')[1].text()).toContain(
			'Edits content and settings, and schedules classes'
		)
	})
})

describe('EvaluationGroup', () => {
	const mountEvaluation = (
		rows: PersonRow[],
		extra: Record<string, unknown> = {}
	) =>
		host(
			EvaluationGroup,
			{
				doctype: 'LMS Batch',
				enabled: true,
				format: 'Live call',
				duration: '30',
				...extra,
			},
			rows,
			'people'
		)

	it('shows its fields as plain rows under the switch, with nothing to expand', () => {
		const { wrapper } = mountEvaluation([
			{ member: 'eve@example.com', role: 'Grader' },
			{ member: 'both@example.com', role: 'Grader' },
		])
		expect(wrapper.find('.switch').text()).toContain(
			'Learners book a slot with whoever is free.'
		)
		const text = wrapper.text()
		expect(text).toContain('2 evaluators, also listed as Graders in People')
		expect(text).toContain('Format')
		expect(text).toContain('Length')
		expect(wrapper.find('[aria-expanded]').exists()).toBe(false)
	})

	it('lists the Graders with their open slots this week', async () => {
		const { wrapper } = mountEvaluation([
			{ member: 'ash@example.com', role: 'Editor' },
			{ member: 'eve@example.com', role: 'Grader' },
		])
		await flushPromises()
		const evaluators = wrapper.find('ul[aria-label="Evaluators"]')
		expect(evaluators.findAll('li')).toHaveLength(1)
		expect(evaluators.text()).toContain('EVE')
		expect(evaluators.text()).toContain('3 open slots this week')
	})

	it('adds evaluators as Graders and removes them from People', async () => {
		const { wrapper, people } = mountEvaluation([
			{ member: 'ash@example.com', role: 'Editor' },
		])
		const picker = wrapper.findComponent({ name: 'MultiLink' })
		expect(picker.props('searchParams')).toEqual({
			roles: JSON.stringify(['Batch Evaluator']),
		})
		expect(picker.props('allowSelectAll')).toBe(true)
		picker.vm.$emit('update:modelValue', ['eve@example.com'])
		await flushPromises()
		expect(people.value).toContainEqual({
			member: 'eve@example.com',
			role: 'Grader',
		})

		await wrapper.find('button[aria-label="Remove EVE"]').trigger('click')
		expect(people.value).toEqual([
			{ member: 'ash@example.com', role: 'Editor' },
		])
	})

	it('removing an evaluator keeps their other roles', async () => {
		const { wrapper, people } = mountEvaluation([
			{ member: 'both@example.com', role: 'Editor' },
			{ member: 'both@example.com', role: 'Grader' },
		])
		await flushPromises()
		await wrapper.find('button[aria-label="Remove BOTH"]').trigger('click')
		expect(people.value).toEqual([
			{ member: 'both@example.com', role: 'Editor' },
		])
	})

	it('says a review of submitted work is not bookable yet', () => {
		const { wrapper } = mountEvaluation([], {
			format: 'Review of submitted work',
		})
		expect(wrapper.text()).toContain(
			'Reviews of submitted work are coming later.'
		)
	})

	it('hides the details while evaluations are off', () => {
		const { wrapper } = mountEvaluation([], { enabled: false })
		expect(wrapper.findComponent({ name: 'MultiLink' }).exists()).toBe(false)
		expect(wrapper.text()).not.toContain('Format')
		expect(wrapper.find('.switch').text()).toContain(
			'Learners get no evaluation.'
		)
	})
})

describe('ChangeOwnerDialog', () => {
	const ownerSearch = (doctype: string) => {
		resourceParams.length = 0
		const wrapper = mount(ChangeOwnerDialog, {
			props: { doctype, name: 'x', owner: 'owner@example.com', open: true },
			global,
		})
		return { wrapper, params: resourceParams[0] as { roles: string } }
	}

	it('offers a course only to Course Creators and Moderators', () => {
		const { wrapper, params } = ownerSearch('LMS Course')
		expect(JSON.parse(params.roles)).toEqual(['Course Creator', 'Moderator'])
		expect(wrapper.text()).toContain('Only Course Creators can own a course.')
	})

	it('offers a batch only to Batch Evaluators and Moderators', () => {
		const { wrapper, params } = ownerSearch('LMS Batch')
		expect(JSON.parse(params.roles)).toEqual(['Batch Evaluator', 'Moderator'])
		expect(wrapper.text()).toContain('Only Batch Evaluators can own a batch.')
	})
})
