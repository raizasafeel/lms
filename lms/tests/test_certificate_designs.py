import base64
from unittest.mock import patch

import frappe

from lms.lms.certificate_designs import (
	DESIGNS,
	TEXT_SIZES,
	get_certificate_context,
	get_certificate_font_css,
	get_text_sizes,
	join_names,
)
from lms.lms.test_helpers import BaseTestUtils


class CertificateFixture(BaseTestUtils):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		suffix = frappe.generate_hash(length=6).lower()
		cls.instructors = [
			cls._create_user(f"ctx-inst-{i}-{suffix}@example.com", f"Teacher{i}", "Ctx", ["Course Creator"])
			for i in range(5)
		]
		cls.member = cls._create_user(
			f"ctx-member-{suffix}@example.com", "Maya", "Fernandes", ["LMS Student"]
		)
		cls.evaluator = cls._create_user(
			f"ctx-eval-{suffix}@example.com", "Rahul", "Mehta", ["Batch Evaluator"]
		)
		cls._create_evaluator(cls.evaluator.name)
		cls.course = cls._create_course(title=f"Data analysis {suffix}", instructor=cls.instructors[0].name)
		cls.batch = cls._create_batch(
			cls.course.name,
			title=f"Spring cohort {suffix}",
			instructor=cls.instructors[1].name,
			evaluator=cls.evaluator.name,
		)

	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("System Settings", "language", "en")
		frappe.db.set_single_value("Website Settings", "app_name", "Northwind Academy")
		frappe.db.set_single_value("Website Settings", "banner_image", "/files/northwind.png")

	def certificate(self, **values):
		doc = frappe.new_doc("LMS Certificate")
		doc.update(
			{
				"member": self.member.name,
				"member_name": "Maya Fernandes",
				"course": self.course.name,
				"course_title": self.course.title,
				"issue_date": "2026-08-12",
				**values,
			}
		)
		return doc

	def set_course_instructors(self, count):
		course = frappe.get_doc("LMS Course", self.course.name)
		course.instructors = []
		for user in self.instructors[:count]:
			course.append("instructors", {"instructor": user.name})
		course.save()


class TestCertificateContext(CertificateFixture):
	def test_a_course_certificate_carries_what_every_design_prints(self):
		doc = self.certificate()
		doc.name = "8f3k2q9a1c"
		context = get_certificate_context(doc, "modern")
		self.assertEqual(context.name, "Maya Fernandes")
		self.assertEqual(context.title, self.course.title)
		self.assertEqual(context.kind, "course")
		self.assertEqual(context.completed, "has completed the course")
		self.assertEqual(context.site_name, "Northwind Academy")
		self.assertTrue(context.logo.endswith("/files/northwind.png"))
		self.assertEqual(context.issued, "12 August 2026")
		self.assertEqual(context.expires, "")
		self.assertEqual(context.certificate_id, "8f3k2q9a1c")
		self.assertTrue(context.verify_url.endswith("/certificates/8f3k2q9a1c"))
		self.assertNotIn("://", context.verify_short)
		self.assertEqual(context.direction, "ltr")

	def test_the_qr_code_encodes_the_verification_url(self):
		doc = self.certificate()
		doc.name = "8f3k2q9a1c"
		context = get_certificate_context(doc, "classic")
		prefix = "data:image/svg+xml;base64,"
		self.assertTrue(context.qr_code.startswith(prefix))
		svg = base64.b64decode(context.qr_code[len(prefix) :]).decode()
		self.assertIn("<svg", svg)
		self.assertIn("viewBox", svg)

	def test_an_unsaved_certificate_prints_a_sample_id(self):
		context = get_certificate_context(self.certificate(), "classic")
		self.assertEqual(context.certificate_id, "SAMPLE0000")

	def test_a_batch_certificate_says_batch(self):
		doc = self.certificate(course=None, course_title=None, batch_name=self.batch.name)
		context = get_certificate_context(doc, "classic")
		self.assertEqual(context.kind, "batch")
		self.assertEqual(context.title, self.batch.title)
		self.assertEqual(context.completed, "has completed the batch")
		self.assertEqual(context.people_names, "Teacher1 Ctx")

	def test_instructors_are_listed_with_and(self):
		cases = ((1, "Teacher0 Ctx", "Instructor"), (2, "Teacher0 Ctx and Teacher1 Ctx", "Instructors"))
		for count, names, label in cases:
			with self.subTest(count=count):
				self.set_course_instructors(count)
				context = get_certificate_context(self.certificate(), "classic")
				self.assertEqual(context.people_names, names)
				self.assertEqual(context.people_label, label)
				self.assertEqual(context.people_line, f"Taught by {names}")

	def test_no_more_than_four_instructors_are_printed(self):
		self.set_course_instructors(5)
		context = get_certificate_context(self.certificate(), "classic")
		self.assertEqual(len(context.people), 4)
		self.assertEqual(context.people_names, "Teacher0 Ctx, Teacher1 Ctx, Teacher2 Ctx and Teacher3 Ctx")

	def test_an_evaluator_replaces_the_instructors(self):
		doc = self.certificate(evaluator=self.evaluator.name, evaluator_name="Rahul Mehta")
		context = get_certificate_context(doc, "classic")
		self.assertEqual(context.people, ["Rahul Mehta"])
		self.assertEqual(context.people_label, "Evaluator")
		self.assertEqual(context.people_line, "Evaluated by Rahul Mehta")

	def test_expiry_prints_only_when_set(self):
		context = get_certificate_context(self.certificate(expiry_date="2028-05-30"), "classic")
		self.assertEqual(context.expires, "30 May 2028")

	def test_a_site_without_a_logo_prints_no_logo(self):
		frappe.db.set_single_value("Website Settings", "banner_image", None)
		self.assertEqual(get_certificate_context(self.certificate(), "classic").logo, "")

	def test_an_arabic_site_prints_right_to_left_in_arabic(self):
		frappe.db.set_single_value("System Settings", "language", "ar")
		with patch("lms.lms.certificate_designs._", side_effect=lambda msg, lang=None: f"[{lang}]{msg}"):
			context = get_certificate_context(self.certificate(), "classic")
		self.assertEqual(context.direction, "rtl")
		self.assertEqual(context.lang, "ar")
		self.assertEqual(context.labels.heading, "[ar]Certificate of completion")
		self.assertNotIn("August", context.issued)

	def test_arabic_lists_use_the_arabic_comma(self):
		self.assertEqual(join_names(["أ", "ب", "ج"], "ar").count("، "), 1)

	def test_names_step_down_in_size_and_are_never_cut(self):
		for design in DESIGNS:
			with self.subTest(design=design):
				name_steps = TEXT_SIZES[design][0]
				shortest, longest = name_steps[0], name_steps[-1]
				self.assertEqual(get_text_sizes(design, "x" * shortest[0], "")[0], shortest[1])
				self.assertEqual(get_text_sizes(design, "x" * (shortest[0] + 1), "")[0], name_steps[1][1])
				self.assertEqual(get_text_sizes(design, "x" * 400, "")[0], longest[1])

	def test_a_long_name_is_printed_whole(self):
		name = "Maximiliana Alexandra Wójcik-Fitzgerald Okonkwo"
		self.assertEqual(get_certificate_context(self.certificate(member_name=name), "modern").name, name)

	def test_bundled_fonts_are_inlined_for_each_family(self):
		for family, faces in (("sans", 5), ("serif", 6)):
			with self.subTest(family=family):
				css = get_certificate_font_css(family)
				self.assertEqual(css.count("@font-face"), faces)
				self.assertEqual(css.count("data:font/woff;base64,"), faces)
				self.assertNotIn("http", css)

	def test_the_issue_date_is_required_only_to_print_it(self):
		self.assertEqual(get_certificate_context(self.certificate(issue_date=None), "classic").issued, "")

