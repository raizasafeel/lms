import type { CertificatePreviewOption } from '@/types/api'

export interface CertificateDesign {
	name: string
	label: string
	description: string
	thumbnail: string | null
}

interface DesignInfo {
	label: string
	description: string
	thumbnail: string
}

const SHIPPED: Record<string, DesignInfo> = {
	Certificate: {
		label: 'Original',
		description: 'The design Frappe Learning has always used.',
		thumbnail: 'original',
	},
	'Certificate Classic': {
		label: 'Classic',
		description: 'Serif type and a double border. Formal and centred.',
		thumbnail: 'classic',
	},
	'Certificate Modern': {
		label: 'Modern',
		description: 'Bold sans type, logo at the start, strong rule.',
		thumbnail: 'modern',
	},
	'Certificate Minimal': {
		label: 'Minimal',
		description: 'Light type and generous white space.',
		thumbnail: 'minimal',
	},
	'Certificate Ledger': {
		label: 'Ledger',
		description: 'Details in a side column, name and title get the page.',
		thumbnail: 'ledger',
	},
	'Certificate Banner': {
		label: 'Banner',
		description: 'Dark header band with your site name. Prints solid.',
		thumbnail: 'banner',
	},
	'Certificate Corners': {
		label: 'Corners',
		description: 'Centred sans type framed by corner marks.',
		thumbnail: 'corners',
	},
	'Certificate Record': {
		label: 'Record',
		description: 'Every detail in a labelled grid. Reads like a transcript.',
		thumbnail: 'record',
	},
}

const SHIPPED_ORDER = Object.keys(SHIPPED)

export const PREVIEW_OPTIONS: {
	key: CertificatePreviewOption
	label: string
}[] = [
	{ key: 'long', label: 'Long name and title' },
	{ key: 'batch', label: 'Batch wording' },
	{ key: 'expiry', label: 'Expiry date' },
	{ key: 'no_logo', label: 'No logo' },
	{ key: 'rtl', label: 'Arabic (RTL)' },
]

export function describeDesign(name: string): CertificateDesign {
	const info = SHIPPED[name]
	if (!info) {
		return {
			name,
			label: name,
			description: __('Custom template'),
			thumbnail: null,
		}
	}
	return {
		name,
		label: __(info.label),
		description: __(info.description),
		thumbnail: `/assets/lms/images/certificates/${info.thumbnail}.png`,
	}
}

export function sortDesigns(names: readonly string[]): string[] {
	const rank = (name: string): number => {
		const index = SHIPPED_ORDER.indexOf(name)
		return index === -1 ? SHIPPED_ORDER.length : index
	}
	return [...names].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b))
}
