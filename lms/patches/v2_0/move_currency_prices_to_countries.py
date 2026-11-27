import frappe
from frappe.geo.country_info import get_all as get_all_country_info

PRICE_VALUES = ("price_type", "amount", "currency", "percent_off")


def execute():
	"""Each currency's price row becomes a row for every country paying in that currency.

	A percent off row now takes its percent off the regular price, in the regular currency."""
	rows = frappe.get_all(
		"LMS Price",
		filters={"country": ["is", "not set"], "currency": ["is", "set"]},
		fields=["name", "parenttype", "parent", "parentfield", *PRICE_VALUES],
		order_by="idx",
	)
	for row in rows:
		add_country_rows(row)
		frappe.db.delete("LMS Price", row.name)
	enable_country_prices()


def add_country_rows(row: dict) -> None:
	parent = {"parenttype": row.parenttype, "parent": row.parent}
	taken = set(frappe.get_all("LMS Price", filters={**parent, "country": ["is", "set"]}, pluck="country"))
	idx = frappe.db.count("LMS Price", parent)
	values = {field: row[field] for field in PRICE_VALUES}
	if values["price_type"] != "Fixed":
		values["currency"] = None

	for country in get_currency_countries(row.currency):
		if country in taken:
			continue
		idx += 1
		frappe.get_doc(
			{
				"doctype": "LMS Price",
				**parent,
				"parentfield": row.parentfield,
				"idx": idx,
				"country": country,
				**values,
			}
		).db_insert()


def get_currency_countries(currency: str) -> list:
	known = set(frappe.get_all("Country", pluck="name"))
	return sorted(
		country
		for country, info in get_all_country_info().items()
		if info.get("currency") == currency and country in known
	)


def enable_country_prices() -> None:
	"""Turn subsidized pricing on wherever prices were already set, so buyers see no change."""
	for doctype in ("LMS Course", "LMS Batch"):
		names = frappe.get_all("LMS Price", filters={"parenttype": doctype}, pluck="parent", distinct=True)
		if names:
			frappe.db.set_value(
				doctype, {"name": ["in", names]}, "enable_country_prices", 1, update_modified=False
			)
