import type { LMSPrice } from '@/types/lms/LMSPrice'

export type PriceRow = Pick<
	LMSPrice,
	'name' | 'currency' | 'price_type' | 'amount' | 'percent_off'
>

/** What `lms.lms.api.get_price_previews` returns for one row. */
export interface PricePreview {
	currency: string
	amount?: number
	formatted?: string
	error?: string
}

export const PRICE_TYPES: { label: string; value: PriceRow['price_type'] }[] = [
	{ label: __('Fixed'), value: 'Fixed' },
	{ label: __('% off'), value: 'Percent Off' },
]

/** A row's value: its amount, or its percent off. */
export function rowValue(row: PriceRow): number | undefined {
	return row.price_type === 'Fixed' ? row.amount : row.percent_off
}

/** The row with `value` in the field its type uses, and the other one cleared. */
export function withRowValue(row: PriceRow, value: number): PriceRow {
	return row.price_type === 'Fixed'
		? { ...row, amount: value, percent_off: 0 }
		: { ...row, percent_off: value, amount: 0 }
}

/** Rows the server can price: a currency, and a value for a fixed one. */
export function isPriceable(row: PriceRow): boolean {
	if (!row.currency) return false
	return row.price_type !== 'Fixed' || Number(row.amount) > 0
}

/** "₹ 4,999", or "−40% → ₹ 3,210" for a percent off. */
export function priceResultLabel(
	row: PriceRow,
	preview: PricePreview | undefined
): string {
	if (!preview?.formatted) return ''
	if (row.price_type === 'Fixed') return preview.formatted
	return `−${Number(row.percent_off) || 0}% → ${preview.formatted}`
}
