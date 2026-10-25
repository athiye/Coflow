from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class ActionPrompt:
    key: str
    title: str
    description: str
    pack: str
    prompt_template: str
    system_instructions: str
    recommended_route: str = "auto"

ACTION_LIBRARY = {
    "summarize_file": ActionPrompt("summarize_file","Summarize a File","Read a file and explain what it does.","core","Summarize the code in {filename} in 20 lines or less for a junior software engineer.","For a specific file, use read_file first, then synthesize a concise explanation.","cheap"),
    "debug_file": ActionPrompt("debug_file","Debug a File","Inspect a file and find the most likely bug.","core","Debug {filename} and explain the most likely bug, root cause, and smallest safe fix.","For debugging a specific file, use read_file first. Focus on high-confidence runtime or logic bugs.","mid"),
    "explain_architecture": ActionPrompt("explain_architecture","Explain Architecture","Explain repo structure and execution flow.","brownfield","Summarize the architecture of this repo and explain the main execution flow for a junior software engineer.","For repo-wide architecture prompts, list files first, then read likely entry points and key runtime modules before synthesizing.","mid"),
    "refactor_plan": ActionPrompt("refactor_plan","Refactor Plan","Create a phased refactor plan without changing behavior.","brownfield","Create a phased refactor plan without changing behavior. Focus on module boundaries, coupling, duplication, and safest first changes.","For repo-wide refactor prompts, list files first, then read likely entry points and business-logic modules before synthesizing.","mid"),
    "release_readiness": ActionPrompt("release_readiness","Release Readiness Review","Assess risk before shipping a change or feature.","release","Assess this repo or feature for release readiness. Cover missing tests, migration concerns, observability gaps, rollback risk, and customer impact.","Focus on risk, verification gaps, rollout concerns, and operational readiness.","premium"),
    "incident_prevention": ActionPrompt("incident_prevention","Incident Prevention","Find likely production failure modes before release.","release","Identify the most likely production failure modes in this codebase or feature and recommend mitigations before release.","Focus on reliability, state handling, bad assumptions, and missing safeguards.","premium"),
    "prd_to_architecture": ActionPrompt("prd_to_architecture","PRD to Architecture","Turn requirements into architecture and implementation plan.","greenfield","Turn this product requirement into architecture, domain model, APIs, testing strategy, and a phased implementation plan.","Act like a staff engineer translating product intent into a practical delivery plan.","premium"),
    "brownfield_impact": ActionPrompt("brownfield_impact","Brownfield Impact Analysis","Assess which modules and flows a change touches.","brownfield","If we change this behavior, identify which files, modules, tests, APIs, and downstream systems are most likely affected.","Use repo discovery first, then synthesize a concrete impact map.","mid"),
    "security_review": ActionPrompt("security_review","Security Review","Review for secrets, auth, validation, and abuse paths.","release","Perform a security review of this repo. Focus on input validation, auth, secrets handling, command execution, and unsafe defaults.","Be concrete and rank findings by severity and exploitability.","premium"),
    "performance_review": ActionPrompt("performance_review","Performance Review","Find performance bottlenecks and scaling risks.","release","Review this codebase for performance bottlenecks and rank the top issues by likely impact.","Focus on repeated I/O, hot paths, blocking operations, and scaling bottlenecks.","mid"),
    "onboarding_explainer": ActionPrompt("onboarding_explainer","Onboarding Explainer","Explain the codebase to a new engineer.","brownfield","Explain this codebase to a new engineer. Cover what it does, where to start reading, and the main execution flow.","List files first, then read likely key files, then synthesize a beginner-friendly explanation.","mid"),
    "pm_repo_analysis": ActionPrompt("pm_repo_analysis","Product Manager Repo Analysis","Infer user value, journeys, risks, and roadmap from the repo.","product","Analyze this repo like a product manager. Explain what problem it solves, who the likely users are, what features exist today, the main user journeys, the biggest UX and product risks, the top missing capabilities, and a phased roadmap for what to build next.","Read enough core runtime and UI files to infer product behavior. Synthesize from product and engineering perspectives.","premium"),
    "reverse_prd": ActionPrompt("reverse_prd","Reverse PRD from Repo","Generate a PRD inferred from the codebase.","product","Analyze this repo and generate a reverse PRD. Infer the product vision, target users, jobs to be done, key user journeys, implemented features, non-functional requirements, technical constraints, known gaps, risks, and a suggested roadmap. Ground the PRD in the actual codebase and clearly separate confirmed functionality from inferred intent.","For reverse PRD generation, first list repository files, then read likely product-defining and runtime files such as README.md, MVP specs, requirements, package manifests, backend entry points, frontend entry points, templates/pages, API handlers, and key domain modules.","premium"),
    "ui_reverse_prd": ActionPrompt("ui_reverse_prd","Reverse PRD from Live UI","Generate a reverse PRD from the running product experience.","ui","Inspect the running application and generate a reverse PRD grounded in the live product experience. Infer product overview, users, jobs to be done, key journeys, confirmed visible features, inferred feature intent, UX gaps, operational constraints, and roadmap.","Use the browser harness to open the provided URL, capture key screens, extract visible UI text, and synthesize a PRD grounded in observed behavior. Prefer observation over guessing.","premium"),
    "ui_release_audit": ActionPrompt("ui_release_audit","UI Release Auditor","Walk key live workflows and produce a release audit.","ui","Validate the core user journeys in staging before release. Walk the key workflows, verify expected UI states, capture user-visible defects, and return a release audit grouped by severity and customer impact. Do not take destructive actions.","Use browser automation to inspect the live UI, capture screenshots, and summarize defects, blockers, and release risk.","premium"),
    "ui_incident_repro": ActionPrompt("ui_incident_repro","UI Incident Reproduction","Reproduce a user-reported issue in the live application.","ui","Reproduce this user-reported issue in the application UI. Identify the exact failing step, capture visible evidence, and produce a triage note with suspected frontend, backend, auth, or configuration ownership.","Use the browser harness to walk the app carefully. Stop before destructive actions. Capture evidence and uncertainty explicitly.","premium"),
    "admin_console_verifier": ActionPrompt("admin_console_verifier","Admin Console Verifier","Check internal console settings and configuration visually.","ui","Use the internal admin console to verify the release configuration for feature X. Check environment flags, rollout settings, required content/templates, and logging or alerting surfaces. Do not change settings. Report mismatches with evidence.","Use live UI inspection. Prefer verification and evidence collection over inference.","premium"),
    "ux_accessibility_review": ActionPrompt("ux_accessibility_review","UX and Accessibility Review","Review the live product for usability and accessibility issues.","ui","Review this application as a first-time user and accessibility-conscious PM. Identify weak visual hierarchy, confusing flows, inaccessible interactions, hidden actions, and error states that may reduce task completion.","Use live browser inspection and screenshots. Emphasize customer-facing friction.","premium"),
    "brownfield_flow_mapper_ui": ActionPrompt("brownfield_flow_mapper_ui","Brownfield Flow Mapper","Map how an existing live app actually behaves.","ui","Walk the running application and map the top navigation and user flows. Produce a brownfield flow map showing key screens, likely journey transitions, visible entities, and probable ownership boundaries.","Use browser capture to build a flow-oriented explanation of the live product.","premium"),
    "onboarding_capture_ui": ActionPrompt("onboarding_capture_ui","Onboarding Capture from Live App","Create onboarding notes from the actual first-run experience.","ui","Walk the first-run or first-visit experience of the application and produce onboarding documentation with steps, screens, likely confusion points, and screenshots to include in a help guide.","Use browser capture to document what a new user actually sees.","premium"),
    "visual_regression_audit": ActionPrompt("visual_regression_audit","Visual Regression Audit","Inspect the live UI for visual regressions and broken states.","ui","Walk the top visible user journeys in the live application and identify layout breaks, hidden controls, clipped content, modal issues, and other user-visible regressions. Group findings by severity and customer impact.","Use browser capture and visual/DOM inspection of the current live UI.","premium"),
    "api_contract_review": ActionPrompt("api_contract_review","API Contract Review","Review frontend/backend contract drift and interface risk.","release","Review the API contract in this repo and identify likely frontend/backend mismatches, request/response drift, and missing validation.","Focus on handlers, clients, payload shapes, and error handling.","mid"),
    "legacy_modernization_plan": ActionPrompt("legacy_modernization_plan","Legacy Modernization Plan","Create a phased modernization plan for a brownfield system.","brownfield","Assess this legacy codebase and propose a phased modernization plan that improves reliability, testability, observability, and deployment velocity without destabilizing production behavior.","Focus on safest first changes and modernization sequencing.","premium"),
    "test_strategy": ActionPrompt("test_strategy","Test Strategy Generator","Create a risk-based testing plan for a repo or feature.","release","Generate a risk-based test strategy for this repo or feature, including unit, integration, contract, and end-to-end testing priorities.","Focus on highest-risk flows and release confidence.","mid"),
}

PROMPT_ACTIONS = [asdict(action) for action in ACTION_LIBRARY.values()]

COMPUTER_USE_ACTIONS = {
    "ui_reverse_prd",
    "ui_release_audit",
    "ui_incident_repro",
    "admin_console_verifier",
    "ux_accessibility_review",
    "brownfield_flow_mapper_ui",
    "onboarding_capture_ui",
    "visual_regression_audit",
}

def get_action_prompt(action_key: str | None):
    if not action_key:
        return None
    return ACTION_LIBRARY.get(action_key)

def is_computer_use_action(action_key: str | None) -> bool:
    return bool(action_key and action_key in COMPUTER_USE_ACTIONS)
