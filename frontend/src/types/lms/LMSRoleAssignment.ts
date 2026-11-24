export type PeopleRole = 'Editor' | 'Grader' | 'Live class conductor'

export interface LMSRoleAssignment {
	creation?: string
	name?: string
	modified?: string
	owner?: string
	modified_by?: string
	docstatus?: 0 | 1 | 2
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
	/**	Member : Link - User	*/
	member: string
	/**	Role : Select	*/
	role: PeopleRole
	/**	Member Name : Data	*/
	member_name?: string
	/**	Member Image : Attach Image	*/
	member_image?: string
}

/** A People row as the forms edit it. */
export type PersonRow = Pick<LMSRoleAssignment, 'member' | 'role'>
