# Requirements

Each row is one specified behavior. `AREA` is this project's requirement
namespace (rename it); `NNN` is a 3+ digit number. The last column is the
verification tag: `auto | manual | planned`.

| ID | Behavior | Verify |
|----|----------|--------|
| AREA-001 | Describe the first specified behavior here | planned |

Add rows as behaviors are decided. When a row becomes `auto`, add a test that
references its ID by name in the same change — the `validate-specs` gate checks
for it.
