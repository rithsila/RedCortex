---
name: code-review
description: Code review for quality, security, and maintainability
type: flow
---

# Code Review Workflow

Perform comprehensive code review following best practices.

```mermaid
flowchart TD
    A([BEGIN]) --> B[Identify files to review]
    B --> C[Read and analyze code]
    C --> D{Code Quality Check}
    D -->|Issues found| E[List code quality issues]
    D -->|Clean| F{Security Check}
    E --> F
    F -->|Vulnerabilities| G[List security issues]
    F -->|Secure| H{Testing Check}
    G --> H
    H -->|Missing tests| I[Identify test gaps]
    H -->|Adequate| J{Performance Check}
    I --> J
    J -->|Issues| K[List performance concerns]
    J -->|OK| L{Style Compliance}
    K --> L
    L -->|Violations| M[Style feedback]
    L -->|Compliant| N[Generate review report]
    M --> N
    N --> O{Critical issues?}
    O -->|Yes| P[Status: REQUEST_CHANGES]
    O -->|No| Q{Minor issues?}
    Q -->|Yes| R[Status: COMMENT]
    Q -->|No| S[Status: APPROVE]
    P --> T([END])
    R --> T
    S --> T
```

## Review Checklist

### Code Quality
- [ ] Functions are focused and single-purpose
- [ ] Variable names are descriptive
- [ ] No code duplication (DRY)
- [ ] Error handling is comprehensive
- [ ] Type hints are used

### Security
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] No injection vulnerabilities
- [ ] Proper access controls

### Testing
- [ ] Tests cover critical paths
- [ ] Edge cases handled
- [ ] 80%+ coverage

## How to Use

Run: `/flow:code-review` or `/skill:code-review Review src/rag_pipeline.py`
