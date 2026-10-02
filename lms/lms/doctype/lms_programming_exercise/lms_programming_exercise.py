# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from lms.lms.doctype.lms_content_author.lms_content_author import AuthoredDocument
from lms.lms.lesson_assessments import refuse_assessment_merge, rename_assessment_in_lessons
from lms.lms.utils import generate_slug


class LMSProgrammingExercise(AuthoredDocument, Document):
	def autoname(self):
		# See LMSAssignment.autoname. Older exercises keep their hash names.
		if not self.name:
			self.name = generate_slug(self.title, "LMS Programming Exercise", reserved=frozenset({"new"}))

	def validate(self):
		self.validate_test_cases()

	def before_rename(self, old, new, merge=False):
		refuse_assessment_merge(merge)

	def after_rename(self, old, new, merge=False):
		rename_assessment_in_lessons(self.doctype, old, new)

	def validate_test_cases(self):
		if not self.test_cases:
			frappe.throw(_("At least one test case is required for the programming exercise."))
