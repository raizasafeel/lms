// Whole class strings, so Tailwind finds each one in the source.
export const COURSE_TINTS: Record<string, string> = {
	red: 'bg-surface-red-2 text-ink-red-5',
	blue: 'bg-surface-blue-2 text-ink-blue-5',
	green: 'bg-surface-green-2 text-ink-green-5',
	amber: 'bg-surface-amber-2 text-ink-amber-5',
	cyan: 'bg-surface-cyan-2 text-ink-cyan-5',
	orange: 'bg-surface-orange-2 text-ink-orange-5',
	pink: 'bg-surface-pink-2 text-ink-pink-5',
	purple: 'bg-surface-purple-2 text-ink-purple-5',
	teal: 'bg-surface-teal-2 text-ink-teal-5',
	violet: 'bg-surface-violet-2 text-ink-violet-5',
	yellow: 'bg-surface-yellow-2 text-ink-yellow-5',
	gray: 'bg-surface-gray-2 text-ink-gray-6',
}

// Solid swatches for the colour picker, one per tint.
export const COURSE_SWATCHES: Record<string, string> = {
	red: 'bg-surface-red-5',
	blue: 'bg-surface-blue-5',
	green: 'bg-surface-green-5',
	amber: 'bg-surface-amber-5',
	cyan: 'bg-surface-cyan-5',
	orange: 'bg-surface-orange-5',
	pink: 'bg-surface-pink-5',
	purple: 'bg-surface-purple-5',
	teal: 'bg-surface-teal-5',
	violet: 'bg-surface-violet-5',
	yellow: 'bg-surface-yellow-5',
	gray: 'bg-surface-gray-5',
}

export function courseTint(color?: string | null): string {
	return COURSE_TINTS[(color || '').toLowerCase()] || COURSE_TINTS.blue
}
