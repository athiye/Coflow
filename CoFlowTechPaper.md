# Technical Paper: CoFlow for Runtime Accessibility and Neurodivergent UX Evaluation

## Abstract

This paper argues that computer-use agents can become a powerful complementary layer for accessibility and UX testing, especially in modern applications where many failures emerge only during runtime interaction. The project presented here, the Autonomous SWE Agent, has evolved from a workflow-oriented software engineering assistant into a platform that combines repository intelligence with a robust browser interaction subsystem. The newest contribution is a site-agnostic computer-use engine that can capture page state, choose actions, interact with controls using multiple fallback strategies, validate whether the page changed, and summarize user journeys. The paper focuses on why this matters for accessibility testing, neurodivergent usability, and product-quality evaluation. It also explains why this work is an excellent basis for a summer internship or joint research effort with accessibility software firms or university HCI / CS labs.

## 1. Introduction

Accessibility testing has historically relied on a combination of manual audits, semantic inspection, standards-based checks, and automated scanners. These approaches are essential and should remain central to responsible practice. However, modern software increasingly exposes important failures through interaction, not just through markup.

Examples include:
- controls that are technically present but difficult to discover
- drawers or filters that add hidden complexity
- modals that interrupt flow continuity
- forms whose validation logic becomes confusing only after multiple steps
- interfaces that overload working memory or create high cognitive friction

These are not merely “nice to have” UX concerns. They are often the points at which real users fail to complete a task.

The central idea of this paper is that computer-use agents offer a new way to study these problems. They can navigate live applications, interact with controls, capture state changes, and summarize what happened during a realistic user journey. This creates a form of runtime evidence that neither code analysis nor page-level scanning can fully substitute.

## 2. Core thesis

The core thesis is:

**Computer-use agents should be positioned as a complementary layer for accessibility and UX evaluation, because they can expose runtime, dynamic, and cognitively significant task failures that static scanners and page-local analysis often miss.**

This thesis has three implications:

1. Existing accessibility tools remain indispensable.  
2. Runtime interaction should be treated as a first-class evaluation domain.  
3. Browser agents can help accessibility teams, product teams, and researchers reason about flow-level barriers more effectively.

## 3. System overview

The Autonomous SWE Agent contains two main domains:

- a repo-oriented SWE domain for code and architecture tasks
- a browser-oriented computer-use domain for runtime interaction tasks

The focus of this paper is the second domain.

The updated computer-use subsystem includes:
- a Playwright-based browser harness
- structured page-state capture
- generic action primitives
- robust action fallback strategies
- state-change validation
- goal-directed planner prompts
- retry-aware execution
- chunked summarization and final synthesis

This makes the system suitable for tasks such as:
- runtime accessibility review
- dynamic flow analysis
- reverse PRD generation from live behavior
- neurodivergent usability exploration
- structured UX audits

## 4. Why runtime accessibility testing matters

## 4.1 Page-level conformance is not enough

Many accessibility tools are strongest at:
- missing labels
- role misuse
- contrast issues
- page-local semantic problems
- rule-based violations

These are critical, but there are still important gaps.

A user may fail because:
- the next action is hard to discover
- a flow becomes confusing after multiple state changes
- a control is implemented in a technically valid but interactionally weak way
- the page introduces too many simultaneous choices
- the journey breaks continuity or confidence

These failures are often journey-level failures.

## 4.2 Dynamic interfaces change the problem

Modern products increasingly use:
- drawers
- overlays
- async loading
- contextual filters
- transactional modals
- hidden toggles
- dynamic search states
- branching workflows

The accessibility and usability of these systems depends not only on what exists in the DOM, but on:
- what appears when
- whether the user can discover it
- whether the action works as expected
- what the user must remember across steps
- whether the interface remains understandable as state changes accumulate

## 5. Why neurodivergent usability belongs in scope

A particularly promising research direction is to apply computer-use agents to neurodivergent UX evaluation.

Many neurodivergent barriers are not captured well by rule-based accessibility tooling alone. They may arise from:
- excessive branching
- overloaded filter systems
- weak hierarchy
- interruptions that break task continuity
- inconsistent naming
- poor progressive disclosure
- high working-memory burden
- unclear progress through a flow

A computer-use agent can help surface these issues because it interacts with the product step by step and records where continuity, clarity, or confidence breaks down.

This does **not** mean the agent can fully model neurodivergent experience. It cannot replace direct user-centered research. But it can provide a meaningful runtime signal layer that makes such problems more visible to teams.

## 6. Architecture of the computer-use subsystem

## 6.1 Browser harness

The browser harness is responsible for:
- launching the browser
- navigating pages
- stabilizing after load or action
- capturing structured state
- providing reusable interaction primitives

The captured state includes:
- URL
- title
- visible text
- discovered links
- clickable elements
- inputs
- toggles
- dialogs
- screenshots

This richer state representation is essential because a planner cannot make reliable decisions if it only sees raw text or a list of links.

## 6.2 Generic interaction layer

The interaction layer supports:
- navigation
- click by selector
- click by visible text
- type into field
- search
- apply filter
- toggle controls
- add-to-cart style actions

The important point is that these are **site-agnostic** primitives, not hardcoded scripts for one website.

## 6.3 Robustness layer

A major technical contribution is the robustness layer.

### `robust_click`
Instead of relying on a single click, the system tries:
1. standard click
2. semantic checkbox/radio handling
3. associated label click
4. text fallback
5. force click
6. JavaScript click

This matters because many modern interfaces expose:
- hidden inputs
- label-driven toggles
- intercepting overlays
- custom components

### `safe_fill`
This verifies that text entry actually succeeded.

### `safe_toggle`
This treats toggles semantically rather than as generic clicks.

### `wait_for_state_change`
This checks whether anything meaningful changed after an action.

Without this robustness layer, browser automation often becomes a brittle demo rather than a reliable evaluation system.

## 6.4 Planner-executor loop

At each step:
1. the system captures the current page
2. the planner receives goal + recent history + current state
3. the planner emits a single JSON action
4. the executor performs the action
5. the system retries if needed
6. the trace is stored
7. the loop continues

This planner-executor structure turns browser automation into a proper agent loop.

## 7. Why this is complementary to existing accessibility tools

The most important framing is complementarity.

Computer-use agents should **not** be presented as replacements for:
- WCAG-oriented tooling
- semantic inspection
- screen-reader testing
- keyboard testing
- expert accessibility review

Instead, they add value in areas such as:
- runtime discoverability
- dynamic state behavior
- flow-level task completion
- journey continuity
- cognitive burden
- neurodivergent friction signals
- evidence-rich triage for product teams

A useful mental model is:

- static scanners answer: “What rule violations exist on this page?”
- computer-use agents answer: “What happened when a realistic user tried to complete this task?”

Both are needed.

## 8. Business problems this work can solve

### 8.1 Accessibility software firms
This work can help firms explore new product directions such as:
- task-based audit reports
- dynamic flow accessibility summaries
- runtime explanation layers
- issue prioritization by journey impact
- richer customer-facing evidence

### 8.2 Product and UX teams
The system can help:
- identify where users lose confidence
- surface dynamic friction that is expensive to reproduce manually
- prioritize fixes based on task impact
- communicate UX/accessibility issues in terms engineers and PMs can act on

### 8.3 Engineering and release teams
The system can be used for:
- runtime regression checks
- pre-release journey audits
- live product validation
- better diagnosis of why a task failed in practice

## 9. Why this is a strong topic for summer research or internship work

This topic is a strong summer collaboration area because it is:

### Technically deep
It involves:
- browser automation
- agent design
- robustness engineering
- structured state capture
- multi-step reasoning
- runtime evaluation

### Scientifically interesting
It raises questions about:
- dynamic accessibility
- runtime discoverability
- cognitive usability
- neurodivergent UX
- complementarity between rule-based tools and interaction-based systems

### Practically relevant
It connects directly to the needs of:
- accessibility software firms
- HCI labs
- product quality teams
- browser testing organizations
- inclusive design researchers

## 10. Suggested summer research agenda

A realistic summer research plan could include:

### Phase 1. System refinement
- strengthen action robustness
- add keyboard-first interaction mode
- improve state validation
- improve issue structuring

### Phase 2. Evaluation design
- select representative task flows
- run baseline static accessibility tools
- run the computer-use agent on the same flows
- compare overlap and non-overlap

### Phase 3. Research analysis
- categorize issue types
- identify which issues are unique to computer-use traces
- assess usefulness through expert review
- develop a taxonomy of runtime accessibility and neurodivergent usability barriers

### Phase 4. Output
- workshop-style paper
- demo system
- technical report for partner organization
- follow-on internship or publication path

## 11. Candidate research questions

- Which classes of accessibility issues are most likely to surface only through runtime interaction?
- What kinds of dynamic failures are consistently missed by static scanners?
- Can computer-use traces provide useful signals for neurodivergent usability without overclaiming equivalence to lived experience?
- How should accessibility teams combine scanner outputs and browser-agent outputs in practice?
- What kinds of action traces are most useful to engineers and product managers?

## 12. Limitations

This work must be framed carefully.

The system does not:
- replace accessibility specialists
- replace user research
- replace assistive technology testing
- fully model neurodivergent experience
- guarantee correct action on every website

Its value lies in being:
- runtime-aware
- interaction-aware
- evidence-producing
- complementary

## 13. Why I want to pursue this jointly

I want to pursue this topic through a summer internship or joint research effort because it is one of the few areas where a project I have already built can contribute both technically and meaningfully. I have already developed the core architecture, and the next phase requires exactly the kind of guidance and context that a strong firm or research lab could provide: real accessibility workflows, rigorous evaluation expectations, and expert critique.

A collaboration with an accessibility software company would help me understand how such a system could become useful in product and customer settings. A collaboration with a university professor or lab would help me strengthen the research framing, methodology, and evaluation quality. In either setting, I would like to contribute code, experiments, system improvements, and structured analysis.

## 14. Conclusion

The updated computer-use subsystem of the Autonomous SWE Agent suggests a broader direction for accessibility and UX testing: runtime interaction should be treated as a first-class evaluation domain. Static accessibility tools remain foundational, but modern software increasingly requires complementary methods that can reason about dynamic flows, discoverability, continuity, and cognitive load across real tasks.

That makes this project more than a coding tool. It becomes a candidate research platform for studying how browser agents can help accessibility teams, UX teams, and product organizations see what static analysis alone cannot.

For a company, the opportunity is new product capability and richer triage evidence. For a professor or lab, the opportunity is a research platform for runtime accessibility and neurodivergent UX. For me, the opportunity is to spend the summer building and validating that bridge in a serious, collaborative environment.
