import type { PeopleRole, PersonRow } from '@/types/lms/LMSRoleAssignment'

export type { PersonRow }
export type PeopleDoctype = 'LMS Course' | 'LMS Batch'

export const ROLES_BY_DOCTYPE: Record<PeopleDoctype, PeopleRole[]> = {
	'LMS Course': ['Editor', 'Grader'],
	'LMS Batch': ['Editor', 'Live class conductor', 'Grader'],
}

/** The site roles each People role needs; a Moderator may hold any. Mirrors lms.lms.people. */
const ELIGIBLE_SITE_ROLES: Record<PeopleRole, string[]> = {
	Editor: ['Course Creator'],
	Grader: ['Batch Evaluator'],
	'Live class conductor': ['Course Creator', 'Batch Evaluator'],
}

/** The site role an owner needs; a Moderator may own either. Mirrors lms.lms.people. */
export const OWNER_SITE_ROLE: Record<PeopleDoctype, string> = {
	'LMS Course': 'Course Creator',
	'LMS Batch': 'Batch Evaluator',
}

/** Site roles the "Add someone" search reaches. */
export const STAFF_SITE_ROLES = [
	'Course Creator',
	'Batch Evaluator',
	'Moderator',
]

export function roleLabel(role: PeopleRole): string {
	return {
		Editor: __('Editor'),
		Grader: __('Grader'),
		'Live class conductor': __('Live class conductor'),
	}[role]
}

export function roleDescription(
	role: PeopleRole,
	doctype: PeopleDoctype
): string {
	return {
		Editor:
			doctype === 'LMS Batch'
				? __('Edits content and settings, and schedules classes')
				: __('Edits content and settings'),
		Grader: __('Grades work and answers questions'),
		'Live class conductor': __('Runs live classes'),
	}[role]
}

export function eligibleRoles(
	doctype: PeopleDoctype,
	siteRoles: string[]
): PeopleRole[] {
	if (siteRoles.includes('Moderator')) return ROLES_BY_DOCTYPE[doctype]
	return ROLES_BY_DOCTYPE[doctype].filter((role) =>
		ELIGIBLE_SITE_ROLES[role].some((siteRole) => siteRoles.includes(siteRole))
	)
}

export function membersWith(rows: PersonRow[], role: PeopleRole): string[] {
	return rows.filter((row) => row.role === role).map((row) => row.member)
}

/** Sets one role's members, keeping the other roles' rows and the table in role order. */
export function withMembers(
	doctype: PeopleDoctype,
	rows: PersonRow[],
	role: PeopleRole,
	members: string[]
): PersonRow[] {
	return ROLES_BY_DOCTYPE[doctype].flatMap((each) =>
		(each === role ? [...new Set(members)] : membersWith(rows, each)).map(
			(member) => ({ member, role: each })
		)
	)
}

/** Why someone may not hold `role`, shown beside the disabled choice. */
export function ineligibleReason(role: PeopleRole): string {
	return {
		Editor: __('Needs the Course Creator role'),
		Grader: __('Only evaluators can grade'),
		'Live class conductor': __(
			'Needs the Course Creator or Batch Evaluator role'
		),
	}[role]
}

/** The roles `member` holds, in role order. */
export function rolesOf(
	doctype: PeopleDoctype,
	rows: PersonRow[],
	member: string
): PeopleRole[] {
	return ROLES_BY_DOCTYPE[doctype].filter((role) =>
		rows.some((row) => row.member === member && row.role === role)
	)
}

/** Gives `member` exactly `roles`, leaving everyone else's rows as they were. */
export function withMemberRoles(
	doctype: PeopleDoctype,
	rows: PersonRow[],
	member: string,
	roles: PeopleRole[]
): PersonRow[] {
	return ROLES_BY_DOCTYPE[doctype].flatMap((role) => {
		const members = membersWith(rows, role).filter((each) => each !== member)
		const held = membersWith(rows, role).includes(member)
		if (roles.includes(role)) {
			const at = held ? membersWith(rows, role).indexOf(member) : members.length
			members.splice(at, 0, member)
		}
		return members.map((each) => ({ member: each, role }))
	})
}
