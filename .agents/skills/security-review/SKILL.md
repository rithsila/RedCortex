---
name: security-review
description: Security audit and vulnerability assessment
type: flow
---

# Security Review Workflow

Perform comprehensive security audit following OWASP guidelines.

```mermaid
flowchart TD
    A([BEGIN]) --> B[Scan for hardcoded secrets]
    B --> C{Secrets found?}
    C -->|Yes| D[CRITICAL: List exposed secrets]
    C -->|No| E[Check input validation]
    D --> E
    E --> F{Missing validation?}
    F -->|Yes| G[HIGH: List input vulnerabilities]
    F -->|No| H[Check SQL injection risks]
    G --> H
    H --> I{Injection possible?}
    I -->|Yes| J[CRITICAL: SQL injection found]
    I -->|No| K[Check authentication]
    J --> K
    K --> L{Auth weaknesses?}
    L -->|Yes| M[HIGH: Auth vulnerabilities]
    L -->|No| N[Check authorization]
    M --> N
    N --> O{Missing access control?}
    O -->|Yes| P[HIGH: Access control issues]
    O -->|No| Q[Check dependencies]
    P --> Q
    Q --> R{Vulnerable deps?}
    R -->|Yes| S[MEDIUM: Outdated/vulnerable packages]
    R -->|No| T[Generate security report]
    S --> T
    T --> U([END])
```

## Security Checklist

### Secrets Management
- [ ] No API keys in code
- [ ] No passwords in code
- [ ] No private keys in code
- [ ] `.env` in `.gitignore`

### Input Validation
- [ ] All inputs validated
- [ ] Type checking enforced
- [ ] Sanitization applied

### Injection Prevention
- [ ] SQL uses parameterized queries
- [ ] No eval() or exec()
- [ ] Command injection prevented

### Authentication & Authorization
- [ ] Proper auth checks
- [ ] Role-based access control
- [ ] Session management secure

## How to Use

Run: `/flow:security-review` or `/skill:security-review Audit src/`
