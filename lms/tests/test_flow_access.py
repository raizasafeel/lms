from types import SimpleNamespace
from unittest.mock import patch

import frappe

from lms.lms import flow
from lms.lms.api import can_use_flow
from lms.lms.test_helpers import BaseTestUtils

LAUNCHER = '<script src="/assets/frappe/dist/js/flow_launcher.bundle.ABC.js" defer data-island="x"></script>'


class TestFlowForLearners(BaseTestUtils):
	"""Settings > Integrations > Flow: LMS can take Flow off its pages, or away from learners."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.learner = cls._create_user("flow-learner@example.com", "Flow", "Learner", ["LMS Student"])
		cls.creator = cls._create_user(
			"flow-creator@example.com", "Flow", "Creator", ["LMS Student", "Course Creator"]
		)

	def set_flags(self, enabled=1, hidden=0):
		frappe.db.set_single_value("LMS Settings", {"enable_flow": enabled, "hide_flow_for_learners": hidden})

	def page(self, path="/lms/courses"):
		response = SimpleNamespace(mimetype="text/html", body=f"<html><body>{LAUNCHER}</body></html>")
		response.get_data = lambda as_text=True: response.body
		response.set_data = lambda data: setattr(response, "body", data)
		flow.remove_launcher(response, SimpleNamespace(method="GET", path=path))
		return response.body

	def test_learner_only_means_no_staff_role(self):
		self.assertTrue(flow.is_learner_only(self.learner.name))
		self.assertFalse(flow.is_learner_only(self.creator.name))

	def test_hidden_learner_gets_no_launcher_and_no_chat(self):
		self.set_flags(hidden=1)
		frappe.set_user(self.learner.name)
		self.assertNotIn("flow_launcher", self.page())
		self.assertFalse(flow.flow_session_has_permission(None, "read", self.learner.name))
		with patch("frappe.has_permission", return_value=True):
			self.assertFalse(can_use_flow())

	def test_staff_keep_flow_while_learners_are_hidden(self):
		self.set_flags(hidden=1)
		frappe.set_user(self.creator.name)
		self.assertIn("flow_launcher", self.page())
		self.assertTrue(flow.flow_session_has_permission(None, "read", self.creator.name))

	def test_learners_keep_flow_while_the_switch_is_off(self):
		self.set_flags(hidden=0)
		frappe.set_user(self.learner.name)
		self.assertIn("flow_launcher", self.page())
		self.assertTrue(flow.flow_session_has_permission(None, "read", self.learner.name))

	def test_flow_off_takes_it_off_lms_pages_for_everyone(self):
		self.set_flags(enabled=0)
		self.assertNotIn("flow_launcher", self.page())
		self.assertIn("flow_launcher", self.page("/desk/todo"))
