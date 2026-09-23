# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

"""Tests for lms/frappe_cloud.py: finishing setup on Frappe Cloud without the wizard.

Schema-free. The rules under test are the gates -- Frappe Cloud only, only once
Frappe Cloud has prefilled the site, never when another app needs wizard input
-- and that the answers handed to Frappe's own `setup_complete` are the ones
already on the site.
"""

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from lms import frappe_cloud

READY_ARGS = {"country": "India", "email": "owner@example.com"}


class Settings(dict):
	"""A System Settings row as `frappe.db.get_value(..., as_dict=True)` returns it."""

	__getattr__ = dict.get


PREFILLED = Settings(
	country="India",
	time_zone="Asia/Kolkata",
	currency="INR",
	language="en",
	enable_telemetry=1,
)

OWNER = SimpleNamespace(name="owner@example.com", full_name="Site Owner")


def user(name="owner@example.com", user_type="System User", enabled=1):
	return frappe._dict(name=name, user_type=user_type, enabled=enabled)


class TestIsFrappeCloudSite(UnitTestCase):
	def test_true_with_the_secret_frappe_cloud_writes(self):
		with patch.dict(frappe.conf, {"fc_communication_secret": "s3cret"}):
			self.assertTrue(frappe_cloud.is_frappe_cloud_site())

	def test_false_on_a_self_hosted_site(self):
		with patch.dict(frappe.conf, {"fc_communication_secret": None}):
			self.assertFalse(frappe_cloud.is_frappe_cloud_site())


class TestScheduleSetupCompletion(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.enqueued = []
		patches = [
			patch.object(frappe, "enqueue", lambda *a, **k: self.enqueued.append((a, k))),
			patch.object(frappe_cloud, "is_frappe_cloud_site", lambda: True),
			patch.object(frappe, "is_setup_complete", lambda: False),
			patch.object(frappe_cloud, "get_setup_args", lambda: READY_ARGS),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)

	def test_queues_once_frappe_cloud_has_prefilled_the_owner(self):
		frappe_cloud.schedule_setup_completion(user())

		(args, kwargs) = self.enqueued[0]
		self.assertEqual(args, ("lms.frappe_cloud.complete_setup",))
		# One job per site, however many user saves or logins ask for it.
		self.assertEqual(kwargs["job_id"], frappe_cloud.JOB_ID)
		self.assertTrue(kwargs["deduplicate"])
		# After commit: the job must see the user row this save is writing.
		self.assertTrue(kwargs["enqueue_after_commit"])

	def test_queues_from_a_login_too(self):
		frappe_cloud.schedule_setup_completion()

		self.assertEqual(len(self.enqueued), 1)

	def test_does_nothing_on_a_self_hosted_site(self):
		with patch.object(frappe_cloud, "is_frappe_cloud_site", lambda: False):
			frappe_cloud.schedule_setup_completion(user())

		self.assertEqual(self.enqueued, [])

	def test_does_nothing_once_setup_is_complete(self):
		with patch.object(frappe, "is_setup_complete", lambda: True):
			frappe_cloud.schedule_setup_completion(user())

		self.assertEqual(self.enqueued, [])

	def test_does_nothing_until_the_site_is_prefilled(self):
		with patch.object(frappe_cloud, "get_setup_args", lambda: None):
			frappe_cloud.schedule_setup_completion(user())

		self.assertEqual(self.enqueued, [])

	def test_ignores_saves_of_users_who_cannot_be_the_owner(self):
		for other in (
			user(name="Administrator"),
			user(user_type="Website User"),
			user(enabled=0),
		):
			frappe_cloud.schedule_setup_completion(other)

		self.assertEqual(self.enqueued, [])

	def test_never_fails_the_save_that_triggered_it(self):
		def explode():
			raise RuntimeError("redis is down")

		with (
			patch.object(frappe_cloud, "get_setup_args", explode),
			patch.object(frappe, "log_error", lambda **kwargs: None),
		):
			frappe_cloud.schedule_setup_completion(user())

		self.assertEqual(self.enqueued, [])


class TestGetSetupArgs(UnitTestCase):
	def setUp(self):
		super().setUp()
		patches = [
			patch.object(frappe_cloud, "only_input_free_setup_hooks", lambda: True),
			patch.object(frappe_cloud, "get_prefilled_settings", lambda: PREFILLED),
			patch.object(frappe_cloud, "get_prefilled_owner", lambda: OWNER),
			patch.object(frappe_cloud, "get_language_name", lambda code: "English"),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)

	def test_answers_the_wizard_from_what_is_already_on_the_site(self):
		self.assertEqual(
			frappe_cloud.get_setup_args(),
			{
				"language": "English",
				"lang": "English",
				"country": "India",
				"timezone": "Asia/Kolkata",
				"currency": "INR",
				"full_name": "Site Owner",
				"email": "owner@example.com",
				"enable_telemetry": 1,
			},
		)

	def test_keeps_the_site_telemetry_choice(self):
		# The wizard writes this back, and a missing value reads as "off".
		off = Settings(PREFILLED, enable_telemetry=0)
		with patch.object(frappe_cloud, "get_prefilled_settings", lambda: off):
			self.assertEqual(frappe_cloud.get_setup_args()["enable_telemetry"], 0)

	def test_passes_the_language_under_both_keys_frappe_reads(self):
		with patch.object(frappe_cloud, "get_language_name", lambda code: "Deutsch"):
			args = frappe_cloud.get_setup_args()

		self.assertEqual((args["language"], args["lang"]), ("Deutsch", "Deutsch"))

	def test_waits_for_a_country(self):
		empty = Settings(PREFILLED, country=None)
		with patch.object(frappe_cloud, "get_prefilled_settings", lambda: empty):
			self.assertIsNone(frappe_cloud.get_setup_args())

	def test_waits_for_a_time_zone(self):
		empty = Settings(PREFILLED, time_zone=None)
		with patch.object(frappe_cloud, "get_prefilled_settings", lambda: empty):
			self.assertIsNone(frappe_cloud.get_setup_args())

	def test_waits_for_the_owner(self):
		# A standby site Frappe Cloud keeps warm has the secret but no owner yet.
		with patch.object(frappe_cloud, "get_prefilled_owner", lambda: None):
			self.assertIsNone(frappe_cloud.get_setup_args())

	def test_leaves_the_wizard_to_an_app_that_needs_input(self):
		with patch.object(frappe_cloud, "only_input_free_setup_hooks", lambda: False):
			self.assertIsNone(frappe_cloud.get_setup_args())


class TestOnlyInputFreeSetupHooks(UnitTestCase):
	def check(self, hooks_by_app):
		with (
			patch.object(frappe, "get_installed_apps", lambda: list(hooks_by_app)),
			patch.object(frappe, "get_hooks", lambda app_name=None: hooks_by_app[app_name]),
		):
			return frappe_cloud.only_input_free_setup_hooks()

	def test_lms_own_hook_does_not_count(self):
		self.assertTrue(
			self.check(
				{
					"frappe": {},
					"payments": {},
					"lms": {"setup_wizard_complete": ["lms.demo.demo_data.create_demo_data"]},
				}
			)
		)

	def test_an_app_with_wizard_stages_blocks_it(self):
		self.assertFalse(
			self.check(
				{
					"frappe": {},
					"lms": {},
					"erpnext": {"setup_wizard_stages": ["erpnext.setup.setup_wizard.get_setup_stages"]},
				}
			)
		)

	def test_an_app_with_its_own_completion_hook_blocks_it(self):
		self.assertFalse(
			self.check({"frappe": {}, "lms": {}, "hrms": {"setup_wizard_complete": ["hrms.setup"]}})
		)


class TestCompleteSetup(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.completed = []
		patches = [
			patch(
				"frappe.desk.page.setup_wizard.setup_wizard.setup_complete",
				lambda args: self.completed.append(args),
			),
			patch.object(frappe, "is_setup_complete", lambda: False),
			patch.object(frappe_cloud, "get_setup_args", lambda: READY_ARGS),
			patch("lms.telemetry.capture", lambda *a, **k: None),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)

	def test_runs_frappe_setup_with_the_prefilled_answers(self):
		frappe_cloud.complete_setup(job_id=frappe_cloud.JOB_ID)

		self.assertEqual(self.completed, [READY_ARGS])

	def test_does_nothing_if_the_owner_finished_the_wizard_first(self):
		with patch.object(frappe, "is_setup_complete", lambda: True):
			frappe_cloud.complete_setup()

		self.assertEqual(self.completed, [])

	def test_does_nothing_if_the_answers_went_missing(self):
		with patch.object(frappe_cloud, "get_setup_args", lambda: None):
			frappe_cloud.complete_setup()

		self.assertEqual(self.completed, [])
