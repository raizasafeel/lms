# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.rate_limiter import rate_limit
from frappe.utils import add_months, getdate, validate_url

from lms.lms.utils import generate_slug, validate_image


class JobOpportunity(Document):
	def validate(self):
		self.validate_urls()
		self.company_logo = validate_image(self.company_logo)

	def validate_urls(self):
		validate_url(self.company_website, True, ["http", "https"])

	def autoname(self):
		if not self.name:
			self.name = generate_slug(f"{self.job_title}-${self.company_name}", "LMS Course")


def update_job_openings():
	old_jobs = frappe.get_all(
		"Job Opportunity",
		filters={"status": "Open", "creation": ["<=", add_months(getdate(), -3)]},
		pluck="name",
	)

	for job in old_jobs:
		frappe.db.set_value("Job Opportunity", job, "status", "Closed")


REPORT_REASON_MAX_LENGTH = 1000


@frappe.whitelist()
# The write is privileged (see below), so the only thing bounding how often a
# listing can be re-reported is this. Each report also overwrites the last, so
# an unlimited endpoint lets one caller erase everyone else's reason.
@rate_limit(key="job", limit=5, seconds=60 * 60)
def report(job: str, reason: str):
	# frappe's whitelist argument coercion is switched off in several run modes
	# (see lms/tests/test_notification_rules.py), so an annotated signature is
	# not an input check -- these stay explicit.
	if not isinstance(job, str) or not isinstance(reason, str):
		frappe.throw(_("job and reason must be strings"))

	reason = reason.strip()
	if not reason:
		frappe.throw(_("Reason is required"))
	if len(reason) > REPORT_REASON_MAX_LENGTH:
		frappe.throw(_("Reason must be under {0} characters").format(REPORT_REASON_MAX_LENGTH))

	doc = frappe.get_doc("Job Opportunity", job)

	# This write is deliberately privileged: report() exists so a NON-owner can
	# flag someone else's listing -- Job Opportunity grants only System
	# Manager full rights and LMS Student if_owner, so a reporter by
	# definition has neither read nor write on the document being reported. A
	# has_permission check on the target document would defeat the feature it
	# guards. What bounds this instead: the endpoint is not allow_guest, so a
	# caller is at least authenticated; report_reason and reported_by are both
	# read_only on the doctype; reported_by is always frappe.session.user,
	# never a caller-supplied value (report()'s signature takes no such
	# argument); and reason is rejected above if empty or over
	# REPORT_REASON_MAX_LENGTH characters, so an unbounded blob cannot be
	# stored and mailed.
	doc.db_set("reported_by", frappe.session.user, update_modified=False)
	doc.db_set("report_reason", reason, update_modified=False)
	doc.reload()
	doc.run_method("lms_notify")
