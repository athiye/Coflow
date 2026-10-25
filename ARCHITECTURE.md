# Architecture Document

## 1. Overview

The CoFlow Agent is a workflow-oriented software engineering and runtime product-analysis platform. It combines repository reasoning, controlled tool execution, provider abstraction, and a browser-based computer-use subsystem into a single system that can serve engineering, product, QA, release, UX, and accessibility use cases.

The architecture is intentionally split into two major evidence domains:

1. **Repo intelligence**
2. **Runtime computer use**

This separation is central to the design. Code tells part of the truth; runtime interaction tells another part. The system is built to reason across both without collapsing them into one brittle, monolithic loop.

## 2. Business problems the architecture is designed to solve

### 2.1 Engineering organizations lack workflow-level AI, not just code generation
Most AI coding tools improve local developer productivity but do not solve higher-level delivery problems such as:
- understanding unfamiliar systems
- identifying change impact
- reviewing release readiness
- evaluating customer journey risk
- explaining product behavior to non-engineers

### 2.2 Accessibility and UX failures often emerge only in runtime
Traditional tooling is strong at:
- static checks
- code and DOM inspection
- standards conformance

It is weaker at:
- dynamic interaction flows
- hidden controls and overlays
- drawers, dialogs, filters, and stateful forms
- real task completion
- cognitive overload and neurodivergent usability barriers

### 2.3 Cross-functional teams need a shared system of evidence
Engineering, product, release, and UX teams often reason from different artifacts:
- source code
- tickets and plans
- screenshots and analytics
- production behavior

The architecture solves this by providing:
- code-grounded workflows
- runtime-grounded workflows
- shared structured outputs

## 3. Design goals

### 3.1 Workflow orientation
The platform should expose meaningful actions and outcome shapes, not only raw prompting.

### 3.2 Evidence-grounded reasoning
The system should prefer:
- file reads
- search results
- runtime captures
- action traces
over unsupported speculation.

### 3.3 Extensibility
Developers should be able to add:
- tools
- workflows
- browser actions
- providers
without rewriting core orchestration logic.

### 3.4 Safety and bounded execution
The architecture must support:
- step caps
- controlled tool registries
- restricted shell commands
- read-mostly browser defaults
- future approval gates for destructive actions

### 3.5 Cross-functional usefulness
Outputs must be usable by:
- developers
- PMs
- UX leads
- accessibility teams
- release managers

## 4. High-level layered architecture

### 4.1 Interface layer
User entry points include:
- web UI
- VS Code extension
- CLI/API consumers

### 4.2 Orchestration layer
Responsibilities:
- route requests by complexity and use case
- select workflow packs
- choose providers/models
- normalize outputs

### 4.3 Protocol layer
NTP converts model intent into controlled executable structures for the repo path.

### 4.4 Execution layer
Two main subsystems:
- repo tool execution
- browser/computer-use execution

### 4.5 Provider layer
Model backends expose a common interface for:
- `complete()`
- `stream()`

## 5. Core architectural domains

## 5.1 Repo intelligence path

### Purpose
Solve code- and architecture-centered problems.

### Typical use cases
- explain architecture
- summarize file or service behavior
- debug likely root causes
- produce refactor plans
- assess API contract drift
- generate release-readiness notes
- support onboarding into a repo

### Core evidence sources
- file listing
- file reading
- file search
- patches
- shell command results

### Typical flow
1. request enters through UI/API/IDE
2. router chooses provider tier and action pack
3. system prompt and task prompt are built
4. NTP parses plan/action intent
5. repo tools are invoked
6. agent synthesizes final answer from collected evidence

## 5.2 Runtime computer-use path

### Purpose
Solve browser- and interaction-centered problems.

### Typical use cases
- accessibility testing
- UX and journey review
- reverse PRD from live product
- admin-console verification
- release validation of runtime flows
- product gap analysis from actual UI
- neurodivergent usability testing

### Why this path exists separately
Runtime evidence differs from code evidence:
- interaction is stateful
- the important behavior may depend on clicks, typing, filters, drawers, dialogs, and async transitions
- the browser is the source of truth for user-facing problems

### Typical flow
1. request includes `computer_use` context and start URL
2. computer-use agent launches browser harness
3. harness captures page state and performs bounded interactions
4. interactions generate:
   - screenshots
   - visible text
   - discovered links
   - clickable controls
   - inputs
   - toggles
   - dialogs
   - action traces
5. evidence is chunked and summarized
6. final structured synthesis is produced

## 6. Main components

## 6.1 `core/schemas.py`
Defines strongly typed request/response structures, including:
- chat requests
- IDE context
- computer-use context
- tool calls
- metrics-bearing responses

Important browser fields include:
- start URL
- goal
- max steps
- headless/visible mode
- pause options

## 6.2 `core/prompt_library.py`
Provides named action packs instead of requiring every task to be hand-prompted.

Examples:
- architecture explanation
- release readiness
- reverse PRD
- accessibility review
- UX audit
- PM repo analysis

## 6.3 `core/router.py`
Selects:
- cheap
- mid
- premium

based on:
- task complexity
- repo involvement
- browser/runtime context
- reasoning depth

This is the right place for future:
- cost-aware routing
- policy controls
- role-based routing

## 6.4 `agents/swe_agent.py`
The repo-focused execution engine.

Responsibilities:
- construct prompt context
- invoke provider
- interpret NTP output
- execute repo tools
- synthesize evidence-backed outputs

## 6.5 `agents/computer_use_agent.py`
The runtime-focused execution engine.

Responsibilities:
- interpret a live interaction goal
- open and manage browser sessions
- capture page state at every step
- plan and execute browser actions
- retry failed actions with alternative strategies
- produce chunked summaries and final outputs

This agent now behaves more like an actual interaction engine than a snapshot collector.

## 6.6 `computer_use/browser_harness.py`
The browser harness is the low-level execution substrate for computer use.

### Earlier role
Originally, it mostly:
- opened a URL
- captured screenshots and text
- optionally followed a limited set of links

### Current role
It now provides generic interaction primitives such as:
- `goto()`
- `navigate_page()`
- `click_selector()`
- `click_text()`
- `type_selector()`
- `search()`
- `apply_filter()`
- `safe_toggle()`
- `add_to_cart()`
- `robust_click()`
- `wait_for_state_change()`
- `capture_current_page()`

### Why this is important
This turns the browser layer into a reusable interaction engine rather than a passive renderer.

## 6.7 `providers/`
Provider abstraction isolates model APIs from agent logic.

Benefits:
- cleaner migration across model interfaces
- support for mock and real providers
- reuse across repo and runtime paths

## 6.8 Tool system
Repo tools remain separate from browser actions. This is intentional.

Repo tools:
- operate on code and shell environment

Browser actions:
- operate on runtime UI state

This avoids conflating software execution with browser interaction.

## 6.9 `protocol/ntp.py`
NTP provides the structured boundary between model reasoning and tool execution in repo workflows.

It improves:
- safety
- auditability
- modularity
- extensibility

## 7. Detailed computer-use architecture

## 7.1 Page-state model
Each browser step can capture:
- URL
- title
- visible text
- screenshot path
- discovered links
- clickable elements
- inputs
- toggles
- dialogs

This is much richer than traditional browser automation logs.

## 7.2 Interaction model
The system supports generic action types:
- `NAVIGATE`
- `CLICK_LINK`
- `CLICK_TEXT`
- `CLICK_SELECTOR`
- `TYPE_SELECTOR`
- `SEARCH`
- `APPLY_FILTER`
- `TOGGLE`
- `ADD_TO_CART`
- `STOP`

This gives the planner a broad but bounded vocabulary.

## 7.3 Generic robustness layer
The current architecture specifically improves robustness through:

### `robust_click()`
Fallback order:
1. normal click
2. checkbox/radio semantic interaction
3. associated label click
4. visible-text click
5. force click
6. JS click

### `safe_fill()`
- waits for visible input
- fills and validates input value
- optionally submits

### `safe_toggle()`
- uses semantic toggle methods when possible
- falls back to label click or robust click

### `wait_for_state_change()`
Validates that actions actually changed observable state.

### `execute_action_with_retries()`
Retries failed actions with alternate strategies.

## 7.4 Why generic robustness matters
Many modern web apps use:
- hidden inputs
- stylized labels
- intercepted pointer events
- animated overlays
- drawer-based filters
- async state transitions

Without generic interaction fallbacks, browser agents fail frequently. The new harness makes those failures much less likely.

## 8. Accessibility and neurodivergent UX as first-class business problems

## 8.1 Why standard testing is incomplete
Static and rule-based testing often misses:
- interaction-level discoverability problems
- task continuity breakdowns
- modal interruption cost
- weak user reassurance after actions
- overloaded decision spaces
- inconsistent navigation models
- excessive working-memory burden

## 8.2 What this architecture adds
Because the agent can actually interact with the live UI, it can evaluate:
- whether a task can be completed
- how many steps are required
- where friction accumulates
- whether controls are discoverable and operable
- whether flow structure is cognitively demanding

## 8.3 Why this can be a game changer
This architecture reframes accessibility and UX evaluation from:
- page-level compliance

to:
- flow-level interaction quality

That is powerful for:
- ecommerce
- enterprise apps
- customer support tools
- admin portals
- internal workflows
- any dynamic stateful web application

## 9. Safety model

### 9.1 Repo safety
- bounded tool steps
- restricted shell prefixes
- explicit tool registries

### 9.2 Browser safety
- step caps
- retry limits
- optional manual login pause
- optional pause before close
- generic read-mostly defaults

### 9.3 Future safety upgrades
- destructive-action approvals
- selector blacklists
- role-based browser policy
- environment restrictions
- action audit logs

## 10. Extensibility points

### 10.1 New workflows
Add action definitions to the prompt library.

### 10.2 New providers
Implement provider interface and register in factory.

### 10.3 New repo tools
Extend registry and executor.

### 10.4 New browser actions
Add generic or domain-focused actions without changing the overall architecture.

### 10.5 New evaluators
Add higher-level evaluators such as:
- accessibility tree analysis
- keyboard-only mode
- cognitive load scoring
- issue taxonomies
- structured finding outputs

## 11. Architectural differentiation

This system differs from a standard coding copilot because it combines:
- workflow orchestration
- repo intelligence
- runtime browser interaction
- role-aware outputs
- complementary accessibility and UX analysis

It is not just a model wrapped around code. It is a multi-domain software delivery system.

## 12. Summary

The latest architecture is not just a repo-aware coding agent with basic browser support but a more differentiated system with:
- real browser interaction
- generic action robustness
- richer runtime evidence
- stronger accessibility and UX relevance
- better cross-functional value

CoFlow is positioned to solve real business problems in engineering, product quality, accessibility, and neurodivergent usability.
