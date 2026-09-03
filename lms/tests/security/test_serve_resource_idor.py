import base64
import json

import frappe
from frappe.tests.test_api import FrappeAPITestCase

from lms.lms.doctype.course_lesson import course_lesson
from lms.lms.doctype.course_lesson.course_lesson import serve_resource
from lms.lms.test_helpers import BaseTestUtils

_MIN_PDF = (
	b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
	b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
	b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 100 100]>>endobj\n"
	b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n164\n%%EOF\n"
)


class TestServeResourceContentSearchIDOR(BaseTestUtils, FrappeAPITestCase):
	"""Permanent regression test for lms-security-audit.md finding E05.

	Exploit shape: the content-field search in _resolve_lesson_references treated "some
	lesson I authored contains this string" as authorization to read the referenced file,
	with no check that the matching lesson is the file's legitimate owner. An attacker who
	can author any lesson (Course Creator) pastes a victim's private file_url into their
	own lesson's content and was granted the bytes.

	The fix: _resolve_lesson_references now also requires that the FILE's owner could
	legitimately have authored content into the matched lesson's course (Administrator,
	Moderator, or a Course Instructor of that course) before treating a content-search
	match as a reference. See _uploader_authorized_on_course in course_lesson.py.
	"""

	def setUp(self):
		super().setUp()
		h = frappe.generate_hash(length=6)

		# Deliberately NOT Moderator: a moderator-owned file used to be authorized on
		# every course by _uploader_authorized_on_course regardless of the matched
		# lesson, which would have hidden the bug this test exists to catch. That gap
		# (Administrator/Moderator-owned files) is now closed and has its own dedicated
		# regression test below. See specs-ankush/permission-and-security-tests.md #5.
		self.victim_instructor = self._create_user(
			f"victim-instr-{h}@example.com", "Vic", "Instr", ["Course Creator"]
		)
		self.co_instructor = self._create_user(f"co-instr-{h}@example.com", "Cora", "Co", ["Course Creator"])
		self.attacker = self._create_user(f"attacker-{h}@example.com", "Att", "Acker", ["Course Creator"])

		# Victim's course/lesson: attacker is NOT an instructor and NOT enrolled.
		self.victim_course = self._create_course(
			title=f"Victim Course {h}", instructor=self.victim_instructor.email
		)
		self.victim_chapter = self._create_chapter(f"Victim Chapter {h}", self.victim_course.name)
		self.victim_lesson = self._create_lesson(
			f"Victim Lesson {h}", self.victim_chapter.name, self.victim_course.name
		)
		self._create_chapter_reference(self.victim_course.name, self.victim_chapter.name, idx=1)
		self._create_lesson_reference(self.victim_chapter.name, self.victim_lesson.name)

		# A second, legitimate instructor of the SAME course, with their own lesson in it —
		# used by the right-role positive case below. Reload first: the chapter/lesson
		# reference inserts above already bumped the course's `modified` on the DB row.
		self.victim_course.reload()
		self.victim_course.append("instructors", {"instructor": self.co_instructor.email})
		self.victim_course.save()
		self.co_lesson = self._create_lesson(
			f"Co-instructor Lesson {h}", self.victim_chapter.name, self.victim_course.name
		)
		self._create_lesson_reference(self.victim_chapter.name, self.co_lesson.name)

		# Attacker's own, unrelated course/lesson.
		self.attacker_course = self._create_course(
			title=f"Attacker Course {h}", instructor=self.attacker.email
		)
		self.attacker_chapter = self._create_chapter(f"Attacker Chapter {h}", self.attacker_course.name)
		self.attacker_lesson = self._create_lesson(
			f"Attacker Lesson {h}", self.attacker_chapter.name, self.attacker_course.name
		)
		self._create_chapter_reference(self.attacker_course.name, self.attacker_chapter.name, idx=1)
		self._create_lesson_reference(self.attacker_chapter.name, self.attacker_lesson.name)

		# Victim's private file: attached to the VICTIM lesson, canary content. Inserted
		# while logged in as the victim instructor so File.owner is genuinely theirs —
		# Document.insert() always stamps owner from the active session user, so this
		# must happen under frappe.set_user, not by passing "owner" in the dict.
		frappe.set_user(self.victim_instructor.email)
		self.secret = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"victim-payroll-{h}.pdf",
				"is_private": 1,
				"attached_to_doctype": "Course Lesson",
				"attached_to_name": self.victim_lesson.name,
				"attached_to_field": "content",
				"content": base64.b64encode(_MIN_PDF).decode(),
				"decode": True,
			}
		).insert(ignore_permissions=True)
		frappe.set_user("Administrator")
		self.cleanup_items.append(("File", self.secret.name))
		self.file_url = self.secret.file_url
		self.assertEqual(self.secret.owner, self.victim_instructor.email)

		# Sanity: the victim lesson's own content never actually references the file (it
		# was attached out-of-band, e.g. by a moderator), so only the attacker's paste
		# below creates any content-field reference to it.
		frappe.db.commit()

	def _serve_as(self, user):
		sentinel = object()
		original = course_lesson._serve_private_file
		course_lesson._serve_private_file = lambda relative_path, filename: sentinel
		frappe.set_user(user)
		try:
			return serve_resource(self.file_url)
		finally:
			course_lesson._serve_private_file = original
			frappe.set_user("Administrator")

	def test_baseline_attacker_denied_before_paste(self):
		"""Control: before pasting the URL anywhere, the attacker cannot read the victim's
		file (native /private/files/ semantics — establishes this isn't already open)."""
		with self.assertRaises(frappe.PermissionError):
			self._serve_as(self.attacker.email)

	def test_attacker_reads_victim_file_by_pasting_url_into_own_lesson(self):
		"""The exploit: pasting the victim's file_url into the attacker's OWN lesson content
		must NOT grant the attacker the victim's file bytes."""
		self.attacker_lesson.content = json.dumps(
			{"blocks": [{"type": "upload", "data": {"file_url": self.file_url, "file_type": "PDF"}}]}
		)
		self.attacker_lesson.save(ignore_permissions=True)
		frappe.db.commit()

		with self.assertRaises(
			frappe.PermissionError,
			msg=(
				"E05: attacker served the victim's private file after merely pasting its URL "
				"into their own, unrelated lesson's content"
			),
		):
			self._serve_as(self.attacker.email)

	def test_anonymous_caller_denied_even_via_guest_readable_preview_lesson(self):
		"""Anonymous caller (spec: permission-and-security-tests.md's four-caller
		minimum). The attacker's exploit lesson is made guest-readable (published
		course, preview lesson, guest access on) so an unauthenticated caller can reach
		it too -- and must still be denied, because the new authorization check gates
		the reference itself, not just who is asking."""
		self.attacker_lesson.content = json.dumps(
			{"blocks": [{"type": "upload", "data": {"file_url": self.file_url, "file_type": "PDF"}}]}
		)
		self.attacker_lesson.save(ignore_permissions=True)
		self.attacker_lesson.db_set("include_in_preview", 1)
		frappe.db.set_single_value("LMS Settings", "allow_guest_access", 1)
		frappe.db.commit()

		with self.assertRaises(
			frappe.PermissionError,
			msg="E05: an anonymous caller read the victim's private file via a guest-readable preview lesson",
		):
			self._serve_as("Guest")

	def test_legitimate_co_instructor_reuse_within_same_course_is_served(self):
		"""Right-role positive: a second, legitimate instructor of the SAME course pastes
		the file's url into ANOTHER lesson they own in that course, and IS served. The fix
		must not break legitimate cross-lesson reuse by someone who could have placed that
		content there — the file's owner (the victim instructor) is a real Course
		Instructor of this course, so the reference is authorized."""
		self.co_lesson.content = json.dumps(
			{"blocks": [{"type": "upload", "data": {"file_url": self.file_url, "file_type": "PDF"}}]}
		)
		self.co_lesson.save(ignore_permissions=True)
		frappe.db.commit()

		self.assertIsNotNone(self._serve_as(self.co_instructor.email))

	def test_attacker_reads_administrator_owned_file_by_pasting_url_into_own_lesson(self):
		"""E05 for a privileged file owner: the same exploit, but the file is owned by
		Administrator (the common case for seeded/bulk-imported/officially-uploaded
		content) rather than an ordinary Course Creator.

		_uploader_authorized_on_course's Administrator/Moderator branch answers "could
		owner have written into ANY course", which is trivially true for a global role
		and so cannot gate anything by itself -- it must also require the MATCHED lesson
		to have been authored by a privileged account, not merely reference
		privileged-owned media. Without that, this collapses to the exact same exploit as
		test_attacker_reads_victim_file_by_pasting_url_into_own_lesson, just with the
		file's owner swapped."""
		h = frappe.generate_hash(length=6)

		# Administrator-owned private file, attached to the victim's lesson -- mirrors
		# seeded/bulk-imported content. Session is still Administrator here (setUp's
		# last action), so File.owner is stamped Administrator.
		admin_secret = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"admin-payroll-{h}.pdf",
				"is_private": 1,
				"attached_to_doctype": "Course Lesson",
				"attached_to_name": self.victim_lesson.name,
				"attached_to_field": "content",
				"content": base64.b64encode(_MIN_PDF).decode(),
				"decode": True,
			}
		).insert(ignore_permissions=True)
		self.cleanup_items.append(("File", admin_secret.name))
		self.assertEqual(admin_secret.owner, "Administrator")

		# A lesson genuinely authored BY the attacker: `owner` is stamped from the
		# active session at insert (exactly like a real create through the app), so it
		# must be created under the attacker's own session, not Administrator's.
		frappe.set_user(self.attacker.email)
		try:
			attacker_own_chapter = self._create_chapter(f"Attacker Chapter B {h}", self.attacker_course.name)
			attacker_own_lesson = self._create_lesson(
				f"Attacker Lesson B {h}", attacker_own_chapter.name, self.attacker_course.name
			)
			self.assertEqual(attacker_own_lesson.owner, self.attacker.email)
			attacker_own_lesson.content = json.dumps(
				{
					"blocks": [
						{"type": "upload", "data": {"file_url": admin_secret.file_url, "file_type": "PDF"}}
					]
				}
			)
			attacker_own_lesson.save()
		finally:
			frappe.set_user("Administrator")
		frappe.db.commit()

		with self.assertRaises(
			frappe.PermissionError,
			msg=(
				"E05: attacker served an Administrator-owned private file after pasting its "
				"url into their own lesson -- _uploader_authorized_on_course must not treat "
				"a privileged file owner as authorized on every course"
			),
		):
			self._serve_as(self.attacker.email)

	def test_attacker_reads_victim_file_by_repointing_attachment_onto_own_lesson(self):
		"""The File-attachment fast path (loop 1 in _resolve_lesson_references) must
		independently clear the same authorization check as the content-search path
		(loop 2), covered by the tests above. attached_to_name/attached_to_field are
		ordinary writable fields on File -- no if_owner gate on File's DocPerm -- so a
		Course Creator who can write File rows can repoint the victim's already-uploaded
		File onto a lesson they own, without ever touching the victim lesson's content.
		This must not grant the attacker the file's bytes: the fast path is gated on the
		FILE's own `owner` (still the victim instructor after the repoint), not on
		whichever lesson attached_to_name now points at.

		The repoint itself is simulated with a direct field write (mirroring what
		frappe.client.set_value would do): File's own DocPerm boundary -- whether the
		attacker's role may write that field at all -- is a separate concern from this
		IDOR gate, which must hold regardless.
		"""
		frappe.db.set_value("File", self.secret.name, "attached_to_name", self.attacker_lesson.name)
		frappe.db.commit()

		with self.assertRaises(
			frappe.PermissionError,
			msg=(
				"E05: attacker served the victim's private file after repointing its File "
				"row's attached_to_name onto their own lesson"
			),
		):
			self._serve_as(self.attacker.email)

	def test_legitimate_co_instructor_attachment_reuse_within_same_course_is_served(self):
		"""Right-role positive for the File-attachment path: a legitimate co-instructor of
		the SAME course repoints the file's attachment onto another lesson they own in
		that course, and IS served -- the fix must not break legitimate cross-lesson
		attachment reuse, mirroring the content-search positive case above."""
		frappe.db.set_value("File", self.secret.name, "attached_to_name", self.co_lesson.name)
		frappe.db.commit()

		self.assertIsNotNone(self._serve_as(self.co_instructor.email))

	def test_known_limitation_admin_owned_file_on_ordinary_instructors_lesson_is_denied(self):
		"""Pins a known, deliberate cost of the fix (see _uploader_authorized_on_course's
		comment): an Administrator-owned file legitimately attached to an ORDINARY
		instructor's own lesson (e.g. seeded/officially-uploaded content) is denied to
		EVERYONE, including that instructor and enrolled members -- not just an attacker.
		No signal available at this point distinguishes "Administrator seeded this" from
		"attacker pasted this" once the file owner is privileged, so this fails closed
		rather than reopening test_attacker_reads_administrator_owned_file_by_pasting_url_into_own_lesson's
		exploit. If a future change narrows this, that test must still pass."""
		h = frappe.generate_hash(length=6)

		# A lesson genuinely owned by an ORDINARY instructor: `owner` is stamped from the
		# active session at insert, so it must be created under their own session (the
		# fixture's `self.victim_lesson` is Administrator-owned -- created in setUp before
		# any frappe.set_user call -- so it does not exercise this case).
		frappe.set_user(self.victim_instructor.email)
		try:
			own_lesson = self._create_lesson(
				f"Own Lesson {h}", self.victim_chapter.name, self.victim_course.name
			)
			self.assertEqual(own_lesson.owner, self.victim_instructor.email)
		finally:
			frappe.set_user("Administrator")

		# Content, not just file_name, must be unique: File.save_file dedupes by
		# content_hash and reuses an existing file's file_url regardless of the name given
		# (frappe/core/doctype/file/file.py), so a byte-identical _MIN_PDF here would
		# resolve to whatever file_url every other test in this suite already shares --
		# and with it, every unrelated (possibly preview-enabled, possibly
		# Administrator-owned) lesson leftover from the whole site's test history.
		unique_pdf = _MIN_PDF + f"\n% unique-{h}\n".encode()
		admin_secret = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"seeded-content-{h}.pdf",
				"is_private": 1,
				"attached_to_doctype": "Course Lesson",
				"attached_to_name": own_lesson.name,
				"attached_to_field": "content",
				"content": base64.b64encode(unique_pdf).decode(),
				"decode": True,
			}
		).insert(ignore_permissions=True)
		self.cleanup_items.append(("File", admin_secret.name))
		self.assertEqual(admin_secret.owner, "Administrator")
		frappe.db.commit()

		sentinel = object()
		original = course_lesson._serve_private_file
		course_lesson._serve_private_file = lambda relative_path, filename: sentinel
		frappe.set_user(self.victim_instructor.email)
		try:
			with self.assertRaises(frappe.PermissionError):
				serve_resource(admin_secret.file_url)
		finally:
			course_lesson._serve_private_file = original
			frappe.set_user("Administrator")

	def test_serve_resource_rejects_non_string_file_url(self):
		"""Malformed input: a non-string file_url must raise via serve_resource's own
		isinstance check, before any lesson-reference resolution runs."""
		with self.assertRaises(frappe.ValidationError):
			serve_resource(["not-a-string"])
