import type { DoctypePermissionType, SessionUser } from '@/types'

type PermissionSource =
	| SessionUser
	| { data?: Record<string, unknown> | null }
	| undefined

type PermissionMap = NonNullable<
	NonNullable<SessionUser['data']>['permissions']
>

// Reads the doctype-level answers get_user_info carries for its fixed
// PERMISSION_DOCTYPES allowlist. A doctype outside that list reads as denied.
export const hasDoctypePermission = (
	user: PermissionSource,
	doctype: string,
	ptype: DoctypePermissionType = 'read'
): boolean => {
	const permissions = user?.data?.permissions as PermissionMap | undefined
	return Boolean(permissions?.[doctype]?.[ptype])
}

export const canReadDiscussions = (user: PermissionSource): boolean =>
	hasDoctypePermission(user, 'Discussion Topic') &&
	hasDoctypePermission(user, 'Discussion Reply')
