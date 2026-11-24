from types import SimpleNamespace
from unittest.mock import patch

import frappe

from lms import unsplash
from lms.lms import code_runner
from lms.lms.doctype.lms_live_class import lms_live_class
from lms.lms.integrations import (
	SETTINGS_FLAGS,
	get_integration_status,
	set_integrations_enabled,
)
from lms.lms.test_helpers import BaseTestUtils

LIVE_CLASS = "lms.lms.doctype.lms_live_class.lms_live_class"


class TestIntegrationSwitches(BaseTestUtils):
	"""Each integration's switch on LMS Settings stops the server from using it."""

	def set_flags(self, **flags):
		for key, value in flags.items():
			frappe.db.set_single_value("LMS Settings", SETTINGS_FLAGS[key], 1 if value else 0)

	def test_zoom_off_refuses_a_zoom_account(self):
		self.set_flags(zoom=False)
		with self.assertRaisesRegex(frappe.ValidationError, "Zoom is turned off"):
			lms_live_class.check_class_can_use_account("LMS Zoom Settings", "any", "any")

	def test_google_meet_off_refuses_a_meet_account(self):
		self.set_flags(google_meet=False)
		with self.assertRaisesRegex(frappe.ValidationError, "Google Meet is turned off"):
			lms_live_class.check_class_can_use_account("LMS Google Meet Settings", "any", "any")

	def test_zoom_on_reaches_the_account_check(self):
		self.set_flags(zoom=True)
		with patch(f"{LIVE_CLASS}.can_use_conferencing_account", return_value=True) as account_check:
			lms_live_class.check_class_can_use_account("LMS Zoom Settings", "any", "any")
		account_check.assert_called_once()

	def run_attendance_job(self):
		live_class = SimpleNamespace(name="class", uuid="uuid", zoom_account="account")
		with (
			patch(f"{LIVE_CLASS}.frappe.get_all", return_value=[live_class]),
			patch(f"{LIVE_CLASS}.get_attendance", return_value=[]) as fetch,
			patch(f"{LIVE_CLASS}.create_attendance"),
			patch(f"{LIVE_CLASS}.update_attendees_count"),
		):
			lms_live_class.update_attendance()
		return fetch

	def test_attendance_job_skips_when_tracking_is_off(self):
		self.set_flags(zoom=True, zoom_attendance=False)
		self.run_attendance_job().assert_not_called()

	def test_attendance_job_skips_when_zoom_is_off(self):
		self.set_flags(zoom=False, zoom_attendance=True)
		self.run_attendance_job().assert_not_called()

	def test_attendance_job_fetches_when_tracking_is_on(self):
		self.set_flags(zoom=True, zoom_attendance=True)
		self.run_attendance_job().assert_called_once()

	def test_code_runner_off_refuses_to_run(self):
		self.set_flags(code_runner=False)
		with (
			patch.object(code_runner, "run_once") as run_once,
			self.assertRaisesRegex(frappe.ValidationError, "Code runner is turned off"),
		):
			code_runner.run_test_cases("python", "print(1)", [SimpleNamespace(input="")])
		run_once.assert_not_called()

	def test_unsplash_off_sends_no_request(self):
		frappe.db.set_single_value("LMS Settings", "unsplash_access_key", "key")
		self.set_flags(unsplash=False)
		with patch("requests.get") as request:
			self.assertIsNone(unsplash.make_unsplash_request("/photos"))
		request.assert_not_called()


class TestIntegrationSettings(BaseTestUtils):
	def test_writes_switches_and_reports_them(self):
		status = set_integrations_enabled({"zoom": True, "zoom_attendance": False, "unsplash": True})
		self.assertTrue(status["zoom"]["enabled"])
		self.assertFalse(status["zoom"]["attendance"])
		self.assertTrue(status["unsplash"]["enabled"])
		self.assertEqual(get_integration_status()["zoom"], status["zoom"])

	def test_refuses_an_unknown_integration(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Unknown integration"):
			set_integrations_enabled({"fax": True})

	def test_raven_cannot_be_turned_off(self):
		with self.assertRaisesRegex(frappe.ValidationError, "can't be turned off"):
			set_integrations_enabled({"raven": False})

	def test_requires_a_manager(self):
		user = self._create_user(
			"integrations-student@example.com", "Integrations", "Student", ["LMS Student"]
		)
		frappe.set_user(user.name)
		with self.assertRaises(frappe.PermissionError):
			get_integration_status()

	def test_calendar_invites_turn_on_before_any_calendar_exists(self):
		"""Configure stays closed while the card is off, so the switch must not need a calendar first."""
		google = frappe.get_doc("Google Settings")
		google.update({"enable": 1, "client_id": "id", "client_secret": "secret"})
		google.save()
		frappe.db.delete("Google Calendar")
		status = set_integrations_enabled({"google_calendar": True})
		self.assertTrue(status["google_calendar"]["enabled"])
