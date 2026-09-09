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
# The write is privileged, so this is the only thing bounding how often a
# listing can be re-reported. Each report also overwrites the last, so an
# unlimited endpoint lets one caller erase everyone else's reason.
@rate_limit(key="job", limit=5, seconds=60 * 60)
def report(job: str, reason: str):
	# frappe's whitelist argument coercion is switched off in several run modes, so
	# an annotated signature is not an input check. These stay explicit.
	if not isinstance(job, str) or not isinstance(reason, str):
		frappe.throw(_("job and reason must be strings"))

	reason = reason.strip()
	if not reason:
		frappe.throw(_("Reason is required"))
	if len(reason) > REPORT_REASON_MAX_LENGTH:
		frappe.throw(_("Reason must be under {0} characters").format(REPORT_REASON_MAX_LENGTH))

	doc = frappe.get_doc("Job Opportunity", job)

	# Deliberately privileged. report() exists so a non-owner can flag someone
	# else's listing, so a has_permission check on the target would defeat the
	# feature it guards.

	# What bounds it instead: the endpoint is not allow_guest, both report fields
	# are read_only, reported_by is always frappe.session.user, and reason is
	# rejected above if empty or too long.
	doc.db_set("reported_by", frappe.session.user, update_modified=False)
	doc.db_set("report_reason", reason, update_modified=False)
	doc.reload()
	doc.run_method("lms_notify")
