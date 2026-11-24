import frappe
from frappe import _

from lms.lms.code_runner import DEFAULT_RUNNER_URL

# Integration switches stored on LMS Settings. Google and Raven keep their own.
SETTINGS_FLAGS = {
	"google_calendar": "send_calendar_invite_for_evaluations",
	"google_meet": "enable_google_meet",
	"zoom": "enable_zoom",
	"zoom_attendance": "track_zoom_attendance",
	"code_runner": "enable_code_runner",
	"unsplash": "enable_unsplash",
}

LABELS = {
	"google_calendar": "Google Calendar",
	"google_meet": "Google Meet",
	"zoom": "Zoom",
	"code_runner": "Code runner",
	"unsplash": "Unsplash",
}

CONFERENCING_INTEGRATIONS = {
	"LMS Zoom Settings": "zoom",
	"LMS Google Meet Settings": "google_meet",
}

MANAGER_ROLES = ["Moderator", "System Manager"]


def is_integration_enabled(key: str) -> bool:
	return bool(frappe.db.get_single_value("LMS Settings", SETTINGS_FLAGS[key]))


def check_integration_enabled(key: str):
	if not is_integration_enabled(key):
		frappe.throw(
			_("{0} is turned off. Turn it on in Settings > Integrations.").format(_(LABELS[key])),
			title=_("Integration turned off"),
		)


def check_conferencing_enabled(account_doctype: str):
	check_integration_enabled(CONFERENCING_INTEGRATIONS[account_doctype])


def is_zoom_attendance_tracked() -> bool:
	return is_integration_enabled("zoom") and is_integration_enabled("zoom_attendance")


@frappe.whitelist()
def get_integration_status() -> dict:
	"""Every integration's on/off state and the counts its card reports."""
	frappe.only_for(MANAGER_ROLES)
	settings = frappe.get_cached_doc("LMS Settings")
	apps = frappe.get_active_apps()
	return {
		"google": get_google_status(),
		"google_calendar": {
			"enabled": bool(settings.send_calendar_invite_for_evaluations),
			**get_calendar_counts(),
		},
		"google_meet": {
			"enabled": bool(settings.enable_google_meet),
			"accounts": frappe.db.count("LMS Google Meet Settings"),
		},
		"zoom": {
			"enabled": bool(settings.enable_zoom),
			"attendance": bool(settings.track_zoom_attendance),
			"accounts": frappe.db.count("LMS Zoom Settings"),
		},
		"code_runner": {
			"enabled": bool(settings.enable_code_runner),
			"own_server": (settings.livecode_url or DEFAULT_RUNNER_URL).rstrip("/") != DEFAULT_RUNNER_URL,
		},
		"unsplash": {
			"enabled": bool(settings.enable_unsplash),
			"has_key": bool(settings.unsplash_access_key),
		},
		"raven": get_raven_status(apps),
		"frappe_meet": {"installed": "meet" in apps},
	}


def get_google_status() -> dict:
	settings = frappe.get_cached_doc("Google Settings")
	return {
		"enabled": bool(settings.enable),
		"has_credentials": bool(settings.client_id and settings.client_secret),
		"permitted": bool(frappe.has_permission("Google Settings", "write")),
	}


def get_calendar_counts() -> dict:
	"""Calendars, and how many still lack Google's consent. Counted only for a user who may read them."""
	if not frappe.has_permission("Google Calendar", "read"):
		return {"calendars": 0, "need_access": 0}
	calendars = frappe.get_all("Google Calendar", pluck="name")
	if not calendars:
		return {"calendars": 0, "need_access": 0}
	auth = frappe.qb.Table("__Auth")
	authorized = (
		frappe.qb.from_(auth)
		.select(auth.name)
		.where(auth.doctype == "Google Calendar")
		.where(auth.fieldname == "refresh_token")
		.where(auth.name.isin(calendars))
		.run(pluck=True)
	)
	return {"calendars": len(calendars), "need_access": len(calendars) - len(set(authorized))}


def get_raven_status(apps: list[str]) -> dict:
	installed = {"raven": "raven" in apps, "raven_integration": "raven_integration" in apps}
	enabled = all(installed.values()) and bool(
		frappe.db.get_single_value("Raven Membership Settings", "enabled")
	)
	return {**installed, "enabled": enabled}


@frappe.whitelist(methods=["POST"])
def set_integrations_enabled(changes: dict):
	"""Turn integrations on or off. Google is written before LMS Settings, whose
	calendar switch validates against it."""
	frappe.only_for(MANAGER_ROLES)
	unknown = set(changes) - {*SETTINGS_FLAGS, "google", "raven"}
	if unknown:
		frappe.throw(_("Unknown integration: {0}").format(", ".join(sorted(unknown))))

	if "google" in changes:
		google = frappe.get_doc("Google Settings")
		google.enable = 1 if changes["google"] else 0
		google.save()

	if "raven" in changes:
		set_raven_enabled(bool(changes["raven"]))

	flags = {
		SETTINGS_FLAGS[key]: 1 if value else 0 for key, value in changes.items() if key in SETTINGS_FLAGS
	}
	if flags:
		settings = frappe.get_doc("LMS Settings")
		settings.update(flags)
		settings.save()

	return get_integration_status()


def set_raven_enabled(enabled: bool):
	if not enabled:
		frappe.throw(_("Raven membership sync can't be turned off once it is on."))
	if not get_raven_status(frappe.get_active_apps())["raven_integration"]:
		frappe.throw(_("Install the Raven integration app first."))

	from raven_integration.api import enable_integration

	enable_integration()
