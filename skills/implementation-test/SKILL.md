---
name: implementation-test
description: Run the repo's test suite for implemented changes and report pass/fail.
---

# Implementation Test Skill

Runs the test suite to verify implemented changes. Called by the implementation
orchestrator after implementation; can also be run independently.

## Usage

```
/implementation-test
```

## Workflow

1. **Run tests:** `{{ config.test_command }}`
2. **Capture output:** test count, passed/failed, any failures.
3. **Check exit code:** 0 = success, non-zero = failure.
4. **Report:**
   - PASS → "All tests passed. Ready for verification."
   - FAIL → list the failed tests + error messages. Blocks the workflow until fixed.

{{ config.test_notes? }}

## Notes

- Tests must all pass before proceeding.
- Never claim a suite passed that did not actually run — report the real result.
