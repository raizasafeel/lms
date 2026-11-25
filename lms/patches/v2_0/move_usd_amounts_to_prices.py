import frappe

PRICED_DOCTYPES = ("LMS Course", "LMS Batch")
REMOVED_SETTINGS = ("show_usd_equivalent", "exception_country", "apply_rounding", "rounding_step")


def execute():
	"""An explicit USD amount becomes a fixed USD price row, unless the primary price is already USD."""
	for doctype in PRICED_DOCTYPES:
		if frappe.db.has_column(doctype, "amount_usd"):
			move_usd_amounts(doctype)

	frappe.db.delete("Singles", {"doctype": "LMS Settings", "field": ["in", REMOVED_SETTINGS]})
	frappe.db.delete("Payment Country", {"parenttype": "LMS Settings"})


def move_usd_amounts(doctype: str) -> None:
	table = frappe.qb.DocType(doctype)
	rows = (
		frappe.qb.from_(table)
		.select(table.name, table.amount_usd)
		.where((table.amount_usd > 0) & (table.currency != "USD"))
	).run(as_dict=True)

	for row in rows:
		if has_usd_price(doctype, row.name):
			continue
		frappe.get_doc(
			{
				"doctype": "LMS Price",
				"parenttype": doctype,
				"parent": row.name,
				"parentfield": "prices",
				"idx": frappe.db.count("LMS Price", {"parenttype": doctype, "parent": row.name}) + 1,
				"currency": "USD",
				"price_type": "Fixed",
				"amount": row.amount_usd,
			}
		).db_insert()


def has_usd_price(doctype: str, name: str) -> bool:
	return bool(frappe.db.exists("LMS Price", {"parenttype": doctype, "parent": name, "currency": "USD"}))
