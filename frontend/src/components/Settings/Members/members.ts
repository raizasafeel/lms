import { call, toast } from 'frappe-ui'
import { markRaw } from 'vue'
// @ts-expect-error utils/dialogs.js is still plain JS, so it has no declarations
import { createDialog } from '@/utils/dialogs'
import Members from '@/components/Settings/Members/Members.vue'
import { cleanError } from '@/utils'
import type { CustomPage, SelectOption } from '@/types/settingsSchema'
import type { SettingsListColumn, SettingsListRow } from '@/types'

/**
 * Settings > Users, as config: what the list shows, what a row offers, and the
 * roles the form can grant. The rows arrive from `get_members` rather than a
 * doctype list, so the paging is done against `start`.
 */

// This module and Members.vue import each other, so neither may read the
// other's bindings while it is still evaluating. Everything Members.vue takes
// from here it reads inside its setup, and the component below is a getter.

export const MEMBERS_METHOD = 'lms.lms.api.get_members'

// Users, as far as list invalidation is concerned: get_members returns them
// and delete_member removes them.
export const MEMBERS_DOCTYPE = 'User'

// The raw role names get_members returns, and what a badge calls them. Only
// these four are shown, because member_roles() returns LMS_ROLES and a role
// outside this map is not one of them.
const ROLE_LABELS: Record<string, () => string> = {
	'LMS Student': () => __('Student'),
	'Course Creator': () => __('Instructor'),
	Moderator: () => __('Moderator'),
	'Batch Evaluator': () => __('Evaluator'),
}

export const roleOptions = (): SelectOption[] => [
	{ label: __('All'), value: 'All' },
	...Object.entries(ROLE_LABELS).map(([value, label]) => ({
		label: label(),
		value,
	})),
]

/**
 * The four roles the form grants, in the order they are drawn. `role` is the
 * server's name and `label` is what the row reads. Course Creator keeps the
 * server's name rather than the badge's "Instructor".
 */
export const ROLE_ROWS = [
	{ key: 'lms_student', role: 'LMS Student', label: () => __('Student') },
	{
		key: 'course_creator',
		role: 'Course Creator',
		label: () => __('Course Creator'),
	},
	{
		key: 'batch_evaluator',
		role: 'Batch Evaluator',
		label: () => __('Evaluator'),
	},
	{ key: 'moderator', role: 'Moderator', label: () => __('Moderator') },
] as const

export type MemberRoleKey = typeof ROLE_ROWS[number]['key']

export type MemberRoles = Record<MemberRoleKey, boolean>

export const noRoles = (): MemberRoles => ({
	lms_student: false,
	course_creator: false,
	batch_evaluator: false,
	moderator: false,
})

/** The four switches, as the server would name them. */
export const rolesFrom = (granted: string[] | undefined): MemberRoles => {
	const held = granted ?? []
	const roles = noRoles()
	for (const row of ROLE_ROWS) roles[row.key] = held.includes(row.role)
	return roles
}

export interface MemberRowActions {
	/** The member's own page, which is not a settings page. */
	profile: (row: SettingsListRow) => void
	remove: (row: SettingsListRow) => void
}

export const memberColumns = (
	actions: MemberRowActions
): SettingsListColumn[] => [
	{
		key: 'member',
		label: __('User'),
		type: 'stacked',
		primary: (row) => row.full_name,
		secondary: (row) => row.name,
		avatar: (row) => ({ image: row.user_image, label: row.full_name }),
	},
	{
		key: 'roles',
		label: __('Roles'),
		type: 'badge',
		badges: (row) =>
			((row.roles || []) as string[])
				.filter((role) => ROLE_LABELS[role])
				.map((role) => ({
					label: ROLE_LABELS[role](),
					theme: 'gray' as const,
				})),
	},
	{
		key: 'actions',
		type: 'actions',
		ariaLabel: (row) => __('Actions for {0}').format(row.full_name),
		// Editing is what a row click does now, so the menu carries the two
		// things a click cannot: the person's public profile, and deletion.
		options: (row) => [
			{
				label: __('Go to Profile'),
				icon: 'lucide-user',
				onClick: () => actions.profile(row),
			},
			{
				label: __('Delete user'),
				icon: 'lucide-trash-2',
				theme: 'red',
				onClick: () => actions.remove(row),
			},
		],
	},
]

export const memberError = (
	error: { messages?: string[]; message?: string },
	fallback: string
): string => {
	const message = error?.messages?.[0] || error?.message
	return message ? cleanError(message) : fallback
}

const removeMember = (
	row: SettingsListRow,
	close: (() => void) | undefined,
	onDeleted: () => void
) =>
	call('lms.lms.api.delete_member', { user: row.name })
		.then(() => {
			if (typeof close === 'function') close()
			toast.success(__('User deleted'))
			onDeleted()
		})
		.catch((error: { messages?: string[] }) => {
			toast.error(memberError(error, __('Unable to delete user')))
			console.error(error)
		})

// Same confirmation the other settings lists put a delete behind: a red solid
// Delete in a dialog that says what is lost. A user account is the most
// destructive row in settings.
export const confirmMemberDeletion = (
	row: SettingsListRow,
	onDeleted: () => void
) => {
	createDialog({
		title: __('Delete {0}?').format(row.full_name),
		message: __(
			'This permanently deletes the user account and cannot be undone.'
		),
		size: 'sm',
		actions: [
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				onClick({ close }: { close: () => void }) {
					removeMember(row, close, onDeleted)
				},
			},
		],
	})
}

// A getter, not a property. This module and Members.vue import each other, so
// whichever loads first finds the other's bindings uninitialized. Reading the
// component at render time is what makes the pair safe to enter from either side.
export const membersSettingsPage: CustomPage = {
	kind: 'custom',
	get component() {
		return markRaw(Members)
	},
}
