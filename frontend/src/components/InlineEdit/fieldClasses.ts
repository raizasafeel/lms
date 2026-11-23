/** frappe-ui's outline input chrome, minus the fill so the missing ring shows. */
export const OUTLINE_FIELD =
	'rounded-4 border border-outline-gray-2 transition-colors placeholder:text-ink-gray-4 hover:border-outline-gray-3 hover:shadow-sm focus:border-outline-gray-4 focus:shadow-sm focus:outline-none focus:ring-0'

/** Rings a required field that is still empty while the form shows its gaps. */
export const MISSING_RING = 'bg-surface-red-1 ring-2 ring-outline-red-3'

export const missingRing = (missing?: boolean): string =>
	missing ? MISSING_RING : ''
