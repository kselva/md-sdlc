# AI agent rules - read before touching code

DO
- Work only the Story handed to you. Its files only (see `touches:`).
- Branch: feat/<story-id>. Never commit to main.
- Extend, don't rewrite. Keep existing signatures, exports, response
  shapes, DB columns. New params get defaults.
- Check callers before editing shared code.
- Match surrounding code style. Use the project logger, not console.
- Stop and ask if the Story needs a breaking change.

DON'T
- Don't edit files outside your Story's `touches:` list.
- Don't write assertion tests for a Story marked `stability: exploring` -
  smoke test only.
- Don't run the test suites unless the project says to.
- Don't add per-endpoint audit calls or per-controller response
  formatting if the project centralises them.
- Don't touch env, migrations, or CI config unless the Story says so.
- Don't refactor adjacent code "while you're here".

WHEN DONE
- Summary: what changed, how to verify, risks. 5 lines.
- List any file you touched that wasn't in `touches:`.
