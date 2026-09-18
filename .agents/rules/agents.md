---
trigger: always_on
---

# Job Agent Coding Rules

## 1. Analyze First

* Never modify code immediately when I report an issue or request a change.
* First inspect the existing code and understand the flow.
* Identify the root cause and affected files.
* Explain the proposed solution.
* Wait for my explicit approval before modifying code.

## 2. Follow Existing Code Style

* Follow the existing project structure and coding patterns.
* Keep code compact, clean, readable, and easy to understand.
* Use meaningful variable and function names.
* Do not unnecessarily rename existing variables/functions.
* Do not introduce a different coding style without a reason.

## 3. Keep Changes Minimal

* Change only what is required.
* Do not modify unrelated code.
* Do not perform unnecessary refactoring.
* Do not add unnecessary classes, helpers, dependencies, or abstractions.
* Do not over-engineer simple requirements.

## 4. Verify Changes

* After implementation, verify the changed functionality.
* Check for obvious regressions.
* Make sure only the intended files/code were changed.
* Do not consider the task complete without verification.

## 5. Git Workflow

Use this development flow:

```text
dev2 → dev → main
```

* Develop locally on `dev2`.
* Never develop directly on `main`.
* When I say **"push the code"**, first commit the changes.
* Merge `dev2` into `dev`.
* Verify/test the `dev` branch.
* Merge `dev` into `main`.
* Push the code.
* After release, `dev` and `main` must point to the same tested commit.
* Never force-push, reset, delete branches, or discard changes without my explicit approval.

## 6. Git Safety

* Always check `git status` and the current branch before Git operations.
* Never include unrelated changes in a commit.
* Never push unless I explicitly ask.
* If a merge conflict occurs, stop and analyze it before resolving it.

## 7. Secrets

* Never hardcode API keys, tokens, passwords, or other secrets.
* Use `.env` for local secrets.
* Never print or expose secrets.
* Never commit `.env`.

## 8. Project Approach

* Keep this project simple and practical.
* Prefer reliable solutions over complex solutions.
* Do not introduce AI, AWS, automation, or other infrastructure unless explicitly requested.
* Always preserve working functionality when making changes.
