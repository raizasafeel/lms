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
	`seed_notifications` never rewrites a rule the site already has, so on a site
	seeded before a catalogue edit the row under test would be the stale one.
	"""
	for name in names:
		if frappe.db.exists("Notification", name):
			frappe.delete_doc("Notification", name, force=True, ignore_permissions=True)
	seed_notifications()


def set_enabled(name, value):
	"""Flip a seeded rule's Enabled switch the way the settings page does.
	`frappe.db.set_value` writes under the document layer, so the enabled-rules
	cache has to be cleared by hand.
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
		# Develop gated both publish mails behind an LMS Settings Select that
		# defaulted to blank, so a stock site sent neither. Seeded enabled, the
		# first publish after an upgrade would mass-mail every enabled User.
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
		# The enabled-rules cache lives in redis, outside the per-test SQL
		# rollback, so a prior test that disabled this rule leaves an empty entry
		# behind. Clear it so every test starts from the rolled-back DB state.
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
		# IntegrationTestCase rolls back at class teardown, not per test, so this
		# write to the shared seeded rule would read as disabled in every test
		# that runs after this one. Restore it explicitly.
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
		# System timezone here is Asia/Kolkata. A batch in America/Los_Angeles is
		# over 12 hours behind, so a 09:00 IST slot changes both the clock time
		# and the date, proving the message renders the converted pair.
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

		# Both publish rules seed disabled, so the broadcast tests below switch
		# them on the way an admin would. Restored afterwards, because this
		# class rolls back only at teardown and TestReminders watches LMS Batch.
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
		The availability rule fires on `upcoming` going falsy, not on `published`,
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
		# The second-save test never touches `published`, so frappe's own
		# unchanged-field check would skip it even without the condition guard.
		# Republishing flips `published` twice, so only the guard can stop it.
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
		# The rule watches `upcoming`, not `published`. A publish on a course that
		# was never upcoming changes nothing it watches.
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
		# "LMS Course Availability" carries no `notification_sent`-style guard on
		# purpose. Flagging a course upcoming again and clearing it should
		# re-mail every currently interested user, not just the first cohort.
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
		# `LMS Course Interest` grants read to System Manager only. Administrator
		# bypasses permissions, so this test has to switch user to see the bug.
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
	One save can change both `upcoming` and `published`, and the availability
	mail survives it only while its rule is evaluated first. Both directions are
	pinned here so the catalogue cannot be reordered silently.
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
		Core reads the rules newest first, so `creation` is written directly; two
		inserts a microsecond apart are not deterministic. The cached rule list
		holds the order too, so it goes with them.
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
		# Not a double-send but a silent no-send. This is the hazard the catalogue
		# comment describes, pinned so nobody "fixes" it by reordering the list.
		self.evaluate_first("LMS New Course Published")
		availability, broadcasts = self.publish_and_clear_upcoming(self.upcoming_draft_course())
		self.assertFalse(availability)
		self.assertEqual(len(broadcasts), 1)


class TestReminders(IntegrationTestCase):
	"""The three Days Before reminders.
	`trigger_daily_alerts` commits after every document it evaluates, which
	would write this test's fixtures to the shared site. `trigger()` below
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
		# create_calendar_event throws without a configured Google Calendar, and it
		# is irrelevant to what this rule fires on, so skip it rather than build
		# the Google fixtures.
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
		# Scoped to this batch's own randomised title. lms-audit.localhost is a
		# shared site carrying unrelated batches and live classes with real
		# enrollments that fire the same two rules on the same run.
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
		# Develop's `send_batch_start_reminder` filtered on `published`, so a batch
		# still in draft was never reminded, however soon it starts.
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
	"""LMS Payment Reminder, the first Method-event rule.
	`send_payment_reminder` keeps its own selection and fires the rule per
	surviving payment. `calls_to_me` below scopes every assertion to this
	test's own student, because earlier methods leave unpaid rows behind.
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
		# The class rolls back only at teardown, so an earlier method's incomplete
		# payment still matches the same query. `sendmail.call_args` can belong to
		# that leftover, so scope every assertion to this test's own student.
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
		# Develop rendered an override with the sender's own flat `args`, so every
		# override written before this branch names `billing_name`, never `doc`.
		# DebugUndefined prints an unknown name verbatim.
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
		# A Use HTML template keeps its body in `response_html` and leaves
		# `response` empty, so reading `response` alone returns "" and the site's
		# own wording is silently replaced by the built-in copy.
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
	"""LMS Job Application and LMS Job Post Reported.
	Both documents are created fresh per test method, so nothing needs
	restoring afterwards except the doctype-keyed notifications cache.
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
		# A rule whose only recipient row is a cc leaves `recipients` empty, so the
		# employer's copy went out with a blank To header and `make_communication`
		# was called with no recipients either.
		with patch("frappe.sendmail") as sendmail:
			self.apply()
		self.assertTrue(sendmail.call_args.kwargs["recipients"])

	def test_applying_attaches_the_resume(self):
		with patch("frappe.sendmail") as sendmail:
			self.apply(resume="/files/job-mail-resume.pdf")
		attachments = sendmail.call_args.kwargs["attachments"]
		self.assertIn({"file_url": "/files/job-mail-resume.pdf"}, attachments)

	def test_a_missing_company_email_sends_nothing_not_the_literal_none(self):
		# `get_value` returning None renders as the string "None", which
		# `get_emails_from_template` does not drop the way it drops "". The field
		# is `reqd`, so this write bypasses the form's own validation.
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
		# frappe's whitelist argument coercion is off in several run modes and
		# would turn a bad argument into a string before the guard saw it. Call
		# the unwrapped function so the isinstance checks are what reject it.
		with self.assertRaises(frappe.ValidationError):
			report.__wrapped__(job=self.job.name, reason=["not", "a", "string"])

	def test_report_rejects_an_empty_reason(self):
		with self.assertRaises(frappe.ValidationError):
			report.__wrapped__(job=self.job.name, reason="   ")

	def test_report_rejects_a_reason_over_the_length_cap(self):
		with self.assertRaises(frappe.ValidationError):
			report.__wrapped__(job=self.job.name, reason="x" * 1001)

	def test_the_poster_cannot_read_who_reported_them(self):
		# Job Opportunity grants LMS Student read with if_owner, so persisting the
		# reporter on the reported document handed their name to the person they
		# reported. Both report fields are permlevel 1.
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(self.student)
		own_job = frappe.get_doc(
			{
				"doctype": "Job Opportunity",
				"job_title": f"Poster Owned {frappe.generate_hash(length=6)}",
				"location": "Remote",
				"country": "India",
				"type": "Full Time",
				"company_name": "Poster Co",
				"company_website": "https://example.com",
				"company_logo": "/files/job-mail-logo.png",
				"company_email_address": "poster@test.com",
				"description": "A listing owned by the student who posted it.",
			}
		).insert(ignore_permissions=True)

		frappe.set_user("Administrator")
		report.__wrapped__(job=own_job.name, reason="Spam listing")

		frappe.set_user(self.student)
		seen = frappe.get_doc("Job Opportunity", own_job.name)
		seen.apply_fieldlevel_read_permissions()
		# The filter removes the key outright rather than blanking it.
		self.assertIsNone(seen.get("reported_by"))
		self.assertIsNone(seen.get("report_reason"))
		# The listing itself is still theirs to read.
		self.assertEqual(seen.company_name, "Poster Co")

	def test_a_system_manager_still_reads_the_report(self):
		report.__wrapped__(job=self.job.name, reason="Spam listing")
		seen = frappe.get_doc("Job Opportunity", self.job.name)
		seen.apply_fieldlevel_read_permissions()
		self.assertEqual(seen.report_reason, "Spam listing")

	def test_reported_by_is_the_session_user_not_a_caller_supplied_value(self):
		# `report()` takes no reported_by argument, so the only way to spoof it is
		# the write reading from the wrong place. A hardcoded "Administrator"
		# would pass every other assertion here, hence the user switch.
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(self.student)
		report.__wrapped__(job=self.job.name, reason="Spam listing")
		self.assertEqual(frappe.db.get_value("Job Opportunity", self.job.name, "reported_by"), self.student)


class TestMention(IntegrationTestCase):
	"""A discussion mention sends no mail, but still files a Notification Log.
	`notify_mentions_via_email` was deleted rather than converted, because its
	recipients are parsed out of the reply text. Core's own generic mention
	email is switched off for this test's student so it cannot confound the
	assertion.
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
	"""The two gated endpoints the notifications page reads and writes through.
	Core Notification grants DocPerms to System Manager only, and this page is
	reachable by Moderators too. Every test creates and deletes its own non-LMS
	row rather than sharing one.
	"""

	def setUp(self):
		seed_notifications()

	def foreign_rule(self):
		"""A Notification row that is not LMS's, for the "not ours" tests.
		Created and torn down per test rather than shared.
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
		# `channel` is `set_only_once`, so `doc.save()` throws for any change to it,
		# a supported value included. The write has to go around the ORM, and this
		# proves it lands rather than being swallowed by that same exception.
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
		# The frontend's `required` is not a server guarantee. A direct call could
		# still send a whitespace-only subject, which would mail with no subject.
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
	"""`subject` and `message` require System Manager; the rest stays open.
	A rule's `message` renders as Jinja whose restricted namespace still
	exposes unchecked reads, so a Moderator who could write it could read any
	table. Administrator bypasses `frappe.only_for`, so these switch user.
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
		# The gate reads the arguments given, not the one a caller expects to be
		# scrutinised, so a Moderator cannot smuggle a subject change in behind an
		# enabled toggle.
		self.addCleanup(lambda: frappe.db.set_value("Notification", "LMS Certification", "enabled", 1))
		frappe.set_user(self.moderator)
		with self.assertRaises(frappe.PermissionError):
			set_notification_rule(name="LMS Certification", enabled=0, subject="Hijacked")

	def test_a_system_manager_can_write_the_subject(self):
		# The split is Moderator against System Manager, not Moderator against
		# nobody. A plain System Manager can still write wording.
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
