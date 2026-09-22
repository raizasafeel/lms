# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

"""Tests for lms/telemetry.py.

Schema-free: everything here exercises the shaping of an event, not the sending
of one, so `pulse_capture` and the settings reads are patched out. The one thing
worth asserting hardest is that nothing in this module can raise -- it runs
inside document hooks and payment handlers that have real work after it.
"""

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from lms import telemetry


class FakeDoc:
	"""A document stand-in: a doctype, `get`, and a changed-field answer.

	Deliberately not a `frappe._dict`: a method defined on the class would always
	win over a key of the same name, so a test could not replace one.
	"""

	def __init__(self, doctype, changed=(), **fields):
		self.doctype = doctype
		self.fields = fields
		self.changed = set(changed)

	def get(self, fieldname, default=None):
		return self.fields.get(fieldname, default)

	def has_value_changed(self, fieldname):
		return fieldname in self.changed


class UnsnapshottedDoc(FakeDoc):
	"""A document that cannot say what changed, the way one saved outside the
	normal path cannot."""

	def has_value_changed(self, fieldname):
		raise AttributeError("no snapshot to compare against")


class TelemetryTestCase(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.sent = []

		def record(event, app, properties=None, **kwargs):
			self.sent.append((event, app, properties or {}))

		patches = [
			patch.object(telemetry, "pulse_capture", record),
			patch.object(telemetry, "get_common_properties", lambda: {"role": "moderator"}),
			# A test bench has no Pulse key, so the real gate would turn every
			# event away before it could be inspected.
			patch.object(telemetry, "is_enabled", lambda: True),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)


class TestCapture(TelemetryTestCase):
	def test_merges_the_standing_context(self):
		telemetry.capture("course_created", {"paid": True})

		event, app, properties = self.sent[0]
		self.assertEqual(event, "course_created")
		self.assertEqual(app, "lms")
		self.assertEqual(properties, {"role": "moderator", "paid": True})

	def test_caller_properties_win_over_the_context(self):
		telemetry.capture("course_created", {"role": "student"})

		self.assertEqual(self.sent[0][2]["role"], "student")

	def test_swallows_a_failure_in_the_client(self):
		def explode(*args, **kwargs):
			raise RuntimeError("pulse is down")

		with patch.object(telemetry, "pulse_capture", explode):
			telemetry.capture("course_created")

		self.assertEqual(self.sent, [])

	def test_sends_nothing_when_telemetry_is_off(self):
		with patch.object(telemetry, "is_enabled", lambda: False):
			telemetry.capture("course_created")

		self.assertEqual(self.sent, [])


class TestIsEnabled(UnitTestCase):
	def test_is_off_without_a_client(self):
		with patch.object(telemetry, "pulse_capture", None):
			self.assertFalse(telemetry.is_enabled())

	def test_follows_the_framework_when_it_answers(self):
		with (
			patch.object(telemetry, "pulse_capture", lambda *a, **k: None),
			patch.object(telemetry, "is_pulse_enabled", lambda: False),
		):
			self.assertFalse(telemetry.is_enabled())

	def test_is_on_when_the_framework_does_not_offer_the_check(self):
		with (
			patch.object(telemetry, "pulse_capture", lambda *a, **k: None),
			patch.object(telemetry, "is_pulse_enabled", None),
		):
			self.assertTrue(telemetry.is_enabled())

	def test_is_off_when_the_check_itself_fails(self):
		def explode():
			raise RuntimeError("no site config")

		with (
			patch.object(telemetry, "pulse_capture", lambda *a, **k: None),
			patch.object(telemetry, "is_pulse_enabled", explode),
		):
			self.assertFalse(telemetry.is_enabled())


class TestDocumentEvents(TelemetryTestCase):
	def test_captures_a_tracked_doctype(self):
		doc = FakeDoc("LMS Course", paid_course=1, published=0, chapters=[1, 2])

		with patch.object(telemetry, "is_first_of_doctype", lambda doctype: True):
			telemetry.capture_doc_event(doc)

		event, _, properties = self.sent[0]
		self.assertEqual(event, "course_created")
		self.assertTrue(properties["is_first"])
		self.assertTrue(properties["paid"])
		self.assertFalse(properties["published"])
		self.assertEqual(properties["chapter_count"], 2)

	def test_ignores_an_untracked_doctype(self):
		telemetry.capture_doc_event(FakeDoc("Email Queue"))

		self.assertEqual(self.sent, [])

	def test_does_no_work_when_telemetry_is_off(self):
		def explode(doctype):
			raise AssertionError("the milestone must not be counted when off")

		with (
			patch.object(telemetry, "is_enabled", lambda: False),
			patch.object(telemetry, "is_first_of_doctype", explode),
		):
			telemetry.capture_doc_event(FakeDoc("LMS Course"))

		self.assertEqual(self.sent, [])

	def test_a_doctype_without_an_extractor_still_reports_the_milestone(self):
		with patch.object(telemetry, "is_first_of_doctype", lambda doctype: False):
			telemetry.capture_doc_event(FakeDoc("LMS Badge"))

		event, _, properties = self.sent[0]
		self.assertEqual(event, "badge_created")
		self.assertFalse(properties["is_first"])

	def test_keeps_the_event_when_a_property_cannot_be_read(self):
		def explode(doc):
			raise ValueError("no such field")

		with (
			patch.dict(telemetry.DOC_PROPERTIES, {"LMS Course": explode}),
			patch.object(telemetry, "is_first_of_doctype", lambda doctype: False),
		):
			telemetry.capture_doc_event(FakeDoc("LMS Course"))

		self.assertEqual(self.sent[0][0], "course_created")

	def test_keeps_the_event_when_the_milestone_cannot_be_counted(self):
		def explode(doctype):
			raise ValueError("table is gone")

		with patch.object(telemetry, "is_first_of_doctype", explode):
			telemetry.capture_doc_event(FakeDoc("LMS Badge"))

		self.assertEqual(self.sent[0][0], "badge_created")
		self.assertNotIn("is_first", self.sent[0][2])


class TestPublishEvents(TelemetryTestCase):
	def test_captures_a_course_going_live(self):
		doc = FakeDoc("LMS Course", changed=["published"], published=1, paid_course=1)

		telemetry.capture_publish_event(doc)

		event, _, properties = self.sent[0]
		self.assertEqual(event, "course_published")
		self.assertTrue(properties["paid"])
		# The milestone flag belongs to creation: on a publish it would read as
		# "this site has one course", which is a different claim.
		self.assertNotIn("is_first", properties)

	def test_captures_a_course_being_taken_down(self):
		doc = FakeDoc("LMS Course", changed=["published"], published=0)

		telemetry.capture_publish_event(doc)

		self.assertEqual(self.sent[0][0], "course_unpublished")

	def test_ignores_a_save_that_left_published_alone(self):
		doc = FakeDoc("LMS Course", changed=["title"], published=1)

		telemetry.capture_publish_event(doc)

		self.assertEqual(self.sent, [])

	def test_ignores_a_doctype_that_does_not_publish(self):
		doc = FakeDoc("LMS Quiz", changed=["published"], published=1)

		telemetry.capture_publish_event(doc)

		self.assertEqual(self.sent, [])

	def test_ignores_a_document_that_cannot_answer(self):
		# `on_update` is registered against every doctype, so this handler meets
		# documents in states it knows nothing about.
		telemetry.capture_publish_event(UnsnapshottedDoc("LMS Course", published=1))

		self.assertEqual(self.sent, [])


class TestProperties(UnitTestCase):
	def test_quiz_submission_reports_a_pass(self):
		doc = FakeDoc("LMS Quiz Submission", percentage=80, passing_percentage=70)

		self.assertTrue(telemetry.quiz_submission_properties(doc)["passed"])

	def test_quiz_submission_reports_a_fail(self):
		doc = FakeDoc("LMS Quiz Submission", percentage=40, passing_percentage=70)

		self.assertFalse(telemetry.quiz_submission_properties(doc)["passed"])

	def test_quiz_submission_does_not_guess_without_a_threshold(self):
		doc = FakeDoc("LMS Quiz Submission", percentage=40)

		self.assertIsNone(telemetry.quiz_submission_properties(doc)["passed"])

	def test_payment_properties_carry_no_names(self):
		doc = FakeDoc(
			"LMS Payment",
			currency="INR",
			amount=500,
			billing_name="Someone Real",
			payment_for_document_type="LMS Course",
			coupon="LAUNCH",
		)

		properties = telemetry.payment_properties(doc)

		self.assertEqual(properties["currency"], "INR")
		self.assertTrue(properties["used_coupon"])
		# A coupon code is a flag, not a value, and nothing a person typed goes out.
		self.assertNotIn("billing_name", properties)
		self.assertNotIn("coupon", properties)

	def test_every_tracked_doctype_names_an_event(self):
		for doctype, event in telemetry.TRACKED_DOCTYPES.items():
			self.assertTrue(event, f"{doctype} has no event name")
			self.assertEqual(event, event.lower())

	def test_every_publishable_doctype_is_tracked(self):
		for doctype in telemetry.PUBLISHABLE_DOCTYPES:
			self.assertIn(doctype, telemetry.TRACKED_DOCTYPES)

	def test_every_extractor_belongs_to_a_tracked_doctype(self):
		for doctype in telemetry.DOC_PROPERTIES:
			self.assertIn(doctype, telemetry.TRACKED_DOCTYPES)


class TestActorRole(UnitTestCase):
	def setUp(self):
		super().setUp()
		# Administrator and Guest are reported as themselves, so a role test has
		# to run as somebody else.
		original = frappe.session.user
		frappe.session.user = "telemetry-actor@example.com"
		self.addCleanup(lambda: setattr(frappe.session, "user", original))

	def test_reports_the_most_specific_role(self):
		with patch.object(frappe, "get_roles", lambda user: ["Course Creator", "Moderator"]):
			self.assertEqual(telemetry.get_actor_role(), "moderator")

	def test_reports_a_learner_as_a_student(self):
		with patch.object(frappe, "get_roles", lambda user: ["LMS Student"]):
			self.assertEqual(telemetry.get_actor_role(), "student")

	def test_does_not_guess_when_roles_cannot_be_read(self):
		def explode(user):
			raise RuntimeError("no session")

		with patch.object(frappe, "get_roles", explode):
			self.assertEqual(telemetry.get_actor_role(), "unknown")

	def test_reports_administrator_as_itself(self):
		frappe.session.user = "Administrator"

		self.assertEqual(telemetry.get_actor_role(), "administrator")
