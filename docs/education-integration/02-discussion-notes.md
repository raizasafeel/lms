# Meeting notes: Education × Learning integration (v17)

Audience: the Frappe Education maintainers. Bring `01-design.md` for the details. This page is the agenda, the asks, and the decisions we need from the room.

## Why now

- Education deprecated its built-in LMS in v14 (Dec 2022) and pointed users at Frappe Learning. The residue (`Article`, `Topic`, `Quiz`, `Question`, `Course Activity`, `Quiz Activity`, `Course.topics`, "LMS Utils") is still shipped and still referenced by `Course`, `Course Enrollment` and `Student`. It references a `Video` doctype that no longer exists.
- Both apps are moving to framework-aligned versioning (Education is already `17.0.0-dev`; Learning will jump from `2.45.x`). For Learning this is effectively "v3": roles, batch model and versioning all change at once. A major on both sides is the one moment breaking changes are cheap.
- Customers ask for the same three things: one login for students, timetables and grades that include online work, and attendance for online sessions.

## The proposal in five lines

1. Education = institution record (students, programs, groups, schedules, rooms, attendance, fees, grades). Learning = content and online delivery (courses, lessons, quizzes, assignments, progress, live classes, certificates).
2. Learning becomes a required app of Education and installs with it. Education owns the bridge; Learning ships a frozen contract (fields, server flags, a Python module, role names) and never references Education. Learning stays usable on its own.
2a. One role vocabulary: `Student`, `Instructor`, `Evaluator`, `Learning Manager`. Learning renames its roles to match Education's existing `Student` and `Instructor`.
3. `Student Group` ↔ `LMS Batch` is the cohort mapping. Groups with `delivery_mode` = Online or Blended get a managed batch that Learning locks for editing. Classroom groups are untouched.
4. `Course Schedule` rows become batch timetable rows; online sessions become Live Classes; attendance for online sessions is derived from participation.
5. `Assessment Plan` can source scores from an LMS quiz or assignment, so online results land on the existing Grades page.
6. Learning gets optional ERPNext invoicing for its own payments (public courses and batches). It works with ERPNext alone; when Education is present, two hooks route the invoice to the student's existing Customer and stamp the `student` field, so purchases appear on the Fees page.

## What we are asking Education to own

| Item | Effort (rough) |
|---|---|
| `required_apps` change, `before_migrate` guard for existing sites, CI installs Learning | Small |
| Remove residual LMS doctypes and utils, with a JSON export patch and optional migration into Learning | Small |
| `Instructor.user` field; `Instructor.desk_access = 1` after install and in a patch; `Education Manager` → `Learning Manager` | Small |
| `Student Group.delivery_mode`, batch creation and member sync through `lms.lms.integration` | Medium |
| `Course Schedule.session_type`, timetable + live-class sync, room optional for online sessions | Medium |
| Attendance job from live-class participation | Small |
| `Assessment Plan.assessment_source` + fetch/auto hooks | Medium |
| Student portal: Learning link, join links on Schedule | Small |
| Implement `lms_get_customer` and `lms_before_sales_invoice_insert` hooks (Student → Customer, `student` on Sales Invoice) | Small |
| Nightly reconciliation, tests | Medium |

What the Learning side owns: the contract (§4 of the design), the role rename with merge patches, the `medium` → `delivery_mode` rename, managed-batch locking and UI, profile privacy setting, docs.

## Decisions we need from the room

1. **Hard dependency.** Education 17 requires Learning 17 (`required_apps`). Payments comes along transitively and stays unused unless a school sells public courses. Existing sites install Learning before migrating; a `before_migrate` guard stops them with instructions otherwise. Confirm this is acceptable for schools with no e-learning: they get a Learning app they do not open, and `Classroom` groups create nothing in it.
1a. **Role names.** Learning renames `LMS Student` → `Student`, `Course Creator` → `Instructor`, `Batch Evaluator` → `Evaluator`, `Moderator` → `Learning Manager`. `Student` and `Instructor` merge with Education's existing roles. Two guard rails: Learning stops force-setting `desk_access` on existing roles (teachers keep the desk), and Learning stops adding the student role to every new user (otherwise every new user on an Education site inherits the `Student` role's Sales Invoice permissions). Confirm both, and whether `Learning Manager` is worth its rename cost versus keeping `Moderator`.
1b. **Bridge ownership.** Education owns the bridge code and Learning owns the contract. A third "education_lms" app is not needed now that the dependency is hard.
2. **Dead code removal.** Confirm no one is using `Article` / `Quiz` / `Question` / `Topic` content. Is an export-to-JSON patch sufficient, or do we build the migration into Learning courses in v17?
3. **Identity of minors.** Every bridged student needs a `User` with an email. What is the policy for students without their own email (guardian email, generated addresses)? Duplicate emails across siblings break `User`.
4. **Instructors.** Is every instructor an `Employee` with a `user_id`? If not, `Instructor.user` must be set by hand before online sessions can be hosted.
5. **Cohort mapping.** One `Student Group` = one batch. Batch-based groups (a whole class across subjects) produce a batch containing every online-enabled program course. Course-based groups produce a single-course batch. Is that the right grain, or should batch-based groups never be online?
6. **Delivery mode defaults.** `Classroom` for groups, `In Person` for sessions. Should `Program` carry a default that new groups inherit?
7. **Attendance policy.** Online: Present at ≥ 75 % of scheduled duration. Asynchronous: "any LMS activity on the day" by default, or "completed the lessons scheduled for the day". Records created as drafts for the teacher to submit. Should auto-submit be on by default? Does `attendance_freeze_date` apply to auto-marked rows? Is an asynchronous session even something schools want to record as attendance, or should it stay progress-only?
8. **Grades.** Best attempt or latest attempt as the default? Results as drafts (teacher submits) or auto-submitted? Do we need a criterion-level mapping UI or is proportional distribution enough for v17?
9. **Money.** Confirm: institution students never pay in Learning; fees stay in ERPNext. A school may still sell public courses through Learning's marketplace with Learning payments; with invoicing enabled those land in ERPNext as Sales Invoice + Payment Entry against the student's Customer. Confirm the Fees page should list them alongside fee invoices, and whether Education wants a say in item, income account and taxes defaults (they live in LMS Settings).
10. **Portals.** Two frontends in v17 with cross-links (Learning sidebar → Timetable/Attendance/Fees/Grades; Education portal → Learning). Unification is a v18 topic. Any objection?
11. **Privacy.** Learning's public member profiles and certified-participants page will be hidden by default on sites with Education. Agreed?
12. **Conferencing.** Zoom and Google Meet via Learning's existing settings doctypes. Accounts chosen per Student Group with defaults in Education Settings. OK to have no Education-side conferencing config at all?
13. **Guardians.** Out of v17. Guardian read-only progress view targeted at v18. OK?
14. **Release.** `version-17` on both, Education 17 requires Learning 17, Frappe Cloud marketplace notes (required app is auto-added), upgrade guide leads with "install Learning first". Who owns the joint upgrade guide?

## How this maps to issue frappe/lms#1275

| Ask in the issue | Where it lands |
|---|---|
| Reuse Education groups in LMS without recreating them | Student Group ↔ managed batch (design D5), creatable from either side: the Education desk, or LMS's "Create from Student Group" through the `lms_batch_sources` hook |
| Attendance sync, in-person and digital | One `Student Attendance` record type for all three session types: In Person (marked by the teacher), Online (from live-class participation), Asynchronous (from LMS activity on the day); `session_type` on the record for reporting (D8) |
| Grades from LMS assessments into Education | Assessment Plan sourced from an LMS quiz or assignment (D9) |
| Link Education articles/videos to LMS lessons | One content store: Education's content doctypes are removed and migrated into LMS courses (D3) |
| Permissions maintained in both modules | Shared role vocabulary and the access rules in D14 |
| Native rather than manual API integration | Contract module plus hooks, no site-specific glue |

## Risks we want on the record

- **Two schedulers, one truth.** For managed batches Learning hides timetable and live-class creation. Teachers who used to create live classes in Learning must do it from `Course Schedule`. Needs a UI hint on the Learning side and a line in the upgrade guide.
- **Upgrade order.** Existing Education sites that run `bench update` to v17 without first installing Learning will stop at the `before_migrate` guard. The message must be explicit and the Frappe Cloud release notes must say it in the first line.
- **Shared roles.** `Instructor` is created by Learning first (with `desk_access = 0`) on fresh installs. Education must set it to 1 in `after_install`, and the v17 patch must do the same for existing sites, or teachers lose the desk on day one. Test this on a fresh install and on an upgraded site.
- **Timezones.** Education has no timezone concept; batches get the system timezone. Multi-campus, multi-timezone institutions are out of scope.
- **Performance.** Member sync diffs child rows on every `Student Group` save. Groups above a few hundred students should sync in a background job. The design calls for `frappe.enqueue` above 100 members.
- **Testing.** Education CI currently installs Education alone. It must add `bench get-app lms --branch version-17` (payments comes with it) before `install-app education`, and the role-merge patch needs a test that starts from an Education 16 style site with `Student` and `Instructor` already present.

## Proposed timeline

| Week | Milestone |
|---|---|
| 1 | Both `version-17` branches cut; Learning role-rename + contract PR opened; Education dead-code + `required_apps` PR opened |
| 2 | Contract merged and tagged as frozen; Education Phase 2 starts |
| 4 | Phase 2 demo: blended group visible in Learning with correct members |
| 6 | Phase 3 demo: online session with join link and auto attendance |
| 7 | Phase 4 demo: quiz results on the Grades page |
| 8 | Docs, upgrade guide, joint release candidate |

## Follow-ups after the meeting

- Confirm owners for each row in the effort table.
- Freeze the contract (design §4) in a PR the Education team reviews before merge.
- Agree the naming of `In Person` vs `Offline` in the Learning UI.
- Agree `Learning Manager` vs keeping `Moderator`.
