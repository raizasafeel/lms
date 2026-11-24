import frappe


def execute():
	"""Keep every integration a site already uses on, now that each has a switch."""
	unsplash_key = frappe.db.get_single_value("LMS Settings", "unsplash_access_key")
	switches = {
		"enable_zoom": frappe.db.exists("LMS Zoom Settings"),
		"track_zoom_attendance": True,
		"enable_google_meet": frappe.db.exists("LMS Google Meet Settings"),
		"enable_code_runner": True,
		"enable_unsplash": unsplash_key,
	}
	for field, enabled in switches.items():
		frappe.db.set_single_value("LMS Settings", field, 1 if enabled else 0)
