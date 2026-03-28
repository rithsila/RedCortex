---
name: plan-feature
description: Create implementation plan for new features
type: flow
---

# Feature Planning Workflow

Create comprehensive implementation plans for new features.

```mermaid
flowchart TD
    A([BEGIN]) --> B[Understand feature requirements]
    B --> C[Explore existing codebase]
    C --> D[Identify affected components]
    D --> E{Components clear?}
    E -->|No| F[Research more]
    F --> C
    E -->|Yes| G[Define implementation steps]
    G --> H[Estimate time for each step]
    H --> I[Identify dependencies]
    I --> J[Assess risks]
    J --> K{Acceptable risks?}
    K -->|No| L[Propose mitigations]
    L --> J
    K -->|Yes| M[Define testing strategy]
    M --> N[Generate plan document]
    N --> O([END])
```

## Output Format

```markdown
## Implementation Plan: [Feature Name]

### Overview
[Description and approach]

### Affected Components
- [Component 1]
- [Component 2]

### Implementation Steps
| Step | Task | Files | Estimate |
|------|------|-------|----------|
| 1 | ... | ... | Xh |

### Testing Strategy
- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests

### Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| ... | High/Med/Low | ... |
```

## How to Use

Run: `/flow:plan-feature` or `/skill:plan-feature Add user authentication`
