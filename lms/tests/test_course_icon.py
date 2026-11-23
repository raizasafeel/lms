# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe

from lms.lms.doctype.lms_course.lms_course import COURSE_ICONS
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import get_course_details


class TestCourseIcon(BaseTestUtils):
	"""A course thumbnail icon is one of the allowed lucide names, or empty."""

	def setUp(self):
		super().setUp()
		self.course = self._create_course(title=f"Icon Course {frappe.generate_hash(length=6)}")

	def test_saves_an_allowed_icon(self):
		self.course.icon = "rocket"
		self.course.save()
		self.assertEqual(frappe.db.get_value("LMS Course", self.course.name, "icon"), "rocket")

	def test_rejects_an_unknown_icon(self):
		self.course.icon = "lucide-rocket"
		with self.assertRaises(frappe.ValidationError):
			self.course.save()

	def test_trims_and_allows_empty(self):
		self.course.icon = "  globe "
		self.course.save()
		self.assertEqual(self.course.icon, "globe")
		self.course.icon = ""
		self.course.save()
		self.assertEqual(self.course.icon, "")

	def test_course_details_carry_the_icon(self):
		self.course.icon = COURSE_ICONS[0]
		self.course.save()
		self.assertEqual(get_course_details(self.course.name).icon, COURSE_ICONS[0])
