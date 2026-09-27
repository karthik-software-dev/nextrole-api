---
trigger: always_on
---

# Job Agent Coding Rules

## 1. Analyze First

* Never modify code immediately when an issue is reported or a change is requested.
* First inspect the existing code, file layout, execution flow, and dependencies.
* For UI changes, inspect both the existing frontend and the corresponding backend/API/data flow.
* Identify the exact root cause and affected files.
* Explain the current implementation and proposed solution.
* Clearly identify whether the change is frontend-only, backend-only, frontend + backend/API, or database-related.
* **Wait for explicit approval before modifying any code.**

## 2. UI Preservation & Cosmetic Adjustments

* **The existing UI is the source of truth.**
* When an image, screenshot, mockup, or reference design is provided, treat it as a **visual reference for the requested changes**, NOT as instructions to recreate or replace the existing UI.
* **Never regenerate an entire page or component just because a reference image was provided.**
* Do not replace existing layouts, templates, components, or styling systems with a newly generated design.
* Identify the **specific visual differences requested** and make only those changes.
* UI changes should be minimal, incremental, and cosmetic unless a functional change is explicitly requested.
* Preserve the existing page structure, component hierarchy, DOM structure where possible, routes, functionality, CSS conventions, design system, responsive behavior, API integration, and state management.
* Reuse existing components and styles wherever possible.
* Do not introduce a new design system just because the reference image looks different.
* Do not introduce new CSS frameworks, component libraries, or animation libraries unless explicitly requested.

## 3. UI Enhancement vs UI Replacement

* UI enhancement means **incremental improvement of the existing UI**.
* UI replacement means rebuilding the page to look like the reference image.
* **Replacement is prohibited unless explicitly requested.**
* If a screenshot contains a different layout, inspect the existing implementation first and reproduce only the requested visual/functional delta within the existing structure.
* Never delete an existing dashboard/page and recreate it from the screenshot.

## 4. Backend & API Alignment

* Every dynamic UI element must be backed by real application data.
* **Never invent, hardcode, or fake production data merely to make the UI look correct.**
* Before adding a new UI metric, chart, counter, status, filter, or action:

  1. Check whether the required data already exists.
  2. Check whether an existing API already provides it.
  3. Check whether the frontend already has the required data.
  4. Only if the data is genuinely unavailable, determine the minimum backend/API change required.
* Reuse existing endpoints whenever possible.
* Do not create duplicate APIs for data that an existing endpoint already provides.
* If backend support is missing, implement it using the existing backend architecture, route conventions, schemas, services, and database patterns.
* Do not introduce a new architectural pattern just to support one UI requirement.

## 5. API Contract Protection

* **Any API contract change must be explicitly identified before implementation.**
* This includes endpoint changes, request/query parameters, request bodies, response keys, response structure, field names, data types, pagination, error structures, and status codes.
* If a UI enhancement requires an API contract change, explain:

  * Current API contract
  * Required change
  * Frontend impact
  * Impact on existing consumers
* **Wait for approval before implementing an API contract change.**
* Prefer backward-compatible solutions whenever possible.

## 6. Keep Changes Minimal

* Change only what is required.
* Do not modify unrelated code.
* Do not perform unsolicited refactoring, cleanup, or modernization.
* Do not rename unrelated variables, functions, classes, routes, or components.
* Do not reorganize files unnecessarily.
* Do not add unnecessary helpers, abstractions, dependencies, or services.
* **Prefer the smallest safe change that satisfies the requirement.**

## 7. Follow Existing Code Style

* Follow the existing project structure.
* Follow existing naming conventions, indentation, formatting, and coding patterns.
* Reuse existing utilities and components where appropriate.
* Do not introduce a different coding style without a clear reason.
* Do not rename existing variables, functions, classes, routes, or components unless required.

## 8. Verify Changes

* After implementation, verify the modified frontend.
* Verify the corresponding backend/API.
* Verify frontend ↔ backend integration.
* Check browser console and API/network errors.
* Verify existing functionality around the changed area.
* Check responsive behavior when UI changes affect layout.
* Run relevant tests.
* Run `git diff`.
* Confirm only intended files were changed.
* Confirm no unrelated behavior was modified.
* **Do not consider the task complete without functional verification.**

## 9. Git Workflow & Safety

```text
dev2 → dev → main
```

* Develop locally on `dev2`.
* Never develop directly on `dev` or `main`.
* Always check `git status` and the current branch before Git operations.
* Never include unrelated changes in a commit.
* Never push unless explicitly requested.

When instructed to **"push the code"**:

1. Review changes.
2. Review `git diff`.
3. Review staged files using `git diff --staged`.
4. Commit only related changes.
5. Merge `dev2 → dev`.
6. Verify/test `dev`.
7. Merge `dev → main`.
8. Verify `dev` and `main` point to the same tested commit.
9. Push the tested code.

Never force-push, reset/discard changes, delete branches, destructively rebase, or overwrite unrelated work without explicit approval.

If a merge conflict occurs:

**Stop. Analyze the conflict. Do not automatically resolve it.**

## 10. Secrets & Environment Safety

* Never hardcode API keys, passwords, tokens, database credentials, or private endpoints.
* Use environment variables / `.env`.
* Ensure `.env` and local secret files remain in `.gitignore`.
* Never expose secrets in logs, terminal output, API responses, frontend code, or commits.

## 11. Practical Engineering Constraints

* Keep the project simple and practical.
* Prefer reliable, lightweight, native solutions.
* Avoid unnecessary third-party dependencies.
* Do not introduce AI, AWS, cloud services, microservices, queues, workers, or other infrastructure unless explicitly requested.
* Preserve existing working functionality.
* Do not sacrifice backend stability for UI improvements.
* Do not sacrifice existing UI functionality for visual changes.

## 12. Mandatory UI → Backend/Data Rule

**UI is not just visual.**

Whenever a requested UI contains metrics, charts, counters, statuses, filters, or actions, trace the data flow:

```text
Database
   ↓
Backend / Service
   ↓
API
   ↓
Frontend State
   ↓
UI Component
```

* If the data already exists → reuse it.
* If the API already provides it → reuse the API.
* If the backend has the data but the API does not expose it → propose the minimum API change.
* If the database does not contain the required information → identify the gap before creating anything.
* **Never create fake frontend values simply because they appear in a reference image.**
* If backend/API support is missing for a requested UI feature, identify the gap and propose the minimum required implementation without deviating from the requested UI.

## 13. Mandatory Approval Gate

For every non-trivial change:

```text
ANALYZE
   ↓
UNDERSTAND
   ↓
IDENTIFY IMPACT
   ↓
PROPOSE SOLUTION
   ↓
SHOW AFFECTED FILES / API IMPACT
   ↓
WAIT FOR APPROVAL
   ↓
IMPLEMENT
   ↓
VERIFY
```

**Do not skip the approval step.**

## 14. Critical Antigravity Rule

> **REFERENCE IMAGES ARE NOT REPLACEMENT INSTRUCTIONS.**
>
> When I provide a UI screenshot or image, preserve my existing application and make only the requested minimal changes needed to align with the reference. Do not rebuild, regenerate, restructure, or replace the existing UI unless I explicitly ask you to do so.

> **A UI requirement must be validated against the backend/API/data flow before implementation. If the required data or API support does not exist, identify the gap and propose the minimum backend/API change. Do not invent or hardcode data.** 
