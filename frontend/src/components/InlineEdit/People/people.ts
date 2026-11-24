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

export function roleDescription(role: PeopleRole): string {
	return {
		Editor: __('Edits content and settings'),
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
