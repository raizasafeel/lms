import frappe

from lms.lms.certificate_verification import get_print_format
from lms.lms.doctype.lms_certificate.lms_certificate import get_default_certificate_template
from lms.lms.test_helpers import BaseTestUtils
from lms.www import certificate as certificate_page


class TestCertificatePdfUrl(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self._create_user("frappe@example.com", "Frappe", "Admin", ["Moderator", "Course Creator"])
		course = self._create_course(title="Certificate PDF Course")
		student = self._create_user("cert-pdf@example.com", "Cert", "Pdf", ["LMS Student"])
		self._create_enrollment(student.name, course.name)
		self.certificate = self._create_certificate(course.name, student.name)
		frappe.db.set_single_value("Print Settings", "with_letterhead", 1)
		letter_head = frappe.get_doc(
			{
				"doctype": "Letter Head",
				"letter_head_name": f"Sandbox Letter Head {frappe.generate_hash(length=6)}",
				"source": "HTML",
				"letter_head_for": "DocType",
				"content": "{% set company = frappe._dict() %}<p>{{ company }}</p>",
				"is_default": 1,
			}
		)
		# nosemgrep: lms-unjustified-ignore-permissions - fixture seeding, not the permission under test
		letter_head.insert(ignore_permissions=True)

	def test_the_certificate_renders_under_an_unsafe_default_letter_head(self):
		# Regression: a default letter head using frappe._dict() 500'd the certificate PDF
		# (#3031, fixed in #3039).
		html = frappe.get_print(
			"LMS Certificate", self.certificate.name, self.certificate.template, no_letterhead=1
		)
		self.assertTrue(html)

	def test_a_certificate_that_does_not_exist_is_not_found(self):
		"""Regression: the lookup came back empty and quote(None) raised a TypeError."""
		for certificate_id in ("no-such-certificate", None, ["!=", ""]):
			with self.subTest(certificate_id=certificate_id):
				frappe.form_dict.certificate_id = certificate_id
				with self.assertRaises(frappe.PageDoesNotExistError):
					certificate_page.get_context(frappe._dict())

	def test_a_certificate_without_a_template_uses_the_default_one(self):
		self.certificate.db_set("template", "")

		self.assertEqual(get_print_format(self.certificate), get_default_certificate_template())
