import type { SelectOption } from 'frappe-ui'
import type {
	SettingsListBadge,
	SettingsListColumn,
	SettingsListRow,
} from '@/types'

/**
 * Settings > Badges, as config: what the list shows and what the form offers.
 * Badges.vue draws both.
 */

export const BADGE_DOCTYPE = 'LMS Badge'

/** LMS Badge autonames `field:title`, so editing the title renames the record. */
export const BADGE_RENAME_FIELD = 'title'

export const BADGE_FIELDS = [
	'name',
	'title',
	'enabled',
	'description',
	'image',
	'grant_only_once',
	'event',
	'reference_doctype',
	'condition',
	'user_field',
	'field_to_check',
]

export const BADGE_SEARCH_FIELDS = ['title', 'description']

const DOCTYPE_LABELS: Record<string, () => string> = {
	'LMS Course': () => __('Course'),
	'LMS Batch': () => __('Batch'),
	'LMS Enrollment': () => __('Course Enrollment'),
	'LMS Batch Enrollment': () => __('Batch Enrollment'),
	'LMS Quiz Submission': () => __('Quiz Submission'),
	'LMS Assignment Submission': () => __('Assignment Submission'),
	'LMS Programming Exercise Submission': () =>
		__('Programming Exercise Submission'),
	Member: () => __('User'),
}

/**
 * The pill in the Awarded For column, and the one place that decides what a
 * reference doctype is called. Gray, like every other pill in the list, and it
 * falls back to the raw doctype so an unmapped one still reads as itself.
 */
export const awardedFor = (doctype: string): SettingsListBadge => ({
	label: DOCTYPE_LABELS[doctype]?.() || doctype,
	theme: 'gray',
})

export interface BadgeRowActions {
	toggleEnabled: (row: SettingsListRow, value: boolean) => void
	remove: (row: SettingsListRow) => void
}

export const badgeColumns = (
	actions: BadgeRowActions
): SettingsListColumn[] => [
	{
		key: 'title',
		label: __('Badge'),
		type: 'stacked',
		width: 'minmax(0, 1.6fr)',
		primary: (row) => row.title,
		avatar: (row) => ({ image: row.image, label: row.title }),
	},
	{
		key: 'reference_doctype',
		label: __('Awarded For'),
		type: 'badge',
		badges: (row) => [awardedFor(row.reference_doctype)],
	},
	{
		// A switch, not a status badge: the state is a thing to change from here.
		// Same column shape Zoom accounts use, optimistic write and all.
		key: 'enabled',
		label: __('Enabled'),
		type: 'switch',
		width: '6.5rem',
		checked: (row) => Boolean(row.enabled),
		ariaLabel: (row) => __('Enable {0}').format(row.title),
		onChange: (row, value) => actions.toggleEnabled(row, value),
	},
	{
		key: 'actions',
		type: 'actions',
		ariaLabel: (row) => __('Actions for {0}').format(row.title),
		options: (row) => [
			{
				label: __('Delete'),
				icon: 'lucide-trash-2',
				theme: 'red',
				onClick: () => actions.remove(row),
			},
		],
	},
]

export const referenceDoctypeOptions = (): SelectOption[] => [
	{ label: __('Course'), value: 'LMS Course' },
	{ label: __('Batch'), value: 'LMS Batch' },
	{ label: __('User'), value: 'Member' },
	{ label: __('Quiz Submission'), value: 'LMS Quiz Submission' },
	{ label: __('Assignment Submission'), value: 'LMS Assignment Submission' },
	{
		label: __('Programming Exercise Submission'),
		value: 'LMS Programming Exercise Submission',
	},
	{ label: __('Course Enrollment'), value: 'LMS Enrollment' },
	{ label: __('Batch Enrollment'), value: 'LMS Batch Enrollment' },
]

export const eventOptions = (): SelectOption[] =>
	['New', 'Value Change', 'Manual Assignment'].map((event) => ({
		label: __(event),
		value: event,
	}))

export const userFieldOptions = (): SelectOption[] => [
	{ label: __('Member'), value: 'member' },
	{ label: __('Owner'), value: 'owner' },
]

// A condition is written here rather than merely checked, so the hint carries a
// worked example of each shape it can take.
export const conditionHint = (): string =>
	__(
		'Manual Assignment takes JSON filters, e.g. {"published": 1}. Every other event takes an expression over `doc`, e.g. doc.progress == 100.'
	)

/** The fields a new badge opens on, before anything has been typed. */
export const newBadge = (): Record<string, unknown> => ({
	title: '',
	enabled: 1,
	description: '',
	image: '',
	grant_only_once: 0,
	event: 'New',
	reference_doctype: '',
	condition: '',
	user_field: 'member',
})
