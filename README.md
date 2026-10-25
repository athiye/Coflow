# CoFlow

An extensible software engineering and runtime product-analysis platform that combines repository intelligence, structured workflow orchestration, browser-based computer use, and role-aware outputs for engineering, product, QA, release, and UX teams.

## Why this project matters

Most AI coding tools help a developer write or edit code faster. That solves only part of the delivery problem.

Real organizations also struggle with:
- understanding unfamiliar or legacy codebases
- evaluating release risk before deployment
- diagnosing flow-level UX problems in live products
- translating runtime behavior into product requirements
- identifying accessibility and neurodivergent usability barriers that emerge only during real interaction
- aligning engineering execution with product and experience goals

The Autonomous SWE Agent addresses this gap by combining:
- repo-aware reasoning for code and architecture work
- workflow packs for repeatable engineering and product tasks
- a browser-based computer-use layer for runtime evidence collection
- a Natural Tool Protocol (NTP) that converts model intent into controlled execution
- multi-surface interfaces across web, API/CLI, and IDE use

## What problem it is trying to solve

### 1. Coding tools stop at code
A modern copilot can suggest code, explain files, and run some commands. It usually does **not** tell a team:
- whether a dynamic flow is confusing in production
- where a user journey breaks down across multiple pages
- how a release impacts usability or accessibility in the live UI
- how a PM should reverse-engineer the product from the actual runtime experience

### 2. Accessibility testing is often too narrow
Static scanners and DOM/rule-based checks are valuable, but they frequently miss:
- multi-step flow friction
- discoverability failures
- modal and drawer interruptions
- hidden or hard-to-activate controls
- cognitive overload and neurodivergent usability barriers
- runtime issues that only appear after interaction

### 3. Teams need one system for code + runtime
Engineering, product, UX, QA, and release teams all need evidence, but from different angles. The Autonomous SWE Agent creates a shared platform for:
- code-grounded reasoning
- runtime-grounded journey analysis
- structured, role-specific outputs

## Core value proposition

The platform is built to be a **workflow engine**, not just a chatbot. It turns model capability into repeatable tasks such as:
- architecture explanation
- debugging and root-cause analysis
- refactor planning
- release-readiness review
- reverse PRD from code
- reverse PRD from live UI
- feature gap analysis
- accessibility and neurodivergent UX reviews
- customer-journey audits using real browser interaction

## Major system capabilities

### Repo intelligence
- explain architecture and main execution flow
- search, read, and summarize key files
- generate refactor and modernization plans
- assess integration and contract risks
- support developer onboarding for unfamiliar repos

### Workflow orchestration
- route work by complexity and use case
- apply reusable action packs
- constrain execution through a protocol layer
- generate outputs for engineering, PM, release, and UX audiences

### Computer use
- open live websites and applications in a browser harness
- capture screenshots, visible text, links, inputs, toggles, dialogs, and clickable controls
- navigate with real interactions such as click, type, search, filter, toggle, and add-to-cart
- retry failed actions with generic fallbacks
- summarize runtime evidence into structured findings

### Accessibility and UX evaluation
- identify friction in dynamic, multi-step flows
- surface weak affordances and discoverability failures
- flag interaction issues that static tooling may not catch
- support neurodivergent usability analysis through runtime and cognitive-flow evidence
- complement existing accessibility scanners rather than replace them

## System architecture at a glance

The system has two primary execution paths.

### 1. Repo path
Used for code-centric tasks:
- architecture explanation
- debugging
- search/read/patch/run workflows
- refactor and release planning

### 2. Computer-use path
Used for runtime-facing tasks:
- accessibility review
- UX flow analysis
- reverse PRD from live UI
- release and admin-console validation
- product journey analysis

These paths share:
- request schemas
- prompt library
- provider abstraction
- workflow routing
- NTP-based execution control

## What changed in the latest computer-use architecture

The latest version of the system moves beyond passive page capture and adds a more agentic interaction model.

### Before
- browser opened a start URL
- snapshots were captured
- navigation mostly depended on shallow page traversal
- interaction robustness was limited

### Now
- the browser harness supports true interaction primitives:
  - robust click
  - text click
  - typed input
  - search
  - filter application
  - toggle handling
  - add-to-cart style actions
- the computer-use agent uses:
  - goal-directed action planning
  - richer page-state capture
  - retry logic with alternate strategies
  - post-action validation
  - chunked evidence summarization for longer runs

This makes the system substantially more useful for:
- complex shopper journeys
- dynamic enterprise apps
- accessibility testing of stateful interfaces
- neurodivergent usability audits

## Why this can be a game changer for accessibility and UX

The biggest shift is that the agent can now analyze a product **as a user experiences it**, not only as a developer sees it in code.

That matters because many serious experience problems are:
- runtime-only
- state-dependent
- journey-level
- interaction-sensitive
- cognitive rather than purely semantic

Examples include:
- controls that are technically present but difficult to activate
- drawers and dialogs that interrupt flow
- confusing search/filter sequences
- weak hierarchy that increases working-memory burden
- poor reassurance after actions
- dense decision spaces that overwhelm users

The agent does not replace existing accessibility tools. Instead, it adds a missing layer:
**interaction-centered runtime evidence.**

## Why this is different from a standard coding copilot

This project is not just:
- autocomplete
- chat over a codebase
- terminal assistance
- patch generation

It adds:
- workflow-first design
- browser-grounded product analysis
- role-aware outputs
- complementary accessibility and UX evaluation
- protocol-based extensibility
- the ability to bridge code, product, and experience

## Who this is for

- software developers
- engineering managers
- product managers
- release managers
- QA teams
- UX and accessibility specialists
- enterprise architecture and modernization teams

## Project structure

```text
backend/
  app/
    agents/
      swe_agent.py
      computer_use_agent.py
    computer_use/
      browser_harness.py
    core/
      config.py
      prompt_library.py
      router.py
      schemas.py
    protocol/
      ntp.py
    providers/
      base.py
      factory.py
      openai_responses.py
      mock_provider.py
    tools/
      executor.py
      registry.py
frontend/
  public/
    index.html
vscode-extension/
  src/
    extension.ts
```

## Key architectural ideas

### Workflow-first, not prompt-first
Use named actions and packs instead of relying only on open-ended prompting.

### Repo and runtime as separate evidence domains
Keep code intelligence and live UI intelligence separate, but interoperable.

### NTP as the execution bridge
Natural Tool Protocol provides a controlled boundary between model reasoning and tool execution.

### Accessibility as runtime experience
Treat accessibility and neurodivergent usability as interaction-centered problems, not only static conformance problems.

## Extensibility

Developers can extend the platform by:
- adding workflow actions
- adding new repo tools
- adding new browser actions
- adding domain-specific analyzers
- integrating external systems
- adding new providers
- tuning routing and governance logic

## Documentation

- `README.md` — project overview and positioning
- `ARCHITECTURE.md` — detailed technical architecture
- `CoFlowTechpaper.md` — research-style paper on architecture, business problem, accessibility, UX, and why computer use matters

