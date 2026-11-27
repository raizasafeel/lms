import type { LMSPrice } from '@/types/lms/LMSPrice'

export type PriceRow = Pick<
	LMSPrice,
	'name' | 'country' | 'price_type' | 'amount' | 'currency' | 'percent_off'
>

/** What `lms.lms.api.get_price_previews` returns for one row. */
export interface PricePreview {
	country: string
	amount: number
	currency: string
	formatted: string
}

export const PRICE_TYPES: { label: string; value: PriceRow['price_type'] }[] = [
	{ label: __('Fixed'), value: 'Fixed' },
	{ label: __('% off'), value: 'Percent Off' },
]

/** A row's value: its amount, or its percent off. */
export function rowValue(row: PriceRow): number | undefined {
	return row.price_type === 'Fixed' ? row.amount : row.percent_off
}

/**
 * The row with `value` in the field its type uses and the other cleared. A fixed
 * row keeps its currency, or takes `currency`; a percent off is in the regular one.
 */
export function withRowValue(
	row: PriceRow,
	value: number,
	currency?: string | null
): PriceRow {
	return row.price_type === 'Fixed'
		? {
				...row,
				amount: value,
				percent_off: 0,
				currency: row.currency || currency,
		  }
		: { ...row, percent_off: value, amount: 0, currency: null }
}

/** Rows the server can price: a country, and a value for a fixed one. */
export function isPriceable(row: PriceRow): boolean {
	if (!row.country) return false
	return row.price_type !== 'Fixed' || Number(row.amount) > 0
}

/** "₹ 4,999", or "−40% → $ 60" for a percent off. */
export function priceResultLabel(
	row: PriceRow,
	preview: PricePreview | undefined
): string {
	if (!preview?.formatted) return ''
	if (row.price_type === 'Fixed') return preview.formatted
	return `−${Number(row.percent_off) || 0}% → ${preview.formatted}`
}
