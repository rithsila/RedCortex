# Kimi CLI + Everything Claude Code - Quick Reference

> Quick reference for using everything-claude-code patterns with Kimi CLI in RedCortex.

## Quick Start

### 1. Start Kimi CLI
```bash
cd /Users/macmini/Projects/RedCortex
kimi
```

### 2. Load a Skill
```
> /skill:redcortex-dev
> /skill:rag-pipeline How do I optimize hybrid search?
> /skill:tdd-python Create tests for the new API endpoint
```

### 3. Use Subagents
```
> Use the plan subagent to analyze the ingestion module
> Use the explore subagent to find all database-related code
> Use the coder subagent to implement the new feature
```

## Skills Reference

### Project-Specific (in `.agents/skills/`)

| Skill | Command | Purpose |
|-------|---------|---------|
| redcortex-dev | `/skill:redcortex-dev` | Project guidelines, quick commands, structure |
| rag-pipeline | `/skill:rag-pipeline` | RAG development, optimization, debugging |
| tdd-python | `/skill:tdd-python` | TDD workflow, pytest patterns, coverage |

### System-Level (in `~/.config/agents/skills/`)

Install with: `./scripts/install-ecc-for-kimi.sh`

| Skill | Purpose |
|-------|---------|
| tdd-workflow | Test-driven development |
| security-review | Security checklist |
| coding-standards | Universal coding standards |
| python-patterns | Python idioms and patterns |
| backend-patterns | API, database, caching patterns |
| deployment-patterns | CI/CD, Docker patterns |

## Subagents Reference

### Built-in Kimi CLI Subagents

| Type | Purpose | Tools |
|------|---------|-------|
| `coder` | General software engineering | All tools (Shell, Read, Write, etc.) |
| `explore` | Read-only codebase exploration | No write tools |
| `plan` | Architecture and planning | No Shell, no write tools |

### Custom RedCortex Subagents (in `.agents/subagents/`)

| Subagent | File | Purpose |
|----------|------|---------|
| code-reviewer | `code-reviewer.yaml` | Code quality and security review |
| planner | `planner.yaml` | Implementation planning |
| rag-expert | `rag-expert.yaml` | Vector search and RAG specialist |

## Common Tasks

### Planning a Feature
```
> /skill:redcortex-dev
> Create an implementation plan for adding user authentication
```

The agent will use the `planner` subagent pattern to analyze and create a detailed plan.

### Code Review
```
> Review the code in src/rag_pipeline.py for quality and security issues
```

The agent will act as a code reviewer following the skill guidelines.

### Debugging Search Issues
```
> /skill:rag-pipeline
> Why am I getting poor search results for "systemctl commands"?
```

### Writing Tests
```
> /skill:tdd-python
> Create tests for the new hybrid_search function
```

### Development Workflow
```
> /skill:tdd-python
> I need to implement caching for query results
```

Follows RED-GREEN-IMPROVE cycle automatically.

## ECC → Kimi Command Mapping

| ECC Command | Kimi CLI Equivalent |
|-------------|---------------------|
| `/plan "feature"` | Create a plan using the planner subagent |
| `/tdd` | `/skill:tdd-python` |
| `/code-review` | Ask for code review with quality guidelines |
| `/security-scan` | `/skill:security-review` (after install) |
| `/build-fix` | Use `coder` subagent directly |
| `/refactor-clean` | Use `explore` subagent for analysis |
| `/skill-create` | Built-in Kimi skill! |

## Installation

### Install ECC Skills System-Wide
```bash
./scripts/install-ecc-for-kimi.sh
```

This installs common ECC skills to `~/.config/agents/skills/`.

### Full Installation (All Skills)
```bash
./scripts/install-ecc-for-kimi.sh --full
```

## Project Structure

```
RedCortex/
├── .agents/
│   ├── skills/           # Project-specific skills
│   │   ├── rag-pipeline/
│   │   ├── redcortex-dev/
│   │   └── tdd-python/
│   └── subagents/        # Custom subagent configs
│       ├── code-reviewer.yaml
│       ├── planner.yaml
│       └── rag-expert.yaml
├── docs/
│   ├── ECC-KIMI-ADAPTER.md    # Full adapter guide
│   └── KIMI-CLI-QUICKREF.md   # This file
└── scripts/
    └── install-ecc-for-kimi.sh  # Installer script
```

## Key Differences from ECC

| Feature | ECC (Claude Code) | Kimi CLI |
|---------|-------------------|----------|
| Skills | Same format | Same format ✓ |
| Agents | Markdown frontmatter | YAML config |
| Commands | `/command` | `/skill:name` |
| Hooks | Auto-trigger | Not supported |
| Continuous Learning | Instincts | Not supported |

## Resources

- **Full Adapter Guide**: `docs/ECC-KIMI-ADAPTER.md`
- **Kimi CLI Docs**: https://moonshotai.github.io/kimi-cli/
- **Everything Claude Code**: https://github.com/affaan-m/everything-claude-code
- **Agent Skills Format**: https://agentskills.io/

## Tips

1. **Use skills for knowledge** - Load relevant skills before complex tasks
2. **Use subagents for isolation** - Delegate to `explore`, `plan`, or `coder` subagents
3. **Reference AGENTS.md** - Project context is loaded automatically
4. **Create project skills** - Add domain knowledge to `.agents/skills/`
5. **Combine skills** - Chain multiple skills: `/skill:redcortex-dev` then ask specific questions

---

*Last updated: 2026-03-26*
