# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

from lms.lms.utils import has_moderator_role


class LMSCertificateEvaluation(Document):
	def validate(self):
		self.validate_rating()

	def validate_rating(self):
		if self.status not in ["Pending", "In Progress"] and self.rating == 0:
			frappe.throw(_("Rating cannot be 0"))


def has_website_permission(doc, ptype, user, verbose=False):
	if has_moderator_role() or doc.member == frappe.session.user:
		return True
	return False


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if has_moderator_role(user):
		return True
	if ptype == "create":
		return True
	if doc.is_new():
		return True
	# Compare against the PERSISTED evaluator, not doc.evaluator: for write/delete this
	# hook runs after the caller's own in-memory edits are applied (e.g. doc.evaluator =
	# attacker.email; doc.save()), so checking doc.evaluator would let an attacker
	# reassign themselves as evaluator and pass their own check.
	current_evaluator = frappe.db.get_value(doc.doctype, doc.name, "evaluator")
	return current_evaluator == user


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if has_moderator_role(user):
		return None
	return f"""(`tabLMS Certificate Evaluation`.evaluator = {frappe.db.escape(user)})"""


@frappe.whitelist()
def create_lms_certificate(source_name: str, target_doc: dict = None):
	if not isinstance(source_name, str):
		frappe.throw(_("source_name must be a string"))
	if target_doc is not None and not isinstance(target_doc, dict):
		frappe.throw(_("target_doc must be a dict"))

	if not frappe.db.exists("LMS Certificate Evaluation", source_name) or not frappe.has_permission(
		"LMS Certificate Evaluation", "read", doc=source_name
	):
		frappe.logger("lms.security").warning(
			"Unauthorized certificate issuance attempt: user=%s source_name=%s",
			frappe.session.user,
			source_name,
		)
		frappe.throw(_("You are not authorized to issue this certificate."), frappe.PermissionError)

	doc = get_mapped_doc(
		"LMS Certificate Evaluation",
		source_name,
		{"LMS Certificate Evaluation": {"doctype": "LMS Certificate"}},
		target_doc,
	)
	return doc
