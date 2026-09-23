"""Finish a Frappe Cloud site's setup for its owner, so they never see the wizard.

A learner-platform trial on Frappe Cloud goes: sign in to Frappe Cloud, pick a
site name, then land on the desk setup wizard, which asks for a language, a
country, a time zone, a currency, and the owner's name and email. Every one of
those Frappe Cloud already knows. When it hands the site over it writes them in
itself, through `initialize_system_settings_and_user`: the team's country and
currency and the signup's time zone onto System Settings, and the team owner as
a System Manager. The wizard then asks the owner to confirm what was just
written, and that screen is the step this module removes.

It completes setup with the values already on the site, in a background job,
the moment Frappe Cloud has written them -- that is, when the owner's user is
saved. By the time the owner opens the site, setup is done.

Frappe Cloud only
-----------------
The app ships the same code to every site on a bench, self-hosted benches
included, so the check has to be per site. `fc_communication_secret` is what
Frappe Cloud writes into a site's own config once the site is active and owned
by a real team; a self-hosted site never has it. Standby sites Frappe Cloud
keeps warm for fast signups have the secret before anyone claims them, which is
why the other gate is the owner's user: a standby site has none until it is
claimed and prefilled.

Nothing is guessed. If a value the wizard needs is missing, or another app on
the site needs wizard input of its own (ERPNext asks for a company), this does
nothing and the owner gets the normal wizard, prefilled as before.

Uses only `setup_complete`, which every supported Frappe version has; the
`setup_wizard_url` / `complete_app_setup` pair that would let an app own the
setup screen exists on develop only, and benches run version-15 and 16 too.
"""

import frappe
from frappe.utils import cint

# Apps whose setup hooks need nothing typed into the wizard. LMS's own hook seeds
# the demo course and reads nothing the wizard collects. Payments, which every
# LMS bench carries, registers no setup hooks at all, so it needs no entry.
APPS_WITHOUT_WIZARD_INPUT = {"frappe", "lms"}

JOB_ID = "lms::complete_frappe_cloud_setup"


def is_frappe_cloud_site() -> bool:
	"""Whether this site is hosted on Frappe Cloud.

	Read straight from site config rather than through
	`frappecloud_billing.is_fc_site`, which also demands the *current* user be
	a System Manager: this runs from a document hook and a login, as whoever.
	"""
	return bool(frappe.conf.get("fc_communication_secret"))


def schedule_setup_completion(doc=None, method=None):
	"""Queue the completion if this site is ready for it.

	Registered on User `on_update`, which is how it hears that Frappe Cloud has
	prefilled the site: the owner's user is the last thing that call writes.
	Also run on login, which catches a site prefilled before this code shipped.

	Returns early on every other save of every other user, cheaply: two config
	reads, then a cached single-value read.
	"""
	try:
		if not is_frappe_cloud_site() or frappe.is_setup_complete():
			return

		if doc is not None and not is_candidate_owner(doc):
			return

		if not get_setup_args():
			return

		frappe.enqueue(
			"lms.frappe_cloud.complete_setup",
			queue="short",
			job_id=JOB_ID,
			deduplicate=True,
			enqueue_after_commit=True,
		)
	except Exception:
		# Setup is still reachable the ordinary way. A failure here must not
		# fail the user save or the login that triggered it.
		frappe.log_error(title="Could not schedule Frappe Cloud setup")


def is_candidate_owner(user) -> bool:
	return (
		user.name not in ("Administrator", "Guest")
		and user.get("user_type") == "System User"
		and cint(user.get("enabled"))
	)


def complete_setup(**kwargs):
	"""Run Frappe's own setup with the values Frappe Cloud already wrote.

	`setup_complete` is the function the wizard's submit button calls, so every
	app's setup hook runs exactly as it would have -- including the LMS one that
	seeds the demo course. In a worker there is no login manager, so Frappe's
	"log in as the new user" step is a no-op rather than a session swap.

	`**kwargs` absorbs the enqueue options older Frappe versions pass through.
	"""
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	if frappe.is_setup_complete():
		return

	args = get_setup_args()
	if not args:
		return

	setup_complete(args)

	from lms import telemetry

	telemetry.capture("setup_wizard_skipped_on_frappe_cloud")


def get_setup_args() -> dict | None:
	"""The wizard's answers, read off the site, or None if any are missing."""
	if not only_input_free_setup_hooks():
		return None

	settings = get_prefilled_settings()
	if not settings or not settings.country or not settings.time_zone:
		return None

	owner = get_prefilled_owner()
	if not owner:
		return None

	language = get_language_name(settings.language)

	return {
		# Both keys, deliberately. Frappe reads `language` to decide whether to
		# switch the site's language and then `lang` to find it, so passing one
		# would set a non-English site's default language to nothing.
		"language": language,
		"lang": language,
		"country": settings.country,
		"timezone": settings.time_zone,
		"currency": settings.currency,
		"full_name": owner.full_name,
		"email": owner.name,
		# The wizard writes this back unconditionally, and a missing value reads
		# as "off". Passing what the site already has leaves the choice where it
		# was, rather than turning usage data off on every site set up this way.
		"enable_telemetry": cint(settings.enable_telemetry),
	}


def get_prefilled_settings():
	"""What Frappe Cloud wrote onto System Settings, plus the telemetry choice."""
	return frappe.db.get_value(
		"System Settings",
		"System Settings",
		["country", "time_zone", "currency", "language", "enable_telemetry"],
		as_dict=True,
	)


def only_input_free_setup_hooks() -> bool:
	"""True when no installed app needs the wizard's own input screens."""
	for app in frappe.get_installed_apps():
		if app in APPS_WITHOUT_WIZARD_INPUT:
			continue
		hooks = frappe.get_hooks(app_name=app)
		if hooks.get("setup_wizard_stages") or hooks.get("setup_wizard_complete"):
			return False
	return True


def get_prefilled_owner():
	"""The System Manager Frappe Cloud created, if it has created one yet."""
	owners = frappe.get_all(
		"User",
		filters={
			"name": ("not in", ("Administrator", "Guest")),
			"user_type": "System User",
			"enabled": 1,
		},
		fields=["name", "full_name"],
		order_by="creation asc",
	)
	for owner in owners:
		if "System Manager" in frappe.get_roles(owner.name):
			return owner
	return None


def get_language_name(code: str | None) -> str:
	"""System Settings stores a code; the wizard speaks in language names."""
	if code:
		name = frappe.db.get_value("Language", code, "language_name")
		if name:
			return name
	return "English"
