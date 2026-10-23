import frappe

from lms.lms.api import get_my_batches
from lms.lms.test_helpers import BaseTestUtils


class TestMyBatchesProgress(BaseTestUtils):
	"""get_my_batches carries the learner's progress for the Home batch card."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		instructor = cls._create_user(
			"mb-instructor@example.com", "Card", "Instructor", ["Course Creator"]
		).name
		cls.student = cls._create_user("mb-student@example.com", "Card", "Student", ["LMS Student"])
		cls.visitor = cls._create_user("mb-visitor@example.com", "Card", "Visitor", ["LMS Student"])
		cls.started = cls._create_course("My Batches Started Course", instructor=instructor)
		cls.untouched = cls._create_course("My Batches Untouched Course", instructor=instructor)

		batch = {"instructor": instructor, "evaluator": None}
		cls.two_courses = cls._create_batch(cls.started.name, title="My Batches Two Courses", **batch)
		cls.two_courses.append("courses", {"course": cls.untouched.name})
		cls.two_courses.save()
		cls.one_course = cls._create_batch(cls.started.name, title="My Batches One Course", **batch)
		for batch in (cls.two_courses, cls.one_course):
			cls._create_batch_enrollment(cls.student.email, batch.name)

		enrollment = cls._create_enrollment(cls.student.email, cls.started.name)
		frappe.db.set_value("LMS Enrollment", enrollment.name, "progress", 50)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _my_batches(self, user):
		frappe.set_user(user)
		return {batch.name: batch for batch in get_my_batches()}

	def test_progress_averages_the_batch_courses_counting_unstarted_as_zero(self):
		batches = self._my_batches(self.student.email)

		self.assertEqual(batches[self.two_courses.name].progress, 25)
		self.assertEqual(batches[self.one_course.name].progress, 50)

	def test_upcoming_batches_shown_to_a_learner_with_none_carry_no_progress(self):
		batches = self._my_batches(self.visitor.email)

		self.assertTrue(batches)
		self.assertEqual({batch.progress for batch in batches.values()}, {None})
