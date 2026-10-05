import frappe


def execute():
	"""Moderator manages members through lms.lms.api, so it keeps only read/select on User."""
	rows = frappe.get_all("Custom DocPerm", {"parent": "User", "role": "Moderator"}, pluck="name")
	for name in rows:
		frappe.db.set_value("Custom DocPerm", name, {"write": 0, "create": 0, "delete": 0})
	if rows:
		frappe.clear_cache(doctype="User")
