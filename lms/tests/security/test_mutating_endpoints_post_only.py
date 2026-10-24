# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.handler import execute_cmd, is_valid_http_method
from frappe.utils import set_request

from lms.lms.test_helpers import BaseTestUtils

# GET skips the CSRF check and rolls back only the database, so a mutating endpoint
# that accepts it runs from a cross-site link. List every new mutating whitelisted method.
MUTATING_ENDPOINTS = (
	"lms.job.doctype.job_opportunity.job_opportunity.report",
	"lms.lms.api.add_evaluator_slot",
	"lms.lms.api.cancel_evaluation",
	"lms.lms.api.capture_user_persona",
	"lms.lms.api.clear_demo_data",
	"lms.lms.api.create_lesson",
	"lms.lms.api.create_programming_exercise_submission",
	"lms.lms.api.delete_batch",
	"lms.lms.api.delete_category",
	"lms.lms.api.delete_chapter",
	"lms.lms.api.delete_course",
	"lms.lms.api.delete_documents",
	"lms.lms.api.delete_evaluator_slot",
	"lms.lms.api.delete_lesson",
	"lms.lms.api.delete_member",
	"lms.lms.api.delete_programming_exercise",
	"lms.lms.api.delete_sidebar_item",
	"lms.lms.api.ensure_evaluator_calendar",
	"lms.lms.api.export_course_as_zip",
	"lms.lms.api.import_course_from_zip",
	"lms.lms.api.mark_lesson_progress",
	"lms.lms.api.save_role",
	"lms.lms.api.save_sidebar_items",
	"lms.lms.api.set_evaluator_unavailability",
	"lms.lms.api.set_system_preferences",
	"lms.lms.api.track_video_watch_duration",
	"lms.lms.api.update_chapter_index",
	"lms.lms.api.update_evaluator_slot",
	"lms.lms.api.update_lesson_index",
	"lms.lms.api.update_meta_info",
	"lms.lms.api.update_sidebar_item",
	"lms.lms.doctype.course_lesson.course_lesson.save_progress",
	"lms.lms.doctype.lms_badge.lms_badge.assign_badge",
	"lms.lms.doctype.lms_batch.lms_batch.create_google_meet_live_class",
	"lms.lms.doctype.lms_batch.lms_batch.create_live_class",
	"lms.lms.doctype.lms_batch_enrollment.lms_batch_enrollment.send_confirmation_email",
	"lms.lms.doctype.lms_certificate.lms_certificate.create_certificate",
	"lms.lms.doctype.lms_certificate_request.lms_certificate_request.setup_calendar_event",
	"lms.lms.doctype.lms_quiz.lms_quiz.submit_quiz",
	"lms.lms.email_account.create_email_account",
	"lms.lms.email_account.set_default_email_account",
	"lms.lms.payments.get_payment_link",
	"lms.lms.user.sign_up",
	"lms.lms.utils.enroll_in_batch",
	"lms.lms.utils.enroll_in_program",
	"lms.lms.utils.get_discussion_topics",
)

# A read-only endpoint, so a check that refused GET for everything would go red here.
READ_ONLY_CONTROL = "lms.lms.api.get_lms_settings"


class HttpMethodTestCase(BaseTestUtils):
	def _as_request(self, method, form_dict=None):
		previous_request = getattr(frappe.local, "request", None)
		previous_form_dict = frappe.local.form_dict
		set_request(method=method, path="/api/method/lms")
		frappe.local.form_dict = frappe._dict(form_dict or {})
		self.addCleanup(setattr, frappe.local, "form_dict", previous_form_dict)
		self.addCleanup(setattr, frappe.local, "request", previous_request)


class TestMutatingEndpointsArePostOnly(HttpMethodTestCase):
	def test_get_is_refused_for_every_mutating_endpoint(self):
		"""Mutating endpoints accepted GET, e.g. delete_chapter since #1132.
		Added for audit findings #27/#28."""
		self._as_request("GET")
		for path in MUTATING_ENDPOINTS:
			with self.subTest(endpoint=path):
				with self.assertRaises(frappe.PermissionError):
					is_valid_http_method(frappe.get_attr(path))

	def test_post_is_allowed_for_every_mutating_endpoint(self):
		"""Control: POST still passes, so the GET refusal is not blanket."""
		self._as_request("POST")
		for path in MUTATING_ENDPOINTS:
			with self.subTest(endpoint=path):
				is_valid_http_method(frappe.get_attr(path))

	def test_read_only_control_still_answers_get(self):
		"""Control: a read endpoint still answers GET."""
		self._as_request("GET")
		is_valid_http_method(frappe.get_attr(READ_ONLY_CONTROL))


class TestCrossSiteGetChangesNothing(HttpMethodTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.instructor = cls._create_user(
			"frappe@example.com", "Frappe", "Admin", ["Course Creator", "Moderator"]
		)

	def _chapter_on_course(self):
		course = self._create_course()
		chapter = self._create_chapter(f"Chapter {frappe.generate_hash(length=6)}", course.name)
		self._create_chapter_reference(course.name, chapter.name)
		return chapter

	def test_author_get_to_delete_chapter_leaves_the_chapter(self):
		"""delete_chapter accepted GET since #1132.
		Added for audit finding #27."""
		chapter = self._chapter_on_course()
		frappe.set_user(self.instructor.name)
		self._as_request("GET", {"chapter": chapter.name})

		with self.assertRaises(frappe.PermissionError):
			execute_cmd("lms.lms.api.delete_chapter")

		self.assertTrue(frappe.db.exists("Course Chapter", chapter.name))

	def test_author_post_to_delete_chapter_deletes_it(self):
		"""Control for the GET test above."""
		chapter = self._chapter_on_course()
		frappe.set_user(self.instructor.name)
		self._as_request("POST", {"chapter": chapter.name})

		execute_cmd("lms.lms.api.delete_chapter")

		self.assertFalse(frappe.db.exists("Course Chapter", chapter.name))

	def test_get_to_create_live_class_never_reaches_the_body(self):
		"""create_live_class accepted GET since #487.
		Added for audit finding #28."""
		self._as_request("GET", self._live_class_args())

		with (
			patch(
				"lms.lms.doctype.lms_batch.lms_batch.check_can_schedule_live_class",
				side_effect=frappe.PermissionError,
			) as gate,
			self.assertRaises(frappe.PermissionError),
		):
			execute_cmd("lms.lms.doctype.lms_batch.lms_batch.create_live_class")

		gate.assert_not_called()

	def test_post_to_create_live_class_reaches_the_body(self):
		"""Control for the GET test above."""
		self._as_request("POST", self._live_class_args())

		with (
			patch(
				"lms.lms.doctype.lms_batch.lms_batch.check_can_schedule_live_class",
				side_effect=frappe.PermissionError,
			) as gate,
			self.assertRaises(frappe.PermissionError),
		):
			execute_cmd("lms.lms.doctype.lms_batch.lms_batch.create_live_class")

		gate.assert_called_once()

	def _live_class_args(self):
		return {
			"batch_name": "any-batch",
			"zoom_account": "any-account",
			"title": "Injected",
			"duration": 30,
			"date": "2026-10-02",
			"time": "10:00",
			"timezone": "Asia/Kolkata",
			"auto_recording": "No Recording",
		}
