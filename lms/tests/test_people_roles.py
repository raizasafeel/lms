# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, nowdate

from lms.lms.doctype.lms_certificate_evaluation.lms_certificate_evaluation import can_evaluate
from lms.lms.people import EDITOR, GRADER, LIVE_CLASS_CONDUCTOR, change_owner, get_graders, is_grader
from lms.lms.permissions import can_author_course, can_instruct_batch, can_run_live_classes, evaluates_batch
from lms.lms.test_helpers import BaseTestUtils
from lms.patches.v2_0.move_instructors_and_evaluators_to_people import execute as migrate_people


def people(doc):
	return [(row.member, row.role) for row in doc.people]


class PeopleFixtures(BaseTestUtils):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		suffix = frappe.generate_hash(length=6)
		user = cls._create_user
		cls.editor = user(f"ppl-editor-{suffix}@example.com", "Eda", "Editor", ["Course Creator"])
		cls.other_editor = user(f"ppl-editor2-{suffix}@example.com", "Ola", "Editor", ["Course Creator"])
		cls.grader = user(f"ppl-grader-{suffix}@example.com", "Gus", "Grader", ["Batch Evaluator"])
		cls.second_grader = user(f"ppl-grader2-{suffix}@example.com", "Gia", "Grader", ["Batch Evaluator"])
		cls.student = user(f"ppl-student-{suffix}@example.com", "Stu", "Dent", ["LMS Student"])
		cls.moderator = user(f"ppl-mod-{suffix}@example.com", "Mo", "Derator", ["Moderator"])
		cls._require_no_moderators(cls.editor.name, cls.grader.name, cls.student.name)
		cls._create_evaluator(cls.grader.name)
		cls.suffix = suffix

	def make_course(self, **fields):
		course = frappe.new_doc("LMS Course")
		course.update(
			{
				"title": f"People Course {frappe.generate_hash(length=6)}",
				"short_introduction": "People",
				"description": "People",
				"instructors": [{"instructor": self.editor.name}],
				**fields,
			}
		)
		course.insert()
		return course

	def make_batch(self, course, **fields):
		batch = frappe.new_doc("LMS Batch")
		batch.update(
			{
				"title": f"People Batch {frappe.generate_hash(length=6)}",
				"start_date": nowdate(),
				"end_date": add_days(nowdate(), 10),
				"start_time": "09:00:00",
				"end_time": "11:00:00",
				"timezone": "Asia/Kolkata",
				"description": "People",
				"batch_details": "People",
				"instructors": [{"instructor": self.editor.name}],
				"courses": [{"course": course}],
				**fields,
			}
		)
		batch.insert()
		return batch


class TestPeopleSync(PeopleFixtures):
	def test_legacy_instructors_and_evaluator_land_in_people(self):
		course = self.make_course(evaluator=self.grader.name)
		self.assertEqual(people(course), [(self.editor.name, EDITOR), (self.grader.name, GRADER)])

	def test_people_derive_the_legacy_fields(self):
		course = self.make_course()
		course.set("people", [])
		course.append("people", {"member": self.other_editor.name, "role": EDITOR})
		course.append("people", {"member": self.grader.name, "role": GRADER})
		course.save()
		self.assertEqual([row.instructor for row in course.instructors], [self.other_editor.name])
		self.assertEqual(course.evaluator, self.grader.name)

	def test_removing_the_grader_clears_the_evaluator(self):
		course = self.make_course(evaluator=self.grader.name)
		course.set("people", [row for row in course.people if row.role != GRADER])
		course.save()
		self.assertIsNone(course.evaluator)

	def test_batch_graders_become_batch_course_evaluators(self):
		course = self.make_course()
		batch = self.make_batch(course.name)
		batch.append("people", {"member": self.grader.name, "role": GRADER})
		batch.save()
		self.assertEqual(batch.courses[0].evaluator, self.grader.name)
		self.assertEqual(get_graders(course.name, batch.name), [self.grader.name])

	def test_a_grader_gets_a_course_evaluator_schedule(self):
		course = self.make_course()
		self.assertFalse(frappe.db.exists("Course Evaluator", self.second_grader.name))
		course.append("people", {"member": self.second_grader.name, "role": GRADER})
		course.save()
		self.assertEqual(course.evaluator, self.second_grader.name)
		self.assertTrue(frappe.db.exists("Course Evaluator", self.second_grader.name))


class TestPeopleValidation(PeopleFixtures):
	def add(self, doc, member, role):
		doc.append("people", {"member": member, "role": role})
		doc.save()

	def test_only_evaluators_can_be_graders(self):
		course = self.make_course()
		with self.assertRaises(frappe.ValidationError):
			self.add(course, self.other_editor.name, GRADER)

	def test_only_course_creators_can_be_editors(self):
		course = self.make_course()
		with self.assertRaises(frappe.ValidationError):
			self.add(course, self.grader.name, EDITOR)

	def test_moderators_can_hold_any_role(self):
		course = self.make_course()
		self.add(course, self.moderator.name, GRADER)
		self.add(course, self.moderator.name, EDITOR)
		self.assertIn((self.moderator.name, GRADER), people(course))

	def test_a_course_has_no_live_class_conductors(self):
		course = self.make_course()
		with self.assertRaises(frappe.ValidationError):
			self.add(course, self.editor.name, LIVE_CLASS_CONDUCTOR)

	def test_a_role_is_listed_once(self):
		course = self.make_course()
		with self.assertRaises(frappe.ValidationError):
			self.add(course, self.editor.name, EDITOR)

	def test_conductors_need_a_staff_role(self):
		batch = self.make_batch(self.make_course().name)
		with self.assertRaises(frappe.ValidationError):
			self.add(batch, self.student.name, LIVE_CLASS_CONDUCTOR)
		batch.reload()
		self.add(batch, self.grader.name, LIVE_CLASS_CONDUCTOR)


class TestPeoplePermissions(PeopleFixtures):
	def test_editor_edits_and_grader_does_not(self):
		course = self.make_course(evaluator=self.grader.name)
		self.assertTrue(can_author_course(course.name, user=self.editor.name))
		self.assertFalse(can_author_course(course.name, user=self.grader.name))

	def test_only_graders_grade(self):
		course = self.make_course(evaluator=self.grader.name)
		self.assertTrue(is_grader(self.grader.name, course.name))
		self.assertTrue(can_evaluate(self.grader.name, self.student.name, course.name))
		self.assertFalse(is_grader(self.editor.name, course.name))
		self.assertFalse(can_evaluate(self.editor.name, self.student.name, course.name))

	def test_a_grader_who_loses_the_evaluator_role_stops_grading(self):
		course = self.make_course(evaluator=self.grader.name)
		frappe.db.delete("Has Role", {"parent": self.grader.name, "role": "Batch Evaluator"})
		frappe.clear_cache(user=self.grader.name)
		self.assertFalse(is_grader(self.grader.name, course.name))

	def test_batch_grader_reads_but_does_not_edit(self):
		batch = self.make_batch(self.make_course().name)
		batch.append("people", {"member": self.grader.name, "role": GRADER})
		batch.save()
		self.assertTrue(evaluates_batch(batch.name, user=self.grader.name))
		self.assertFalse(can_instruct_batch(batch.name, user=self.grader.name))
		self.assertTrue(frappe.has_permission("LMS Batch", "read", batch.name, user=self.grader.name))
		self.assertFalse(frappe.has_permission("LMS Batch", "write", batch.name, user=self.grader.name))

	def test_conductor_runs_live_classes_without_editing(self):
		batch = self.make_batch(self.make_course().name)
		batch.append("people", {"member": self.grader.name, "role": LIVE_CLASS_CONDUCTOR})
		batch.save()
		self.assertTrue(can_run_live_classes(batch.name, user=self.grader.name))
		self.assertFalse(can_instruct_batch(batch.name, user=self.grader.name))

	def test_only_the_owner_deletes(self):
		frappe.set_user(self.other_editor.name)
		course = self.make_course()
		frappe.set_user("Administrator")
		self.assertTrue(
			frappe.has_permission("LMS Course", "delete", course.name, user=self.other_editor.name)
		)
		self.assertFalse(frappe.has_permission("LMS Course", "delete", course.name, user=self.editor.name))
		self.assertTrue(frappe.has_permission("LMS Course", "write", course.name, user=self.editor.name))


class TestChangeOwner(PeopleFixtures):
	def test_owner_hands_over(self):
		frappe.set_user(self.other_editor.name)
		course = self.make_course()
		change_owner("LMS Course", course.name, self.editor.name)
		self.assertEqual(frappe.db.get_value("LMS Course", course.name, "owner"), self.editor.name)

	def test_an_editor_cannot_take_ownership(self):
		course = self.make_course()
		frappe.set_user(self.editor.name)
		with self.assertRaises(frappe.PermissionError):
			change_owner("LMS Course", course.name, self.editor.name)

	def test_new_owner_needs_course_creator(self):
		course = self.make_course()
		with self.assertRaises(frappe.ValidationError):
			change_owner("LMS Course", course.name, self.grader.name)


class TestPeopleMigration(PeopleFixtures):
	def test_instructors_become_editors_and_evaluators_graders(self):
		course = self.make_course(evaluator=self.grader.name)
		batch = self.make_batch(course.name)
		frappe.db.set_value("Batch Course", batch.courses[0].name, "evaluator", self.grader.name)
		frappe.db.delete("LMS Role Assignment", {"parent": ("in", [course.name, batch.name])})

		migrate_people()
		migrate_people()

		course.reload()
		batch.reload()
		self.assertEqual(people(course), [(self.editor.name, EDITOR), (self.grader.name, GRADER)])
		self.assertEqual(people(batch), [(self.editor.name, EDITOR), (self.grader.name, GRADER)])
		self.assertEqual(course.evaluator, self.grader.name)
		self.assertEqual([row.instructor for row in batch.instructors], [self.editor.name])


class TestGradersShareSlots(PeopleFixtures):
	"""Learners book a slot with whichever Grader is free."""

	DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

	def give_schedule(self, user):
		evaluator = (
			frappe.get_doc("Course Evaluator", user)
			if frappe.db.exists("Course Evaluator", user)
			else frappe.new_doc("Course Evaluator")
		)
		evaluator.evaluator = user
		evaluator.unavailable_from = evaluator.unavailable_to = None
		evaluator.set(
			"schedule", [{"day": day, "start_time": "10:00", "end_time": "11:00"} for day in self.DAYS]
		)
		evaluator.save()

	def test_a_booked_grader_hands_the_slot_to_the_next(self):
		from lms.lms.doctype.course_evaluator.course_evaluator import (
			get_free_grader,
			get_open_slot_counts,
			get_schedule,
		)

		for grader in (self.grader.name, self.second_grader.name):
			self.give_schedule(grader)
		course = self.make_course(evaluator=self.grader.name)
		course.append("people", {"member": self.second_grader.name, "role": GRADER})
		course.save()
		tomorrow = add_days(nowdate(), 1)
		self.assertEqual(get_free_grader(course.name, None, tomorrow, "10:00:00"), self.grader.name)

		request = frappe.get_doc(
			{
				"doctype": "LMS Certificate Request",
				"course": course.name,
				"member": self.student.name,
				"evaluator": self.grader.name,
				"date": tomorrow,
				"start_time": "10:00:00",
				"end_time": "11:00:00",
			}
		)
		request.flags.ignore_validate = True
		request.insert()

		self.assertEqual(get_free_grader(course.name, None, tomorrow, "10:00:00"), self.second_grader.name)
		tomorrows = [
			slot
			for day in get_schedule(course.name)
			for slot in day["slots"]
			if slot["date"] == str(tomorrow)
		]
		self.assertEqual(len(tomorrows), 1)
		counts = get_open_slot_counts([self.grader.name, self.second_grader.name])
		self.assertEqual(counts[self.grader.name], counts[self.second_grader.name] - 1)


class TestOnlyEvaluatorsGrade(PeopleFixtures):
	def graded_submission(self):
		return frappe.get_doc(
			{
				"doctype": "LMS Assignment Submission",
				"member": self.student.name,
				"status": "Pass",
				"comments": "Well done",
			}
		)

	def test_an_editor_cannot_grade_a_submission(self):
		frappe.set_user(self.editor.name)
		with self.assertRaises(frappe.PermissionError):
			self.graded_submission().enforce_grading_permission()

	def test_an_evaluator_grades_it(self):
		frappe.set_user(self.grader.name)
		submission = self.graded_submission()
		submission.enforce_grading_permission()
		self.assertEqual(submission.status, "Pass")

	def test_a_student_grading_is_reverted(self):
		frappe.set_user(self.student.name)
		submission = self.graded_submission()
		submission.enforce_grading_permission()
		self.assertEqual(submission.status, "Not Graded")
