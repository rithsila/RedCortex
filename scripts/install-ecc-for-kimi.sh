#!/bin/bash
# install-ecc-for-kimi.sh
# Adapt everything-claude-code components for Kimi CLI
# Usage: ./install-ecc-for-kimi.sh [ecc-repo-url] [--full]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ECC_REPO="${1:-https://github.com/affaan-m/everything-claude-code.git}"
KIMI_SKILLS_DIR="${KIMI_SKILLS_DIR:-$HOME/.config/agents/skills}"
KIMI_SUBAGENTS_DIR="${KIMI_SUBAGENTS_DIR:-$HOME/.config/agents/subagents}"

echo -e "${BLUE}=== Everything Claude Code → Kimi CLI Adapter ===${NC}"
echo ""
echo -e "Skills directory: ${GREEN}$KIMI_SKILLS_DIR${NC}"
echo -e "Subagents directory: ${GREEN}$KIMI_SUBAGENTS_DIR${NC}"
echo ""

# Create directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p "$KIMI_SKILLS_DIR"
mkdir -p "$KIMI_SUBAGENTS_DIR"

# Clone ECC repo
if [ ! -d "/tmp/everything-claude-code" ]; then
    echo -e "${YELLOW}Cloning ECC repository...${NC}"
    git clone --depth 1 "$ECC_REPO" /tmp/everything-claude-code
else
    echo -e "${GREEN}Using existing ECC repository at /tmp/everything-claude-code${NC}"
fi

cd /tmp/everything-claude-code

# Install core skills (direct copy - they're compatible!)
echo ""
echo -e "${BLUE}Installing core skills...${NC}"
CORE_SKILLS=(
    "tdd-workflow"
    "security-review"
    "coding-standards"
    "python-patterns"
    "python-testing"
    "backend-patterns"
    "api-design"
    "e2e-testing"
    "deployment-patterns"
    "docker-patterns"
    "verification-loop"
    "eval-harness"
    "search-first"
)

INSTALLED_COUNT=0
SKIPPED_COUNT=0

for skill in "${CORE_SKILLS[@]}"; do
    if [ -d "skills/$skill" ]; then
        if [ -d "$KIMI_SKILLS_DIR/$skill" ]; then
            echo -e "  ${YELLOW}⚠${NC}  $skill (already exists, skipping)"
            ((SKIPPED_COUNT++))
        else
            echo -e "  ${GREEN}✓${NC}  $skill"
            cp -r "skills/$skill" "$KIMI_SKILLS_DIR/"
            ((INSTALLED_COUNT++))
        fi
    else
        echo -e "  ${RED}✗${NC}  $skill (not found in ECC repo)"
    fi
done

# Optional: Install additional skills
if [ "$2" == "--full" ]; then
    echo ""
    echo -e "${BLUE}Installing additional skills (--full mode)...${NC}"
    for skill_dir in skills/*/; do
        skill_name=$(basename "$skill_dir")
        if [ ! -d "$KIMI_SKILLS_DIR/$skill_name" ]; then
            echo -e "  ${GREEN}✓${NC}  $skill_name"
            cp -r "$skill_dir" "$KIMI_SKILLS_DIR/"
            ((INSTALLED_COUNT++))
        fi
    done
fi

# Create sample subagents
echo ""
echo -e "${BLUE}Creating sample subagent configurations...${NC}"

# Code reviewer subagent
cat > "$KIMI_SUBAGENTS_DIR/code-reviewer.yaml" << 'EOF'
version: 1
agent:
  name: code-reviewer
  description: Reviews code for quality, security, and maintainability
  extend: default
  system_prompt_path: ./code-reviewer-prompt.md
  exclude_tools:
    - "kimi_cli.tools.file:WriteFile"
    - "kimi_cli.tools.file:StrReplaceFile"
EOF

cat > "$KIMI_SUBAGENTS_DIR/code-reviewer-prompt.md" << 'EOF'
# Code Reviewer Agent

You are a senior code reviewer with expertise in software quality, security, and maintainability.

## Review Checklist

### Code Quality
- [ ] Code follows project conventions
- [ ] Functions are focused and single-purpose
- [ ] Variable names are descriptive
- [ ] No code duplication (DRY principle)
- [ ] Error handling is comprehensive

### Security
- [ ] No hardcoded secrets or API keys
- [ ] Input validation is present
- [ ] SQL queries use parameterized statements
- [ ] No injection vulnerabilities
- [ ] Proper access controls

### Testing
- [ ] Tests cover critical paths
- [ ] Edge cases are handled
- [ ] Test names are descriptive
- [ ] Mocking is appropriate

### Performance
- [ ] No N+1 queries
- [ ] Efficient data structures
- [ ] No unnecessary computations
- [ ] Caching is used appropriately

## Output Format

Provide a structured review with:
1. **Summary** - Overall assessment
2. **Issues** - Specific problems found
3. **Suggestions** - Improvements recommended
4. **Approval Status** - APPROVE / REQUEST_CHANGES / COMMENT
EOF

echo -e "  ${GREEN}✓${NC}  code-reviewer"

# Planner subagent
cat > "$KIMI_SUBAGENTS_DIR/planner.yaml" << 'EOF'
version: 1
agent:
  name: planner
  description: Creates detailed implementation plans
  extend: default
  system_prompt_path: ./planner-prompt.md
  exclude_tools:
    - "kimi_cli.tools.shell:Shell"
    - "kimi_cli.tools.file:WriteFile"
    - "kimi_cli.tools.file:StrReplaceFile"
EOF

cat > "$KIMI_SUBAGENTS_DIR/planner-prompt.md" << 'EOF'
# Planner Agent

You are an expert implementation planner. Your job is to analyze requirements and create detailed, actionable implementation plans.

## Planning Process

1. **Understand** the requirements fully
2. **Analyze** the existing codebase structure
3. **Identify** all affected components
4. **Define** clear, actionable steps
5. **Estimate** time for each step
6. **Consider** edge cases and risks

## Output Format

```markdown
## Implementation Plan: [Feature Name]

### Overview
[Brief description of the feature and approach]

### Affected Components
- [Component 1] - [Description]
- [Component 2] - [Description]

### Implementation Steps
| Step | Description | Files | Estimate |
|------|-------------|-------|----------|
| 1 | [Step description] | [Files to modify] | [Time] |
| 2 | [Step description] | [Files to modify] | [Time] |

### Testing Strategy
- [ ] Unit tests for [component]
- [ ] Integration tests for [flow]
- [ ] E2E tests for [user journey]

### Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk 1] | High/Medium/Low | [How to mitigate] |

### Dependencies
- [Dependency 1]
- [Dependency 2]
```

Be thorough and consider all edge cases.
EOF

echo -e "  ${GREEN}✓${NC}  planner"

echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo -e "Installed ${GREEN}$INSTALLED_COUNT${NC} skills"
echo -e "Skipped ${YELLOW}$SKIPPED_COUNT${NC} existing skills"
echo ""
echo -e "${BLUE}Installed skills:${NC}"
ls -1 "$KIMI_SKILLS_DIR" | head -20
if [ $(ls -1 "$KIMI_SKILLS_DIR" | wc -l) -gt 20 ]; then
    echo "  ... and more"
fi
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Start Kimi CLI: kimi"
echo "2. Test a skill: /skill:tdd-workflow"
echo "3. View available skills: /skills"
echo ""
echo -e "${BLUE}For your project:${NC}"
echo "1. Create AGENTS.md in your project root"
echo "2. Create project-specific skills in .agents/skills/"
echo ""
echo -e "${YELLOW}Note:${NC} Some ECC features (hooks, continuous learning) are not available in Kimi CLI."
echo -e "See docs/ECC-KIMI-ADAPTER.md for workarounds and detailed documentation."
