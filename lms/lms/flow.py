import re

import frappe

from lms.lms.utils import LMS_ROLES

LEARNER_ROLE = "LMS Student"
STAFF_ROLES = {*LMS_ROLES, "System Manager"} - {LEARNER_ROLE}
# The event the LMS pages of the user Flow acts for listen to.
FLOW_CHANGE_EVENT = "lms_flow_change"
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


def is_flow_request() -> bool:
	"""Whether Flow's agent is acting for the user in this request (frappe.auth.set_agent)."""
	agent = frappe.session.data.get("agent") if frappe.session else None
	return bool(agent) and agent.get("via") == "Flow"


def publish_flow_change(doc, method=None):
	"""Tells the open LMS pages of the user Flow acts for which record it changed, so they refresh."""
	if doc.meta.istable or not is_flow_request() or frappe.get_doctype_app(doc.doctype) != "lms":
		return
	frappe.publish_realtime(
		FLOW_CHANGE_EVENT,
		{"doctype": doc.doctype, "name": doc.name, "deleted": method == "on_trash"},
		user=frappe.session.user,
		after_commit=True,
	)
