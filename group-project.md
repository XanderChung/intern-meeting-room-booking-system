# Group Project Assessment — Meeting Room Booking App

> **Team:** Alex, Angad, Dyllon
> **Stack:** Your choice, one for the whole team. Recommended: **Python + SQLite + Flask/FastAPI**, with HTML pages rendered by the server using templates (e.g. Jinja).
> **Before you start:** have your language, editor and Git set up and working, and accept the repo invitation.

---

## 1. The Brief

Our corporate office books meeting rooms through a shared spreadsheet. Double bookings and overfilled rooms happen every week. Build a small **working web app** that employees can use in a browser to:
- manage meeting rooms and employees,
- book and cancel rooms **without double bookings**,
- see which rooms are used the most.

The app has two layers:
- **API:** JSON endpoints, the rules, and the database.
- **Frontend:** simple HTML pages that employees click through.

**How you work together counts as much as what you build.** A smaller, working, well-reviewed app beats a big, broken one.

---

## 2. Data Model

```
rooms(id, name, floor, capacity)
employees(id, name, email, department)
bookings(id, room_id, employee_id, title, start_at, end_at, attendees, cancelled_at)
```

All dates and times use the office's local time, stored in ISO 8601 format (`2026-10-01T10:00`).

---

## 3. Requirements

### Architecture rule
Each business rule (no overlap, capacity, office hours, unique email…) must be written **in one place**, as a function or service. The API endpoints and the HTML pages both call those functions. Never copy a rule into a page.

### Must have

**Rooms**

| API | Page |
|---|---|
| `GET /api/rooms`: list all rooms, each with an **available now** flag | **Rooms page** (`/rooms`): a table of name, floor, capacity and *Available now* (yes/no) |
| `GET /api/rooms/{id}?date=YYYY-MM-DD`: one room with its bookings on that date (defaults to today) | **Room detail page** (`/rooms/{id}`): the room's bookings for a chosen date, in time order |
| `POST /api/rooms`: add a room. `name` (unique), `floor` and `capacity ≥ 1` are required | An "Add room" form on the Rooms page. Invalid input shows an error message |

**Employees**

| API | Page |
|---|---|
| `GET /api/employees`: list all employees | **Employees page** (`/employees`): a table of employees plus an "Add employee" form |
| `GET /api/employees/{id}`: one employee with their **upcoming** bookings | **Employee detail page** (`/employees/{id}`): upcoming bookings with room, date and time |
| `POST /api/employees`: `name`, `email` and `department` are required; the email must be **unique** and valid (contain `@`) | A duplicate or invalid email shows a clear error on the page |

**Bookings & Reports**

| API | Page |
|---|---|
| `POST /api/bookings`: book a room (rules below) | **Bookings page** (`/bookings`): a booking form with **dropdowns** of rooms and employees, plus title, date, start time, end time and attendees |
| `POST /api/bookings/{id}/cancel`: cancel a booking. Cancelling twice, or cancelling a booking that has already started, is rejected | A list of bookings for a chosen date, with a **Cancel** button on each upcoming booking |
| `GET /api/bookings?date=YYYY-MM-DD&room_id=`: list bookings that are not cancelled, filtered by date and optionally by room | Rule violations (overlap, too many attendees, outside office hours…) show a clear error on the page |
| `GET /api/reports/top-rooms?n=5`: the rooms with the most bookings that were not cancelled; ties are sorted by room name A→Z | A "Top 5 rooms" table on the Bookings page |

**Booking rules**
1. **No overlap:** a room cannot have two bookings at the same time that are not cancelled. Back-to-back bookings **are** allowed: 10:00–11:00 and 11:00–12:00 do not overlap.
2. **Capacity:** `attendees` must be between 1 and the room's capacity.
3. **Valid time range:** `start_at` must be before `end_at`, and a booking may last **at most 4 hours**.
4. **Office hours:** a booking must start and end on the same day, between **08:00 and 18:00**.
5. **No past bookings:** `start_at` must be in the future.

**Shared (build together first)**
- A base layout with a navigation bar linking **Rooms · Employees · Bookings**, a single CSS file, and one shared way to display success and error messages.
- `/` redirects to `/rooms`.

**Quality (everyone)**
- API errors use one shared format, e.g. `{"error": "message"}`, with correct status codes: `400` invalid input, `404` not found, `409` rule violation (e.g. overlap).
- **At least one automated test for every rule**, including edge cases such as back-to-back bookings and exactly 18:00. Test the rule functions or the API; automated page tests are not required.
- Every PR that changes a page includes **manual test steps** in its description (what you clicked and what you saw).
- A README with one command to run the app and one command to run the tests.
- A seed script with sample rooms and employees.

### Acceptance flow
From a fresh clone, following only the README, all of the following must work in the browser:
1. Add a room with capacity 6, then add an employee.
2. Book the room tomorrow from 10:00 to 11:00.
   - Try 10:30–11:30 in the same room: an overlap error is shown.
   - Book 11:00–12:00: it succeeds (back-to-back).
3. Try booking with 8 attendees: a capacity error is shown.
4. Try 17:00–19:00, and try an end time before the start time: an error is shown for each.
5. Cancel the 10:00 booking: the slot can be booked again, and cancelling it a second time shows an error.
6. The room detail page and the employee detail page both show the correct bookings.
7. The Top 5 rooms table shows the right order, with ties sorted A→Z.

### Nice to have (only after all *Must have* items are merged)
- Find free rooms: search by date, time range and minimum capacity.
- Edit a booking (with all the rules still applied).
- A weekly calendar view for a room.
- Recurring bookings (e.g. every Monday 09:00–10:00 for 4 weeks). Any clash with an existing booking must be reported.
- JavaScript enhancements (e.g. cancelling a booking without reloading the page).

---

## 4. Team Rules

1. **Contract first.** Before anyone writes feature code, merge the following. All three of you must approve it.
   - `docs/api.md`: every endpoint (request, response, errors) and the schema,
   - the shared layout, navigation and error display.
2. **Ownership.** Split the three areas (Rooms, Employees, Bookings & Reports) among yourselves, one area per person, and record who owns what in the README. Each person owns their area end-to-end: rules, API, page(s) and tests. The Bookings page depends on Rooms and Employees data, so keep to the contract.
3. **Git workflow.**
   - No direct commits to `main`. Use one branch per feature: `feature/<area>-<short-name>`.
   - Every PR needs **1 approving review from a teammate**. Don't merge your own PR without that approval.
   - Keep PRs small (about 200 changed lines or fewer) and give each a description: *what, why, how tested*.
   - Review your teammates' PRs promptly, so nobody is left blocked.
   - Commit messages must describe the change (e.g. `Reject overlapping bookings for the same room`, not `update`).
4. **Check-ins.** Post a short written check-in in the team channel when you start a task, finish it, or get blocked: *done / next / blocked*.
5. **AI and internet use are allowed.** However:
   - say in the PR description when AI generated a significant part of the code,
   - **you must be able to explain and change any code in your area without help.**

---

## 5. Deliverables

1. **Repository** with the full commit and PR history, with all work merged to `main`.
2. **README:** how to run the app and the tests, stack choice, who owns which area, known limitations.
3. **`docs/api.md`:** the final API contract.
4. **Individual reflection** (5–10 sentences, sent privately to the reviewers): what you built, one thing you learned, one thing you would do differently, how the team worked.

A separate follow-up discussion will be held with each of you after submission.

---

## 6. Scoring (100 pts)

### Team score (40 pts), shared by all members
| Area | Pts |
|---|---|
| API *Must have* features working | 10 |
| Acceptance flow works end-to-end in the browser | 12 |
| Tests cover every rule, including edge cases | 8 |
| Consistency: one error format, shared layout, rules kept in one place | 5 |
| README and API contract | 5 |

### Individual score (60 pts)
| Area | Pts |
|---|---|
| Own area (API + page): correctness, edge cases, readability, usable page | 20 |
| Git and PR quality: small PRs, clear descriptions and commit messages, manual test steps | 10 |
| Code reviews given: specific and useful | 10 |
| Follow-up discussion: explaining and changing your own code | 15 |
| Teamwork: check-ins, helping others, reflection | 5 |

---

## 7. Definition of Done

A feature is **done** when it:
- is merged to `main` through a reviewed PR,
- follows the rules in section 3, with each rule written once and used by both the API and the page,
- has at least one passing test for each rule,
- works in the browser, with its error messages visible to the user,
- is listed in `docs/api.md`,
- works from a fresh clone using the README.
