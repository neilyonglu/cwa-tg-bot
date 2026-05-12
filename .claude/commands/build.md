---
description: Implement the next task incrementally — build, test, verify, commit
---

Pick the next pending task from the plan. For each task:

1. Read the task's acceptance criteria
2. Load relevant context (existing code, patterns, types)
3. Write a failing test for the expected behavior (RED)
4. Implement the minimum code to pass the test (GREEN)
5. Run the full test suite to check for regressions
6. Run type checking to verify correctness
7. Commit with a descriptive message following `feat/fix/refactor/test/chore:` convention
8. Mark the task complete and move to the next one

**Simplicity first:** Ask "What is the simplest thing that could work?" before writing any code.

**Scope discipline:** Touch only what the task requires. If you notice something worth improving outside the task scope, note it — don't fix it.

**Keep it compilable:** After each increment the project must run and existing tests must pass.

If any step fails, stop and debug the root cause before continuing.
