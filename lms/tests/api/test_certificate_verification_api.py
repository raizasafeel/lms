from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate
from frappe.website.path_resolver import resolve_redirect
from werkzeug.exceptions import HTTPException

from lms.lms.api import (
	download_certificate_pdf,
	get_certificate,
	get_certification_categories,
	get_certified_participants,
)
from lms.lms.certificate_verification import redirect_raw_certificate_prints
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import get_lms_route
from lms.www import certificate as certificate_page


class CertificateVerificationFixture(BaseTestUtils):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		suffix = frappe.generate_hash(length=6).lower()
		cls.author = cls._create_user(
			f"verify-author-{suffix}@example.com", "Ada", "Author", ["Course Creator"]
		)
		cls.member = cls._create_user(
			f"verify-member-{suffix}@example.com", "Maya", "Fernandes", ["LMS Student"]
		)
		cls.stranger = cls._create_user(
			f"verify-stranger-{suffix}@example.com", "Sam", "Stranger", ["LMS Student"]
		)
		cls._require_no_moderators(cls.member.name, cls.stranger.name)
		cls.course = cls._create_course(title=f"Verify Course {suffix}", instructor=cls.author.name)
		cls._create_enrollment(cls.member.name, cls.course.name)

	def setUp(self):
		super().setUp()
		self.certificate = self._create_certificate(self.course.name, self.member.name)

	def set_certificate(self, **values):
		frappe.db.set_value("LMS Certificate", self.certificate.name, values)


class TestGetCertificate(CertificateVerificationFixture):
	def test_a_guest_sees_a_published_certificate(self):
		frappe.set_user("Guest")
		details = get_certificate(self.certificate.name)
		self.assertEqual(details["status"], "valid")
		self.assertEqual(details["kind"], "course")
		self.assertEqual(details["title"], self.course.title)
		self.assertEqual(details["member"]["full_name"], "Maya Fernandes")
		self.assertEqual(details["member"]["username"], self.member.username)
		self.assertFalse(details["is_member"])
		self.assertTrue(details["html"])

	def test_the_payload_carries_no_email(self):
		frappe.set_user("Guest")
		details = get_certificate(self.certificate.name)
		self.assertNotIn(self.member.name, frappe.as_json(details))

	def test_the_card_links_the_published_course(self):
		details = get_certificate(self.certificate.name)
		self.assertEqual(details["awarded_for"]["name"], self.course.name)
		self.assertEqual(details["awarded_for"]["description"], self.course.short_introduction)

	def test_an_unpublished_course_gets_no_card(self):
		frappe.db.set_value("LMS Course", self.course.name, "published", 0)
		self.assertIsNone(get_certificate(self.certificate.name)["awarded_for"])

	def test_an_unknown_certificate_is_not_found(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.DoesNotExistError):
			get_certificate("no-such-certificate")

	def test_an_expired_certificate_says_so(self):
		self.set_certificate(expiry_date=add_days(nowdate(), -1))
		self.assertEqual(get_certificate(self.certificate.name)["status"], "expired")

	def test_the_member_sees_their_unpublished_certificate(self):
		self.set_certificate(published=0)
		frappe.set_user(self.member.name)
		details = get_certificate(self.certificate.name)
		self.assertEqual(details["status"], "unpublished")
		self.assertTrue(details["is_member"])

	def test_others_cannot_see_an_unpublished_certificate(self):
		self.set_certificate(published=0)
		for user in ("Guest", self.stranger.name):
			frappe.set_user(user)
			with self.assertRaises(frappe.PermissionError):
				get_certificate(self.certificate.name)


class TestDownloadCertificatePdf(CertificateVerificationFixture):
	def download(self):
		with patch(
			"lms.lms.certificate_verification.get_certificate_pdf", return_value=b"%PDF-1.4"
		) as get_pdf:
			download_certificate_pdf(self.certificate.name)
		return get_pdf

	def test_a_guest_downloads_a_published_certificate(self):
		frappe.set_user("Guest")
		get_pdf = self.download()
		get_pdf.assert_called_once_with(self.certificate.name, self.certificate.template)
		self.assertEqual(frappe.local.response.type, "pdf")
		self.assertEqual(frappe.local.response.filecontent, b"%PDF-1.4")
		self.assertEqual(frappe.local.response.filename, f"{self.certificate.name}.pdf")

	def test_a_stranger_cannot_download_an_unpublished_certificate(self):
		self.set_certificate(published=0)
		frappe.set_user(self.stranger.name)
		with self.assertRaises(frappe.PermissionError):
			self.download()


class TestRawCertificateRoutes(CertificateVerificationFixture):
	def setUp(self):
		super().setUp()
		self.page = get_lms_route(f"certificates/{self.certificate.name}")

	def tearDown(self):
		frappe.local.request = None
		frappe.form_dict.clear()
		super().tearDown()

	def request(self, path, **form):
		frappe.local.request = frappe._dict(path=path)
		frappe.form_dict.clear()
		frappe.form_dict.update(form)

	def assert_redirects(self):
		with self.assertRaises(HTTPException) as raised:
			redirect_raw_certificate_prints()
		self.assertEqual(raised.exception.response.headers["Location"], self.page)

	def test_the_pdf_url_opens_the_verification_page(self):
		for path in (
			"/api/method/frappe.utils.print_format.download_pdf",
			"/api/v2/method/frappe.utils.print_format.download_pdf",
		):
			self.request(path, doctype="LMS Certificate", name=self.certificate.name, format="x")
			self.assert_redirects()

	def test_the_print_view_opens_the_verification_page(self):
		self.request("/printview", doctype="LMS Certificate", name=self.certificate.name)
		self.assert_redirects()

	def test_other_doctypes_print_as_before(self):
		self.request("/printview", doctype="LMS Course", name=self.course.name)
		self.assertIsNone(redirect_raw_certificate_prints())

	def test_other_paths_are_left_alone(self):
		self.request("/api/method/lms.lms.api.get_certificate", doctype="LMS Certificate", name="x")
		self.assertIsNone(redirect_raw_certificate_prints())

	def test_the_old_course_url_opens_the_verification_page(self):
		frappe.form_dict.certificate_id = self.certificate.name
		with self.assertRaises(frappe.Redirect):
			certificate_page.get_context(frappe._dict())
		self.assertEqual(frappe.local.flags.redirect_location, self.page)

	def test_the_printed_qr_url_opens_the_verification_page(self):
		frappe.cache.delete_value("website_redirects")
		with self.assertRaises(frappe.Redirect):
			resolve_redirect(f"certificates/{self.certificate.name}")
		self.assertEqual(frappe.flags.redirect_location, self.page)


class TestCertifiedParticipantsCertificate(CertificateVerificationFixture):
	def find_member_row(self):
		participants = get_certified_participants(
			filters={"member_name": ["like", "%Maya Fernandes%"]}, page_length=500
		)
		return next(row for row in participants if row["username"] == self.member.username)

	def test_each_member_carries_their_published_certificates(self):
		self.assertEqual(
			self.find_member_row()["certificates"],
			[{"name": self.certificate.name, "title": self.course.title}],
		)

	def test_the_card_carries_only_the_profile_summary_and_certificates(self):
		self.assertEqual(
			set(self.find_member_row()),
			{"full_name", "user_image", "username", "headline", "creation", "open_to", "certificates"},
		)

	def test_the_card_carries_the_open_to_status(self):
		frappe.db.set_value("User", self.member.name, "open_to", "Hiring")
		self.assertEqual(self.find_member_row()["open_to"], "Hiring")

	def test_members_come_by_their_newest_certificate(self):
		self.set_certificate(issue_date="2020-01-01")
		course = self._create_course(
			title=f"Verify Order {frappe.generate_hash(length=6)}", instructor=self.author.name
		)
		self._create_enrollment(self.member.name, course.name)
		newest = self._create_certificate(course.name, self.member.name)
		frappe.db.set_value("LMS Certificate", newest.name, "issue_date", "2022-01-01")
		rival = self._create_user(
			f"verify-rival-{frappe.generate_hash(length=6).lower()}@example.com",
			"Maya",
			"Fernhill",
			["LMS Student"],
		)
		self._create_enrollment(rival.name, self.course.name)
		rival_certificate = self._create_certificate(self.course.name, rival.name)
		frappe.db.set_value("LMS Certificate", rival_certificate.name, "issue_date", "2021-06-01")

		usernames = [
			row["username"]
			for row in get_certified_participants(
				filters={"member_name": ["like", "%Maya Fern%"]}, page_length=500
			)
		]
		self.assertLess(usernames.index(self.member.username), usernames.index(rival.username))

	def test_categories_are_trimmed_non_empty_and_unique(self):
		tag = frappe.generate_hash(length=6)
		self.set_certificate(course_title=f"  Verify Dup {tag}  ")
		for title in (f"verify  DUP {tag}", "   "):
			course = self._create_course(
				title=f"Verify Category {frappe.generate_hash(length=6)}", instructor=self.author.name
			)
			self._create_enrollment(self.member.name, course.name)
			certificate = self._create_certificate(course.name, self.member.name)
			frappe.db.set_value("LMS Certificate", certificate.name, "course_title", title)

		labels = [category["label"] for category in get_certification_categories()]
		self.assertTrue(all(label and label == label.strip() for label in labels))
		self.assertEqual(len([label for label in labels if tag.casefold() in label.casefold()]), 1)

	def test_certificates_come_latest_first(self):
		self.set_certificate(issue_date="2020-01-01")
		course = self._create_course(
			title=f"Verify Second {frappe.generate_hash(length=6)}", instructor=self.author.name
		)
		self._create_enrollment(self.member.name, course.name)
		newer = self._create_certificate(course.name, self.member.name)
		names = [certificate["name"] for certificate in self.find_member_row()["certificates"]]
		self.assertEqual(names, [newer.name, self.certificate.name])
