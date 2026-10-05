import frappe
from frappe.core.doctype.user.user import change_password

from lms.install import give_user_list_permission
from lms.lms.api import create_member, delete_member, save_role, update_member
from lms.lms.course_import_export import create_user as create_imported_instructor
from lms.lms.test_helpers import BaseTestUtils
from lms.patches.v2_0.revoke_moderator_user_write import execute as revoke_moderator_user_write

# Whitelist coercion refuses a wrong type before the endpoint's own guard does.
BAD_INPUT = (frappe.ValidationError, frappe.FrappeTypeError)


class TestModeratorUserWrite(BaseTestUtils):
	"""Regression from #2084 (eba181539): install gave Moderator write and create on core
	User, so a Moderator could reset a System Manager's password and log in as them.
	Added for audit finding #1 on branch fix/moderator-user-write."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.moderator = cls._create_user("muw-mod@example.com", "Mod", "One", ["Moderator"]).name
		cls.course_creator = cls._create_user("muw-cc@example.com", "Cc", "One", ["Course Creator"]).name
		cls.student = cls._create_user("muw-stu@example.com", "Stu", "One", ["LMS Student"]).name
		cls.manager = cls._create_user(
			"muw-sm@example.com", "Sm", "One", ["System Manager"], user_type="System User"
		).name
		cls.desk_user = cls._create_user("muw-desk@example.com", "Desk", "One", ["LMS Student"]).name

	def setUp(self):
		super().setUp()
		frappe.db.set_value("User", self.desk_user, "user_type", "System User")

	def tearDown(self):
		super().tearDown()
		frappe.clear_cache(doctype="User")

	def test_moderator_cannot_reset_a_system_manager_password(self):
		frappe.set_user(self.moderator)
		with self.assertRaises(frappe.PermissionError):
			change_password(user=self.manager, new_password="Owned-Passw0rd-!x")

	def test_moderator_keeps_read_on_user(self):
		self.assertTrue(frappe.has_permission("User", "read", user=self.moderator))
		for target in (self.manager, self.student):
			with self.subTest(target=target):
				self.assertFalse(frappe.has_permission("User", "write", doc=target, user=self.moderator))
		self.assertFalse(frappe.has_permission("User", "create", user=self.moderator))

	def test_install_does_not_grant_moderator_write_on_user(self):
		frappe.db.delete("Custom DocPerm", {"parent": "User", "role": "Moderator"})
		give_user_list_permission()
		row = frappe.db.get_value(
			"Custom DocPerm",
			{"parent": "User", "role": "Moderator", "permlevel": 0},
			["read", "write", "create"],
			as_dict=True,
		)
		self.assertEqual((row.read, row.write, row.create), (1, 0, 0))

	def test_patch_revokes_moderator_write_and_create_but_keeps_read(self):
		name = frappe.db.get_value("Custom DocPerm", {"parent": "User", "role": "Moderator", "permlevel": 0})
		frappe.db.set_value("Custom DocPerm", name, {"write": 1, "create": 1, "delete": 1})

		revoke_moderator_user_write()
		revoke_moderator_user_write()

		row = frappe.db.get_value("Custom DocPerm", name, ["read", "write", "create", "delete"], as_dict=True)
		self.assertEqual((row.read, row.write, row.create, row.delete), (1, 0, 0, 0))

	def test_moderator_creates_a_member(self):
		frappe.set_user(self.moderator)
		created = create_member({"email": "muw-new@example.com", "first_name": "New", "bio": "Hi"})

		self.assertEqual(created["name"], "muw-new@example.com")
		user = frappe.db.get_value("User", created["name"], ["first_name", "bio", "user_type"], as_dict=True)
		self.assertEqual((user.first_name, user.bio, user.user_type), ("New", "Hi", "Website User"))

	def test_create_member_refuses_fields_outside_the_profile(self):
		frappe.set_user(self.moderator)
		for field, value in (
			("roles", [{"role": "System Manager"}]),
			("new_password", "x"),
			("user_type", "System User"),
		):
			with self.subTest(field=field), self.assertRaises(frappe.ValidationError):
				create_member({"email": "muw-new@example.com", "first_name": "New", field: value})

	def test_create_member_refuses_malformed_input(self):
		frappe.set_user(self.moderator)
		for details in (
			"muw-new@example.com",
			["muw-new@example.com"],
			{"first_name": "No email"},
			{"email": 1},
		):
			with self.subTest(details=details), self.assertRaises(BAD_INPUT):
				create_member(details)

	def test_only_moderators_create_members(self):
		for actor in (self.course_creator, self.student, "Guest"):
			frappe.set_user(actor)
			with self.subTest(actor=actor), self.assertRaises(frappe.PermissionError):
				create_member({"email": "muw-new@example.com", "first_name": "New"})

	def test_moderator_updates_a_member_profile(self):
		frappe.set_user(self.moderator)
		update_member(self.student, {"first_name": "Renamed", "location": "Pune"})

		row = frappe.db.get_value("User", self.student, ["first_name", "location"], as_dict=True)
		self.assertEqual((row.first_name, row.location), ("Renamed", "Pune"))

	def test_moderator_updates_their_own_profile(self):
		frappe.set_user(self.moderator)
		update_member(self.moderator, {"bio": "Mine"})
		self.assertEqual(frappe.db.get_value("User", self.moderator, "bio"), "Mine")

	def test_update_member_refuses_system_users(self):
		frappe.set_user(self.moderator)
		for target in (self.manager, self.desk_user, "Administrator"):
			with self.subTest(target=target), self.assertRaises(frappe.PermissionError):
				update_member(target, {"first_name": "Owned"})

	def test_update_member_refuses_fields_outside_the_profile(self):
		frappe.set_user(self.moderator)
		for field in ("email", "enabled", "new_password", "roles", "api_key"):
			with self.subTest(field=field), self.assertRaises(frappe.ValidationError):
				update_member(self.student, {field: "x"})

	def test_only_moderators_update_members(self):
		frappe.set_user(self.course_creator)
		with self.assertRaises(frappe.PermissionError):
			update_member(self.student, {"first_name": "Owned"})

	def test_save_role_grants_and_revokes_an_lms_role(self):
		frappe.set_user(self.moderator)
		save_role(self.student, "Course Creator", 1)
		self.assertIn("Course Creator", frappe.get_roles(self.student))
		save_role(self.student, "Course Creator", 0)
		self.assertNotIn("Course Creator", frappe.get_roles(self.student))

	def test_save_role_refuses_system_users_and_self(self):
		frappe.set_user(self.moderator)
		for target in (self.manager, self.desk_user, self.moderator, "Administrator"):
			with self.subTest(target=target), self.assertRaises(frappe.PermissionError):
				save_role(target, "Moderator", 0 if target == self.moderator else 1)

	def test_save_role_refuses_a_user_with_a_role_profile(self):
		profile = frappe.get_doc({"doctype": "Role Profile", "role_profile": "muw-profile"})
		profile.append("roles", {"role": "LMS Student"})
		profile.insert(ignore_permissions=True, ignore_if_duplicate=True)
		frappe.db.set_value("User", self.student, "role_profile_name", "muw-profile")

		frappe.set_user(self.moderator)
		with self.assertRaises(frappe.PermissionError):
			save_role(self.student, "Course Creator", 1)

	def test_save_role_refuses_non_lms_roles_and_malformed_input(self):
		frappe.set_user(self.moderator)
		with self.assertRaises(frappe.PermissionError):
			save_role(self.student, "System Manager", 1)
		for args in (
			(["x"], "Course Creator", 1),
			(self.student, ["Moderator"], 1),
			(self.student, "Moderator", "x"),
		):
			with self.subTest(args=args), self.assertRaises(BAD_INPUT):
				save_role(*args)

	def test_delete_member_refuses_system_users(self):
		frappe.set_user(self.moderator)
		for target in (self.manager, self.desk_user):
			with self.subTest(target=target), self.assertRaises(frappe.PermissionError):
				delete_member(target)
		self.assertTrue(frappe.db.exists("User", self.manager))

	def test_system_manager_moderator_may_manage_system_users(self):
		frappe.set_user("Administrator")
		update_member(self.desk_user, {"first_name": "Desk2"})
		save_role(self.desk_user, "Course Creator", 1)
		self.assertIn("Course Creator", frappe.get_roles(self.desk_user))

	def test_course_import_creates_instructors_only_for_moderators(self):
		instructor = {"email": "muw-imported@example.com", "full_name": "Imported One"}
		frappe.set_user(self.course_creator)
		with self.assertRaises(frappe.PermissionError):
			create_imported_instructor(dict(instructor))

		frappe.set_user(self.moderator)
		create_imported_instructor(dict(instructor))
		self.assertIn("Course Creator", frappe.get_roles("muw-imported@example.com"))
