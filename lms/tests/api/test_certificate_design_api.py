import json

import frappe
from frappe.exceptions import FrappeTypeError

from lms.lms.api import (
	get_certificate_designs,
	get_certificate_template_default,
	preview_certificate_template,
)
from lms.lms.doctype.lms_certificate import lms_certificate as cert_module
from lms.lms.doctype.lms_certificate.lms_certificate import (
	get_certificate_template,
	get_default_certificate_template,
)
from lms.lms.test_helpers import BaseTestUtils


class DesignFixture(BaseTestUtils):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		suffix = frappe.generate_hash(length=6).lower()
		cls.author = cls._create_user(
			f"design-author-{suffix}@example.com", "Ada", "Author", ["Course Creator"]
		)
		cls.other_creator = cls._create_user(
			f"design-other-{suffix}@example.com", "Otto", "Other", ["Course Creator"]
		)
		cls.student = cls._create_user(
			f"design-student-{suffix}@example.com", "Sam", "Student", ["LMS Student"]
		)
		cls.evaluator = cls._create_user(
			f"design-eval-{suffix}@example.com", "Eve", "Evaluator", ["Batch Evaluator"]
		)
		cls._require_no_moderators(cls.author.name, cls.other_creator.name, cls.student.name)
		cls.course = cls._create_course(title=f"Design Course {suffix}", instructor=cls.author.name)

	def setUp(self):
		super().setUp()
		frappe.db.set_value("Print Format", "Certificate Modern", "disabled", 0)

	def set_design(self, print_format):
		course = frappe.get_doc("LMS Course", self.course.name)
		course.certificate_template = print_format
		course.save()
		return course

	def make_format(self, doc_type="LMS Certificate", html="<p>{{ doc.member_name }}</p>"):
		print_format = frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": f"Design Test {frappe.generate_hash(length=6)}",
				"doc_type": doc_type,
				"module": "LMS",
				"custom_format": 1,
				"print_format_type": "Jinja",
				"standard": "No",
				"html": html,
			}
		)
		# nosemgrep: lms-unjustified-ignore-permissions - fixture seeding, not the permission under test
		print_format.insert(ignore_permissions=True)
		return print_format.name


class TestCertificateDesignChoice(DesignFixture):
	def test_a_course_can_choose_a_certificate_design(self):
		self.set_design("Certificate Modern")
		self.assertEqual(get_certificate_template(self.course.name), "Certificate Modern")

	def test_an_empty_choice_means_the_site_default(self):
		self.set_design(None)
		self.assertEqual(get_certificate_template(self.course.name), get_default_certificate_template())

	def test_a_course_cannot_choose_a_format_for_another_doctype(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_design(self.make_format(doc_type="User"))

	def test_a_course_cannot_choose_a_disabled_design(self):
		frappe.db.set_value("Print Format", "Certificate Modern", "disabled", 1)
		with self.assertRaises(frappe.ValidationError):
			self.set_design("Certificate Modern")

	def test_a_design_disabled_after_it_was_chosen_falls_back_to_the_default(self):
		self.set_design("Certificate Modern")
		frappe.db.set_value("Print Format", "Certificate Modern", "disabled", 1)
		self.assertEqual(get_certificate_template(self.course.name), get_default_certificate_template())

	def test_a_new_self_issued_certificate_uses_the_course_design(self):
		self.set_design("Certificate Ledger")
		frappe.db.set_value("LMS Course", self.course.name, "enable_certification", 1)
		enrollment = self._create_enrollment(self.student.name, self.course.name)
		frappe.db.set_value("LMS Enrollment", enrollment.name, "progress", 100)
		frappe.set_user(self.student.name)
		certificate = cert_module.create_certificate(self.course.name)
		self.assertEqual(certificate.template, "Certificate Ledger")

	def test_changing_the_course_design_leaves_issued_certificates_alone(self):
		enrollment = self._create_enrollment(self.student.name, self.course.name)
		frappe.db.set_value("LMS Enrollment", enrollment.name, "progress", 100)
		issued = self._create_certificate(self.course.name, self.student.name)
		self.set_design("Certificate Banner")
		self.assertNotEqual(
			frappe.db.get_value("LMS Certificate", issued.name, "template"), "Certificate Banner"
		)

	def test_a_certificate_cannot_switch_to_a_format_for_another_doctype(self):
		self._create_enrollment(self.student.name, self.course.name)
		certificate = self._create_certificate(self.course.name, self.student.name)
		certificate.template = self.make_format(doc_type="User")
		with self.assertRaises(frappe.ValidationError):
			certificate.save()

	def test_a_certificate_keeps_a_design_disabled_after_it_was_issued(self):
		self._create_enrollment(self.student.name, self.course.name)
		certificate = self._create_certificate(self.course.name, self.student.name)
		frappe.db.set_value("LMS Certificate", certificate.name, "template", "Certificate Modern")
		frappe.db.set_value("Print Format", "Certificate Modern", "disabled", 1)
		certificate.reload()
		certificate.published = 0
		certificate.save()


class TestPreviewCertificateTemplate(DesignFixture):
	def preview(self, user, print_format="Certificate Classic", sample=None, course=None):
		frappe.set_user(user)
		return preview_certificate_template(print_format, course or self.course.name, sample)

	def test_the_course_author_previews_with_sample_data(self):
		html = self.preview(self.author.name)["html"]
		self.assertIn("Maya Fernandes", html)
		self.assertIn("SAMPLE0000", html)
		self.assertIn(".action-banner{display:none!important}", html)

	def test_a_moderator_previews_any_course(self):
		moderator = self._create_user("design-moderator@example.com", "Mo", "Derator", ["Moderator"])
		self.assertIn("Maya Fernandes", self.preview(moderator.name)["html"])

	def test_callers_who_do_not_author_the_course_are_refused(self):
		for user in ("Guest", self.student.name, self.other_creator.name, self.evaluator.name):
			with self.subTest(user=user), self.assertRaises(frappe.PermissionError):
				self.preview(user)

	def test_the_permission_check_runs_before_input_validation(self):
		with self.assertRaises(frappe.PermissionError):
			self.preview(self.student.name, sample='{"not_an_option": true}')

	def test_sample_options_change_the_render(self):
		cases = (
			({"long": True}, "Maximiliana Alexandra"),
			({"batch": True}, "has completed the batch"),
			({"rtl": True}, 'dir="rtl"'),
		)
		for options, expected in cases:
			with self.subTest(options=options):
				self.assertIn(expected, self.preview(self.author.name, sample=json.dumps(options))["html"])

	def test_no_logo_and_expiry_options(self):
		frappe.db.set_single_value("Website Settings", "banner_image", "/files/design-logo.png")
		html = self.preview(self.author.name, sample=json.dumps({"no_logo": True, "expiry": True}))["html"]
		self.assertNotIn("design-logo.png", html)
		self.assertIn("Valid until", html)

	def test_malformed_sample_options_are_rejected(self):
		for sample in ("not json", "[]", '{"long": "yes"}', '{"script": true}'):
			with self.subTest(sample=sample), self.assertRaises(frappe.ValidationError):
				self.preview(self.author.name, sample=sample)

	def test_only_certificate_designs_can_be_previewed(self):
		for print_format in (self.make_format(doc_type="User"), "No Such Format"):
			with self.subTest(print_format=print_format), self.assertRaises(frappe.ValidationError):
				self.preview(self.author.name, print_format=print_format)

	def test_non_string_input_is_rejected(self):
		frappe.set_user(self.author.name)
		with self.assertRaises(FrappeTypeError):
			preview_certificate_template(["Certificate Classic"], self.course.name)
		with self.assertRaises(frappe.ValidationError):
			preview_certificate_template.__wrapped__(["Certificate Classic"], self.course.name)

	def test_a_custom_design_that_cannot_render_samples_returns_no_html(self):
		broken = self.make_format(html="{{ doc.no_such_field.title() }}")
		self.assertIsNone(self.preview(self.author.name, print_format=broken)["html"])


class TestCertificateTemplateDefault(DesignFixture):
	def test_issuers_get_the_course_design(self):
		self.set_design("Certificate Record")
		for user in (self.evaluator.name, self.author.name):
			with self.subTest(user=user):
				frappe.set_user(user)
				self.assertEqual(get_certificate_template_default(self.course.name), "Certificate Record")

	def test_without_a_course_issuers_get_the_site_default(self):
		frappe.set_user(self.evaluator.name)
		self.assertEqual(get_certificate_template_default(), get_default_certificate_template())

	def test_learners_and_guests_are_refused(self):
		for user in ("Guest", self.student.name):
			with self.subTest(user=user), self.assertRaises(frappe.PermissionError):
				frappe.set_user(user)
				get_certificate_template_default(self.course.name)

	def test_non_string_course_is_rejected(self):
		frappe.set_user(self.evaluator.name)
		with self.assertRaises(frappe.ValidationError):
			get_certificate_template_default.__wrapped__({"name": ["!=", ""]})


class TestCertificateDesignList(DesignFixture):
	def test_issuers_list_enabled_designs_and_the_default(self):
		frappe.db.set_value("Print Format", "Certificate Corners", "disabled", 1)
		frappe.set_user(self.author.name)
		result = get_certificate_designs()
		self.assertIn("Certificate Classic", result["designs"])
		self.assertNotIn("Certificate Corners", result["designs"])
		self.assertEqual(result["default"], get_default_certificate_template())
		self.assertEqual(set(result), {"designs", "default"})

	def test_learners_and_guests_cannot_list_designs(self):
		for user in ("Guest", self.student.name):
			with self.subTest(user=user), self.assertRaises(frappe.PermissionError):
				frappe.set_user(user)
				get_certificate_designs()
