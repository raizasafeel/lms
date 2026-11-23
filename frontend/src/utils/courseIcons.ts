import { COURSE_SWATCHES } from '@/utils/courseTints'

// Mirrors COURSE_ICONS in lms/lms/doctype/lms_course/lms_course.py, in order.
// Whole class strings, so Tailwind's icon plugin finds each one in the source.
const ICON_CLASSES: Record<string, string> = {
	boxes: 'lucide-boxes',
	'layout-template': 'lucide-layout-template',
	award: 'lucide-award',
	'code-xml': 'lucide-code-xml',
	database: 'lucide-database',
	calculator: 'lucide-calculator',
	factory: 'lucide-factory',
	package: 'lucide-package',
	users: 'lucide-users',
	handshake: 'lucide-handshake',
	'graduation-cap': 'lucide-graduation-cap',
	'book-open': 'lucide-book-open',
	palette: 'lucide-palette',
	'chart-line': 'lucide-chart-line',
	briefcase: 'lucide-briefcase',
	rocket: 'lucide-rocket',
	wrench: 'lucide-wrench',
	globe: 'lucide-globe',
}

export const COURSE_ICONS: string[] = Object.keys(ICON_CLASSES)

const DEFAULT_ICON = 'book-open'

/** The lucide class for a course icon name, or an open book. */
export function courseIcon(name?: string | null): string {
	return ICON_CLASSES[name || ''] || ICON_CLASSES[DEFAULT_ICON]
}

/** The colour as stored on the course: `Pink` for the `pink` swatch. */
export const courseColor = (swatch: string): string =>
	swatch.charAt(0).toUpperCase() + swatch.slice(1)

export interface CourseThumbnail {
	color: string
	icon: string
}

/** A random colour and icon, never the pair the course already has. */
export function shuffleThumbnail(
	color?: string | null,
	icon?: string | null
): CourseThumbnail {
	const current = `${(color || '').toLowerCase()}/${icon || DEFAULT_ICON}`
	const pairs = Object.keys(COURSE_SWATCHES)
		.flatMap((swatch) => COURSE_ICONS.map((name) => ({ swatch, name })))
		.filter(({ swatch, name }) => `${swatch}/${name}` !== current)
	const pick = pairs[Math.floor(Math.random() * pairs.length)]
	return { color: courseColor(pick.swatch), icon: pick.name }
}
