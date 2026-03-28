# Kimi CLI Commands Guide

> Correct usage of ECC-style commands in Kimi CLI

## ⚠️ Important Difference

**Claude Code (ECC)** uses commands like `/tdd`, `/code-review`

**Kimi CLI** uses:
- `/skill:<name>` for regular skills
- `/flow:<name>` for flow skills (workflows)

There are **NO custom slash commands** like `/tdd` in Kimi CLI by default!

## Correct Command Usage

| What You Want | Wrong (ECC) | Correct (Kimi CLI) |
|---------------|-------------|-------------------|
| TDD workflow | `/tdd` | `/flow:tdd-workflow` or `/skill:tdd-workflow` |
| Code review | `/code-review` | `/flow:code-review` or `/skill:code-review` |
| Security scan | `/security-scan` | `/flow:security-review` or `/skill:security-review` |
| Plan feature | `/plan` | `/flow:plan-feature` or `/skill:plan-feature` |
| RAG help | - | `/skill:rag-pipeline` |
| Project help | - | `/skill:redcortex-dev` |

## Command Types Explained

### 1. `/skill:<name>` - Load Knowledge
Loads a skill and sends it to the agent as context.

```
> /skill:tdd-workflow Create tests for user authentication
> /skill:code-review Review src/api/main.py
> /skill:security-review Check for vulnerabilities
> /skill:rag-pipeline Optimize hybrid search
```

### 2. `/flow:<name>` - Execute Workflow
Runs a flow skill that guides through multi-step process.

```
> /flow:tdd-workflow
> /flow:code-review
> /flow:security-review
> /flow:plan-feature
```

## Available Commands in This Project

### Flow Skills (Use `/flow:<name>`)

| Command | Purpose |
|---------|---------|
| `/flow:tdd-workflow` | TDD RED-GREEN-IMPROVE cycle |
| `/flow:code-review` | Comprehensive code review |
| `/flow:security-review` | Security audit |
| `/flow:plan-feature` | Implementation planning |

### Regular Skills (Use `/skill:<name>`)

| Command | Purpose |
|---------|---------|
| `/skill:redcortex-dev` | Project guidelines |
| `/skill:rag-pipeline` | RAG development |
| `/skill:tdd-python` | Python TDD patterns |
| `/skill:tdd-workflow` | TDD methodology |
| `/skill:code-review` | Code review guide |
| `/skill:security-review` | Security checklist |

### Built-in Subagents (Mention in prompts)

```
> Use the plan subagent to analyze the codebase
> Use the explore subagent to find API endpoints
> Use the coder subagent to implement the feature
```

## Examples

### Example 1: TDD Workflow
```
> /flow:tdd-workflow
[Agent follows the flow diagram]

Or with specific task:
> /skill:tdd-workflow Create caching for query results
```

### Example 2: Code Review
```
> /flow:code-review
[Agent asks which files to review]

Or directly:
> /skill:code-review Review src/rag_pipeline.py
```

### Example 3: Security Audit
```
> /flow:security-review
[Agent scans for security issues]

Or targeted:
> /skill:security-review Check src/api/ for vulnerabilities
```

### Example 4: Planning
```
> /flow:plan-feature
[Agent guides through planning]

Or with context:
> /skill:plan-feature Add OAuth authentication
```

## Creating Aliases (Optional)

If you want shortcuts like `/tdd`, create shell aliases:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias kimi-tdd='kimi -c "/flow:tdd-workflow"'
alias kimi-review='kimi -c "/flow:code-review"'
```

## Troubleshooting

### "Unknown slash command"
You used `/tdd` instead of `/flow:tdd-workflow` or `/skill:tdd-workflow`

### "Skill not found"
The skill isn't in `.agents/skills/`. Check with:
```
> /skills
```

### Flow skill doesn't execute
Flow skills need `type: flow` in frontmatter. Regular skills just load knowledge.

## Quick Reference Card

```
┌─────────────────────────────────────────┐
│  KIMI CLI COMMAND CHEAT SHEET           │
├─────────────────────────────────────────┤
│  Load knowledge:  /skill:<name>         │
│  Run workflow:    /flow:<name>          │
│  List skills:     /skills               │
│  List subagents:  /subagents            │
├─────────────────────────────────────────┤
│  COMMON PATTERNS                        │
│  /skill:redcortex-dev                   │
│  /skill:rag-pipeline                    │
│  /flow:tdd-workflow                     │
│  /flow:code-review                      │
│  /flow:security-review                  │
└─────────────────────────────────────────┘
```
