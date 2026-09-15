# Execution prompt for Sonnet

Two prompts follow. Run **Prompt A** in the `lms` repo first (it defines the contract). Run **Prompt B** in the `education` repo after Prompt A is merged. Each prompt is self-contained: paste it as the first message of a fresh session in the right repository. The shared contract is repeated in both so neither session needs the other's transcript.

---

## Prompt A — Frappe Learning (repo `lms`, branch `version-17`)

```
You are implementing the Learning side of the Frappe Education × Frappe Learning v17 integration in this repository (the Frappe LMS app, python package `lms`, app_name `frappe_lms`). Work on branch `version-17` (create it from `develop` if it does not exist). Commit in small, reviewable commits with conventional-commit messages (`feat:`, `refactor:`, `chore:`, `test:`). Push with `git push -u origin version-17`. Do not open a pull request unless asked.

Read `docs/education-integration/01-design.md` in this repo first. It is the source of truth; if anything below conflicts with it, follow this prompt and note the difference in your final summary.

### Context you need
Education 17 will declare LMS as a required app, and Education already ships roles named `Student` (portal role, desk_access 0) and `Instructor` (desk role). LMS 17 adopts the same names. Two consequences are non-negotiable and are spelled out in Step 1: LMS never changes `desk_access` on a role that already exists, and LMS never adds a role to every new User.

### Ground rules
- LMS must stay installable alone. Never import or reference an Education doctype, module or role anywhere in this app.
- Everything Education will call is in the contract below. Keep names exactly as written.
- Bypasses use `doc.flags` (server-side only), never fields. A student can set fields through REST; they cannot set flags.
- Do not remove or rename existing whitelisted methods other than those listed under "Breaking changes".
- Follow the repo conventions: tabs in Python, ruff line length 110 (`pyproject.toml`), pre-commit hooks in `.pre-commit-config.yaml`, Vue 3 + frappe-ui in `frontend/`, e2e tests with Playwright in `e2e/`. Run `pre-commit run --all-files` before each commit.
- Tests: Python unit tests live in `lms/lms/doctype/<doctype>/test_<doctype>.py` and `lms/tests/`. Read `lms/tests/test_enrollment_races.py` and `lms/tests/docperms.json`/`test_docperm_snapshot.py` before touching permissions; the docperm snapshot test will fail if you change permissions without updating the snapshot the way that test documents.

### Step 0 — Version 17
1. Set `lms/__init__.py` `__version__ = "17.0.0"`.
2. Create `lms/patches/v17_0/__init__.py`. New patches in this task go under `lms/patches/v17_0/` and are appended to `lms/patches.txt` under `[post_model_sync]` with a `#DD-MM-YYYY` suffix like the existing entries.
3. Update `README.md` install instructions that mention a version to say `version-17`.

### Step 1 — Role rename (breaking)
Rename the four LMS roles everywhere: `LMS Student` → `Student`, `Course Creator` → `Instructor`, `Batch Evaluator` → `Evaluator`, `Moderator` → `Learning Manager`.
1. Patch `lms/patches/v17_0/rename_roles.py` (post_model_sync, listed BEFORE any other v17 patch): for each pair, if the old role exists: if the new role does not exist, `frappe.rename_doc("Role", old, new, force=True)`; if it does exist (Education sites already have `Student` and `Instructor`), `frappe.rename_doc("Role", old, new, force=True, merge=True)` and then delete duplicate `Has Role` rows per user (same `parent`, same `role`) and duplicate `Custom DocPerm` rows. Do not touch `desk_access` of the target role in either branch. Wrap each pair in its own `try/except` with `frappe.log_error` and re-raise, so a partial failure is visible.
2. `lms/install.py`: rewrite `create_lms_roles` so each role is created with `desk_access = 0` only when it does not exist; remove every `frappe.db.set_value("Role", ..., "desk_access", 0)` on existing roles. Rename the functions accordingly. `give_lms_roles_to_admin` grants the new names. `delete_lms_roles` in `before_uninstall` must delete only roles that no other installed app's DocPerms reference (query `DocPerm` and `Custom DocPerm` for the role before deleting); otherwise leave the role and log.
3. Remove `"before_insert": "lms.lms.user.add_lms_student_role"` from the `User` doc_events in `hooks.py` and delete `add_lms_student_role`. Grant `Student` instead in `lms.lms.user.sign_up` (after the user is created) and in `LMSEnrollment.after_insert` / `LMSBatchEnrollment.after_insert` when the member lacks every privileged role. Add a unit test that creating a plain `User` grants no LMS role and that self-enrollment grants `Student`.
4. Replace the role strings in every doctype JSON under `lms/lms/doctype/**` (`permissions[].role`), every Python file (`PRIVILEGED_ROLES` in `lms/lms/utils.py`, `is_admin` helpers, `has_permission` and `get_permission_query_conditions` functions, `lms/lms/api.py::get_user_info`, `lms/lms/user.py`, `lms/install.py`, patches that reference roles, `lms/tests/**`), every frontend file under `frontend/src` (grep for each old string; role checks in stores and components), `e2e/**` fixtures, `lms/fixtures/**` if roles appear there, and the `lms/locale/*.po` translations (update `msgid` entries; run `bench generate-pot-file --app lms` if the repo's workflow expects it, see `.github/workflows/generate-pot-file.yml`). Keep the keys returned by `get_user_info` (`is_instructor`, `is_moderator`, `is_evaluator`, `is_student`) unchanged so the frontend contract holds; only the role names behind them change.
5. Regenerate the permission snapshot used by `lms/tests/test_docperm_snapshot.py` following the instructions in that test file, and confirm the diff shows only renamed roles.
6. Docs and demo data: update `lms/demo/**`, README role mentions and any in-app help text.

### Step 2 — Delivery mode (breaking rename)
1. In `lms/lms/doctype/lms_batch/lms_batch.json` rename field `medium` to `delivery_mode`, label "Delivery Mode", Select options `Online\nIn Person\nHybrid`, default `Online`, keep `in_list_view`/`in_standard_filter` as they were.
2. Patch `lms/patches/v17_0/rename_batch_medium_to_delivery_mode.py`: use `frappe.reload_doc`, `rename_field("LMS Batch", "medium", "delivery_mode")` from `frappe.model.utils.rename_field`, then `UPDATE` rows where the value is `Offline` to `In Person`. Guard every step with `frappe.db.has_column`.
3. Replace every read of `medium` in Python (`lms_batch.py` reminder emails, `send_mail`, `send_batch_start_reminder`), the Jinja email templates in `lms/templates/emails/` (label "Delivery Mode"), and the frontend (`frontend/src/pages/Forms/NewBatchForm.vue`, `frontend/src/pages/Batches/BatchForm.vue`, and any list/detail component that displays it; grep for `medium` and `Offline`). Batch cards and the batch detail header show a small badge with the mode.
4. Add a "Delivery Mode" filter to the batches list page next to the existing filters.

### Step 3 — Managed batches
1. Add to `LMS Batch` JSON: `managed_by_doctype` (Link → DocType, read_only, hidden unless set), `managed_by_docname` (Dynamic Link → managed_by_doctype, read_only), `is_managed` (Check, read_only, computed in `validate` as `bool(managed_by_docname)`).
2. In `LMSBatch.validate`, add `enforce_managed_lock()`: when `is_managed` and not `self.flags.managed_sync`, compare against `get_doc_before_save()` and `frappe.throw` if any of these changed: `title`, `start_date`, `end_date`, `start_time`, `end_time`, `delivery_mode`, `instructors` (as a set of users), `courses` (as a set of course names), `timetable` (as a set of `(reference_doctype, reference_docname)`), `paid_batch`, `allow_self_enrollment`, `seat_count`, `managed_by_doctype`, `managed_by_docname`. On insert with `managed_by_docname` set, require `flags.managed_sync`. The error message names the managing document: "This batch is managed by {doctype} {name}. Edit it there."
3. `LMS Batch Enrollment`: in `validate`, if the batch `is_managed` and not `self.flags.skip_eligibility_checks`, throw "Members of this batch are managed by {doctype} {name}." Same in `on_trash`. This makes membership one-directional. (References to "Step 2" flags below mean this step.)
4. `LMS Live Class`: add `reference_doctype` (Link → DocType) and `reference_docname` (Dynamic Link). When the batch is managed and the live class is created without `flags.managed_sync`, throw "Live classes for this batch are scheduled from {doctype} {name}."
5. Frontend, batch detail (`frontend/src/pages/Batches/` and related components): when `is_managed`, render a banner "Managed by {managed_by_doctype} {managed_by_docname}" (link to `/app/{slug}/{name}` for desk users), hide the Add Student / Remove Student controls, the timetable editor, the New Live Class button, the course add/remove controls and the date/mode fields in the batch form; keep announcements, assessments, feedback, certificates and discussions editable. Add e2e coverage in `e2e/` that a managed batch shows the banner and hides the controls (create the batch through the API with the flag in a fixture; see `e2e/fixtures.ts` and `e2e/helpers.ts` for how fixtures are seeded).

### Step 4 — Timetable rows that any app can populate
1. Add to `LMS Batch Timetable` JSON: `title` (Data), `location` (Data), `instructor_name` (Data), `url` (Data). All optional.
2. In `lms_batch.get_timetable_details`, use the row's own `title`/`url` when set and fall back to the existing per-doctype lookups only for `Course Lesson`, `LMS Quiz`, `LMS Assignment`, `LMS Live Class`. Never `frappe.db.get_value` on an unknown `reference_doctype`. Return `location` and `instructor_name` in the payload and show them in the timetable UI (`frontend/src/components/BatchTimetable*` or wherever the timetable renders; grep for `get_batch_timetable`).
3. `validate_timetable` currently rejects rows outside the batch's daily start/end time. Managed batches skip the time-of-day check (an academic timetable spans the whole day) but keep the date-range check.

### Step 5 — Enrollment flags and source
1. Add `source` (Link → LMS Source) to `LMS Enrollment` JSON.
2. `LMSEnrollment.before_insert`: when `self.flags.skip_eligibility_checks` is true, skip `validate_course_enrollment_eligibility` entirely (published, `disable_self_learning`, paid course). Keep `validate_duplicate_enrollment` and `validate_owner`.
3. `LMSBatchEnrollment.validate`: when `self.flags.skip_eligibility_checks` is true, skip `validate_owner`, `validate_payment`, `validate_self_enrollment`, `validate_seat_availability` and the managed-membership throw from Step 2. Keep `validate_duplicate_members` and `validate_course_enrollment`; inside `validate_course_enrollment`, propagate the flag and `source` to the `LMS Enrollment` it creates.
4. Add a unit test that a REST-style insert (no flags) into a paid course still throws, and that an insert with the flag succeeds.

### Step 6 — `lms/lms/integration.py` (the contract)
Create the module with exactly these functions. Every function validates its inputs with `frappe.throw` on bad arguments, is idempotent where the design says so, and commits nothing itself (callers own the transaction). Only `get_progress` and `get_quiz_results` are `@frappe.whitelist()`ed; those two restrict non-privileged users (`lms.lms.utils.PRIVILEGED_ROLES`) to their own member.

```
create_managed_batch(managed_by_doctype, managed_by_docname, title, start_date, end_date,
                     delivery_mode, instructors, courses, description=None, timezone=None,
                     conferencing_provider=None, zoom_account=None, google_meet_account=None) -> str
update_managed_batch(batch, **fields) -> None
sync_batch_members(batch, members, source) -> dict   # {"added": [...], "removed": [...]}
enroll(member, course, source, batch=None) -> str      # returns LMS Enrollment name; existing row returned unchanged
unenroll(member, course) -> None
upsert_timetable_row(batch, reference_doctype, reference_docname, date, start_time, end_time,
                     title, location=None, instructor_name=None, url=None) -> str   # child row name
remove_timetable_row(batch, reference_doctype, reference_docname) -> None
create_live_class(batch, title, date, time, duration, host, reference_doctype=None,
                  reference_docname=None, description=None) -> dict   # {"name", "join_url", "start_url"}
update_live_class(name, **fields) -> None
cancel_live_class(name) -> None
get_progress(member, course) -> float
get_quiz_results(quiz, members=None, attempt="best") -> dict   # member -> {"percentage", "score", "score_out_of", "submission"}
get_assignment_results(assignment, members=None) -> dict       # member -> {"status", "submission"}
get_live_class_participation(live_class) -> dict               # member -> {"duration_seconds", "joined_at", "left_at"}
grant_roles(user, roles) -> None                               # only Student, Instructor, Evaluator, Learning Manager
```
Implementation notes:
- `grant_roles` never changes `desk_access` and refuses any role outside the four LMS roles with `frappe.throw`.
- `create_managed_batch` sets `paid_batch=0`, `seat_count=0`, `allow_self_enrollment=0`, `published=0`, `timezone` defaulting to `frappe.utils.get_system_timezone()`, `start_time`/`end_time` 00:00–23:59, `batch_details` from `description` or the title, and inserts with `flags.managed_sync=True` and `ignore_permissions=True`. It reuses `create_live_class`/`create_google_meet_live_class` already in `lms_batch.py` for conferencing; refactor those so they can be called with an explicit batch doc and host instead of reading `frappe.session.user`.
- `update_managed_batch` accepts only the lockable fields and `description`, sets `flags.managed_sync`, saves with `ignore_permissions`.
- `sync_batch_members` diffs current `LMS Batch Enrollment` rows against `members`, inserts missing with `flags.skip_eligibility_checks` and `source`, deletes extra rows with `flags.skip_eligibility_checks`. Use the same row locks the existing enrollment code uses (read the comments in `lms_batch_enrollment.py` before touching locking).
- `get_quiz_results` with `attempt="best"` picks the highest `percentage` per member, `"latest"` picks the newest `creation`.
- Add `lms/tests/test_integration_contract.py` covering each function, including: batch lock rejects a plain save and accepts a flagged one; members sync add/remove; enroll idempotency; timetable upsert updates in place; quiz results best vs latest; role granting refuses non-LMS roles.

### Step 7 — Profile privacy
1. Add `hide_member_profiles` (Check) to `LMS Settings` under the existing privacy/visibility section.
2. When enabled, non-privileged users get a 403 from the profile pages (`/user/:username` routes in `frontend/src/routes.js` and their API calls in `lms/lms/api.py` or `lms/lms/utils.py`; grep for `get_profile` / `username`) and the `/certified-participants` page, except for their own profile. Privileged roles are unaffected.
3. Unit test for the API side; e2e test that a student opening another student's profile sees the not-permitted page.

### Step 8 — Optional ERPNext invoicing (`lms/lms/accounting.py`)
This feature must work on a site with ERPNext but without Education, and must not exist at all (no fields, no jobs) on a site without ERPNext. LMS still requires neither.
1. Native field: `LMS Settings.enable_invoicing` (Check, default 0) in a new "Accounting" section with a description "Requires ERPNext".
2. Custom fields, created by `accounting.setup_accounting_fields()` from `after_install` and from a new `after_app_install` hook in `hooks.py` that runs when the installed app is `erpnext` (both idempotent; skip entirely when ERPNext is absent):
   - `LMS Settings`: `company` (Link → Company), `income_account` (Link → Account), `cost_center` (Link → Cost Center), `customer_group` (Link → Customer Group), `taxes_and_charges` (Link → Sales Taxes and Charges Template), `mode_of_payment` (Link → Mode of Payment), `auto_submit_invoice` (Check).
   - `LMS Course.item` and `LMS Batch.item` (Link → Item, read_only, in a collapsed "Accounting" section).
   - `LMS Payment.customer` (Link → Customer, read_only) and `LMS Payment.sales_invoice` (Link → Sales Invoice, read_only).
   Use `frappe.custom.doctype.custom_field.custom_field.create_custom_fields` with `module = "LMS"`; `before_uninstall` removes them (extend the existing `delete_custom_fields`).
3. Hooks LMS declares (add to `hooks.py` with a comment explaining the contract):
   - `lms_get_customer`: list of dotted paths `fn(user) -> str | None`. LMS iterates `frappe.get_hooks("lms_get_customer")` and uses the first non-empty result.
   - `lms_before_sales_invoice_insert`: list of dotted paths `fn(invoice_doc, payment_doc) -> None`, called before the invoice is inserted.
4. `accounting.py`:
   - `is_enabled()`: ERPNext installed and `enable_invoicing` and `company` set.
   - `get_or_create_customer(user)`: run the hook resolvers; fallback: find a `Customer` linked (via Dynamic Link) to a `Contact` with `email_id == user`; else create `Customer` (`customer_type = Individual`, `customer_name = full name`, `customer_group` from settings or the default from Selling Settings) and a `Contact` with that email linked to it. Set `Customer.tax_id` from `LMS Payment.gstin` when present and empty.
   - `get_or_create_item(doctype, name)`: `Item` with `item_code = "LMS-COURSE-<name>"` / `"LMS-BATCH-<name>"`, `item_name = title`, `item_group` "Courses" (create the group under All Item Groups if missing), `is_stock_item = 0`, `is_sales_item = 1`; store on the course/batch.
   - `create_invoice_for_payment(payment_name)`: idempotent (returns early when `sales_invoice` is set). Builds `Sales Invoice` with `customer`, `company`, `currency = payment.currency`, `customer_address = payment.address`, `set_posting_time = 1`, `posting_date = payment.creation date`, one item row (`item_code`, `qty = 1`, `rate = payment.original_amount or payment.amount`, `income_account`, `cost_center`), `discount_amount = payment.discount_amount`, `taxes_and_charges` from settings (run `set_missing_values` / `calculate_taxes_and_totals` like ERPNext expects), `remarks` with the LMS Payment name and coupon code. Call the `lms_before_sales_invoice_insert` hooks, insert with `ignore_permissions`. Then `get_payment_entry("Sales Invoice", invoice.name)` from `erpnext.accounts.doctype.payment_entry.payment_entry`, set `mode_of_payment`, `reference_no = payment.payment_id`, `reference_date`, insert. Submit both when `auto_submit_invoice`. Save `LMS Payment.customer` and `sales_invoice` with `frappe.db.set_value`. Any exception → `frappe.log_error(title="LMS invoicing")` and re-raise inside the job only (never inside the payment callback).
   - `enqueue_invoice(payment_doc)`: called from `LMSPayment.on_update` when `payment_received` flipped to 1 and `is_enabled()`; `frappe.enqueue(create_invoice_for_payment, payment_name=..., enqueue_after_commit=True)`.
   - Whitelisted `get_invoice_pdf(payment)`: allowed when `payment.member == frappe.session.user` or a privileged role; returns the PDF of the default Sales Invoice print format via `frappe.get_print(..., as_pdf=True)`, wrapping the call so it does not depend on the student holding Sales Invoice permission.
   - Whitelisted `create_invoice(payment)` for privileged roles (the "Create Invoice" button in the LMS Payment desk form and on the LMS billing admin view) that runs the job synchronously and returns the invoice name.
5. Frontend: on the billing / payment history views (`frontend/src/pages/Billing.vue` and wherever payment history is listed; grep for `LMS Payment`), show an "Invoice" link that opens the PDF from `get_invoice_pdf` when `sales_invoice` is set.
6. Tests in `lms/tests/test_accounting.py`, skipped with `unittest.skipUnless("erpnext" in frappe.get_installed_apps())`: fields created and removed; customer fallback creates one Customer per email; hook resolver wins over fallback (register a test hook by monkeypatching `frappe.get_hooks`); invoice + payment entry created once for a paid payment and not twice; disabled setting creates nothing. Add an `erpnext` job to `.github/workflows/ci.yml` that installs ERPNext before LMS and runs this test module; the existing job without ERPNext must still pass (the module is skipped there).
7. Docs: `docs/erpnext-invoicing.md` describing setup, the two hooks with a minimal example implementation, and the limits (no backfill by default, no credit notes, single company). Mention the optional `bench execute lms.lms.accounting.backfill_invoices` helper you add for past payments, which only runs when explicitly called.

### Step 9 — Housekeeping
1. `lms/install.py`: no change required, but confirm `LMS Source` records are not seeded with anything named "Education" (Education creates its own).
2. Docs: add `docs/integration-contract.md` describing the fields, flags and `integration.py` functions above with one example call each. Link it from `README.md`.
3. Update `lms/lms/doctype/lms_batch/lms_batch_dashboard.py` if it exists to include `LMS Live Class` under a "Scheduling" group (skip if no dashboard file).

### Breaking changes you are allowed to make
- Role renames listed in Step 1 and the end of automatic `Student` assignment on User insert.
- `LMS Batch.medium` → `delivery_mode` with `Offline` → `In Person`.
- Managed batches reject direct edits of locked fields and direct membership changes.
- Version 2.45.x → 17.0.0.
The ERPNext invoicing feature is additive and off by default; it must not change behaviour for sites that do not enable it. Anything else that would break an existing API consumer: stop and list it in the summary instead of doing it.

### Verification before you finish
- `bench --site <site> migrate` on a site that has batches with `medium = Offline` shows them as `In Person`, and on a site that already had a `Student` role with `desk_access = 0` and an `Instructor` role with `desk_access = 1`, both keep their `desk_access` and all former `LMS Student` / `Course Creator` users hold the merged roles exactly once.
- `bench --site <site> run-tests --app lms` passes, including the docperm snapshot test.
- `cd frontend && yarn lint && yarn build` pass; `yarn test:e2e` (see `package.json` for the exact script) passes for the batch specs you added.
- On a bench with ERPNext: enable invoicing, complete a paid course purchase in a test, and show the Sales Invoice and Payment Entry linked from the LMS Payment; on a bench without ERPNext: `LMS Settings` shows only the `enable_invoicing` check and no ERPNext custom fields exist.
- Final summary: list every file touched grouped by step, every new field, every patch, and any deviation from this prompt.
```

---

## Prompt B — Frappe Education (repo `education`, branch `version-17`)

```
You are implementing the Education side of the Frappe Education × Frappe Learning v17 integration in this repository (python package `education`, requires `erpnext`; from v17 it also requires `lms`). Work on branch `version-17` (create from `develop` if missing). Commit in small conventional commits and push with `git push -u origin version-17`. Do not open a pull request unless asked.

Learning (LMS, python package `lms`, installed app name `lms`) version 17 already ships the contract below. Treat it as frozen. Read `lms/lms/integration.py` and `docs/integration-contract.md` in the LMS app in your bench before starting.

### The Learning contract you build on
Roles (shared with Education from v17): `Student`, `Instructor`, `Evaluator`, `Learning Manager`. LMS no longer assigns `Student` to every new User and never changes `desk_access` of an existing role.
Fields on LMS doctypes: `LMS Batch.delivery_mode` (Online / In Person / Hybrid), `LMS Batch.managed_by_doctype` + `managed_by_docname` + `is_managed`; `LMS Batch Timetable.title/location/instructor_name/url`; `LMS Live Class.reference_doctype/reference_docname`; `LMS Enrollment.source`; `LMS Settings.hide_member_profiles`.
Server flags: `doc.flags.managed_sync` (LMS Batch, LMS Live Class), `doc.flags.skip_eligibility_checks` (LMS Enrollment, LMS Batch Enrollment).
Module `lms.lms.integration`: `create_managed_batch`, `update_managed_batch`, `sync_batch_members`, `enroll`, `unenroll`, `upsert_timetable_row`, `remove_timetable_row`, `create_live_class`, `update_live_class`, `cancel_live_class`, `get_progress`, `get_quiz_results`, `get_assignment_results`, `get_live_class_participation`, `grant_roles`. Always call these instead of writing to LMS doctypes directly.
Doc events you may subscribe to: `LMS Quiz Submission.after_insert`, `LMS Assignment Submission.on_update`, `LMS Enrollment.on_update`, `LMS Live Class Participant.after_insert`.
Hooks LMS declares for its optional ERPNext invoicing: `lms_get_customer` (list of `fn(user) -> customer or None`, first non-empty wins) and `lms_before_sales_invoice_insert` (list of `fn(invoice_doc, payment_doc)`). LMS creates the Sales Invoice and Payment Entry itself; Education only resolves the customer and stamps its own fields.

### Ground rules
- Learning is a required app. `hooks.py` declares `required_apps = ["frappe/erpnext", "frappe/lms"]`. Education may import `lms` at module level and its doctype JSON may hold native Link fields to LMS doctypes. Do not add installed-app guards.
- Existing sites upgrading without LMS must stop early: add `before_migrate = ["education.lms_integration.setup.check_lms_installed"]` that throws `Install the Learning app before migrating to Education 17: bench get-app lms --branch version-17 && bench --site <site> install-app lms` when `"lms" not in frappe.get_installed_apps()`.
- All sync code lives in `education/education/lms_integration/` with modules `__init__.py` (helpers: `get_student_user`, `get_lms_courses_for_group`), `setup.py` (LMS Source, sidebar items, settings defaults, role fixes), `groups.py`, `enrollments.py`, `schedule.py`, `attendance.py`, `assessments.py`, `roles.py`, `tasks.py`.
- Every sync function is idempotent and safe to re-run. Wrap per-document work in `try/except` with `frappe.log_error(title="LMS sync")` so one failure does not abort a batch of updates.
- Repo conventions: tabs, ruff config in `pyproject.toml`, tests are `test_*.py` next to doctypes and use `education/education/test_utils.py`. CI runs `bench --site test_site run-tests --app education`.

### Step 0 — Version 17 and removal of legacy LMS residue
1. `education/__init__.py` → `__version__ = "17.0.0"`. Create `education/patches/v17_0/`.
2. Patch `education/patches/v17_0/export_legacy_lms_content.py` (post_model_sync, must run BEFORE doctype deletion, so list it first): for each of `Article`, `Topic`, `Quiz`, `Question`, `Course Activity`, `Quiz Activity`, `Course Enrollment` (only its rows, not the doctype), dump all rows with child tables as JSON into `frappe.get_site_path("private", "files", "education_legacy_lms", f"{doctype}.json")`. Skip tables that do not exist. Log the export location with `frappe.logger().info`.
3. Delete doctype folders and all references: `article`, `topic`, `topic_content`, `course_topic`, `quiz`, `question`, `options`, `quiz_question`, `quiz_activity`, `quiz_result`, `course_activity`. Remove `Course.topics`, `Course.get_topics`, the "LMS Utils" section of `education/education/utils.py` (`get_current_student` stays because the portal uses it; move it above the removed section), `Student.get_topic_progress`, `Student.enroll_in_program`, `Student.enroll_in_course`, `CourseEnrollment.get_progress`, `add_quiz_activity`, `add_activity`, `check_activity_exists`. Remove the entries from `global_search_doctypes` in `hooks.py` including the non-existent `Video`, `Announcement`, `Assessment Code`, `Discussion`. Add patch `delete_legacy_lms_doctypes.py` that calls `frappe.delete_doc("DocType", name, ignore_missing=True, force=True)` for each removed doctype. Keep `Course Enrollment` (it becomes the per-course link to LMS).
4. Optional migration into Learning, patch `migrate_legacy_content_to_lms.py`: only when the export files exist. For each Education Course that had topics: create an unpublished `LMS Course` titled after the course, one `Course Chapter` per topic, one `Course Lesson` per Article (body = article content), one `LMS Quiz` per Quiz with `LMS Question` rows (map `Options` to `option_N`/`is_correct_N`, up to 10), and set the new `Course.lms_course` field. Wrap in a settings check `Education Settings.migrate_legacy_lms_content` (Check, default 0) so it is opt-in; document how to run it later with `bench execute`.

### Step 1 — Setup: fields, source, sidebar, roles, hooks
1. Native fields in doctype JSON (Link options are LMS doctypes; this is fine because LMS is always installed first):
   - `Course.lms_course` Link → LMS Course.
   - `Student Group.lms_batch` Link → LMS Batch (read_only), `Student Group.conferencing_provider` Select (`\nZoom\nGoogle Meet`), `Student Group.zoom_account` Link → LMS Zoom Settings, `Student Group.google_meet_account` Link → LMS Google Meet Settings, `Student Group.batch_start_date` Date, `Student Group.batch_end_date` Date (both optional; default from academic term, else academic year).
   - `Course Schedule.lms_live_class` Link → LMS Live Class (read_only), `Course Schedule.join_url` Data (read_only, fetched from `lms_live_class.join_url`).
   - `Course Enrollment.lms_enrollment` Link → LMS Enrollment (read_only), `Course Enrollment.lms_progress` Percent (read_only).
   - `Assessment Plan.lms_quiz` Link → LMS Quiz, `Assessment Plan.lms_assignment` Link → LMS Assignment, depends_on `assessment_source`.
   - `Education Settings.default_conferencing_provider` Select, `default_zoom_account` Link → LMS Zoom Settings, `default_google_meet_account` Link → LMS Google Meet Settings.
   `lms_integration/setup.py::setup_lms_integration()` (idempotent, called from `after_install` and `after_migrate`) creates:
   - `LMS Source` record named "Education".
   - Role fixes: ensure `Instructor` exists with `desk_access = 1` and `Student` with `desk_access = 0` (LMS installs first and creates `Instructor` with `desk_access = 0`; Education needs the desk for teachers). Also add patch `education/patches/v17_0/instructor_role_desk_access.py` doing the same for upgraded sites, listed AFTER LMS's role rename has run (Education patches run after LMS patches because of app order; verify with `bench --site <site> migrate` on an upgraded site).
   - For every enabled User holding `Education Manager`, `lms.lms.integration.grant_roles(user, ["Learning Manager"])`.
   - `LMS Sidebar Item` rows on `LMS Settings.sidebar_items` (item_type `External`, `open_in_new_window` 0) titled Timetable → `/student-portal/schedule`, Attendance → `/student-portal/attendance`, Fees → `/student-portal/fees`, Grades → `/student-portal/grades`; skip rows that already exist by title.
   - Set `LMS Settings.hide_member_profiles = 1` if it is currently 0 and `Education Settings.lms_profiles_configured` is 0; then set that flag so we never override an admin's later choice.
2. More native JSON fields: `Student Group.delivery_mode` Select `Classroom\nOnline\nBlended` default Classroom (insert after `group_based_on`); `Course Schedule.session_type` Select `In Person\nOnline` default In Person; `Assessment Plan.assessment_source` Select `Manual\nLMS Quiz\nLMS Assignment` default Manual, `Assessment Plan.attempt_policy` Select `Best attempt\nLatest attempt` default Best attempt; `Instructor.user` Link → User with `fetch_from: employee.user_id`, `fetch_if_empty: 1`; `Education Settings`: `enable_lms_integration` Check default 1, `live_class_attendance_threshold` Percent default 75, `auto_submit_live_class_attendance` Check default 0, `lms_profiles_configured` Check hidden, `migrate_legacy_lms_content` Check.
3. `hooks.py`: `required_apps = ["frappe/erpnext", "frappe/lms"]`; `after_install` also calls `setup_lms_integration`; `before_migrate` from the ground rules; `after_migrate = ["education.lms_integration.setup.setup_lms_integration"]`. Add `doc_events`:
   - `Student Group`: `on_update` → `groups.sync_group`, `on_trash` → `groups.on_group_trash`.
   - `Course Schedule`: `after_insert` and `on_update` → `schedule.sync_schedule`, `on_trash` → `schedule.on_schedule_trash`.
   - `Program Enrollment`: `on_submit` → `enrollments.on_program_enrollment_submit`, `on_cancel` → `enrollments.on_program_enrollment_cancel`.
   - `Instructor`: `on_update` → `roles.sync_instructor_roles`. `Student`: `on_update` → `roles.sync_student_role`. `User`: `on_update` → `roles.sync_manager_role`.
   - `LMS Enrollment`: `on_update` → `enrollments.on_lms_enrollment_update`. `LMS Quiz Submission`: `after_insert` → `assessments.on_quiz_submission`. `LMS Assignment Submission`: `on_update` → `assessments.on_assignment_submission`.
   `scheduler_events`: `hourly` → `attendance.mark_attendance_for_ended_sessions`; `daily` → `tasks.reconcile`.
   Every handler returns immediately when `Education Settings.enable_lms_integration` is 0.
4. `Course Schedule.validate`: `room` is mandatory only when `session_type == "In Person"` (currently `reqd` in JSON; make it optional in JSON and validate in Python).

### Step 2 — Identity and roles (`roles.py`, `__init__.py`)
- `get_student_user(student_name) -> str`: return `Student.user`; if empty and `student_email_id` matches an existing User, link it; otherwise create the user the way `Student.validate_user` does (respecting `user_creation_skip` only for the automatic path; the bridge always needs a user, so create one and log it). Then `grant_roles(user, ["Student"])`. Since LMS no longer adds `Student` to every new User, this and the `Student` doctype are the only places the role is granted on an Education site.
- `sync_instructor_roles`: when `Instructor.user` is set, `grant_roles(user, ["Instructor"])`. Because the role is shared, this is the same role that gives desk access to attendance and assessment. Do not grant `Evaluator` automatically; it is assigned by hand or when a user is added as an LMS `Course Evaluator`.
- `sync_student_role`: on Student update with a user, ensure `Student`.
- `sync_manager_role(user_doc, method)`: when a User gains `Education Manager`, grant `Learning Manager`; when it loses it, leave `Learning Manager` alone (removing is a manual decision) and log nothing.

### Step 3 — Groups ↔ batches (`groups.py`)
- `get_lms_courses_for_group(group)`: course-based group → `[Course.lms_course]` if set; batch-based or activity-based → `lms_course` of every `Program Course` of the group's program that has one. Empty list → the group cannot be Online/Blended; `frappe.throw` in `Student Group.validate` with a message naming which Course needs an LMS course.
- `sync_group(doc, method)`: if `delivery_mode == "Classroom"`: if `lms_batch` exists, leave it but set `update_managed_batch(batch, published=0)` and log; do not delete. Else: if no `lms_batch`, `create_managed_batch(managed_by_doctype="Student Group", managed_by_docname=doc.name, title=doc.student_group_name, start_date, end_date, delivery_mode = "Online" if Online else "Hybrid", instructors=[Instructor.user of each Student Group Instructor with a user], courses=get_lms_courses_for_group(doc), conferencing_provider/accounts from the group or Education Settings defaults)` and store `lms_batch` via `frappe.db.set_value` (avoid recursion). If it exists, `update_managed_batch` with the same values. Then `sync_batch_members(batch, [get_student_user(row.student) for row in doc.students if row.active], source="Education")`. If `len(doc.students) > 100`, run the member sync through `frappe.enqueue` with `enqueue_after_commit=True`.
- `on_group_trash`: if `lms_batch`, `update_managed_batch(batch, published=0)`; never delete LMS data.
- Desk: `student_group.js` adds a button "Open in Learning" → `/lms/batches/details/{lms_batch}` when set.
- Batch instructors passed to `create_managed_batch` are the `Instructor.user` values; users without one are skipped with a `frappe.msgprint` warning on the group.

### Step 4 — Program enrollment → self-paced access (`enrollments.py`)
- `on_program_enrollment_submit`: for each course row with `Course.lms_course`, `enroll(user, lms_course, source="Education")` and set `Course Enrollment.lms_enrollment` on the matching Course Enrollment row (created by the existing `create_course_enrollments`).
- `on_program_enrollment_cancel`: `unenroll` only when the student is not in any Student Group with a managed batch that includes that LMS course.
- `on_lms_enrollment_update(doc, method)`: find Course Enrollments with `lms_enrollment == doc.name` and set `lms_progress = doc.progress`.
- `course.js`: button "Create Learning course" (visible when `lms_course` is empty) calls whitelisted `education.lms_integration.enrollments.create_lms_course(course)` which inserts an unpublished `LMS Course` (title, short_introduction = description or title, description, instructors = users of instructors in any group for that course, else the current user) and links it.

### Step 5 — Schedule, live classes, attendance (`schedule.py`, `attendance.py`)
- `sync_schedule(doc, method)`: skip unless the group has `lms_batch`. `upsert_timetable_row(batch, "Course Schedule", doc.name, doc.schedule_date, doc.from_time, doc.to_time, title=doc.title, location=doc.room, instructor_name=doc.instructor_name, url=join_url if online)`. If `session_type == "Online"`: require `Instructor.user` (throw otherwise); if no `lms_live_class`, `create_live_class(batch, title, date, time, duration_minutes, host=instructor user, reference_doctype="Course Schedule", reference_docname=doc.name)` and store `lms_live_class` + `join_url` with `frappe.db.set_value`; else `update_live_class(name, date=..., time=..., duration=..., title=...)`. If switched from Online to In Person, `cancel_live_class` and clear the fields.
- `on_schedule_trash`: `remove_timetable_row` and `cancel_live_class` when set.
- `Course Scheduling Tool` creates schedules through `frappe.get_doc(...).insert()`, so the doc events fire; verify and add a test.
- `mark_attendance_for_ended_sessions()` (hourly): Course Schedules with `session_type = Online`, `lms_live_class` set, ended more than 15 minutes ago, and no Student Attendance rows yet for that schedule. For each student in the group: participation = `get_live_class_participation(live_class)`; Present if `duration_seconds >= threshold% * scheduled_seconds` else Absent; respect `Student Leave Application` (status Leave) the same way `education.education.api.mark_attendance` does; reuse `make_attendance_records`; submit only when `auto_submit_live_class_attendance` is on. Skip schedules on or before `attendance_freeze_date`.
- Student portal (`frontend/`): on `Schedule.vue` show a "Join" link when a schedule row has `join_url` (extend `get_course_schedule_for_student` in `education/education/api.py` to return `session_type` and `join_url`), and add a "Learning" item in the portal navigation that links to `/lms`.

### Step 6 — Assessments from LMS (`assessments.py`)
- `Assessment Plan` JS: show `lms_quiz` when `assessment_source == "LMS Quiz"`, `lms_assignment` for `LMS Assignment`; button "Fetch results from Learning" → whitelisted `fetch_lms_results(assessment_plan)`.
- `fetch_lms_results(plan)`: students = `get_assessment_students`; members = their users; results = `get_quiz_results(plan.lms_quiz, members, attempt="best"|"latest")` or `get_assignment_results`. For each student, use the existing `get_assessment_result_doc` / `mark_assessment_result` path to upsert a draft Assessment Result: total = percentage/100 × `maximum_assessment_score` (assignments: Pass → full, Fail → 0, Not Graded → skip), distributed across `assessment_criteria` rows proportionally to each criterion's `maximum_score`, grade via `get_grade`. Return counts of created/updated/skipped.
- `on_quiz_submission(doc, method)` / `on_assignment_submission`: find submitted Assessment Plans with matching `lms_quiz`/`lms_assignment` whose student group contains the student for this user; call the same upsert for that one student. Never touch submitted (docstatus 1) results.

### Step 6b — Invoicing hooks (`billing.py` inside `lms_integration`)
- `hooks.py`: `lms_get_customer = ["education.education.lms_integration.billing.get_customer_for_user"]` and `lms_before_sales_invoice_insert = ["education.education.lms_integration.billing.before_sales_invoice_insert"]`.
- `get_customer_for_user(user)`: find the enabled `Student` with `user == user` (fallback `student_email_id == user`); return `Student.customer`, creating it through the existing `Student.set_missing_customer_details` path if empty; return `None` when no Student exists so LMS's fallback runs.
- `before_sales_invoice_insert(invoice, payment)`: if the customer belongs to a Student, set `invoice.student` (the custom field Education adds to Sales Invoice) so the purchase appears on the portal Fees page (`get_student_invoices` in `education/education/api.py`; verify it lists invoices by `student` and not only by `fee_schedule`, and extend it if needed so LMS purchases show with a "Learning" label).
- Tests: a Student's LMS purchase resolves to `Student.customer`; a non-student user returns `None`; the Fees page API includes the invoice.

### Step 7 — Reconciliation and tests (`tasks.py`, tests)
- `reconcile()` daily: for every Student Group with `delivery_mode != Classroom`, call `sync_group`; for every Course Enrollment with `lms_enrollment`, refresh `lms_progress`; log a summary.
- Tests in `education/education/lms_integration/tests/`. Cover: setup idempotency (run twice, no duplicates); `Instructor` keeps `desk_access = 1` after setup and after the patch; a new plain User gets no `Student` role; an Education Manager gets `Learning Manager`; group create → managed batch with correct courses/members; member removal; classroom group creates nothing; program enrollment → LMS enrollment and cancel behaviour; online schedule → timetable row + live class (mock the Zoom/Meet HTTP call by patching `lms.lms.doctype.lms_batch.lms_batch.authenticate` and the request function, look at how LMS's own tests do it); attendance job with mocked participation; assessment fetch mapping for best/latest and assignment statuses.
- CI: in the existing workflow add `bench get-app https://github.com/frappe/payments` and `bench get-app https://github.com/frappe/lms --branch version-17` before `install-app education` (bench installs required apps first), then `run-tests --app education`. Add a second job that starts from an Education site without LMS, installs LMS, runs migrate, and asserts the role merge and `desk_access` outcomes.

### Step 8 — Docs
- `docs/learning-integration.md` in this repo: concepts (delivery modes at group and session level), the shared role model, setup, how managed batches behave in Learning, attendance and grading rules, the upgrade guide for v17 (install Learning first, dead doctypes, export location, opt-in migration), and known limits (timezones, guardians).

### Breaking changes you are allowed to make
Learning as a required app; removal of the legacy content doctypes and their whitelisted methods; `Instructor.user`; the three new Select fields with safe defaults; `Course Schedule.room` optional for online sessions; version 17.0.0. Anything else that breaks an existing API consumer: stop and list it in the summary.

### Verification before you finish
- Fresh site: `bench --site <site> install-app education` pulls in LMS and payments first; afterwards `LMS Source` "Education", the sidebar items, `hide_member_profiles = 1`, `Instructor.desk_access = 1` and `Student.desk_access = 0` all hold.
- Upgraded site: an Education 16 style site with `Student` and `Instructor` roles and users holding them, plus LMS 17 installed before migrate → after migrate no duplicate `Has Role` rows, teachers still have desk access, `Education Manager` users hold `Learning Manager`.
- Site without LMS: `bench --site <site> migrate` stops at the `before_migrate` guard with the install instruction.
- `bench --site <site> run-tests --app education` passes.
- Manual scenario written up in the summary: a Blended Student Group with 3 students, one In Person and one Online Course Schedule, a quiz-sourced Assessment Plan; show the batch in Learning, the join link on the portal, the auto-marked attendance and the draft results.
- Final summary lists files touched per step, every new field, every patch, and any deviation from this prompt.
```
