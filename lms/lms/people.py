# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now

EDITOR = "Editor"
GRADER = "Grader"
LIVE_CLASS_CONDUCTOR = "Live class conductor"

ROLES_BY_DOCTYPE = {
	"LMS Course": (EDITOR, GRADER),
	"LMS Batch": (EDITOR, LIVE_CLASS_CONDUCTOR, GRADER),
}

# The site roles a user needs to hold each People role. A Moderator may hold any.
ELIGIBLE_SITE_ROLES = {
	EDITOR: {"Course Creator"},
	GRADER: {"Batch Evaluator"},
	LIVE_CLASS_CONDUCTOR: {"Course Creator", "Batch Evaluator"},
}


STAFF_SITE_ROLES = ("Moderator", "Course Creator", "Batch Evaluator")

# Who may own each: a course belongs to a Course Creator, a batch to a Batch Evaluator.
OWNER_SITE_ROLE = {"LMS Course": "Course Creator", "LMS Batch": "Batch Evaluator"}


def can_own(doctype: str, user: str) -> bool:
	site_roles = set(frappe.get_roles(user))
	return "Moderator" in site_roles or OWNER_SITE_ROLE[doctype] in site_roles


def owner_message(doctype: str) -> str:
	if doctype == "LMS Batch":
		return _("Only a Batch Evaluator or a Moderator can own a batch.")
	return _("Only a Course Creator or a Moderator can own a course.")


def is_eligible(user: str, role: str) -> bool:
	site_roles = set(frappe.get_roles(user))
	return "Moderator" in site_roles or bool(ELIGIBLE_SITE_ROLES[role] & site_roles)


def get_members(doctype: str, name: str, role: str) -> list[str]:
	"""Members holding `role` on the stored course or batch, in table order."""
	if not name:
		return []
	return frappe.get_all(
		"LMS Role Assignment",
		filters={"parenttype": doctype, "parent": name, "parentfield": "people", "role": role},
		pluck="member",
		order_by="idx asc",
	)


def has_role(doctype: str, name: str | None, role: str, user: str) -> bool:
	if not isinstance(name, str) or not name or not user:
		return False
	return bool(
		frappe.db.exists(
			"LMS Role Assignment",
			{"parenttype": doctype, "parent": name, "parentfield": "people", "role": role, "member": user},
		)
	)


def get_graders(course: str, batch: str | None = None) -> list[str]:
	"""Who grades `course`: the batch's Graders when taken in a batch, else the course's."""
	if batch:
		return get_members("LMS Batch", batch, GRADER)
	return get_members("LMS Course", course, GRADER)


def is_grader(user: str, course: str | None, batch: str | None = None) -> bool:
	"""A Grader row on the course (or on the batch that runs it) held by a Batch Evaluator.
	Only evaluators grade, so a revoked role ends grading even while the row stays."""
	if not user or "Batch Evaluator" not in frappe.get_roles(user):
		return False
	if not batch:
		return has_role("LMS Course", course, GRADER, user)
	if course and not frappe.db.exists(
		"Batch Course", {"parent": batch, "parenttype": "LMS Batch", "course": course}
	):
		return False
	return has_role("LMS Batch", batch, GRADER, user)


class PeopleTable:
	"""Keeps a course's or batch's `people` rows valid and its legacy fields derived from them."""

	def __init__(self, doc):
		self.doc = doc
		self.stored = None if doc.is_new() else doc.get_doc_before_save()

	def sync(self):
		self.validate_new_owner()
		if self.stored_rows() == self.rows():
			self.adopt_legacy_fields()
		else:
			self.validate_added_rows()
		self.validate_rows()
		self.derive_legacy_fields()

	def validate_new_owner(self):
		"""Checked on new documents only: existing owners predate the rule and keep saving."""
		if self.doc.is_new() and not can_own(self.doc.doctype, self.doc.owner or frappe.session.user):
			frappe.throw(owner_message(self.doc.doctype), frappe.PermissionError)

	def rows(self, doc=None) -> list[tuple[str, str]]:
		doc = doc or self.doc
		return [(row.member, row.role) for row in doc.get("people") or []]

	def stored_rows(self) -> list[tuple[str, str]]:
		return self.rows(self.stored) if self.stored else []

	def members(self, role: str) -> list[str]:
		return [member for member, row_role in self.rows() if row_role == role]

	def adopt_legacy_fields(self):
		"""A writer that only knows the old fields (an older client, an import) still
		lands in the role table."""
		instructors = [row.instructor for row in self.doc.get("instructors") or [] if row.instructor]
		stored_instructors = (
			[row.instructor for row in self.stored.get("instructors") or []] if self.stored else []
		)
		if instructors != stored_instructors or (self.doc.is_new() and not self.members(EDITOR)):
			self.replace_members(EDITOR, instructors)
		if self.doc.doctype == "LMS Course":
			self.adopt_course_evaluator()
			return
		stored = {row.evaluator for row in self.stored.get("courses") or []} if self.stored else set()
		for row in self.doc.get("courses") or []:
			if row.evaluator and row.evaluator not in stored | set(self.members(GRADER)):
				self.doc.append("people", {"member": row.evaluator, "role": GRADER})

	def adopt_course_evaluator(self):
		"""The single legacy evaluator replaces the Grader it named before."""
		previous = self.stored.evaluator if self.stored else None
		if self.doc.evaluator == previous:
			return
		graders = [grader for grader in self.members(GRADER) if grader != previous]
		if self.doc.evaluator and self.doc.evaluator not in graders:
			graders.insert(0, self.doc.evaluator)
		self.replace_members(GRADER, graders)

	def replace_members(self, role: str, members: list[str]):
		"""Sets one role's members and keeps the table grouped in role order."""
		rows = {other: self.members(other) for other in ROLES_BY_DOCTYPE[self.doc.doctype]}
		rows[role] = members
		self.doc.set("people", [])
		for row_role, row_members in rows.items():
			for member in row_members:
				self.doc.append("people", {"member": member, "role": row_role})

	def validate_rows(self):
		allowed = ROLES_BY_DOCTYPE[self.doc.doctype]
		seen = set()
		for member, role in self.rows():
			if role not in allowed:
				frappe.throw(_("{0} is not a role on a {1}.").format(role, _(self.doc.doctype)))
			if (member, role) in seen:
				frappe.throw(
					_("{0} is already listed as {1}.").format(frappe.bold(member_name(member)), _(role))
				)
			seen.add((member, role))

	def validate_added_rows(self):
		"""People edits are checked against site roles: only evaluators grade."""
		for member, role in set(self.rows()) - set(self.stored_rows()):
			if not is_eligible(member, role):
				frappe.throw(eligibility_message(member, role), title=_("Not allowed"))

	def derive_legacy_fields(self):
		editors = self.members(EDITOR)
		self.doc.set("instructors", [{"instructor": editor} for editor in editors])
		graders = self.members(GRADER)
		if self.doc.doctype == "LMS Course":
			self.doc.evaluator = self.pick_evaluator(self.doc.evaluator, graders)
			return
		for row in self.doc.get("courses") or []:
			row.evaluator = self.pick_evaluator(row.evaluator, graders)

	def pick_evaluator(self, current: str | None, graders: list[str]) -> str | None:
		"""Keeps a current evaluator who is still a Grader, else the first Grader."""
		if current in graders:
			return current
		if not graders:
			return None
		ensure_course_evaluator(graders[0])
		return graders[0]


def ensure_course_evaluator(user: str):
	"""The legacy evaluator fields link Course Evaluator, so a Grader needs one."""
	if frappe.db.exists("Course Evaluator", user):
		return
	evaluator = frappe.new_doc("Course Evaluator")
	evaluator.evaluator = user
	# nosemgrep: lms-unjustified-ignore-permissions - an eligible Grader's empty schedule; the People edit was authorised
	evaluator.insert(ignore_permissions=True)


def member_name(user: str) -> str:
	return frappe.db.get_value("User", user, "full_name") or user


def eligibility_message(user: str, role: str) -> str:
	name = frappe.bold(member_name(user))
	if role == GRADER:
		return _("{0} can't grade: only users with the Batch Evaluator role can.").format(name)
	if role == EDITOR:
		return _("{0} can't be an editor: they need the Course Creator role.").format(name)
	return _("{0} can't run live classes: they need the Course Creator or Batch Evaluator role.").format(name)


def people_changed(stored, doc) -> bool:
	"""Whether a save changes who works on `doc`, through `people` or a legacy field."""
	table = PeopleTable(doc)
	instructors = [row.instructor for row in doc.get("instructors") or []]
	stored_instructors = [row.instructor for row in stored.get("instructors") or []]
	return table.rows(stored) != table.rows() or instructors != stored_instructors


@frappe.whitelist(methods=["POST"])
def change_owner(doctype: str, name: str, owner: str):
	"""Hands a course to another Course Creator, or a batch to another Batch Evaluator.
	Only its owner or a Moderator may."""
	from lms.lms.permissions import owns

	if doctype not in ROLES_BY_DOCTYPE or not frappe.db.exists(doctype, name):
		frappe.throw(_("Not found."), frappe.DoesNotExistError)
	if not owns(doctype, name):
		frappe.throw(_("Only the owner or a Moderator can change the owner."), frappe.PermissionError)
	if not frappe.db.exists("User", {"name": owner, "enabled": 1}) or not can_own(doctype, owner):
		frappe.throw(owner_message(doctype))
	frappe.db.set_value(doctype, name, "owner", owner)
	return owner


@frappe.whitelist()
def get_people_details(users: str | list) -> list[dict]:
	"""Name, avatar and staff site roles of each user, for the People settings."""
	frappe.only_for(["Moderator", "Course Creator", "Batch Evaluator"])
	if isinstance(users, str):
		users = frappe.parse_json(users)
	users = [user for user in users or [] if isinstance(user, str)][:100]
	if not users:
		return []
	details = frappe.get_all(
		"User", filters={"name": ("in", users)}, fields=["name", "full_name", "user_image"]
	)
	for user in details:
		user.roles = get_staff_roles(user.name)
	return details


def get_staff_roles(user: str) -> list[str]:
	"""The site roles People eligibility reads."""
	return [role for role in frappe.get_roles(user) if role in STAFF_SITE_ROLES]


def add_missing_rows(doctype: str, name: str, rows: list[tuple[str, str]]):
	"""Writes People rows straight to the table, skipping ones already there, for a
	patch that must not re-run the parent's validation."""
	existing = frappe.get_all(
		"LMS Role Assignment",
		filters={"parent": name, "parenttype": doctype, "parentfield": "people"},
		fields=["member", "role"],
	)
	present = {(row.member, row.role) for row in existing}
	idx = len(existing)
	for member, role in dict.fromkeys(rows):
		if (member, role) in present or not frappe.db.exists("User", member):
			continue
		idx += 1
		full_name, user_image = frappe.db.get_value("User", member, ["full_name", "user_image"])
		row = frappe.new_doc("LMS Role Assignment")
		row.update(
			{
				"parent": name,
				"parenttype": doctype,
				"parentfield": "people",
				"idx": idx,
				"member": member,
				"role": role,
				"member_name": full_name,
				"member_image": user_image,
				"creation": now(),
				"modified": now(),
			}
		)
		row.db_insert()
