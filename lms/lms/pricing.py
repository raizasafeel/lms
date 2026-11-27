import frappe
from frappe import _
from frappe.utils import flt, fmt_money, rounded

FALLBACK_CURRENCY = "USD"
FIXED = "Fixed"
PRICE_FIELDS = ["country", "price_type", "amount", "currency", "percent_off"]


def get_primary_currency() -> str:
	"""The currency new courses and batches are priced in."""
	return frappe.db.get_single_value("LMS Settings", "default_currency") or FALLBACK_CURRENCY


def get_price(doctype: str, name: str, amount: float, currency: str, country: str | None = None) -> tuple:
	"""The amount and currency a buyer billed in `country` pays for a course or batch.

	With subsidized pricing on, the price row for the buyer's country wins; otherwise
	the regular price. `country` defaults to the session user's billing country."""
	from lms.lms.utils import get_billing_country

	if not frappe.db.get_value(doctype, name, "enable_country_prices"):
		return amount, currency
	country = get_billing_country(country)
	if not country:
		return amount, currency

	row = frappe.db.get_value(
		"LMS Price",
		{"parenttype": doctype, "parent": name, "parentfield": "prices", "country": country},
		PRICE_FIELDS,
		as_dict=True,
	)
	if not row:
		return amount, currency
	return get_row_price(row, amount, currency)


def get_display_price(
	doctype: str, name: str, amount: float, currency: str, country: str | None = None
) -> frappe._dict:
	"""The buyer's price, formatted, and the regular price when theirs differs."""
	price, price_currency = get_price(doctype, name, amount, currency, country)
	is_regular = (flt(price), price_currency) == (flt(amount), currency)
	return frappe._dict(
		amount=price,
		currency=price_currency,
		price=fmt_money(price, 0, price_currency),
		regular_price=None if is_regular else fmt_money(amount, 0, currency),
	)


def get_row_price(row: dict, amount: float, currency: str) -> tuple:
	"""A row's fixed amount and currency, or the regular price less its percent."""
	if row.get("price_type") == FIXED:
		return flt(row.get("amount")), row.get("currency") or currency
	discounted = flt(amount) * (100 - flt(row.get("percent_off"))) / 100
	return round_for_currency(discounted, currency), currency


def get_price_preview(row: dict, amount: float, currency: str) -> dict:
	"""A row's price, formatted, for the pricing editor."""
	value, value_currency = get_row_price(row, amount, currency)
	return {
		"country": row.get("country"),
		"amount": value,
		"currency": value_currency,
		"formatted": fmt_money(value, 0, value_currency),
	}


def round_for_currency(amount: float, currency: str) -> float:
	"""Whole units, or multiples of the currency's smallest fraction when that is coarser."""
	fraction = flt(frappe.get_cached_value("Currency", currency, "smallest_currency_fraction_value"))
	step = max(fraction, 1)
	return flt(rounded(amount / step) * step)


def validate_prices(doc, currency: str | None) -> None:
	"""One row per country, each with a usable value."""
	seen = set()
	for row in doc.get("prices") or []:
		if row.country in seen:
			frappe.throw(_("Row {0}: {1} has more than one price.").format(row.idx, row.country))
		seen.add(row.country)
		validate_price_row(row, currency)


def validate_price_row(row, currency: str | None) -> None:
	if row.price_type == FIXED:
		row.percent_off = 0
		row.currency = row.currency or currency
		if flt(row.amount) <= 0:
			frappe.throw(_("Row {0}: the price for {1} must be more than zero.").format(row.idx, row.country))
		return

	row.amount = 0
	row.currency = None
	if not 0 <= flt(row.percent_off) < 100:
		frappe.throw(_("Row {0}: the percent off must be from 0 to less than 100.").format(row.idx))
