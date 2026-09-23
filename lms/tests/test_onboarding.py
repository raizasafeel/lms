# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

"""Tests for lms/lms/onboarding.py: which course the checklist opens."""

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from lms.lms import onboarding


class TestFirstOwnCourse(UnitTestCase):
	def first_own(self, courses, demo=("demo-course",)):
		with (
			patch.object(frappe, "get_all", lambda *a, **k: list(courses)[: k.get("limit")]),
			patch.object(onboarding, "is_demo_course", lambda name: name in demo),
		):
			return onboarding.get_first_own_course()

	def test_skips_the_demo_course(self):
		# The seeder runs at setup, so on a fresh site the demo is the oldest.
		self.assertEqual(self.first_own(["demo-course", "my-course"]), "my-course")

	def test_is_the_oldest_when_there_is_no_demo(self):
		self.assertEqual(self.first_own(["my-course", "later-course"]), "my-course")

	def test_is_nothing_when_only_the_demo_exists(self):
		self.assertIsNone(self.first_own(["demo-course"]))

	def test_is_nothing_on_an_empty_site(self):
		self.assertIsNone(self.first_own([]))
