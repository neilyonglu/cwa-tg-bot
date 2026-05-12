---
description: Security review — OWASP Top 10, secrets management, auth/authz, input validation
---

Review staged changes for security issues. This project handles API keys, external weather APIs, and user location data — treat all of it with care.

**Always required (no exceptions):**
- All external input validated at system boundaries (Telegram messages, API responses)
- No secrets, API keys, or tokens in source code or git history
- Environment variables used for all credentials (check `.env` is in `.gitignore`)
- External API responses treated as untrusted data — validate before use

**Check for:**
- Injection: user input passed to shell commands, file paths, or query strings without sanitization
- Broken auth: missing token validation on webhook endpoints
- Sensitive data exposure: API keys, coordinates, or PII appearing in logs
- Security misconfiguration: hardcoded URLs with credentials, debug mode left on

**Secrets checklist:**
```
- [ ] No API keys in source code
- [ ] .env file is in .gitignore
- [ ] Logs don't contain secrets or user location data
- [ ] Webhook endpoint validates Telegram token
- [ ] Error messages don't expose internal details to users
```

Output: pass/fail per checklist item, Critical findings first with specific file:line references.
