import re

import frappe

from lms.lms.utils import LMS_ROLES

LEARNER_ROLE = "LMS Student"
STAFF_ROLES = {*LMS_ROLES, "System Manager"} - {LEARNER_ROLE}
LAUNCHER_SCRIPT = re.compile(r'<script src="[^"]*flow_launcher\.bundle[^"]*"[^>]*></script>')


def is_learner_only(user: str | None = None) -> bool:
	"""A learner holding no staff role in the LMS."""
	roles = set(frappe.get_roles(user))
	return LEARNER_ROLE in roles and not roles & STAFF_ROLES


def is_flow_hidden_for(user: str | None = None) -> bool:
	return bool(frappe.db.get_single_value("LMS Settings", "hide_flow_for_learners")) and is_learner_only(
		user
	)


def is_flow_offered(user: str | None = None) -> bool:
	"""Whether LMS pages carry Flow for this user, on top of Flow's own access check."""
	return bool(frappe.db.get_single_value("LMS Settings", "enable_flow")) and not is_flow_hidden_for(user)


def flow_session_has_permission(doc, ptype=None, user=None) -> bool:
	"""A learner hidden from Flow can't open or start a chat, whatever Flow role they hold."""
	return not is_flow_hidden_for(user)


def remove_launcher(response, request):
	"""Takes the launcher Frappe added (frappe.flow.launcher.add_to_page) back off LMS pages."""
	if (
		request.method != "GET"
		or response.mimetype != "text/html"
		or request.path.split("/")[1] != "lms"
		or is_flow_offered()
	):
		return
	html = response.get_data(as_text=True)
	stripped = LAUNCHER_SCRIPT.sub("", html)
	if stripped != html:
		response.set_data(stripped)
