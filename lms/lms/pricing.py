import functools

import frappe
import requests
from frappe import _
from frappe.geo.country_info import get_all as get_all_country_info
from frappe.utils import flt, fmt_money, rounded

FALLBACK_CURRENCY = "USD"
FIXED = "Fixed"
PERCENT_OFF = "Percent Off"
PRICE_FIELDS = ["currency", "price_type", "amount", "percent_off"]
EXCHANGE_RATE_TTL = 6 * 60 * 60


def get_primary_currency() -> str:
	"""The currency new courses and batches are priced in."""
	return frappe.db.get_single_value("LMS Settings", "default_currency") or FALLBACK_CURRENCY


def get_price(doctype: str, name: str, amount: float, currency: str, country: str | None = None) -> tuple:
	"""The amount and currency a buyer billed in `country` pays for a course or batch.

	A price row in the currency of the buyer's country wins; otherwise the primary price.
	`country` defaults to the session user's billing country."""
	from lms.lms.utils import get_billing_country

	buyer_currency = get_country_currency(get_billing_country(country))
	if not buyer_currency or buyer_currency == currency:
		return amount, currency

	row = frappe.db.get_value(
		"LMS Price",
		{"parenttype": doctype, "parent": name, "parentfield": "prices", "currency": buyer_currency},
		PRICE_FIELDS,
		as_dict=True,
	)
	if not row:
		return amount, currency
	return get_row_amount(row, amount, currency), row.currency


def get_row_amount(row: dict, amount: float, currency: str) -> float:
	"""A row's price: its fixed amount, or the converted primary price less its percent."""
	if row.get("price_type") == FIXED:
		return flt(row.get("amount"))

	converted = flt(amount) * get_current_exchange_rate(currency, row.get("currency"))
	return round_for_currency(converted * (100 - flt(row.get("percent_off"))) / 100, row.get("currency"))


def get_price_preview(row: dict, amount: float, currency: str) -> dict:
	"""A row's price, formatted, or why it has none yet."""
	try:
		value = get_row_amount(row, amount, currency)
	except frappe.ValidationError as error:
		frappe.clear_last_message()
		return {"currency": row.get("currency"), "error": str(error)}
	return {
		"currency": row.get("currency"),
		"amount": value,
		"formatted": fmt_money(value, 0, row.get("currency")),
	}


def round_for_currency(amount: float, currency: str) -> float:
	"""Whole units, or multiples of the currency's smallest fraction when that is coarser."""
	fraction = flt(frappe.get_cached_value("Currency", currency, "smallest_currency_fraction_value"))
	step = max(fraction, 1)
	return flt(rounded(amount / step) * step)


def get_country_currency(country: str | None) -> str | None:
	return get_country_currencies().get(country) if country else None


@functools.cache
def get_country_currencies() -> dict:
	return {country: info.get("currency") for country, info in get_all_country_info().items()}


def get_current_exchange_rate(source: str, target: str) -> float:
	key = f"lms:exchange_rate:{source}:{target}"
	rate = frappe.cache.get_value(key)
	if not rate:
		rate = fetch_exchange_rate(source, target)
		frappe.cache.set_value(key, rate, expires_in_sec=EXCHANGE_RATE_TTL)
	return rate


def fetch_exchange_rate(source: str, target: str) -> float:
	try:
		response = requests.get(
			"https://api.frankfurter.app/latest", params={"from": source, "to": target}, timeout=10
		)
		rate = response.json().get("rates", {}).get(target) if response.ok else None
	except requests.RequestException:
		rate = None
	if not rate:
		frappe.throw(_("No exchange rate from {0} to {1} is available.").format(source, target))
	return flt(rate)


def validate_prices(doc, primary_currency: str | None) -> None:
	"""One row per currency, none in the primary currency, each with a usable value."""
	seen = set()
	for row in doc.get("prices") or []:
		if row.currency == primary_currency:
			frappe.throw(
				_("Row {0}: {1} is already the primary price's currency.").format(row.idx, row.currency)
			)
		if row.currency in seen:
			frappe.throw(_("Row {0}: {1} has more than one price.").format(row.idx, row.currency))
		seen.add(row.currency)
		validate_price_row(row, primary_currency)


def validate_price_row(row, primary_currency: str | None) -> None:
	if row.price_type == FIXED:
		row.percent_off = 0
		if flt(row.amount) <= 0:
			frappe.throw(_("Row {0}: the price in {1} must be more than zero.").format(row.idx, row.currency))
		return

	row.amount = 0
	if not 0 <= flt(row.percent_off) < 100:
		frappe.throw(_("Row {0}: the percent off must be from 0 to less than 100.").format(row.idx))
	if not primary_currency:
		frappe.throw(_("Set the primary price's currency before a percent off price."))
	get_current_exchange_rate(primary_currency, row.currency)
