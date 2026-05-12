---
description: Break work into small, verifiable tasks with acceptance criteria and dependency ordering
---

Enter read-only plan mode before making any code changes.

1. Read the spec and relevant codebase sections
2. Map component dependencies (build foundations first)
3. Slice work vertically — complete feature paths, not horizontal layers
4. Write each task with:
   - Description
   - Acceptance criteria (specific, testable)
   - Verification steps (`python -m pytest`, `python -m mypy`, etc.)
   - Dependencies (task numbers)
   - Files likely touched
   - Size estimate: XS=1 file | S=1-2 files | M=3-5 files | L=5+ files (too large → split)
5. Add review checkpoints every 2-3 tasks
6. Output plan to `tasks/plan.md` and checklist to `tasks/todo.md`
7. Present the plan for human review before implementing anything

**Do NOT write code during planning.** The output is a plan document, not implementation.

Red flags: tasks without acceptance criteria, no verification steps, all tasks are L-sized, no checkpoints between phases.
