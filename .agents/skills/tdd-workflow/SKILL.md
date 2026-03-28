---
name: tdd-workflow
description: Test-Driven Development workflow - RED GREEN IMPROVE cycle
type: flow
---

# TDD Workflow

Execute Test-Driven Development workflow following RED-GREEN-IMPROVE cycle.

```mermaid
flowchart TD
    A([BEGIN]) --> B[Analyze requirements and existing code]
    B --> C[Write failing test - RED phase]
    C --> D{Test fails?}
    D -->|No| E[Fix test - must fail first]
    E --> C
    D -->|Yes| F[Write minimal code - GREEN phase]
    F --> G{Test passes?}
    G -->|No| H[Fix implementation]
    H --> G
    G -->|Yes| I[Refactor - IMPROVE phase]
    I --> J{Tests still pass?}
    J -->|No| K[Fix refactoring]
    K --> J
    J -->|Yes| L[Check coverage >= 80%]
    L --> M{Coverage OK?}
    M -->|No| N[Add more tests]
    N --> C
    M -->|Yes| O[Generate summary report]
    O --> P([END])
```

## How to Use

Run: `/flow:tdd-workflow` or `/skill:tdd-workflow <feature description>`

You can also use: `/tdd` (if aliased in your shell)
