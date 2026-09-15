# Frappe Education × Frappe Learning — v17 Integration Design

Status: proposal for discussion. Target: `version-17` of both apps (versioning aligned with the Frappe Framework). Breaking changes are accepted in this release.

## 1. The one-sentence model

**Education is the institution's system of record (who studies what, when, where, and how it was graded). Learning (LMS) is the system of record for learning content and online delivery (courses, lessons, quizzes, assignments, progress, live classes, certificates).** Each app stays installable on its own. Education knows about LMS optionally; LMS never imports Education.

## 2. What exists today (facts that shaped the design)

| Concern | Education (17.0.0-dev) | Learning (2.45.2 → 17) |
|---|---|---|
| Identity | `Student` (own doctype) with `user` link; `Instructor` linked to `Employee`, no `user` field; `Guardian` with `user` | Everything keyed on `User` directly; roles `LMS Student`, `Course Creator`, `Moderator`, `Batch Evaluator` |
| Catalog | `Program` → `Program Course` → `Course` (subject + grading scale + assessment criteria) | `LMS Course` → `Course Chapter` → `Course Lesson`; `LMS Program` = ordered list of LMS courses |
| Cohort | `Student Group` (batch/course/activity based; students + instructors; academic year/term) | `LMS Batch` (dates, courses, instructors, timetable, live classes, assessments, `medium` Online/Offline) |
| Enrollment | `Program Enrollment` (submittable) → auto `Course Enrollment` | `LMS Enrollment` (course), `LMS Batch Enrollment` (cohort) |
| Timetable | `Course Schedule` (room, instructor, date, time) per Student Group | `LMS Batch Timetable` rows with generic `reference_doctype/reference_docname`, plus `LMS Live Class` (Zoom / Google Meet) |
| Attendance | `Student Attendance` (per schedule or per group) | None. `LMS Live Class Participant` records join/leave/duration |
| Assessment | `Assessment Plan` → `Assessment Result` with grading scale and criteria | `LMS Quiz Submission`, `LMS Assignment Submission`, `LMS Certificate Evaluation` |
| Money | Fees via ERPNext Sales Invoice / Sales Order | `LMS Payment` via the Payments app for public paid courses/batches |
| Dependencies | `erpnext` | `frappe/payments` |
| Legacy | Dead LMS residue since v14: `Article`, `Topic`, `Topic Content`, `Course Topic`, `Quiz`, `Question`, `Options`, `Quiz Question`, `Quiz Activity`, `Quiz Result`, `Course Activity`, `Course.topics`, "LMS Utils" in `education/utils.py`, references to a `Video` doctype that no longer exists | `LMS Batch.medium` is stored and emailed but never affects behaviour |

Education deprecated its own LMS in December 2022 and pointed users at Frappe LMS. This proposal finishes that move.

## 3. Decisions

### D1. Dependency direction and where the bridge lives
- LMS stays standalone (no ERPNext, no Education). LMS ships a **stable integration contract**: fields, server-side flags, a Python module, and generic reference links. Nothing in LMS references an Education doctype.
- Education owns the bridge. Code lives in `education/education/lms_integration/` and is active only when `"lms" in frappe.get_installed_apps()`. Education subscribes to LMS doc events via `doc_events` in its hooks (Frappe ignores hooks for doctypes that do not exist, so this is safe without LMS).
- Link fields from Education doctypes to LMS doctypes are created as **Custom Fields at runtime** (`after_install` and `after_app_install` hooks), never in the doctype JSON. A Link whose target doctype is missing fails `bench migrate`.
- Install order must not matter: Education installed first then LMS, or the reverse, both end in the same state.

### D2. Identity = `User`
- Student ↔ User via `Student.user` (already exists). The bridge requires a `User`; if `user_creation_skip` is on and no user exists, the bridge creates one on demand using the existing `Student.validate_user` path.
- New users already receive `LMS Student` from an LMS hook. Education additionally grants it explicitly when linking, so the order of installation does not matter.
- `Instructor` gets a native `user` Link field (fetched from `Employee.user_id`, editable). Instructors with a user receive `Course Creator` + `Batch Evaluator`. `Education Manager` receives `Moderator`. Guardians get nothing in v17 (see Open Questions).

### D3. Catalog: `Course` → `LMS Course` (optional, 1:1)
- Custom field `Course.lms_course` (Link → LMS Course). Presence of the link is what "has online content" means. No `delivery_mode` at catalog level: the same subject can be taught in a classroom one year and online the next.
- `Program` does not map to `LMS Program`. `LMS Program` stays an LMS-only concept for the public marketplace.
- Education's residual content doctypes are removed. A one-time patch exports them to JSON under `sites/<site>/private/files/education_legacy_lms/` and, if LMS is installed, offers to migrate them (one unpublished `LMS Course` per Education `Course` with topics; topics → chapters, articles → lessons, quizzes/questions → `LMS Quiz`/`LMS Question`).

### D4. Delivery mode taxonomy (the online/offline distinction)
Three levels. The distinction lives on the cohort and the session, not on the subject.

| Level | Doctype and field | Values | Effect |
|---|---|---|---|
| Cohort | `Student Group.delivery_mode` (native Select) | `Classroom` (default), `Online`, `Blended` | `Classroom`: no LMS objects are created; Education behaves exactly as today. `Online` / `Blended`: a managed `LMS Batch` is created and kept in sync. |
| Session | `Course Schedule.session_type` (native Select) | `In Person` (default), `Online` | `In Person`: room mandatory, attendance marked in Education as today. `Online`: room optional, an `LMS Live Class` is created through the batch's conferencing provider, join link shown in both portals, attendance can be auto-marked from participation. |
| LMS cohort | `LMS Batch.delivery_mode` (renamed from `medium`) | `Online`, `In Person`, `Hybrid` | Mirrors the group's mode for managed batches (`Online`→`Online`, `Blended`→`Hybrid`, and an `In Person` value exists for LMS-only classroom batches). Patch: `Offline` → `In Person`. |

Self-paced access (no cohort at all) is simply an `LMS Enrollment` without a batch, created from `Program Enrollment` for courses that have `lms_course`. It is a fourth mode by absence, not a value.

### D5. Cohort: `Student Group` ↔ `LMS Batch` (1:1, managed)
- Education creates the batch when `delivery_mode` is not `Classroom` and stores `Student Group.lms_batch`. Education is authoritative for: title, description, start/end date (from academic term or year, overridable on the group), delivery mode, instructors, courses (the LMS courses linked to the group's course, or to all program courses for batch-based groups), members, timetable.
- LMS marks such a batch as **managed**: `LMS Batch.managed_by_doctype` (Link → DocType) + `managed_by_docname` (Dynamic Link). LMS locks members, courses, dates, instructors and timetable in its UI and in `validate`, unless the write carries the server-side flag `doc.flags.managed_sync = True`. Announcements, discussions, assessments, feedback, certificates stay LMS-native and editable.
- `Student Group Student` rows drive `LMS Batch Enrollment` (add/remove; `active = 0` removes). LMS's existing behaviour then creates the per-course `LMS Enrollment` rows. `LMS Source` "Education" is created by Education and set on every bridge-created enrollment.
- Managed batches are never `paid_batch`, have `seat_count = 0`, `allow_self_enrollment = 0`, `published = 0` (institution-only, not on the marketplace) and `timezone` = system time zone.

### D6. Enrollment: `Program Enrollment` → self-paced `LMS Enrollment`
- On submit, for each `Program Enrollment Course` whose `Course.lms_course` is set, the bridge creates an `LMS Enrollment` (member = student user, source = Education) with `flags.skip_eligibility_checks = True`. On cancel, the enrollment is removed only if no managed batch still includes the student for that course.
- `Course Enrollment` gets custom fields `lms_enrollment` (Link) and `lms_progress` (Percent), the latter refreshed from `LMS Enrollment.progress` on change and nightly.
- Flags, not fields, carry the bypass. A student can set fields through the REST API; they cannot set `doc.flags`.

### D7. Scheduling and live classes
- `Course Schedule` (any session type) → one `LMS Batch Timetable` row on the managed batch with `reference_doctype = "Course Schedule"`. LMS renders it generically, so `LMS Batch Timetable` gains denormalised `title`, `location`, `instructor_name` and `url` fields. LMS never looks up Course Schedule columns.
- `Course Schedule` with `session_type = Online` → `LMS Live Class` via `lms.lms.integration.create_live_class(...)`. `Course Schedule.lms_live_class` (custom Link) and a fetched `join_url`. Host = `Instructor.user` (validation error if missing). Updating date/time updates the live class; deleting cancels it. `LMS Live Class` gains `reference_doctype/reference_docname` so LMS can show "Scheduled from Course Schedule X".
- For managed batches the LMS UI hides "New live class" and timetable editing. One place schedules; the other displays.
- Conferencing provider and account are chosen on the `Student Group` (custom Links to `LMS Zoom Settings` / `LMS Google Meet Settings`) with defaults in `Education Settings`.

### D8. Attendance
- `In Person` sessions: unchanged, `Student Attendance` in Education.
- `Online` sessions: after the session ends, a scheduled job reads `LMS Live Class Participant` rows for the linked live class and marks `Student Attendance` for every student in the group: `Present` if total duration ≥ `Education Settings.live_class_attendance_threshold` (default 75 % of the scheduled duration), else `Absent`. Records are created as drafts so a teacher can correct and submit, unless `auto_submit_live_class_attendance` is enabled. Existing `attendance_freeze_date` and holiday validations apply.
- Self-paced enrollments have no attendance, only progress.

### D9. Assessment and grades
- `Assessment Plan.assessment_source` (native Select): `Manual` (default), `LMS Quiz`, `LMS Assignment`. Custom Links `lms_quiz`, `lms_assignment`. Button **Fetch results from LMS** and an automatic hook on `LMS Quiz Submission` / `LMS Assignment Submission` insert.
- Score mapping: LMS percentage × `maximum_assessment_score` → one `Assessment Result Detail` row per plan criterion in proportion to the criterion's `maximum_score`. Attempt policy on the plan: `Best attempt` (default) or `Latest attempt`. Assignments: `Pass` = full marks, `Fail` = 0, `Not Graded` = skipped.
- Results are created as drafts; teachers submit. Grades reach the Education student portal through the normal `Assessment Result` path, so no portal work is needed.
- `LMS Certificate` is left as an LMS artifact. Education does not issue or mirror certificates in v17.

### D10. Money
- No coupling. Institution students never pay inside LMS; managed batches and bridge enrollments bypass `paid_course` / `paid_batch` checks via flags. Fees remain in Education/ERPNext. A school can still sell public courses on the same LMS marketplace; those are ordinary LMS enrollments with `LMS Payment`.

### D11. Portals
- v17 keeps both frontends. Cross-links only:
  - LMS sidebar gets `LMS Sidebar Item` rows (type `External`) for Timetable, Attendance, Fees, Grades → `/student-portal/...`, created by Education when it detects LMS. Rows are hidden for users who are not linked to a `Student`.
  - Education student portal gets a **Learning** entry → `/lms`, and online sessions on the Schedule page show the join link.
  - Desk: `Student Group` shows "Open in Learning"; `Course` shows "Create Learning course" (creates an unpublished `LMS Course` with the same title and the group's instructors).
- Privacy: `LMS Settings.hide_member_profiles` (new) disables public `/user/:username` pages and the certified-participants page for non-privileged users. Education turns it on by default when it detects LMS, because institution students may be minors.

### D12. Versioning, branches, release
- Both apps get `version-17` branches and `17.0.0` versions. LMS jumps from `2.45.x` to `17.0.0`; patches move from `lms/patches/v2_0` to `lms/patches/v17_0`.
- Compatibility statement: Education 17 ↔ Learning 17 only. Neither app checks the other's version at runtime; the contract is the module `lms.lms.integration` and the fields listed in §4.

## 4. The contract LMS exposes (owned by the LMS team, frozen before Education starts Phase 2)

Fields (all native to LMS JSON):
- `LMS Batch`: `delivery_mode` (Select: Online / In Person / Hybrid, replaces `medium`), `managed_by_doctype` (Link → DocType), `managed_by_docname` (Dynamic Link), read-only computed `is_managed`.
- `LMS Batch Timetable`: `title` (Data), `location` (Data), `instructor_name` (Data), `url` (Data).
- `LMS Live Class`: `reference_doctype` (Link → DocType), `reference_docname` (Dynamic Link).
- `LMS Enrollment`: `source` (Link → LMS Source).
- `LMS Settings`: `hide_member_profiles` (Check).

Server-side flags honoured in `validate`/`before_insert` (never settable over REST):
- `doc.flags.managed_sync` on `LMS Batch`: allows changing locked fields of a managed batch.
- `doc.flags.skip_eligibility_checks` on `LMS Enrollment` and `LMS Batch Enrollment`: skips payment, self-enrollment, `disable_self_learning`, unpublished and seat checks. Duplicate checks still apply.

Python module `lms/lms/integration.py` (importable, not whitelisted unless stated):
```
create_managed_batch(managed_by_doctype, managed_by_docname, title, start_date, end_date,
                     delivery_mode, instructors, courses, description=None, timezone=None,
                     conferencing_provider=None, zoom_account=None, google_meet_account=None) -> str
update_managed_batch(batch, **fields) -> None
sync_batch_members(batch, members: list[str], source: str) -> dict(added=[], removed=[])
enroll(member, course, source, batch=None) -> str            # LMS Enrollment name, idempotent
unenroll(member, course) -> None
upsert_timetable_row(batch, reference_doctype, reference_docname, date, start_time, end_time,
                     title, location=None, instructor_name=None, url=None) -> str
remove_timetable_row(batch, reference_doctype, reference_docname) -> None
create_live_class(batch, title, date, time, duration, host, reference_doctype=None,
                  reference_docname=None, description=None) -> dict(name, join_url, start_url)
update_live_class(name, **fields) -> None
cancel_live_class(name) -> None
get_progress(member, course) -> float
get_quiz_results(quiz, members=None, attempt="best") -> dict[member] = dict(percentage, score, score_out_of, submission)
get_assignment_results(assignment, members=None) -> dict[member] = dict(status, submission)
get_live_class_participation(live_class) -> dict[member] = dict(duration_seconds, joined_at, left_at)
grant_roles(user, roles: list[str]) -> None
```
Whitelisted read endpoints for portals: `get_progress`, `get_quiz_results` (own results only for non-privileged users).

Doc events Education subscribes to (LMS side needs no change; listed so LMS does not rename them):
`LMS Quiz Submission.after_insert`, `LMS Assignment Submission.on_update`, `LMS Enrollment.on_update`, `LMS Live Class Participant.after_insert`.

## 5. Sync rules and conflict policy

| Data | Authoritative app | Direction | Trigger |
|---|---|---|---|
| Batch identity, dates, mode, instructors, courses | Education | Education → LMS | `Student Group` on_update |
| Batch members | Education | Education → LMS | `Student Group` on_update (rows diffed) |
| Timetable rows, live classes | Education | Education → LMS | `Course Schedule` after_insert / on_update / on_trash, and `Course Scheduling Tool` |
| Self-paced course access | Education | Education → LMS | `Program Enrollment` on_submit / on_cancel |
| Content, progress, quiz/assignment results, participation | LMS | LMS → Education | LMS doc events + nightly reconciliation job in Education |
| Attendance for online sessions | Education (derived from LMS participation) | LMS → Education | Hourly job after session end |

Reconciliation job (`education.lms_integration.tasks.reconcile`, nightly): re-syncs every group with a batch, repairs missing enrollments and progress. All sync writes are idempotent; a failure in one group is logged (`frappe.log_error`) and does not abort the rest.

## 6. Breaking changes

Learning (LMS) 17:
- Version number jumps to 17.0.0.
- `LMS Batch.medium` → `delivery_mode`; value `Offline` → `In Person`. Email templates and the batch form use the new field.
- Managed batches lock member/timetable/course/date/instructor edits in the UI and API.
- `LMS Enrollment` and `LMS Batch Enrollment` honour new server flags (no behaviour change for existing callers).
- New `hide_member_profiles` setting can hide `/user/:username` and `/certified-participants` when enabled.

Education 17:
- Removed doctypes: `Article`, `Topic`, `Topic Content`, `Course Topic`, `Quiz`, `Question`, `Options`, `Quiz Question`, `Quiz Activity`, `Quiz Result`, `Course Activity`, and `Course.topics`. Removed whitelisted methods: `education.education.utils.enroll_in_program`, `add_activity`, `evaluate_quiz`, `get_quiz`, plus the "LMS Utils" helpers. Data is exported before deletion.
- `Instructor.user` added; required for instructors who host online sessions.
- `Student Group.delivery_mode`, `Course Schedule.session_type`, `Assessment Plan.assessment_source` added with safe defaults (`Classroom`, `In Person`, `Manual`).
- `Course Schedule.room` becomes optional when `session_type = Online`.

## 7. Phases

| Phase | Owner | Scope | Exit criterion |
|---|---|---|---|
| 0 | Both | `version-17` branches, version bumps, Education dead-code removal + export patch | CI green on both, install in both orders |
| 1 | LMS | Contract in §4: fields, flags, `integration.py`, managed-batch lock, delivery mode rename, profile privacy, UI for managed/mode badges | Contract frozen, unit + e2e tests |
| 2 | Education | Identity, `Course.lms_course`, `Student Group ↔ LMS Batch`, membership sync, `Program Enrollment` → self-paced enrollment, roles, sidebar links | A blended group with 30 students appears in LMS with correct members and courses |
| 3 | Education | `Course Schedule` → timetable rows + live classes; attendance from participation | Online session join link visible in both portals; attendance auto-marked |
| 4 | Education | `Assessment Plan` sources from LMS quiz/assignment | Quiz results appear as draft Assessment Results and on the Grades page |
| 5 | Both | Legacy content migration (optional), docs, Frappe Cloud compatibility notes, demo data | Docs published; upgrade guide |

## 8. Open questions (see 02-discussion-notes.md for the meeting version)

1. Guardians: read-only view of a child's LMS progress in v17 or v18?
2. Should `Program` carry a default `delivery_mode` for new groups?
3. Attendance threshold and auto-submit defaults.
4. Assessment attempt policy default (best vs latest).
5. Whether Education should create the LMS course automatically for every `Course`, or only on demand.
6. Naming: `In Person` vs `Offline` in the LMS UI.
