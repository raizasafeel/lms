import frappe

from lms.lms.people import EDITOR, GRADER, add_missing_rows


def execute():
	"""Instructors become Editors and evaluators Graders. The old fields keep their
	data; LMS Course and LMS Batch now derive them from People on save."""
	for course in frappe.get_all("LMS Course", fields=["name", "evaluator"]):
		editors = get_instructors("LMS Course", course.name)
		add_people("LMS Course", course.name, editors, [course.evaluator] if course.evaluator else [])

	for batch in frappe.get_all("LMS Batch", pluck="name"):
		graders = frappe.get_all(
			"Batch Course",
			filters={"parent": batch, "parenttype": "LMS Batch", "evaluator": ("is", "set")},
			pluck="evaluator",
			order_by="idx asc",
		)
		add_people("LMS Batch", batch, get_instructors("LMS Batch", batch), list(dict.fromkeys(graders)))


def get_instructors(doctype: str, name: str) -> list[str]:
	return frappe.get_all(
		"Course Instructor",
		filters={"parent": name, "parenttype": doctype, "instructor": ("is", "set")},
		pluck="instructor",
		order_by="idx asc",
	)


def add_people(doctype: str, name: str, editors: list[str], graders: list[str]):
	add_missing_rows(
		doctype, name, [(editor, EDITOR) for editor in editors] + [(grader, GRADER) for grader in graders]
	)
