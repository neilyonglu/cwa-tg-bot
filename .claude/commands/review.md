---
description: Five-axis code review: correctness, readability, architecture, security, performance
---

Review all staged or recently changed code across five dimensions:

1. **Correctness** — Matches spec? Edge cases handled? Error paths covered? Tests adequate?
2. **Readability** — Clear names consistent with project conventions? Simple control flow? No unnecessary complexity? Could this be done in fewer lines?
3. **Architecture** — Follows existing patterns? Clean module boundaries? No over-engineering? Abstraction level appropriate?
4. **Security** — Input validated at boundaries? No secrets in code? Auth checked on every protected path? No injection vulnerabilities? External data treated as untrusted?
5. **Performance** — No N+1 patterns? No unbounded operations? Pagination on list endpoints?

Label every finding:
- *(no prefix)* = Required before merge
- **Critical:** = Blocks merge (security vulnerability, data loss, broken functionality)
- **Nit:** = Optional minor (style preference)
- **Consider:** = Suggestion, not required

Output: structured review with `file:line` references and specific fix recommendations.

The approval standard: approve when the change definitely improves overall code health, even if not perfect. Don't reject for style differences if the code follows project conventions.
