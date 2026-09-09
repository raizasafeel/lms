# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class LMSJobApplication(Document):
	def validate(self):
		self.validate_duplicate()

	def after_insert(self):
		job_owner = frappe.get_value("Job Opportunity", self.job, "owner")
		if job_owner:
			frappe.share.add_docshare("LMS Job Application", self.name, job_owner, read=1)

	def validate_duplicate(self):
		if frappe.db.exists("LMS Job Application", {"job": self.job, "user": self.user}):
			frappe.throw(_("You have already applied for this job."))
