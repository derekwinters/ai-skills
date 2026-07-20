---
name: implementation-verify
description: Build/verify the change and show a changes summary for user review, then pause.
---

# Implementation Verify Skill

Runs the repo's verification, then shows a summary of changes for user review.
This is the human control point before commit.

## Usage

```
/implementation-verify <issue-number>
```

## Workflow

1. **Verify:** `{{ config.verify_command }}` — must succeed. It must NEVER
   silently pass; report the real result.
{{ config.verify_notes? }}
2. **Prepare a changes summary:** `git diff --stat`; list files modified with
   line counts; summarize the implementation; include the test/verify results.
3. **Pause:** wait for the user to Approve for commit / Request changes / Abort.

## Parameters

- `issue_number` (optional): for reference in the output.

## Notes

- Called by the orchestrator after tests pass.
- Shows all changes before the user reviews; the user has the control point here.
