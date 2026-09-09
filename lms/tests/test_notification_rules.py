"""The Notification rules that replaced LMS's hardcoded mails."""

from datetime import datetime
from unittest.mock import patch

import frappe
from frappe.email.doctype.notification.notification import trigger_daily_alerts
from frappe.tests import IntegrationTestCase

from lms.job.doctype.job_opportunity.job_opportunity import report
from lms.lms.api import get_notification_rules, set_notification_rule
from lms.lms.doctype.lms_certificate.lms_certificate import get_default_certificate_template
from lms.lms.doctype.lms_payment.lms_payment import send_payment_reminder
from lms.lms.notifications import LMS_NOTIFICATIONS, rule_names, seed_notifications
from lms.lms.utils import convert_from_system_timezone, format_timezone


def reseed(*names):
	"""Rebuild these rules from the catalogue before exercising them.

	`seed_notifications` deliberately never rewrites a rule the site already has,
	so on a site that was seeded before a catalogue edit -- which the shared
	lms-audit.localhost always is -- the row under test is the stale one and the
	test passes against code it never touched. Deleting first is what makes these
	tests read the current catalogue.

	No cache clearing needed alongside it: `Notification.on_trash` and
	`Notification.validate` both call `clear_notification_cache()`, which drops
	every `notifications::<doctype>` key `Document.run_notifications` reads.
	"""
	for name in names:
		if frappe.db.exists("Notification", name):
			frappe.delete_doc("Notification", name, force=True, ignore_permissions=True)
	seed_notifications()


def set_enabled(name, value):
	"""Flip a seeded rule's Enabled switch the way the settings page does.

	`frappe.db.set_value` writes under the document layer, so it does not clear
	the enabled-rules cache `Document.run_notifications` reads; do it by hand.
	"""
	frappe.db.set_value("Notification", name, "enabled", value)
	frappe.client_cache.delete_keys("notifications::")


class TestSeeding(IntegrationTestCase):
	def test_every_catalogued_rule_exists_after_seeding(self):
		seed_notifications()
		for name in rule_names():
			self.assertTrue(frappe.db.exists("Notification", name), f"{name} was not seeded")

	def test_every_rule_is_owned_by_the_lms_module(self):
		seed_notifications()
		for name in rule_names():
			row = frappe.db.get_value("Notification", name, ["module", "is_standard"], as_dict=True)
			self.assertEqual(row.module, "LMS")
			self.assertEqual(row.is_standard, 0)

	def test_seeding_never_rewrites_an_edited_rule(self):
		seed_notifications()
		name = rule_names()[0]
		frappe.db.set_value("Notification", name, "subject", "An admin wrote this")
		seed_notifications()
		self.assertEqual(frappe.db.get_value("Notification", name, "subject"), "An admin wrote this")

	def test_a_deleted_rule_comes_back_on_the_next_seed(self):
		seed_notifications()
		name = rule_names()[-1]
		frappe.delete_doc("Notification", name, force=True, ignore_permissions=True)
		seed_notifications()
		self.assertTrue(frappe.db.exists("Notification", name))

	def test_the_catalogue_is_twelve_rules(self):
		self.assertEqual(len(LMS_NOTIFICATIONS), 12)

	def test_the_two_publish_rules_seed_disabled(self):
		# On develop each publish mail was gated by an LMS Settings Select with a
		# blank first option and no default, so a stock site sent neither. Seeded
		# enabled, the first publish after an upgrade would mass-mail every
		# enabled User.
		for name in ("LMS New Course Published", "LMS New Batch Published"):
			with self.subTest(rule=name):
				reseed(name)
				self.assertEqual(frappe.db.get_value("Notification", name, "enabled"), 0)

	def test_every_other_rule_seeds_enabled(self):
		off = {"LMS New Course Published", "LMS New Batch Published"}
		for name in [n for n in rule_names() if n not in off]:
			with self.subTest(rule=name):
				reseed(name)
				self.assertEqual(frappe.db.get_value("Notification", name, "enabled"), 1)


class TestBatchConfirmation(IntegrationTestCase):
	def setUp(self):
		reseed("LMS Batch Enrollment Confirmation")
		# The enabled-rules list Document.run_notifications caches under this key
		# lives in redis, outside the per-test SQL rollback. A prior test that
		# disabled the rule (and cleared the cache to see that) leaves the *next*
		# read to repopulate the cache from disabled state, and that empty-rule
		# cache entry survives this test's own rollback. Clear it here too so
		# every test starts from the DB's real (rolled-back) enabled state.
		frappe.client_cache.delete_value("notifications::LMS Batch Enrollment")

		hash_ = frappe.generate_hash(length=6)

		self.student = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"batch-confirm-student-{hash_}@test.com",
					"first_name": "Batch",
					"last_name": "Student",
					"send_welcome_email": 0,
					"roles": [{"role": "LMS Student"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		self.batch = frappe.get_doc(
			{
				"doctype": "LMS Batch",
				"title": f"Confirmation Batch {hash_}",
				"start_date": frappe.utils.today(),
				"end_date": frappe.utils.add_days(frappe.utils.today(), 7),
				"description": "Batch for enrollment confirmation tests",
				"batch_details": "Batch for enrollment confirmation tests",
				"start_time": "09:00:00",
				"end_time": "10:00:00",
				"timezone": "Asia/Kolkata",
				"published": 1,
				"instructors": [{"instructor": "Administrator"}],
			}
		).insert(ignore_permissions=True)

		self.template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": f"Batch Confirmation Override {hash_}",
				"subject": "Custom Enrollment Confirmation",
				"response": "<p>This batch has its own wording.</p>",
			}
		).insert(ignore_permissions=True)

		self.site_template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": f"Site Confirmation Override {hash_}",
				"subject": "Custom Site Confirmation",
				"response": "<p>This site has its own wording.</p>",
			}
		).insert(ignore_permissions=True)

	def enrol(self):
		return frappe.get_doc(
			{
				"doctype": "LMS Batch Enrollment",
				"batch": self.batch.name,
				"member": self.student,
			}
		).insert(ignore_permissions=True)

	def use_site_template(self):
		frappe.db.set_single_value("LMS Settings", "batch_confirmation_template", self.site_template.name)
		self.addCleanup(
			lambda: frappe.db.set_single_value("LMS Settings", "batch_confirmation_template", None)
		)

	def test_enrolling_a_student_mails_that_student(self):
		with patch("frappe.sendmail") as sendmail:
			frappe.get_doc(
				{
					"doctype": "LMS Batch Enrollment",
					"batch": self.batch.name,
					"member": self.student,
				}
			).insert(ignore_permissions=True)
		self.assertTrue(sendmail.called)
		self.assertIn(self.student, sendmail.call_args.kwargs["recipients"])
		self.assertIn(self.batch.title, sendmail.call_args.kwargs["subject"])

	def test_a_batch_with_its_own_template_sends_that_template(self):
		frappe.db.set_value("LMS Batch", self.batch.name, "confirmation_email_template", self.template.name)
		with patch("frappe.sendmail") as sendmail:
			self.enrol()
		self.assertIn("This batch has its own wording", sendmail.call_args.kwargs["message"])

	def test_a_batch_with_its_own_template_sends_that_templates_subject(self):
		# Develop's override went through `get_email_template`, which returns
		# subject AND message, so a custom template replaces both.
		frappe.db.set_value("LMS Batch", self.batch.name, "confirmation_email_template", self.template.name)
		with patch("frappe.sendmail") as sendmail:
			self.enrol()
		self.assertEqual(sendmail.call_args.kwargs["subject"], "Custom Enrollment Confirmation")

	def test_the_site_wide_template_is_used_when_the_batch_has_none(self):
		# `LMS Settings.batch_confirmation_template` is a live per-site override on
		# develop (`lms_batch_enrollment.py`'s `send_mail`), read whenever the batch
		# names no template of its own.
		self.use_site_template()
		with patch("frappe.sendmail") as sendmail:
			self.enrol()
		self.assertIn("This site has its own wording", sendmail.call_args.kwargs["message"])
		self.assertEqual(sendmail.call_args.kwargs["subject"], "Custom Site Confirmation")

	def test_the_batch_template_wins_over_the_site_wide_one(self):
		# Develop's precedence, exactly: `batch.confirmation_email_template or
		# frappe.db.get_single_value("LMS Settings", "batch_confirmation_template")`.
		self.use_site_template()
		frappe.db.set_value("LMS Batch", self.batch.name, "confirmation_email_template", self.template.name)
		with patch("frappe.sendmail") as sendmail:
			self.enrol()
		self.assertIn("This batch has its own wording", sendmail.call_args.kwargs["message"])
		self.assertNotIn("This site has its own wording", sendmail.call_args.kwargs["message"])
		self.assertEqual(sendmail.call_args.kwargs["subject"], "Custom Enrollment Confirmation")

	def test_a_disabled_rule_sends_nothing(self):
		# IntegrationTestCase only rolls back at class teardown, not per test (see
		# frappe/tests/classes/integration_test_case.py: addClassCleanup(_rollback_db)
		# runs once, not per setUp/tearDown). Left alone, this write to the shared
		# seeded rule would still read as disabled in every test that runs after
		# this one in the same suite invocation, so restore it explicitly.
		self.addCleanup(
			lambda: frappe.db.set_value("Notification", "LMS Batch Enrollment Confirmation", "enabled", 1)
		)
		self.addCleanup(lambda: frappe.client_cache.delete_value("notifications::LMS Batch Enrollment"))
		frappe.db.set_value("Notification", "LMS Batch Enrollment Confirmation", "enabled", 0)
		frappe.client_cache.delete_value("notifications::LMS Batch Enrollment")
		with patch("frappe.sendmail") as sendmail:
			frappe.get_doc(
				{
					"doctype": "LMS Batch Enrollment",
					"batch": self.batch.name,
					"member": self.student,
				}
			).insert(ignore_permissions=True)
		self.assertFalse(sendmail.called)


class TestCertification(IntegrationTestCase):
	def setUp(self):
		reseed("LMS Certification")
		# Same leaked-cache risk TestBatchConfirmation guards against, for this
		# rule's own doctype key.
		frappe.client_cache.delete_value("notifications::LMS Certificate")

		hash_ = frappe.generate_hash(length=6)

		self.student = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"certification-student-{hash_}@test.com",
					"first_name": "Certification",
					"last_name": "Student",
					"send_welcome_email": 0,
					"roles": [{"role": "LMS Student"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		self.course = frappe.get_doc(
			{
				"doctype": "LMS Course",
				"title": f"Certification Course {hash_}",
				"short_introduction": "A course for the certification notification test.",
				"description": "A course for the certification notification test.",
				"published": 1,
				"instructors": [{"instructor": "Administrator"}],
			}
		).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "LMS Enrollment",
				"member": self.student,
				"course": self.course.name,
			}
		).insert(ignore_permissions=True)

		self.template = get_default_certificate_template()

	def issue(self):
		return frappe.get_doc(
			{
				"doctype": "LMS Certificate",
				"member": self.student,
				"course": self.course.name,
				"issue_date": frappe.utils.nowdate(),
				"template": self.template,
			}
		).insert(ignore_permissions=True)

	def test_issuing_a_certificate_mails_the_member(self):
		with patch("frappe.sendmail") as sendmail:
			self.issue()
		self.assertIn(self.student, sendmail.call_args.kwargs["recipients"])
		self.assertIn("certified", sendmail.call_args.kwargs["subject"].lower())

	def test_the_site_wide_template_replaces_the_body_and_the_subject(self):
		# `LMS Settings.certification_template` is a live per-site override on
		# develop (`lms_certificate.py`'s `send_mail`), and it went through
		# `get_email_template`, so it replaces the subject as well as the body.
		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": f"Certification Override {frappe.generate_hash(length=6)}",
				"subject": "Custom Certification",
				"response": "<p>This site has its own certificate wording.</p>",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_single_value("LMS Settings", "certification_template", template.name)
		self.addCleanup(lambda: frappe.db.set_single_value("LMS Settings", "certification_template", None))
		with patch("frappe.sendmail") as sendmail:
			self.issue()
		self.assertIn("This site has its own certificate wording", sendmail.call_args.kwargs["message"])
		self.assertEqual(sendmail.call_args.kwargs["subject"], "Custom Certification")


class TestEvaluationBooking(IntegrationTestCase):
	def setUp(self):
		reseed("LMS Evaluation Booking")
		# Same leaked-cache risk TestBatchConfirmation guards against, for this
		# rule's own doctype key.
		frappe.client_cache.delete_value("notifications::LMS Certificate Request")

		hash_ = frappe.generate_hash(length=6)

		self.student = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"eval-student-{hash_}@test.com",
					"first_name": "Eval",
					"last_name": "Student",
					"send_welcome_email": 0,
					"roles": [{"role": "LMS Student"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		self.evaluator = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"eval-evaluator-{hash_}@test.com",
					"first_name": "Eval",
					"last_name": "Uator",
					"send_welcome_email": 0,
					"roles": [{"role": "Batch Evaluator"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		# validate_unavailability looks this doc up by name == evaluator email and
		# dereferences it unconditionally; without a row it AttributeErrors on None.
		frappe.get_doc({"doctype": "Course Evaluator", "evaluator": self.evaluator}).insert(
			ignore_permissions=True
		)

		self.course = frappe.get_doc(
			{
				"doctype": "LMS Course",
				"title": f"Evaluation Course {hash_}",
				"short_introduction": "A course for the evaluation booking notification test.",
				"description": "A course for the evaluation booking notification test.",
				"published": 1,
				"instructors": [{"instructor": "Administrator"}],
			}
		).insert(ignore_permissions=True)

	def test_booking_an_evaluation_mails_student_and_evaluator(self):
		with patch("frappe.sendmail") as sendmail:
			frappe.get_doc(
				{
					"doctype": "LMS Certificate Request",
					"member": self.student,
					"evaluator": self.evaluator,
					"course": self.course.name,
					# Tomorrow, not today: validate_if_existing_requests rejects a
					# same-day slot earlier than the current time, which nowdate()
					# would risk depending on when the test runs.
					"date": frappe.utils.add_days(frappe.utils.nowdate(), 1),
					"start_time": "10:00:00",
					"end_time": "10:30:00",
				}
			).insert(ignore_permissions=True)
		addressed = sendmail.call_args.kwargs["recipients"]
		self.assertIn(self.student, addressed)
		self.assertIn(self.evaluator, addressed)

	def test_booking_an_evaluation_renders_the_batch_display_timezone(self):
		# System timezone on this site is Asia/Kolkata (UTC+5:30). A batch in
		# America/Los_Angeles is >12 hours behind, so a 09:00 IST slot both
		# shows a different clock time AND rolls back to the previous day --
		# proving the message renders the *converted* pair, not doc.date /
		# doc.start_time verbatim.
		hash_ = frappe.generate_hash(length=6)
		batch = frappe.get_doc(
			{
				"doctype": "LMS Batch",
				"title": f"Timezone Batch {hash_}",
				"start_date": frappe.utils.add_days(frappe.utils.nowdate(), 1),
				"end_date": frappe.utils.add_days(frappe.utils.nowdate(), 8),
				"description": "Batch for the evaluation timezone test",
				"batch_details": "Batch for the evaluation timezone test",
				"start_time": "09:00:00",
				"end_time": "10:00:00",
				"timezone": "America/Los_Angeles",
				"published": 1,
				"instructors": [{"instructor": "Administrator"}],
			}
		).insert(ignore_permissions=True)

		booked_date = frappe.utils.add_days(frappe.utils.nowdate(), 1)
		booked_time = "09:00:00"

		with patch("frappe.sendmail") as sendmail:
			frappe.get_doc(
				{
					"doctype": "LMS Certificate Request",
					"member": self.student,
					"evaluator": self.evaluator,
					"course": self.course.name,
					"batch_name": batch.name,
					"date": booked_date,
					"start_time": booked_time,
					"end_time": "09:30:00",
				}
			).insert(ignore_permissions=True)

		expected_date, expected_time = convert_from_system_timezone(
			booked_date, booked_time, "America/Los_Angeles"
		)
		self.assertNotEqual(expected_date, frappe.utils.getdate(booked_date), "the date did not roll over")
		expected_label = format_timezone(
			"America/Los_Angeles", datetime.combine(expected_date, expected_time)
		)

		message = sendmail.call_args.kwargs["message"]
		self.assertIn(frappe.utils.format_date(expected_date, "medium"), message)
		self.assertIn(frappe.utils.format_time(expected_time, "short"), message)
		self.assertIn(expected_label, message)
		# The stored system-time clock should not leak into the rendered body.
		self.assertNotIn(frappe.utils.format_time(booked_time, "short"), message)


class TestPublishBroadcasts(IntegrationTestCase):
	def setUp(self):
		reseed("LMS New Course Published", "LMS New Batch Published", "LMS Course Availability")
		# Same leaked-cache risk TestBatchConfirmation guards against, for both
		# doctypes this class's rules watch.
		frappe.client_cache.delete_value("notifications::LMS Course")
		frappe.client_cache.delete_value("notifications::LMS Batch")

		# Both publish rules seed disabled (see their catalogue entries), so the
		# broadcast tests below have to switch them on the way an admin would.
		# Restored afterwards: this class's writes are only rolled back at class
		# teardown, and TestReminders watches LMS Batch too.
		for name in ("LMS New Course Published", "LMS New Batch Published"):
			self.addCleanup(set_enabled, name, 0)
			set_enabled(name, 1)

		hash_ = frappe.generate_hash(length=6)

		self.instructor = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"publish-instructor-{hash_}@test.com",
					"first_name": "Publish",
					"last_name": "Instructor",
					"send_welcome_email": 0,
					"roles": [{"role": "Course Creator"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		self.student = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"publish-student-{hash_}@test.com",
					"first_name": "Publish",
					"last_name": "Student",
					"send_welcome_email": 0,
					"enabled": 1,
					"roles": [{"role": "LMS Student"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		self.disabled_user = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"publish-disabled-{hash_}@test.com",
					"first_name": "Publish",
					"last_name": "Disabled",
					"send_welcome_email": 0,
					"enabled": 0,
					"roles": [{"role": "LMS Student"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		self.interested = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"publish-interested-{hash_}@test.com",
					"first_name": "Publish",
					"last_name": "Interested",
					"send_welcome_email": 0,
					"roles": [{"role": "LMS Student"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def draft_course(self):
		hash_ = frappe.generate_hash(length=6)
		return frappe.get_doc(
			{
				"doctype": "LMS Course",
				"title": f"Publish Broadcast Course {hash_}",
				"short_introduction": "A course for the publish broadcast tests.",
				"description": "A course for the publish broadcast tests.",
				"published": 0,
				"instructors": [{"instructor": self.instructor}],
			}
		).insert(ignore_permissions=True)

	def upcoming_course(self):
		"""A published course still flagged Upcoming.

		The availability rule fires on `upcoming` going falsy, not on `published`
		(develop: `if not self.upcoming and self.has_value_changed("upcoming")`),
		so a course has to start out upcoming for there to be a transition.
		"""
		hash_ = frappe.generate_hash(length=6)
		return frappe.get_doc(
			{
				"doctype": "LMS Course",
				"title": f"Upcoming Course {hash_}",
				"short_introduction": "A course for the availability tests.",
				"description": "A course for the availability tests.",
				"published": 1,
				"upcoming": 1,
				"instructors": [{"instructor": self.instructor}],
			}
		).insert(ignore_permissions=True)

	def register_interest(self, course):
		return frappe.get_doc(
			{"doctype": "LMS Course Interest", "course": course.name, "user": self.interested}
		).insert(ignore_permissions=True)

	def availability_mails(self, sendmail, course):
		# The availability subject is "{{ doc.title }} is available!" and no other
		# rule on LMS Course puts the title in its subject, so the title alone
		# separates this test's mail from the publish broadcast's.
		return [c for c in sendmail.call_args_list if course.title in c.kwargs["subject"]]

	def draft_batch(self):
		hash_ = frappe.generate_hash(length=6)
		return frappe.get_doc(
			{
				"doctype": "LMS Batch",
				"title": f"Publish Broadcast Batch {hash_}",
				"start_date": frappe.utils.add_days(frappe.utils.today(), 7),
				"end_date": frappe.utils.add_days(frappe.utils.today(), 14),
				"description": "A batch for the publish broadcast tests.",
				"batch_details": "A batch for the publish broadcast tests.",
				"start_time": "09:00:00",
				"end_time": "10:00:00",
				"timezone": "Asia/Kolkata",
				"published": 0,
				"instructors": [{"instructor": self.instructor}],
			}
		).insert(ignore_permissions=True)

	def test_publishing_a_course_bccs_every_enabled_user(self):
		course = self.draft_course()
		with patch("frappe.sendmail") as sendmail:
			course.published = 1
			course.save(ignore_permissions=True)
		bcc = sendmail.call_args.kwargs["bcc"]
		self.assertIn(self.student, bcc)
		self.assertNotIn(self.disabled_user, bcc)

	def test_the_instructors_are_addressed_not_bcc(self):
		course = self.draft_course()
		with patch("frappe.sendmail") as sendmail:
			course.published = 1
			course.save(ignore_permissions=True)
		self.assertIn(self.instructor, sendmail.call_args.kwargs["recipients"])

	def test_saving_a_published_course_again_sends_nothing(self):
		course = self.draft_course()
		course.published = 1
		course.save(ignore_permissions=True)
		with patch("frappe.sendmail") as sendmail:
			course.title = f"{course.title} (edited)"
			course.save(ignore_permissions=True)
		self.assertFalse(sendmail.called)

	def test_republishing_a_course_sends_the_broadcast_only_once(self):
		# test_saving_a_published_course_again_sends_nothing doesn't touch
		# `published` at all on its second save, so frappe's own Value Change
		# unchanged-field check (evaluated AFTER the rule's `condition`,
		# `notification.py:852-864`) is what skips it -- that would pass even
		# with `and not doc.notification_sent` deleted from the condition.
		# Unpublishing and republishing flips `published` 0->1 twice, so the
		# built-in check passes both times and only `notification_sent` can
		# stop the second broadcast.
		course = self.draft_course()
		with patch("frappe.sendmail") as sendmail:
			course.published = 1
			course.save(ignore_permissions=True)
			course.published = 0
			course.save(ignore_permissions=True)
			course.published = 1
			course.save(ignore_permissions=True)
		broadcasts = [
			call for call in sendmail.call_args_list if "published on" in call.kwargs["subject"].lower()
		]
		self.assertEqual(len(broadcasts), 1)

	def test_a_course_leaving_upcoming_mails_the_users_who_registered_interest(self):
		course = self.upcoming_course()
		self.register_interest(course)
		with patch("frappe.sendmail") as sendmail:
			course.upcoming = 0
			course.save(ignore_permissions=True)
		availability = self.availability_mails(sendmail, course)
		self.assertTrue(availability)
		self.assertIn(self.interested, availability[0].kwargs["bcc"])

	def test_publishing_a_course_that_is_not_upcoming_mails_no_interested_user(self):
		# The rule watches `upcoming`, not `published` -- develop fired it from
		# `if not self.upcoming and self.has_value_changed("upcoming")`. A publish
		# on a course that was never upcoming changes nothing it watches.
		course = self.draft_course()
		self.register_interest(course)
		with patch("frappe.sendmail") as sendmail:
			course.published = 1
			course.save(ignore_permissions=True)
		self.assertFalse(self.availability_mails(sendmail, course))

	def test_an_unrelated_save_mails_no_interested_user(self):
		course = self.upcoming_course()
		self.register_interest(course)
		with patch("frappe.sendmail") as sendmail:
			course.short_introduction = "Edited, and nothing this rule watches."
			course.save(ignore_permissions=True)
		self.assertFalse(self.availability_mails(sendmail, course))

	def test_marking_a_course_upcoming_again_mails_interested_users_again(self):
		# No `notification_sent`-style guard on "LMS Course Availability" is
		# deliberate (see the comment on its catalogue entry) -- flagging a course
		# upcoming again and then clearing it should re-mail every currently
		# interested user, not just the first cohort.
		course = self.upcoming_course()
		self.register_interest(course)
		course.upcoming = 0
		course.save(ignore_permissions=True)
		course.upcoming = 1
		course.save(ignore_permissions=True)
		with patch("frappe.sendmail") as sendmail:
			course.upcoming = 0
			course.save(ignore_permissions=True)
		availability = self.availability_mails(sendmail, course)
		self.assertTrue(availability)
		self.assertIn(self.interested, availability[0].kwargs["bcc"])

	def test_a_course_creator_clearing_upcoming_still_mails_interested_users(self):
		# The bcc query renders in the session of whoever saved the course, and
		# `LMS Course Interest` grants read to System Manager only. A
		# permission-checked query raises PermissionError there --
		# `send_notification_by_channel` swallows every exception into an Error
		# Log, so the mail vanishes and nothing says so. Administrator, who
		# bypasses permissions, cannot see this class of bug at all, which is why
		# this test switches user.
		course = self.upcoming_course()
		self.register_interest(course)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(self.instructor)
		self.assertNotIn("System Manager", frappe.get_roles())
		with patch("frappe.sendmail") as sendmail:
			course.reload()
			course.upcoming = 0
			course.save()
		frappe.set_user("Administrator")
		availability = self.availability_mails(sendmail, course)
		self.assertTrue(availability)
		self.assertIn(self.interested, availability[0].kwargs["bcc"])

	def test_a_course_creator_publishing_still_bccs_every_enabled_user(self):
		# Same exposure on the publish broadcast's own audience: `User` read is
		# System Manager only, and its `get_permission_query_conditions` silently
		# drops Administrator and Guest for everyone else rather than raising.
		course = self.draft_course()
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(self.instructor)
		with patch("frappe.sendmail") as sendmail:
			course.reload()
			course.published = 1
			course.save()
		frappe.set_user("Administrator")
		broadcasts = [c for c in sendmail.call_args_list if "published on" in c.kwargs["subject"].lower()]
		self.assertTrue(broadcasts)
		self.assertIn("Administrator", broadcasts[0].kwargs["bcc"])
		self.assertIn(self.student, broadcasts[0].kwargs["bcc"])

	def test_publishing_a_batch_bccs_every_enabled_user(self):
		batch = self.draft_batch()
		with patch("frappe.sendmail") as sendmail:
			batch.published = 1
			batch.save(ignore_permissions=True)
		bcc = sendmail.call_args.kwargs["bcc"]
		self.assertIn(self.student, bcc)
		self.assertNotIn(self.disabled_user, bcc)

	def test_the_batch_instructors_are_addressed_not_bcc(self):
		batch = self.draft_batch()
		with patch("frappe.sendmail") as sendmail:
			batch.published = 1
			batch.save(ignore_permissions=True)
		self.assertIn(self.instructor, sendmail.call_args.kwargs["recipients"])


class TestPublishAndAvailabilityOrdering(IntegrationTestCase):
	"""The ordering hazard recorded above LMS_NOTIFICATIONS.

	"LMS Course Availability" and "LMS New Course Published" watch different
	fields, but one save can change both -- an admin clearing Upcoming and ticking
	Published together. The availability mail survives that save only while it is
	evaluated BEFORE the publish rule, which falls out of `Notification`'s
	`sort_field: creation DESC` and therefore out of the catalogue's own order.
	Reverse them and the mail is silenced, not duplicated: the publish rule's
	`set_property_after_alert` re-enters `doc.save()` on the same document object,
	the availability rule is evaluated inside that reentrant save (where
	`get_doc_before_save()` already carries the new `upcoming`, so core's Value
	Change check finds nothing changed and returns), and its name is appended to
	`flags.notifications_executed` all the same -- so the outer loop skips it.

	Both directions are pinned here so the comment cannot rot and the catalogue
	cannot be reordered silently.
	"""

	def setUp(self):
		reseed("LMS New Course Published", "LMS Course Availability")
		self.addCleanup(set_enabled, "LMS New Course Published", 0)
		set_enabled("LMS New Course Published", 1)

		hash_ = frappe.generate_hash(length=6)
		self.instructor = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"ordering-instructor-{hash_}@test.com",
					"first_name": "Ordering",
					"last_name": "Instructor",
					"send_welcome_email": 0,
					"roles": [{"role": "Course Creator"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.interested = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"ordering-interested-{hash_}@test.com",
					"first_name": "Ordering",
					"last_name": "Interested",
					"send_welcome_email": 0,
					"roles": [{"role": "LMS Student"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def evaluate_first(self, name):
		"""Make `name` the rule core evaluates first.

		`Document.run_notifications` reads the rules with `frappe.get_all`, which
		takes `Notification`'s `sort_field: creation DESC` -- the newer row wins.
		Writing `creation` directly is what makes the order deterministic; two
		inserts a microsecond apart are not. The cached rule list is keyed by
		doctype and holds the order too, so it has to go with them.
		"""
		other = (
			"LMS Course Availability" if name == "LMS New Course Published" else "LMS New Course Published"
		)
		frappe.db.set_value("Notification", other, "creation", "2020-01-01 00:00:00", update_modified=False)
		frappe.db.set_value("Notification", name, "creation", "2020-01-02 00:00:00", update_modified=False)
		frappe.client_cache.delete_keys("notifications::")

	def upcoming_draft_course(self):
		hash_ = frappe.generate_hash(length=6)
		course = frappe.get_doc(
			{
				"doctype": "LMS Course",
				"title": f"Ordering Course {hash_}",
				"short_introduction": "A course for the ordering-hazard tests.",
				"description": "A course for the ordering-hazard tests.",
				"published": 0,
				"upcoming": 1,
				"instructors": [{"instructor": self.instructor}],
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{"doctype": "LMS Course Interest", "course": course.name, "user": self.interested}
		).insert(ignore_permissions=True)
		return course

	def publish_and_clear_upcoming(self, course):
		with patch("frappe.sendmail") as sendmail:
			course.upcoming = 0
			course.published = 1
			course.save(ignore_permissions=True)
		availability = [c for c in sendmail.call_args_list if course.title in c.kwargs["subject"]]
		broadcasts = [c for c in sendmail.call_args_list if "published on" in c.kwargs["subject"].lower()]
		return availability, broadcasts

	def test_the_catalogue_seeds_availability_after_the_publish_rule(self):
		names = rule_names()
		self.assertLess(
			names.index("LMS New Course Published"),
			names.index("LMS Course Availability"),
			"the availability rule must be seeded last so it is the newer row",
		)

	def test_availability_first_mails_both(self):
		self.evaluate_first("LMS Course Availability")
		availability, broadcasts = self.publish_and_clear_upcoming(self.upcoming_draft_course())
		self.assertTrue(availability)
		self.assertIn(self.interested, availability[0].kwargs["bcc"])
		self.assertEqual(len(broadcasts), 1)

	def test_the_publish_rule_first_silences_the_availability_mail(self):
		# Not a double-send -- a silent no-send. This is the hazard the catalogue
		# comment describes, pinned so nobody "fixes" it by reordering the list.
		self.evaluate_first("LMS New Course Published")
		availability, broadcasts = self.publish_and_clear_upcoming(self.upcoming_draft_course())
		self.assertFalse(availability)
		self.assertEqual(len(broadcasts), 1)


class TestReminders(IntegrationTestCase):
	"""LMS Batch Start Reminder / LMS Batch Start Reminder (Recorded) / LMS Live
	Class Reminder -- three "Days Before" rules. `trigger_daily_alerts` is the
	daily scheduler hook these replace; it calls `frappe.db.commit()` after
	every document it evaluates
	(`frappe/email/doctype/notification/notification.py:820-823`), which would
	otherwise commit this test's fixtures to the shared site --
	`IntegrationTestCase`'s rollback only runs once, at class teardown
	(`addClassCleanup(_rollback_db)`,
	`frappe/tests/classes/integration_test_case.py:72`). `trigger()` below
	patches `frappe.db.commit` for the duration of every call.
	"""

	def setUp(self):
		reseed(
			"LMS Batch Start Reminder",
			"LMS Batch Start Reminder (Recorded)",
			"LMS Live Class Reminder",
		)

		hash_ = frappe.generate_hash(length=6)
		self.student = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"reminder-student-{hash_}@test.com",
					"first_name": "Reminder",
					"last_name": "Student",
					"send_welcome_email": 0,
					"roles": [{"role": "LMS Student"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def batch_starting(self, start_date, live=True, published=True):
		hash_ = frappe.generate_hash(length=6)
		return frappe.get_doc(
			{
				"doctype": "LMS Batch",
				"title": f"Reminder Batch {hash_}",
				"start_date": start_date,
				"end_date": frappe.utils.add_days(start_date, 7),
				"description": "Batch for reminder tests",
				"batch_details": "Batch for reminder tests",
				"start_time": "09:00:00",
				"end_time": "10:00:00",
				"timezone": "Asia/Kolkata",
				"published": 1 if published else 0,
				"show_live_class": 1 if live else 0,
				"instructors": [{"instructor": "Administrator"}],
			}
		).insert(ignore_permissions=True)

	def live_class_on(self, batch, date):
		# create_calendar_event throws without a configured Google Calendar --
		# irrelevant to what this rule fires on, so skip it rather than build
		# the Google Calendar / Google Meet Settings fixtures
		# test_lms_live_class.py needs for its own, unrelated purposes.
		with patch("lms.lms.doctype.lms_live_class.lms_live_class.LMSLiveClass.create_calendar_event"):
			hash_ = frappe.generate_hash(length=6)
			return frappe.get_doc(
				{
					"doctype": "LMS Live Class",
					"title": f"Reminder Live Class {hash_}",
					"batch_name": batch.name,
					"date": date,
					"time": "09:00:00",
					"duration": 30,
					"timezone": "Asia/Kolkata",
					"host": "Administrator",
				}
			).insert(ignore_permissions=True)

	def enrol(self, batch, student):
		frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": batch.name, "member": student}).insert(
			ignore_permissions=True
		)

	def trigger(self):
		with patch("frappe.db.commit"):
			trigger_daily_alerts()

	def test_a_live_batch_starting_tomorrow_reminds_its_students(self):
		# Scoped to this batch's own (randomised) title, not a bare subject
		# substring or reminders[0] -- lms-audit.localhost is a shared,
		# long-lived site and already carries unrelated LMS Batch / LMS Live
		# Class rows with real enrollments that legitimately fire the same two
		# rules on the same run (see the report for what was found there).
		# Scoping by title is what tells "this test's mail" apart from theirs.
		batch = self.batch_starting(frappe.utils.add_days(frappe.utils.nowdate(), 1), live=True)
		self.enrol(batch, self.student)
		with patch("frappe.sendmail") as sendmail:
			self.trigger()
		reminders = [c for c in sendmail.call_args_list if batch.title in c.kwargs["subject"]]
		self.assertTrue(reminders)
		self.assertIn("starting tomorrow", reminders[0].kwargs["subject"])
		self.assertIn(self.student, reminders[0].kwargs["bcc"])

	def test_a_recorded_batch_gets_the_other_wording(self):
		batch = self.batch_starting(frappe.utils.add_days(frappe.utils.nowdate(), 1), live=False)
		self.enrol(batch, self.student)
		with patch("frappe.sendmail") as sendmail:
			self.trigger()
		subjects = [
			c.kwargs["subject"] for c in sendmail.call_args_list if batch.title in c.kwargs["subject"]
		]
		self.assertTrue(any("start whenever you're ready" in s for s in subjects))
		self.assertFalse(any("starting tomorrow" in s for s in subjects))

	def test_a_batch_starting_next_week_is_not_reminded(self):
		batch = self.batch_starting(frappe.utils.add_days(frappe.utils.nowdate(), 7), live=True)
		self.enrol(batch, self.student)
		with patch("frappe.sendmail") as sendmail:
			self.trigger()
		matching = [c for c in sendmail.call_args_list if batch.title in c.kwargs["subject"]]
		self.assertFalse(matching)

	def test_a_draft_live_batch_starting_tomorrow_is_not_reminded(self):
		# Develop's `send_batch_start_reminder` selected
		# `{"start_date": add_days(nowdate(), 1), "published": 1}` -- a batch still
		# in draft was never reminded, however live and however soon it starts.
		batch = self.batch_starting(
			frappe.utils.add_days(frappe.utils.nowdate(), 1), live=True, published=False
		)
		self.enrol(batch, self.student)
		with patch("frappe.sendmail") as sendmail:
			self.trigger()
		matching = [c for c in sendmail.call_args_list if batch.title in c.kwargs["subject"]]
		self.assertFalse(matching)

	def test_a_draft_recorded_batch_starting_tomorrow_is_not_reminded(self):
		batch = self.batch_starting(
			frappe.utils.add_days(frappe.utils.nowdate(), 1), live=False, published=False
		)
		self.enrol(batch, self.student)
		with patch("frappe.sendmail") as sendmail:
			self.trigger()
		matching = [c for c in sendmail.call_args_list if batch.title in c.kwargs["subject"]]
		self.assertFalse(matching)

	def test_a_batch_with_no_enrollments_sends_nothing(self):
		batch = self.batch_starting(frappe.utils.add_days(frappe.utils.nowdate(), 1), live=True)
		with patch("frappe.sendmail") as sendmail:
			self.trigger()
		matching = [c for c in sendmail.call_args_list if batch.title in c.kwargs["subject"]]
		self.assertFalse(matching)

	def test_a_live_class_today_reminds_its_students(self):
		batch = self.batch_starting(frappe.utils.add_days(frappe.utils.nowdate(), 30), live=True)
		self.enrol(batch, self.student)
		live_class = self.live_class_on(batch, frappe.utils.nowdate())
		with patch("frappe.sendmail") as sendmail:
			self.trigger()
		reminders = [c for c in sendmail.call_args_list if live_class.title in c.kwargs["subject"]]
		self.assertTrue(reminders)
		self.assertIn(self.student, reminders[0].kwargs["bcc"])

	def test_a_live_class_tomorrow_is_not_reminded_yet(self):
		batch = self.batch_starting(frappe.utils.add_days(frappe.utils.nowdate(), 30), live=True)
		self.enrol(batch, self.student)
		live_class = self.live_class_on(batch, frappe.utils.add_days(frappe.utils.nowdate(), 1))
		with patch("frappe.sendmail") as sendmail:
			self.trigger()
		matching = [c for c in sendmail.call_args_list if live_class.title in c.kwargs["subject"]]
		self.assertFalse(matching)

	def test_a_live_class_with_no_enrollments_sends_nothing(self):
		batch = self.batch_starting(frappe.utils.add_days(frappe.utils.nowdate(), 30), live=True)
		live_class = self.live_class_on(batch, frappe.utils.nowdate())
		with patch("frappe.sendmail") as sendmail:
			self.trigger()
		matching = [c for c in sendmail.call_args_list if live_class.title in c.kwargs["subject"]]
		self.assertFalse(matching)


class TestPaymentReminder(IntegrationTestCase):
	"""LMS Payment Reminder -- the first `Method`-event rule. The daily job
	(`send_payment_reminder`) keeps its own selection (skipping a payment already
	paid under a different payment id, and a now-sold-out batch) and fires this
	rule per surviving LMS Payment via `doc.run_method("lms_notify")`.

	lms-audit.localhost is shared and long-lived; confirmed on 2026-09-05 that
	every pre-existing unpaid "LMS Course" payment on it predates
	`add_days(nowdate(), -1)`, so `send_payment_reminder`'s own creation-date
	filter already excludes them on this class's first test. It does NOT
	exclude an *earlier test method's own* incomplete payment though --
	IntegrationTestCase rolls back only at class teardown (see TestReminders'
	docstring above), so that payment is still unpaid and freshly created when
	a later test method calls send_payment_reminder() again. `calls_to_me`
	below scopes every assertion to this test's own student instead of trusting
	`sendmail.call_args` (the last call) to be about this test's own payment.
	Also restore every Settings/Notification mutation and clear the doctype's
	client_cache entry, the same leaked-cache risk TestBatchConfirmation guards
	against.
	"""

	def setUp(self):
		reseed("LMS Payment Reminder")
		frappe.client_cache.delete_value("notifications::LMS Payment")

		frappe.db.set_single_value("LMS Settings", "send_payment_reminders_for_course", 1)
		self.addCleanup(
			lambda: frappe.db.set_single_value("LMS Settings", "send_payment_reminders_for_course", 0)
		)

		hash_ = frappe.generate_hash(length=6)

		self.student = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"payment-reminder-student-{hash_}@test.com",
					"first_name": "Payment",
					"last_name": "Student",
					"send_welcome_email": 0,
					"roles": [{"role": "LMS Student"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		self.instructor = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"payment-reminder-instructor-{hash_}@test.com",
					"first_name": "Payment",
					"last_name": "Instructor",
					"send_welcome_email": 0,
					"roles": [{"role": "Course Creator"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		self.course = frappe.get_doc(
			{
				"doctype": "LMS Course",
				"title": f"Payment Reminder Course {hash_}",
				"short_introduction": "A course for the payment reminder notification test.",
				"description": "A course for the payment reminder notification test.",
				"published": 1,
				"instructors": [{"instructor": self.instructor}],
			}
		).insert(ignore_permissions=True)

		if not frappe.db.exists("LMS Source", "Website"):
			frappe.get_doc({"doctype": "LMS Source", "source": "Website"}).insert(ignore_permissions=True)

		self.address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": f"Payment Reminder {hash_}",
				"address_type": "Billing",
				"address_line1": "1 Test Street",
				"city": "Mumbai",
				"country": "India",
				"email_id": self.student,
			}
		).insert(ignore_permissions=True)

	def incomplete_payment(self):
		return frappe.get_doc(
			{
				"doctype": "LMS Payment",
				"member": self.student,
				"billing_name": "Payment Reminder Tester",
				"address": self.address.name,
				"source": "Website",
				"amount": 1000,
				"currency": "INR",
				"payment_for_document_type": "LMS Course",
				"payment_for_document": self.course.name,
			}
		).insert(ignore_permissions=True)

	def calls_to_me(self, sendmail):
		# IntegrationTestCase rolls back only at class teardown (see
		# TestReminders' own docstring above), so an earlier test method's
		# incomplete payment is still sitting in the DB, unpaid, when a later
		# test method's own send_payment_reminder() call runs -- and matches
		# the same query. `sendmail.call_args` (the *last* call) can belong to
		# that leftover payment instead of this test's own, so every assertion
		# here is scoped to calls addressed to this test's own student.
		return [c for c in sendmail.call_args_list if self.student in c.kwargs["recipients"]]

	def test_an_incomplete_payment_reminds_the_payer(self):
		self.incomplete_payment()
		with patch("frappe.sendmail") as sendmail:
			send_payment_reminder()
		self.assertTrue(self.calls_to_me(sendmail))

	def test_the_payment_document_instructors_are_cced(self):
		self.incomplete_payment()
		with patch("frappe.sendmail") as sendmail:
			send_payment_reminder()
		calls = self.calls_to_me(sendmail)
		self.assertTrue(calls)
		self.assertIn(self.instructor, calls[0].kwargs["cc"])

	def test_a_completed_payment_reminds_nobody(self):
		payment = self.incomplete_payment()
		frappe.db.set_value("LMS Payment", payment.name, "payment_received", 1)
		with patch("frappe.sendmail") as sendmail:
			send_payment_reminder()
		self.assertFalse(self.calls_to_me(sendmail))

	def test_a_disabled_rule_stops_the_job_mailing(self):
		self.incomplete_payment()
		self.addCleanup(lambda: frappe.db.set_value("Notification", "LMS Payment Reminder", "enabled", 1))
		self.addCleanup(lambda: frappe.client_cache.delete_value("notifications::LMS Payment"))
		frappe.db.set_value("Notification", "LMS Payment Reminder", "enabled", 0)
		frappe.client_cache.delete_value("notifications::LMS Payment")
		with patch("frappe.sendmail") as sendmail:
			send_payment_reminder()
		self.assertFalse(self.calls_to_me(sendmail))

	def test_the_settings_template_override_replaces_the_default_body(self):
		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": f"Payment Reminder Override {frappe.generate_hash(length=6)}",
				"subject": "Custom Payment Reminder",
				"response": "<p>This site has its own wording.</p>",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_single_value("LMS Settings", "payment_reminder_template", template.name)
		self.addCleanup(lambda: frappe.db.set_single_value("LMS Settings", "payment_reminder_template", None))
		self.incomplete_payment()
		with patch("frappe.sendmail") as sendmail:
			send_payment_reminder()
		calls = self.calls_to_me(sendmail)
		self.assertTrue(calls)
		self.assertIn("This site has its own wording", calls[0].kwargs["message"])

	def test_the_settings_template_override_replaces_the_subject_too(self):
		# Develop's override went through `get_email_template`, which returns
		# subject AND message.
		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": f"Payment Reminder Subject Override {frappe.generate_hash(length=6)}",
				"subject": "Custom Payment Reminder",
				"response": "<p>This site has its own wording.</p>",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_single_value("LMS Settings", "payment_reminder_template", template.name)
		self.addCleanup(lambda: frappe.db.set_single_value("LMS Settings", "payment_reminder_template", None))
		self.incomplete_payment()
		with patch("frappe.sendmail") as sendmail:
			send_payment_reminder()
		calls = self.calls_to_me(sendmail)
		self.assertTrue(calls)
		self.assertEqual(calls[0].kwargs["subject"], "Custom Payment Reminder")

	def test_an_override_written_against_develops_args_still_renders(self):
		# Develop rendered the override with the sender's own flat `args` dict
		# (`send_mail` in lms_payment.py on upstream/develop: billing_name, type,
		# title, link), so every override written before this branch names those
		# and never `doc`. frappe's jenv uses DebugUndefined, which emits an
		# unknown name verbatim rather than blank, so a context of `{"doc": doc}`
		# alone mails the literal text `{{ billing_name }}`.
		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": f"Payment Reminder Legacy Args {frappe.generate_hash(length=6)}",
				"subject": "Complete your {{ type }} payment",
				"response": "<p>Hi {{ billing_name }}, about {{ title }}. {{ link }}</p>",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_single_value("LMS Settings", "payment_reminder_template", template.name)
		self.addCleanup(lambda: frappe.db.set_single_value("LMS Settings", "payment_reminder_template", None))
		self.incomplete_payment()
		with patch("frappe.sendmail") as sendmail:
			send_payment_reminder()
		calls = self.calls_to_me(sendmail)
		self.assertTrue(calls)
		message = calls[0].kwargs["message"]
		self.assertNotIn("{{", message)
		self.assertIn("Payment Reminder Tester", message)
		self.assertIn(self.course.title, message)
		self.assertEqual(calls[0].kwargs["subject"], "Complete your course payment")

	def test_a_use_html_override_is_honoured(self):
		# Core reads an Email Template's body through `EmailTemplate.response_`,
		# which returns `response_html` when Use HTML is ticked and leaves
		# `response` empty in that case. Reading the raw `response` column returns
		# "" for such a template, the `{% if override %}` guard falls through, and
		# the site's own wording is silently replaced by the built-in copy.
		template = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": f"Payment Reminder Use HTML {frappe.generate_hash(length=6)}",
				"subject": "Custom HTML Reminder",
				"use_html": 1,
				"response_html": "<p>This site ticked Use HTML.</p>",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_single_value("LMS Settings", "payment_reminder_template", template.name)
		self.addCleanup(lambda: frappe.db.set_single_value("LMS Settings", "payment_reminder_template", None))
		self.incomplete_payment()
		with patch("frappe.sendmail") as sendmail:
			send_payment_reminder()
		calls = self.calls_to_me(sendmail)
		self.assertTrue(calls)
		self.assertIn("This site ticked Use HTML", calls[0].kwargs["message"])


class TestJobMails(IntegrationTestCase):
	"""LMS Job Application (a plain New rule) and LMS Job Post Reported (the
	second and last Method-event rule, via report()). Job Opportunity and LMS
	Job Application are both freshly created per test method here, so -- unlike
	the shared fixtures in the classes above -- no cleanup/restore is needed for
	them; only the doctype-keyed notifications cache needs clearing.
	"""

	def setUp(self):
		reseed("LMS Job Application", "LMS Job Post Reported")
		frappe.client_cache.delete_value("notifications::LMS Job Application")
		frappe.client_cache.delete_value("notifications::Job Opportunity")

		hash_ = frappe.generate_hash(length=6)

		self.student = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"job-applicant-{hash_}@test.com",
					"first_name": "Job",
					"last_name": "Applicant",
					"send_welcome_email": 0,
					"roles": [{"role": "LMS Student"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

		self.job = frappe.get_doc(
			{
				"doctype": "Job Opportunity",
				"job_title": f"Job Mail Tester {hash_}",
				"location": "Remote",
				"country": "India",
				"type": "Full Time",
				"company_name": f"Job Mail Co {hash_}",
				"company_website": "https://example.com",
				"company_logo": "/files/job-mail-logo.png",
				"company_email_address": f"employer-{hash_}@test.com",
				"description": "A job for the job-mail notification tests.",
			}
		).insert(ignore_permissions=True)

	def apply(self, resume="/files/job-mail-resume.pdf"):
		return frappe.get_doc(
			{
				"doctype": "LMS Job Application",
				"job": self.job.name,
				"user": self.student,
				"job_title": self.job.job_title,
				"resume": resume,
			}
		).insert(ignore_permissions=True)

	def test_applying_mails_the_company_address(self):
		with patch("frappe.sendmail") as sendmail:
			self.apply()
		self.assertIn(self.job.company_email_address, sendmail.call_args.kwargs["recipients"])

	def test_the_employer_copy_carries_a_to_header(self):
		# `send_an_email` passes `expose_recipients="header"`, and email_body.py
		# renders `"To": ", ".join(self.recipients)`. A rule whose only recipient
		# row is a cc leaves `recipients` empty, so the employer's copy went out
		# with a blank To: -- a common spam-filter trigger -- and
		# `make_communication` was called with no recipients either.
		with patch("frappe.sendmail") as sendmail:
			self.apply()
		self.assertTrue(sendmail.call_args.kwargs["recipients"])

	def test_applying_attaches_the_resume(self):
		with patch("frappe.sendmail") as sendmail:
			self.apply(resume="/files/job-mail-resume.pdf")
		attachments = sendmail.call_args.kwargs["attachments"]
		self.assertIn({"file_url": "/files/job-mail-resume.pdf"}, attachments)

	def test_a_missing_company_email_sends_nothing_not_the_literal_none(self):
		# frappe.db.get_value returning None renders as the four-character
		# string "None" in a bare `{{ }}` expression, and
		# get_emails_from_template's filter(None, ...) drops an empty string
		# but not that word -- so a naive JOB_EMPLOYER_CC would cc "None"
		# instead of quietly addressing nobody. company_email_address is
		# `reqd`, so this bypasses validation the way the field could never be
		# emptied through the form.
		frappe.db.set_value("Job Opportunity", self.job.name, "company_email_address", None)
		with patch("frappe.sendmail") as sendmail:
			self.apply()
		self.assertFalse(sendmail.called)

	def test_reporting_a_job_mails_system_managers_with_the_reason(self):
		with patch("frappe.sendmail") as sendmail:
			report(job=self.job.name, reason="Spam listing")
		self.assertIn("Spam listing", sendmail.call_args.kwargs["message"])

	def test_reporting_a_job_records_the_reason_on_the_job(self):
		report(job=self.job.name, reason="Spam listing")
		row = frappe.db.get_value(
			"Job Opportunity", self.job.name, ["reported_by", "report_reason"], as_dict=True
		)
		self.assertEqual(row.report_reason, "Spam listing")
		self.assertEqual(row.reported_by, frappe.session.user)

	def test_report_rejects_non_string_arguments(self):
		# frappe's whitelist argument coercion is switched off in several run
		# modes (see local-runner-disabled-whitelist-type-validation in
		# MEMORY.md), so it would silently coerce a list/int into a string
		# before the guard ever saw it -- call the unwrapped function to prove
		# the isinstance checks themselves reject a bad argument.
		with self.assertRaises(frappe.ValidationError):
			report.__wrapped__(job=self.job.name, reason=["not", "a", "string"])

	def test_report_rejects_an_empty_reason(self):
		with self.assertRaises(frappe.ValidationError):
			report.__wrapped__(job=self.job.name, reason="   ")

	def test_report_rejects_a_reason_over_the_length_cap(self):
		with self.assertRaises(frappe.ValidationError):
			report.__wrapped__(job=self.job.name, reason="x" * 1001)

	def test_reported_by_is_the_session_user_not_a_caller_supplied_value(self):
		# report()'s signature takes no reported_by argument at all -- the only
		# way this could be spoofed is the write itself reading from the wrong
		# place. Switching the session to a non-Administrator user before
		# calling makes that visible: a bug that hardcoded "Administrator" (the
		# user every other test in this class runs as) would pass every other
		# assertion here and only this test would catch it.
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(self.student)
		report.__wrapped__(job=self.job.name, reason="Spam listing")
		self.assertEqual(frappe.db.get_value("Job Opportunity", self.job.name, "reported_by"), self.student)


class TestMention(IntegrationTestCase):
	"""A discussion-mention no longer sends a mail (notify_mentions_via_email
	was deleted, not converted -- its recipients are parsed out of the reply
	text, so no trigger/condition/role/field could ever address them as a
	Notification rule). notify_mentions_on_portal, the in-app half of the
	same handle_notifications call, stays and is the actual replacement --
	this class proves both halves: no mail, AND the Notification Log row
	still lands for the mentioned user. Scoped to self.student, not a bare
	`type` filter, since Notification Log is a shared table other suites in
	this run also write "Mention" rows into.

	Frappe core's own Notification Log.after_insert (frappe/desk/doctype/
	notification_log/notification_log.py) independently emails a "Mention"-
	type log by default -- "Mention" is not in the notification_skip_email_types
	hook (only "Alert" is), and every User gets a Notification Settings row at
	after_insert seeded with every non-skipped type opted in
	(create_notification_settings). So notify_mentions_on_portal's own
	Notification Log insert would trigger a *second*, unrelated email --
	Frappe's generic "new_notification" template, not the deleted
	"mention_template" -- confounding "no mail" for a reason that has nothing
	to do with notify_mentions_via_email. That generic per-user opt-out email
	is deliberate, pre-existing, out-of-scope framework behaviour this task
	does not touch, so it is switched off for this test's own student only,
	isolating the assertion to what Task 9 actually changed.
	"""

	def setUp(self):
		hash_ = frappe.generate_hash(length=6)

		self.student = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"mention-student-{hash_}@test.com",
					"first_name": "Mention",
					"last_name": "Student",
					"send_welcome_email": 0,
					"roles": [{"role": "LMS Student"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		frappe.db.set_value("Notification Settings", self.student, "enable_email_notifications", 0)

		self.batch = frappe.get_doc(
			{
				"doctype": "LMS Batch",
				"title": f"Mention Batch {hash_}",
				"start_date": frappe.utils.today(),
				"end_date": frappe.utils.add_days(frappe.utils.today(), 7),
				"description": "Batch for the mention notification test",
				"batch_details": "Batch for the mention notification test",
				"start_time": "09:00:00",
				"end_time": "10:00:00",
				"timezone": "Asia/Kolkata",
				"published": 1,
				"instructors": [{"instructor": "Administrator"}],
			}
		).insert(ignore_permissions=True)

		self.topic = frappe.get_doc(
			{
				"doctype": "Discussion Topic",
				"title": f"Mention Topic {hash_}",
				"reference_doctype": "LMS Batch",
				"reference_docname": self.batch.name,
			}
		).insert(ignore_permissions=True)

	def test_a_mention_posts_in_app_and_sends_no_mail(self):
		with patch("frappe.sendmail") as sendmail:
			frappe.get_doc(
				{
					"doctype": "Discussion Reply",
					"topic": self.topic.name,
					"reply": f'<span class="mention" data-id="{self.student}">@Student</span> look at this',
				}
			).insert(ignore_permissions=True)
		self.assertFalse(sendmail.called)
		self.assertTrue(frappe.db.exists("Notification Log", {"for_user": self.student, "type": "Mention"}))


class TestSettingsEndpoints(IntegrationTestCase):
	"""Settings > Notifications: `get_notification_rules` and
	`set_notification_rule`, the two gated endpoints the page reads and writes
	through instead of a doctype resource -- core Notification grants DocPerms
	to System Manager only, and this page is reachable by Moderators too.

	Every test that needs a non-LMS Notification row creates and deletes its
	own -- an earlier revision shared one fixed-name row across two test
	methods relying on unittest's alphabetical ordering to leave it behind;
	that made the refusal test fail with DoesNotExistError when run alone.
	"""

	def setUp(self):
		seed_notifications()

	def foreign_rule(self):
		"""A Notification row that is not LMS's, for the "not ours" tests.

		Created and torn down per test rather than shared -- see the class
		docstring.
		"""
		name = f"Not An LMS Rule {frappe.generate_hash(length=6)}"
		frappe.get_doc(
			{
				"doctype": "Notification",
				"name": name,
				"document_type": "User",
				"event": "New",
				"channel": "Email",
				"subject": "x",
				"message": "x",
			}
		).insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, "Notification", name, force=True, ignore_permissions=True)
		return name

	def test_the_endpoint_serves_every_lms_rule(self):
		served = [row["name"] for row in get_notification_rules()]
		for name in rule_names():
			self.assertIn(name, served)

	def test_it_serves_no_rule_from_another_app(self):
		foreign = self.foreign_rule()
		self.assertNotIn(foreign, [row["name"] for row in get_notification_rules()])

	def test_search_narrows_by_name_and_subject(self):
		self.assertTrue(
			all(
				"payment" in row["name"].lower() or "payment" in (row["subject"] or "").lower()
				for row in get_notification_rules(search="payment")
			)
		)

	def test_writing_a_rule_that_is_not_ours_is_refused(self):
		foreign = self.foreign_rule()
		with self.assertRaises(frappe.ValidationError):
			set_notification_rule(name=foreign, enabled=0)

	def test_a_non_string_search_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			get_notification_rules.__wrapped__(search={"$ne": 1})

	def test_writing_the_subject_stores_it(self):
		original = next(rule for rule in LMS_NOTIFICATIONS if rule["name"] == "LMS Certification")["subject"]
		self.addCleanup(lambda: frappe.db.set_value("Notification", "LMS Certification", "subject", original))
		set_notification_rule(name="LMS Certification", subject="You did it")
		self.assertEqual(frappe.db.get_value("Notification", "LMS Certification", "subject"), "You did it")

	def test_slack_and_sms_are_refused_lms_has_no_send_path_for_either(self):
		self.addCleanup(lambda: frappe.db.set_value("Notification", "LMS Certification", "channel", "Email"))
		for channel in ("Slack", "SMS"):
			with self.assertRaises(frappe.ValidationError):
				set_notification_rule(name="LMS Certification", channel=channel)
		self.assertEqual(frappe.db.get_value("Notification", "LMS Certification", "channel"), "Email")

	def test_a_valid_channel_change_is_written(self):
		# `channel` is `set_only_once` on core Notification (notification.json),
		# so `doc.save()` throws CannotChangeConstantError for ANY change to it
		# -- a supported value included. Every seeded rule already has a channel
		# from insert_rule(), so the write has to go around the ORM entirely, and
		# this is what proves it actually lands rather than being silently
		# swallowed by the same exception the refusal tests above also raise.
		self.addCleanup(lambda: frappe.db.set_value("Notification", "LMS Certification", "channel", "Email"))
		row = set_notification_rule(name="LMS Certification", channel="System Notification")
		self.assertEqual(row["channel"], "System Notification")
		self.assertEqual(
			frappe.db.get_value("Notification", "LMS Certification", "channel"), "System Notification"
		)

	def test_writing_only_enabled_does_not_blank_the_subject(self):
		original = next(rule for rule in LMS_NOTIFICATIONS if rule["name"] == "LMS Certification")["subject"]
		self.addCleanup(lambda: frappe.db.set_value("Notification", "LMS Certification", "enabled", 1))
		set_notification_rule(name="LMS Certification", enabled=0)
		row = frappe.db.get_value("Notification", "LMS Certification", ["enabled", "subject"], as_dict=True)
		self.assertEqual(row.enabled, 0)
		self.assertEqual(row.subject, original)

	def test_an_empty_subject_is_refused(self):
		# The frontend's own FormControl `required` is not a server guarantee --
		# a direct call (or a client that skips the form) could still send an
		# empty or whitespace-only subject, which would mail with no subject.
		with self.assertRaises(frappe.ValidationError):
			set_notification_rule.__wrapped__(name="LMS Certification", subject="   ")

	def test_set_notification_rule_rejects_a_non_string_name(self):
		with self.assertRaises(frappe.ValidationError):
			set_notification_rule.__wrapped__(name=123)

	def test_set_notification_rule_rejects_a_non_int_enabled(self):
		with self.assertRaises(frappe.ValidationError):
			set_notification_rule.__wrapped__(name="LMS Certification", enabled="not-an-int")

	def test_set_notification_rule_rejects_an_invalid_channel_type(self):
		with self.assertRaises(frappe.ValidationError):
			set_notification_rule.__wrapped__(name="LMS Certification", channel=123)

	def test_set_notification_rule_rejects_a_non_int_send_system_notification(self):
		with self.assertRaises(frappe.ValidationError):
			set_notification_rule.__wrapped__(name="LMS Certification", send_system_notification="yes")

	def test_set_notification_rule_rejects_a_non_string_subject(self):
		with self.assertRaises(frappe.ValidationError):
			set_notification_rule.__wrapped__(name="LMS Certification", subject=123)

	def test_set_notification_rule_rejects_a_non_string_message(self):
		with self.assertRaises(frappe.ValidationError):
			set_notification_rule.__wrapped__(name="LMS Certification", message=123)


class TestSettingsEndpointRoleSplit(IntegrationTestCase):
	"""`subject` and `message` require System Manager; everything else --
	reading, `enabled`, `channel`, `send_system_notification` -- stays open to
	a Moderator.

	A rule's `message` renders as Jinja at send time under
	`restrict_globals=True` (frappe/utils/safe_exec.py), and that restricted
	namespace still exposes `frappe.db.sql`, `frappe.get_all` (called with
	`ignore_permissions=True` inside safe_exec) and `frappe.db.get_value` --
	none permission-checked. A Moderator who could write `message` could read
	any table on the site through it, which is why core itself reserves
	Notification writes to System Manager. The Administrator test runner
	bypasses `frappe.only_for` entirely (`local.session.user ==
	"Administrator"` returns before the role check even runs -- frappe/
	__init__.py), so every test below switches to a real Moderator-only user.
	"""

	def setUp(self):
		seed_notifications()

		hash_ = frappe.generate_hash(length=6)
		self.moderator = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"notif-moderator-{hash_}@test.com",
					"first_name": "Notif",
					"last_name": "Moderator",
					"send_welcome_email": 0,
					"roles": [{"role": "Moderator"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_a_moderator_can_read_the_rules(self):
		frappe.set_user(self.moderator)
		served = [row["name"] for row in get_notification_rules()]
		self.assertIn("LMS Certification", served)

	def test_a_moderator_can_toggle_enabled(self):
		self.addCleanup(lambda: frappe.db.set_value("Notification", "LMS Certification", "enabled", 1))
		frappe.set_user(self.moderator)
		row = set_notification_rule(name="LMS Certification", enabled=0)
		self.assertEqual(row["enabled"], 0)

	def test_a_moderator_can_change_the_channel(self):
		self.addCleanup(lambda: frappe.db.set_value("Notification", "LMS Certification", "channel", "Email"))
		frappe.set_user(self.moderator)
		row = set_notification_rule(name="LMS Certification", channel="System Notification")
		self.assertEqual(row["channel"], "System Notification")

	def test_a_moderator_cannot_write_the_subject(self):
		frappe.set_user(self.moderator)
		with self.assertRaises(frappe.PermissionError):
			set_notification_rule(name="LMS Certification", subject="Hijacked")
		# The refusal happened before any write landed.
		self.assertNotEqual(frappe.db.get_value("Notification", "LMS Certification", "subject"), "Hijacked")

	def test_a_moderator_cannot_write_the_message(self):
		frappe.set_user(self.moderator)
		with self.assertRaises(frappe.PermissionError):
			set_notification_rule(name="LMS Certification", message="{{ frappe.db.sql('select 1') }}")
		self.assertNotIn(
			"frappe.db.sql", frappe.db.get_value("Notification", "LMS Certification", "message") or ""
		)

	def test_a_moderator_writing_enabled_alongside_subject_is_still_refused(self):
		# The gate is on the ARGUMENTS given, not on which one a caller expects
		# to be scrutinised -- a Moderator cannot smuggle a subject change in
		# behind an enabled toggle the endpoint would otherwise allow.
		self.addCleanup(lambda: frappe.db.set_value("Notification", "LMS Certification", "enabled", 1))
		frappe.set_user(self.moderator)
		with self.assertRaises(frappe.PermissionError):
			set_notification_rule(name="LMS Certification", enabled=0, subject="Hijacked")

	def test_a_system_manager_can_write_the_subject(self):
		# The split is Moderator-vs-System-Manager, not Moderator-vs-nobody --
		# a plain System Manager (no Moderator role) can still write wording.
		hash_ = frappe.generate_hash(length=6)
		system_manager = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"notif-sysmanager-{hash_}@test.com",
					"first_name": "Notif",
					"last_name": "SysManager",
					"send_welcome_email": 0,
					"roles": [{"role": "System Manager"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		original = next(rule for rule in LMS_NOTIFICATIONS if rule["name"] == "LMS Certification")["subject"]
		self.addCleanup(lambda: frappe.db.set_value("Notification", "LMS Certification", "subject", original))
		frappe.set_user(system_manager)
		row = set_notification_rule(name="LMS Certification", subject="Authored by a System Manager")
		self.assertEqual(row["subject"], "Authored by a System Manager")
