"""Where each onboarding checklist step should take the person who clicks it.

The checklist in the sidebar sends a new admin to the form that finishes the
step: "Add your first chapter" opens the new-chapter form on their course, not
the course list. To do that it needs to know which course and batch are theirs.

The demo course is left out. On a fresh site the demo
course is the oldest course there is, so "your first course" used to mean the
demo one, and the chapter a new admin added landed in Frappe's sample content.
"""

import frappe

from lms.lms.utils import is_demo_course


@frappe.whitelist()
def get_onboarding_targets() -> dict:
	"""The course and batch the checklist should open, if the site has them.

	`course_has_chapter` decides the lesson step: a lesson needs a chapter to
	sit in, so a course without one sends the admin to add a chapter first.
	"""
	# System Manager too: the checklist is shown to System Managers, and the
	# owner Frappe Cloud creates holds that role before it holds any LMS one.
	frappe.only_for(["System Manager", "Moderator", "Course Creator"])

	course = get_first_own_course()
	return {
		"course": course,
		"course_has_chapter": bool(course and frappe.db.exists("Chapter Reference", {"parent": course})),
		"batch": get_first_batch(),
	}


def get_first_own_course() -> str | None:
	"""The oldest course that is not the demo course.

	Two rows are enough: the seeder makes one demo course, so if the oldest is
	the demo, the next is the admin's own.
	"""
	for name in frappe.get_all("LMS Course", order_by="creation asc", pluck="name", limit=2):
		if not is_demo_course(name):
			return name
	return None


def get_first_batch() -> str | None:
	batch = frappe.get_all("LMS Batch", order_by="creation asc", pluck="name", limit=1)
	return batch[0] if batch else None
