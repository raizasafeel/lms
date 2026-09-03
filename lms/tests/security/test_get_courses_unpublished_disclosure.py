import frappe
from frappe.tests.test_api import FrappeAPITestCase

from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import get_batch_count, get_batches, get_course_count, get_courses


class TestUnpublishedCourseBatchDisclosure(BaseTestUtils, FrappeAPITestCase):
	"""Regression suite for HD ticket 75883: get_courses/get_batches (and their _count
	siblings) must not leak unpublished LMS Course / LMS Batch rows to unauthenticated or
	non-privileged callers.
	"""

	def setUp(self):
		super().setUp()
		h = frappe.generate_hash(length=6)
		self.outsider = self._create_user(f"out-{h}@example.com", "Otto", "Outsider", ["LMS Student"])
		self.instructor = self._create_user(
			f"instr-{h}@example.com", "Ada", "Instr", ["Course Creator", "Batch Evaluator"]
		)
		# Deliberately NOT a System Manager -- a Moderator fixture that also carries
		# System Manager would hide the gap this fix closes (permission-and-security-tests.md #5).
		self.moderator = self._create_user(f"mod-{h}@example.com", "Mo", "Derator", ["Moderator"])
		self.enrolled_student = self._create_user(f"enr-{h}@example.com", "En", "Rolled", ["LMS Student"])
		frappe.db.set_single_value("LMS Settings", "allow_guest_access", 1)

		self.unpublished_course = self._create_course(
			title=f"Secret Draft Course {h}", instructor=self.instructor.email
		)
		self.unpublished_course.db_set("published", 0)
		self.cleanup_items.append(("LMS Course", self.unpublished_course.name))

		self._create_evaluator(self.instructor.email)
		self.unpublished_batch = self._create_batch(
			self.unpublished_course.name,
			instructor=self.instructor.email,
			evaluator=self.instructor.email,
			title=f"Secret Draft Batch {h}",
		)
		self.unpublished_batch.db_set("published", 0)
		self.cleanup_items.append(("LMS Batch", self.unpublished_batch.name))

		self._create_enrollment(self.enrolled_student.email, self.unpublished_course.name)
		self._create_batch_enrollment(self.enrolled_student.email, self.unpublished_batch.name)
		frappe.db.commit()

	def test_guest_sees_unpublished_course(self):
		# Scoped to this course's own unique title: an unscoped call risks a false
		# negative from shared-site pagination (other fixture courses ranking ahead on
		# "enrollments desc" within the default page), not proof of a real filter.
		frappe.set_user("Guest")
		try:
			names = [c["name"] for c in get_courses(filters={"title": self.unpublished_course.title})]
		finally:
			frappe.set_user("Administrator")
		self.assertNotIn(
			self.unpublished_course.name,
			names,
			msg="Guest must not see an unpublished LMS Course via get_courses",
		)

	def test_authenticated_non_privileged_user_sees_unpublished_course(self):
		frappe.set_user(self.outsider.email)
		try:
			names = [c["name"] for c in get_courses(filters={"title": self.unpublished_course.title})]
		finally:
			frappe.set_user("Administrator")
		self.assertNotIn(
			self.unpublished_course.name,
			names,
			msg="A non-instructor, non-moderator LMS Student must not see an unpublished LMS Course",
		)

	def test_guest_sees_unpublished_batch(self):
		frappe.set_user("Guest")
		try:
			names = [b["name"] for b in get_batches(filters={"title": self.unpublished_batch.title})]
		finally:
			frappe.set_user("Administrator")
		self.assertNotIn(
			self.unpublished_batch.name,
			names,
			msg="Guest must not see an unpublished LMS Batch via get_batches",
		)

	def test_authenticated_non_privileged_user_sees_unpublished_batch(self):
		frappe.set_user(self.outsider.email)
		try:
			names = [b["name"] for b in get_batches(filters={"title": self.unpublished_batch.title})]
		finally:
			frappe.set_user("Administrator")
		self.assertNotIn(
			self.unpublished_batch.name,
			names,
			msg="A non-instructor, non-moderator LMS Student must not see an unpublished LMS Batch",
		)

	def test_moderator_sees_unpublished_course(self):
		frappe.set_user(self.moderator.email)
		try:
			names = [c["name"] for c in get_courses(filters={"title": self.unpublished_course.title})]
		finally:
			frappe.set_user("Administrator")
		self.assertIn(
			self.unpublished_course.name,
			names,
			msg="A Moderator must still see unpublished LMS Course rows via get_courses",
		)

	def test_moderator_sees_unpublished_batch(self):
		frappe.set_user(self.moderator.email)
		try:
			names = [b["name"] for b in get_batches(filters={"title": self.unpublished_batch.title})]
		finally:
			frappe.set_user("Administrator")
		self.assertIn(
			self.unpublished_batch.name,
			names,
			msg="A Moderator must still see unpublished LMS Batch rows via get_batches",
		)

	def test_instructor_sees_own_unpublished_course_via_created_filter(self):
		# self.instructor carries Course Creator + Batch Evaluator (both PRIVILEGED_ROLES),
		# so calling get_courses as self.instructor here would pass via the privileged-role
		# early return in _restrict_to_published regardless of the `created` exemption --
		# deleting that exemption would not turn this test red. A Course Instructor row
		# doesn't require the Course Creator role, so use an LMS-Student-only user to
		# exercise the `created`/allow_unpublished branch in isolation from the
		# privileged-role branch.
		non_privileged_instructor = self._create_user(
			f"nonpriv-instr-{frappe.generate_hash(length=6)}@example.com",
			"Nadia",
			"NonPriv",
			["LMS Student"],
		)
		own_draft_course = self._create_course(
			title=f"Own Draft Course {frappe.generate_hash(length=6)}",
			instructor=non_privileged_instructor.email,
		)
		own_draft_course.db_set("published", 0)
		self.cleanup_items.append(("LMS Course", own_draft_course.name))
		frappe.db.commit()

		frappe.set_user(non_privileged_instructor.email)
		try:
			names = [c["name"] for c in get_courses(filters={"created": 1})]
		finally:
			frappe.set_user("Administrator")
		self.assertIn(
			own_draft_course.name,
			names,
			msg="A non-privileged Course Instructor's own 'my courses' tab must still show "
			"their unpublished draft course via the `created` exemption",
		)

	def test_non_moderator_privileged_role_sees_unpublished_course_via_unpublished_tab(self):
		# self.instructor carries Course Creator + Batch Evaluator, deliberately not Moderator
		# (see setUp). This is the "Unpublished" tab's own query shape (published: 0), not the
		# "created" pseudo-filter exercised above -- a different code path in _restrict_to_published.
		frappe.set_user(self.instructor.email)
		try:
			names = [
				c["name"]
				for c in get_courses(filters={"title": self.unpublished_course.title, "published": 0})
			]
		finally:
			frappe.set_user("Administrator")
		self.assertIn(
			self.unpublished_course.name,
			names,
			msg="A Course Creator/Batch Evaluator (non-Moderator) must still see unpublished "
			"LMS Course rows via the Unpublished tab's published=0 filter",
		)

	def test_non_moderator_privileged_role_sees_unpublished_batch_via_unpublished_tab(self):
		frappe.set_user(self.instructor.email)
		try:
			names = [
				b["name"]
				for b in get_batches(filters={"title": self.unpublished_batch.title, "published": 0})
			]
		finally:
			frappe.set_user("Administrator")
		self.assertIn(
			self.unpublished_batch.name,
			names,
			msg="A Course Creator/Batch Evaluator (non-Moderator) must still see unpublished "
			"LMS Batch rows via the Unpublished tab's published=0 filter",
		)

	def test_enrolled_student_sees_own_unpublished_course(self):
		# The Enrolled tab deletes `published` and leans on the enrollment narrowing alone
		# (Courses.vue), so a student enrolled in a course that later moves back to draft
		# must not lose it from their own Enrolled tab.
		frappe.set_user(self.enrolled_student.email)
		try:
			names = [c["name"] for c in get_courses(filters={"enrolled": 1})]
		finally:
			frappe.set_user("Administrator")
		self.assertIn(
			self.unpublished_course.name,
			names,
			msg="A student enrolled in an unpublished LMS Course must still see it via "
			"get_courses({'enrolled': 1})",
		)

	def test_enrolled_student_sees_own_unpublished_batch(self):
		frappe.set_user(self.enrolled_student.email)
		try:
			names = [b["name"] for b in get_batches(filters={"enrolled": 1})]
		finally:
			frappe.set_user("Administrator")
		self.assertIn(
			self.unpublished_batch.name,
			names,
			msg="A student enrolled in an unpublished LMS Batch must still see it via "
			"get_batches({'enrolled': 1})",
		)

	def test_non_moderator_cannot_force_unpublished_via_explicit_filter(self):
		# An attacker asserting published=0 outright must still be denied -- the
		# forced filter must override caller input, not merge with it.
		for as_user in ("Guest", self.outsider.email):
			with self.subTest(as_user=as_user):
				frappe.set_user(as_user)
				try:
					course_names = [
						c["name"]
						for c in get_courses(filters={"title": self.unpublished_course.title, "published": 0})
					]
					batch_names = [
						b["name"]
						for b in get_batches(filters={"title": self.unpublished_batch.title, "published": 0})
					]
				finally:
					frappe.set_user("Administrator")
				self.assertNotIn(self.unpublished_course.name, course_names)
				self.assertNotIn(self.unpublished_batch.name, batch_names)

	def test_bare_call_excludes_unpublished_course(self):
		# The original leak needed no crafted filter at all -- a bare `get_courses()` call
		# returned drafts (design doc's "load-bearing test, not an afterthought"). Every
		# other test in this suite scopes by title/published/enrolled/created, so a
		# regression that only forces published=1 when some filter key is already present
		# would pass every one of them while still leaking here.
		for as_user in ("Guest", self.outsider.email):
			with self.subTest(as_user=as_user):
				frappe.set_user(as_user)
				try:
					names = [c["name"] for c in get_courses()]
				finally:
					frappe.set_user("Administrator")
				self.assertNotIn(
					self.unpublished_course.name,
					names,
					msg="get_courses() with no filters at all must not leak an unpublished course",
				)

	def test_bare_call_excludes_unpublished_batch(self):
		for as_user in ("Guest", self.outsider.email):
			with self.subTest(as_user=as_user):
				frappe.set_user(as_user)
				try:
					names = [b["name"] for b in get_batches()]
				finally:
					frappe.set_user("Administrator")
				self.assertNotIn(
					self.unpublished_batch.name,
					names,
					msg="get_batches() with no filters at all must not leak an unpublished batch",
				)

	def test_course_count_bare_call_matches_explicit_published_filter(self):
		# Same "no crafted filter" gap as the list endpoints above, but for the count
		# sibling: compares the bare-call total against the total for an explicit
		# published=1 filter (the known-correct answer) as the same caller, so this
		# holds regardless of how much other data is on the test site.
		for as_user in ("Guest", self.outsider.email):
			with self.subTest(as_user=as_user):
				frappe.set_user(as_user)
				try:
					bare_total = get_course_count()
					published_total = get_course_count(filters={"published": 1})
				finally:
					frappe.set_user("Administrator")
				self.assertEqual(
					bare_total,
					published_total,
					msg="get_course_count() with no filters at all must match the count "
					"with published=1 explicitly set",
				)

	def test_batch_count_bare_call_matches_explicit_published_filter(self):
		for as_user in ("Guest", self.outsider.email):
			with self.subTest(as_user=as_user):
				frappe.set_user(as_user)
				try:
					bare_total = get_batch_count()
					published_total = get_batch_count(filters={"published": 1})
				finally:
					frappe.set_user("Administrator")
				self.assertEqual(
					bare_total,
					published_total,
					msg="get_batch_count() with no filters at all must match the count "
					"with published=1 explicitly set",
				)

	def test_course_count_does_not_leak_unpublished_existence(self):
		for as_user in ("Guest", self.outsider.email):
			with self.subTest(as_user=as_user):
				frappe.set_user(as_user)
				try:
					total = get_course_count(filters={"title": self.unpublished_course.title})
				finally:
					frappe.set_user("Administrator")
				self.assertEqual(
					total,
					0,
					msg="get_course_count must not confirm an unpublished draft with this title exists",
				)

		frappe.set_user(self.moderator.email)
		try:
			total = get_course_count(filters={"title": self.unpublished_course.title})
		finally:
			frappe.set_user("Administrator")
		self.assertGreaterEqual(total, 1)

	def test_batch_count_does_not_leak_unpublished_existence(self):
		for as_user in ("Guest", self.outsider.email):
			with self.subTest(as_user=as_user):
				frappe.set_user(as_user)
				try:
					total = get_batch_count(filters={"title": self.unpublished_batch.title})
				finally:
					frappe.set_user("Administrator")
				self.assertEqual(
					total,
					0,
					msg="get_batch_count must not confirm an unpublished draft with this title exists",
				)

		frappe.set_user(self.moderator.email)
		try:
			total = get_batch_count(filters={"title": self.unpublished_batch.title})
		finally:
			frappe.set_user("Administrator")
		self.assertGreaterEqual(total, 1)
