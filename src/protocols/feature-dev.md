---
name: feature-development
description: |
  Full-featured workflow for developing new features from concept to deployment.

  This protocol orchestrates multiple specialized agents through a structured multi-phase process.

model: inherit
phases:
  - name: discovery
    agent: explorer
    description: Define scope and requirements by analyzing the codebase
  - name: design
    agent: explorer
    description: Create technical architecture proposal based on exploration
  - name: implementation
    agent: interactive_agent
    description: Write the actual feature code
  - name: review
    agent: reviewer
    description: Security and quality audit
  - name: validation
    agent: validator
    description: End-to-end testing and validation
---

# Feature Development Protocol

## Overview

This protocol provides a structured approach to developing new features, ensuring:
- Clear requirements before coding begins
- Understanding of existing patterns before introducing new code
- Architecture review before implementation
- Quality assurance before completion

## Phase Flow

### Phase 1: Discovery (Scope & Requirements)

**Agent**: Explorer

**Purpose**: Understand what needs to be built by analyzing the existing codebase and user request.

**Outputs**:
- User requirement summary in technical terms
- Identified edge cases and constraints
- Dependencies on existing features
- Success criteria definition

**Transition**: Only proceed when user confirms requirements are understood.

---

### Phase 2: Exploration (Codebase Scan)

**Agent**: Explorer

**Purpose**: Understand what already exists that affects this feature.

**Actions**:
1. Search for relevant patterns in codebase
2. Map dependencies of related features
3. Identify similar implementations we could reuse
4. Find TODOs/FIXMEs that relate to this area

**Outputs**:
- Related files list with descriptions
- Existing patterns that can be leveraged
- Potential conflicts with current design
- Recommended file locations for new code

**Transition**: Proceed only after user confirms exploration findings are accurate.

---

### Phase 3: Design (Architecture Proposal)

**Agent**: Interactive Agent (Generalist)

**Purpose**: Define HOW the feature will be built, acting as the architect.

**Deliverables**:
1. System component diagram showing integration points
2. API contract if external endpoints are needed
3. Database schema changes (if applicable)
4. Interface definitions for new components
5. Migration strategy for existing data

**Review Criteria**:
- Minimal disruption to existing code
- Reuse of proven patterns where appropriate
- Clear separation of concerns
- Extensibility for future needs

**Transition**: Proceed only after design is approved by user.

---

### Phase 4: Implementation (Coding Phase)

**Agent**: Interactive Agent (Generalist)

**Approach**: Incremental development with intermediate commits.

**Steps**:
1. Create new files in identified locations
2. Implement core functionality
3. Add helper utilities as needed
4. Write integration code with existing features
5. Generate unit tests for new functionality

**Intermediate Checkpoints**:
- After file creation: "Files created, ready for implementation"
- After core logic: "Core logic complete, proceeding to tests"
- After tests: "Full implementation complete, pending review"

**Outputs**:
- New/modified files list
- Test coverage report
- Migration scripts (if needed)
- Documentation updates

---

### Phase 5: Review (Quality Audit)

**Agent**: Reviewer

**Focus Areas**:
1. Security vulnerabilities in new code
2. Error handling completeness
3. Test coverage adequacy
4. Code style consistency
5. Performance considerations
6. Documentation completeness

**Validation Checks**:
- No hardcoded secrets or credentials
- Proper input validation on all external data
- Graceful error handling throughout
- Comprehensive test cases including edge cases
- All public functions have docstrings
- Type hints present where applicable

**Outputs**:
- Audit report with severity ratings
- List of items requiring fixes before deployment
- Confidence score in readiness for production

---

### Phase 6: Validation

**Agent**: Validator

**Purpose**: Perform end-to-end and integration testing.

**Actions**:
1. Run all relevant unit and integration tests.
2. Manually (or via script) test the user-facing feature flow.
3. Check for regressions in related system components.

**Outputs**:
- Final validation report.
- Confirmation of feature completeness.

---

## Protocol Execution Engine

This protocol is designed to be executed by the `ProtocolEngine` class, which:

1. **Orchestrates phases sequentially** - Each phase must complete before next begins
2. **Passes context between phases** - Exploration findings inform the design phase
3. **Allows intermediate checkpoints** - User can review after each phase
4. **Supports rollback** - Can undo changes if a phase reveals fundamental issues

## Usage Example

```python
from src.core.protocol_engine import ProtocolEngine
from src.core.agent_loader import get_agent_loader

# Load agents and protocols
loader = get_agent_loader()
loader.load_all()

# Execute feature development protocol
engine = ProtocolEngine(loader)
result = await engine.execute(
    protocol_name="feature-development",
    task="Add JWT authentication to the admin API",
    user_constraints=["Must use existing auth service", "No breaking changes to client API"]
)

print(result.summary())
```

## Customization Points

Teams can customize this protocol by:
1. Adding custom checks at specific phases
2. Changing agent assignments per phase
3. Adding mandatory documentation requirements
4. Integrating with CI/CD pipeline steps

## Success Metrics

A feature development is considered successful when:
- ✅ All 5 phases completed without blockers
- ✅ Reviewer passes security audit (0 critical, <3 high severity)
- ✅ Test coverage meets project minimums
- ✅ Documentation updated to reflect new functionality
- ✅ User confirmation obtained before deployment-ready state
