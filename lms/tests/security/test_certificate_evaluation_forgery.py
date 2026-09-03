import frappe
from frappe.tests.test_api import FrappeAPITestCase

from lms.lms.doctype.lms_certificate_evaluation.lms_certificate_evaluation import (
	create_lms_certificate,
)
from lms.lms.test_helpers import BaseTestUtils


class TestCertificateForgeryViaMappedDoc(BaseTestUtils, FrappeAPITestCase):
	"""Regression suite for VULN-2026-FRAPPE-LMS-011 (HD ticket 76548): create_lms_certificate
	must only issue a certificate for the evaluation's assigned evaluator or a Moderator.
	"""

	def setUp(self):
		super().setUp()
		h = frappe.generate_hash(length=6)
		self.victim_student = self._create_user(f"vic-{h}@example.com", "Vic", "Tim", ["LMS Student"])
		self.unrelated_eval = self._create_user(f"oev-{h}@example.com", "O", "Eval", ["Batch Evaluator"])
		self.assigned_eval = self._create_user(f"aev-{h}@example.com", "A", "Eval", ["Batch Evaluator"])
		# "LMS Certificate Evaluation" has no DocPerm row for "Moderator" (verified
		# against tabDocPerm; unlike the sibling LMS Batch/LMS Certificate doctypes).
		# A has_permission controller hook can only deny access, never grant it
		# beyond DocPerm, so a Moderator without Batch Evaluator would be denied by
		# frappe's base permission system before this hook's moderator branch is
		# ever consulted. Carrying Batch Evaluator here exercises the moderator
		# branch as it actually behaves today; the DocPerm gap itself is flagged
		# separately, not silently patched here.
		self.moderator = self._create_user(
			f"mod-{h}@example.com", "Mod", "Erator", ["Moderator", "Batch Evaluator"]
		)
		self.course = self._create_course(title=f"Cert Course {h}")

		# Evaluation exists but the victim was never enrolled/evaluated to completion,
		# unrelated_eval was never assigned to it, and assigned_eval is the only one
		# actually authorized to issue this certificate.
		self.evaluation = frappe.get_doc(
			{
				"doctype": "LMS Certificate Evaluation",
				"course": self.course.name,
				"member": self.victim_student.email,
				"evaluator": self.assigned_eval.email,
				"status": "Pending",
				"date": frappe.utils.nowdate(),
				"start_time": "10:00:00",
			}
		).insert(ignore_permissions=True)
		self.cleanup_items.append(("LMS Certificate Evaluation", self.evaluation.name))

	def test_unrelated_evaluator_cannot_reassign_themselves_then_forge(self):
		"""Regression: has_permission must gate write (and delete), not just read. An
		earlier version of this fix only restricted ptype=="read", leaving write wide open
		via LMS Certificate Evaluation's own DocPerm (Batch Evaluator: write=1, no
		if_owner) -- letting an unrelated evaluator call the generic frappe.client write
		path to reassign `evaluator` onto themselves, then legitimately pass the read gate
		and forge the certificate. Confirmed exploitable before this test existed."""
		frappe.set_user(self.unrelated_eval.email)
		try:
			doc = frappe.get_doc("LMS Certificate Evaluation", self.evaluation.name)
			doc.evaluator = self.unrelated_eval.email
			with self.assertRaises(frappe.PermissionError):
				doc.save()
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.get_value("LMS Certificate Evaluation", self.evaluation.name, "evaluator"),
			self.assigned_eval.email,
			msg="the evaluator field must be unchanged after the denied write",
		)

	def test_unassigned_evaluator_cannot_forge_certificate(self):
		frappe.set_user(self.unrelated_eval.email)
		try:
			with self.assertRaises(frappe.PermissionError):
				create_lms_certificate(self.evaluation.name)
		finally:
			frappe.set_user("Administrator")

	def test_victim_student_cannot_forge_own_certificate(self):
		# victim_student holds no Batch Evaluator/Moderator role and is the
		# evaluation's `member`, not its `evaluator` -- the wrong-role,
		# self-forgery attacker this ticket is about.
		frappe.set_user(self.victim_student.email)
		try:
			with self.assertRaises(frappe.PermissionError):
				create_lms_certificate(self.evaluation.name)
		finally:
			frappe.set_user("Administrator")

	def test_anonymous_caller_cannot_create_certificate(self):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				create_lms_certificate(self.evaluation.name)
		finally:
			frappe.set_user("Administrator")

	def test_assigned_evaluator_can_create_certificate(self):
		frappe.set_user(self.assigned_eval.email)
		try:
			forged = create_lms_certificate(self.evaluation.name)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(forged.member, self.victim_student.email)

	def test_moderator_can_create_certificate_regardless_of_evaluator(self):
		frappe.set_user(self.moderator.email)
		try:
			doc = create_lms_certificate(self.evaluation.name)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(doc.member, self.victim_student.email)

	def test_malformed_source_name_is_rejected_regardless_of_caller_role(self):
		# require_type_annotated_api_methods coerces/rejects the annotated arg
		# before create_lms_certificate's own body runs, raising FrappeTypeError
		# (a TypeError subclass) rather than the frappe.throw(...) -> ValidationError
		# the in-function isinstance guard would raise if ever reached directly.
		# Either way the malformed input is rejected before it can do anything,
		# for a caller who would also fail the permission check.
		frappe.set_user(self.unrelated_eval.email)
		try:
			with self.assertRaises((frappe.ValidationError, TypeError)):
				create_lms_certificate(source_name=123)
		finally:
			frappe.set_user("Administrator")

	def test_malformed_target_doc_is_rejected_regardless_of_caller_role(self):
		# Mirrors the source_name guard above: target_doc must be a dict or None.
		# require_type_annotated_api_methods coerces/rejects the annotated arg before
		# create_lms_certificate's own isinstance check runs, raising FrappeTypeError
		# (a TypeError subclass). Even the assigned (authorized) evaluator is rejected
		# before the mapped-doc build ever sees the malformed value.
		frappe.set_user(self.assigned_eval.email)
		try:
			with self.assertRaises((frappe.ValidationError, TypeError)):
				create_lms_certificate(self.evaluation.name, target_doc="not-a-dict")
		finally:
			frappe.set_user("Administrator")

	def test_pure_moderator_without_batch_evaluator_role_is_denied_read(self):
		# "LMS Certificate Evaluation" has no DocPerm row for "Moderator" (see setUp
		# comment). has_permission() can only restrict what DocPerm's role permission
		# system already grants, never extend it -- so a Moderator without Batch
		# Evaluator is denied read here even though has_permission()'s moderator
		# branch would, in isolation, say yes. This pins that actual behavior.
		h = frappe.generate_hash(length=6)
		pure_moderator = self._create_user(f"puremod-{h}@example.com", "Pure", "Mod", ["Moderator"])
		self.assertFalse(
			frappe.has_permission(
				"LMS Certificate Evaluation",
				"read",
				doc=self.evaluation.name,
				user=pure_moderator.email,
			)
		)

	def test_has_permission_hook_scopes_read_to_evaluator_and_moderator(self):
		self.assertTrue(
			frappe.has_permission(
				"LMS Certificate Evaluation", "read", doc=self.evaluation.name, user=self.assigned_eval.email
			)
		)
		self.assertFalse(
			frappe.has_permission(
				"LMS Certificate Evaluation",
				"read",
				doc=self.evaluation.name,
				user=self.unrelated_eval.email,
			)
		)
		self.assertTrue(
			frappe.has_permission(
				"LMS Certificate Evaluation", "read", doc=self.evaluation.name, user=self.moderator.email
			)
		)
