import frappe

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
