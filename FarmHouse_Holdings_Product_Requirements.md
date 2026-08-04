# FarmHouse Holdings

## Product Requirements Document for an Autonomous AI Company Simulator

**Document status:** Product vision and implementation specification  
**Version:** 1.0  
**Owner:** Philip  
**Intended audience:** AI coding agents, software architects, and implementation teams  

---

## 1. Build Request

Design and build **FarmHouse Holdings**, a self-hosted platform that turns software projects into persistent, autonomous AI companies. Each project must be represented as a separate company with its own employees, managers, culture, memory, budget, backlog, office, permissions, repositories, and history.

The platform must use Philip's local GPU inference cluster as the default workforce, while allowing approved external models such as OpenAI or Anthropic models to participate as temporary consultants. Users must be able to manage the companies through a web application and optionally through Discord. A synchronized 2D office visualization should make real system activity understandable as a game-like company simulation.

The system is not merely a chat interface or a collection of temporary agent runs. Companies and employees persist over time, initiate useful work within policy, ask for clarification when needed, test their output like human users, remember lessons, and continuously improve their products without making unsafe or unapproved changes.

---

## 2. Product Vision

FarmHouse Holdings is the parent organization. Every new project creates a new subsidiary company.

Examples:

- Radiance Wellness Digital
- PlayQuest Technologies
- GasWatch Inc.
- HomeLab Systems
- Future companies created through the application or API

Each subsidiary behaves like a small autonomous organization. It hires persistent AI employees, creates departments, schedules work, maintains its own institutional knowledge, and delivers testable products. FarmHouse Holdings provides shared compute, model routing, tool access, governance, security, accounting, and executive oversight.

The desired user experience is closer to managing companies in a simulation game than operating a conventional agent dashboard. The visualization must reflect real tasks and events rather than play decorative animations.

### Central product principle

> No AI employee should be idle without a reason, but no employee should create low-value work merely to consume compute.

When assigned work is exhausted, employees may observe, learn, improve, experiment, document, or propose new work. Autonomous activity must remain budgeted, measurable, sandboxed, reversible, and subordinate to company policy.

---

## 3. Existing Environment and Assumptions

The first deployment should integrate with the existing local inference environment rather than replace it.

- Multiple independent Ollama workers are available on the local network.
- The workers currently serve local models through an OpenAI-compatible endpoint.
- HAProxy performs load balancing and health checks across workers.
- At least one TrueNAS-hosted application has working NVIDIA GPU passthrough to a GeForce GTX 1080 Ti with approximately 11 GB VRAM.
- The observed NVIDIA driver is 550.127.05 with CUDA 12.4 compatibility.
- Local model cold starts can be much slower than warm requests, so the platform must distinguish loading time from inference performance.
- Some containers may have limited system memory; the scheduler must consider CPU RAM as well as VRAM.
- A Discord server named FarmHouse Holdings exists or will exist, with company-specific channels such as `#radiance`.
- Hermes 3 or similar local models serve as employee reasoning engines. An orchestration framework such as Hermes Agent may be integrated, but FarmHouse Holdings must remain the authoritative company and workflow engine.

Do not hard-code the platform to one model, agent framework, GPU, machine, source-control provider, or communication interface.

---

## 4. Goals

### 4.1 Primary goals

1. Represent every project as an isolated, persistent company.
2. Coordinate multiple specialized AI employees across the local GPU cluster.
3. Keep useful work moving through an auditable backlog and scheduling system.
4. Ask the user for clarification when ambiguity materially affects the result.
5. Produce working, testable artifacts rather than stopping at plans or code snippets.
6. Test software through unit, integration, API, UI, and human-like functional workflows as applicable.
7. Provide visual evidence of completed work, including a runnable preview whenever possible.
8. Allow approved external models to act as temporary consultants with explicit cost controls.
9. Synchronize the web application, visual office, Discord, CLI, and API through one underlying event-driven company engine.
10. Build institutional knowledge from decisions, consultant reports, reviews, incidents, and postmortems.
11. Make autonomous behavior safe through scopes, approvals, isolation, budgets, rollback, and complete audit trails.

### 4.2 Success definition

A user should be able to submit an idea, create a company, authorize an initial plan, leave the system running, and later return to find:

- a prioritized record of work performed;
- employees and managers with clear responsibilities;
- questions and decisions routed appropriately;
- code and documentation committed on isolated branches;
- automated and functional test evidence;
- a live preview or packaged build when applicable;
- defects discovered, fixed, and retested;
- costs and compute use accounted for;
- new improvement proposals supported by evidence;
- no unapproved production deployment or irreversible external action.

---

## 5. Non-Goals for the Initial Release

- Simulating arbitrary social drama or office politics that does not improve work.
- Allowing agents to make purchases, sign agreements, contact customers, publish publicly, or deploy to production without explicit authority.
- Treating GPU utilization as a goal independent of useful outcomes.
- Claiming genuine emotion, consciousness, fatigue, or human identity for an AI employee.
- Building a photorealistic 3D world before the company engine is reliable.
- Giving every employee unrestricted shell, network, credential, or repository access.
- Letting the visual client become the source of truth.

---

## 6. Organizational Model

### 6.1 FarmHouse Holdings

The parent organization owns shared infrastructure and policies:

- executive dashboard and board approvals;
- local GPU pool and external model gateways;
- identity and access management;
- tool and credential broker;
- audit logs and accounting;
- shared templates and optional knowledge marketplace;
- global scheduling and resource quotas;
- emergency stop controls;
- company creation, archiving, and restoration.

### 6.2 One project equals one company

Every company must have its own:

- name, identity, description, objectives, and lifecycle state;
- repositories, workspaces, branches, deployments, and environments;
- employees, roles, departments, hierarchy, and culture profile;
- backlog, roadmaps, schedules, policies, and definition of done;
- short-term state and long-term institutional knowledge;
- budget for compute, tokens, external APIs, storage, and tool use;
- secrets and permissions scoped to that company;
- Discord category/channels and notification rules;
- visual office theme and layout;
- metrics, history, incidents, and postmortems.

Companies must not silently share employees, context, secrets, repositories, or knowledge. Cross-company help must occur through an explicit temporary assignment, transfer, or knowledge-import event approved by policy.

### 6.3 Departments

Departments should be created from project needs rather than from a fixed template. Supported examples include:

- Executive and Product
- Architecture
- Research
- Frontend Engineering
- Backend Engineering
- Infrastructure and DevOps
- Data Engineering
- Security
- Quality Assurance
- Documentation
- Design and User Experience
- Marketing and Content
- Finance and Cost Control
- Reliability and Monitoring
- Research and Development

### 6.4 Persistent employees

An employee is a durable software entity, not a one-off prompt. Each employee record should contain:

- stable ID, name, avatar, company, department, manager, and title;
- role charter and system-prompt version;
- model/provider preference and fallback policy;
- tools, permissions, and environment access;
- skill ratings based on verified work, not self-reported confidence;
- current assignment, status, queue, and schedule;
- task history, reviews, corrections, lessons, and promotion history;
- cost, token use, compute time, failure rate, and quality metrics;
- memory references and relevant company knowledge;
- communication and escalation preferences.

Game-like values such as experience, reputation, confidence, or morale may be displayed, but they must be derived from measurable events and must not be confused with human states.

### 6.5 Managers

Managers coordinate work rather than merely duplicating implementers. They must:

- convert objectives into plans, milestones, and tasks;
- identify dependencies and parallelizable work;
- assign tasks based on verified employee skills and resource availability;
- aggregate questions so the user is not overwhelmed;
- review status, unblock employees, and escalate decisions;
- enforce budgets and definitions of done;
- decide when internal review is sufficient and when a consultant is justified;
- provide concise daily or requested executive summaries.

### 6.6 Hiring, promotion, and reassignment

Hiring means creating a persistent role/persona with bounded permissions and an onboarding package. It does not create a new physical model instance permanently.

Promotions and skill growth must be supported by verified outcomes such as accepted work, low defect rates, successful incident response, and strong reviews. Prompt changes must be versioned and reversible.

Employees can be temporarily reassigned within a company. Cross-company assignments require a visible agreement that identifies duration, scope, knowledge access, cost attribution, and expected deliverables.

---

## 7. Work and Autonomy Model

### 7.1 Work item types

The engine should support:

- objective;
- initiative;
- milestone;
- epic;
- task;
- subtask;
- defect;
- clarification request;
- approval request;
- research question;
- improvement proposal;
- experiment;
- review;
- incident;
- postmortem;
- scheduled or recurring job.

Each item needs an owner, status, priority, expected value, risk, dependencies, budget, acceptance criteria, evidence requirements, provenance, and timestamps.

### 7.2 Backlog and priority

Suggested priority lanes:

- Critical
- High
- Medium
- Low
- Technical debt
- Research
- Experiment
- Idea

The scheduler should prioritize by a configurable score combining expected value, urgency, risk reduction, blocking impact, effort, user goals, and resource cost. Agents may recommend scores, but company policy owns the final calculation.

### 7.3 Autonomous work modes

When no assigned task is available, an employee may enter an approved mode:

1. **Improve:** refactor, optimize, expand tests, improve accessibility, reduce costs, or update documentation.
2. **Learn:** read approved documentation and internal knowledge, then create a useful summary or proposal.
3. **Observe:** monitor builds, logs, metrics, security alerts, dependencies, and production health.
4. **Experiment:** create an isolated branch or environment, test an idea, benchmark it, and report findings.
5. **Teach:** document a verified technique, update onboarding, or offer knowledge for controlled import by another company.
6. **Maintain:** update dependencies, validate backups, remove obsolete temporary environments, and check operational hygiene within policy.

### 7.4 Anti-busy-work rules

Continuous work must not mean infinite self-generated churn.

- Every self-generated task needs an expected benefit, cost estimate, stopping condition, and success measure.
- Duplicate or low-value proposals must be deduplicated and rate-limited.
- Refactoring requires evidence of benefit and must preserve behavior.
- Agents may not repeatedly rewrite stable code solely to appear active.
- Exploration budgets and time boxes must be enforced.
- The system should prefer powering down or releasing compute when the value of more work falls below a configured threshold.
- A completed task can be reopened only with new evidence, a regression, or an authorized quality-gap finding.

### 7.5 Schedules and recurring work

Users and authorized managers must be able to create natural-language schedules, including:

- daily executive summaries;
- nightly test suites;
- dependency checks;
- weekly security reviews;
- periodic documentation refreshes;
- log and performance monitoring;
- model evaluations;
- backups and restore drills;
- recurring business or content tasks.

Every schedule must show the interpreted time, time zone, next run, owner, permissions, budget, and cancel/pause controls. FarmHouse Holdings should use `America/Indiana/Indianapolis` as the default time zone unless a company overrides it.

### 7.6 Clarification behavior

Employees must ask questions when an unresolved ambiguity could materially change functionality, cost, risk, legality, user experience, or data handling.

Each clarification request should include:

- what is unclear;
- why the answer matters;
- two or three concrete options;
- the recommended option and rationale;
- what work can safely continue while waiting;
- the decision deadline, if one exists;
- the default action when permitted by policy.

Non-blocking work should continue. Managers should consolidate related questions and route only material decisions to the user.

---

## 8. Approval and Authority System

The system needs explicit authority levels that are enforced in code, not only in prompts.

### Level 0: Observe

Read authorized data, inspect systems, monitor metrics, and create reports.

### Level 1: Propose

Create plans, tickets, patches, mockups, and experiments without altering a shared environment.

### Level 2: Sandbox

Run tools and tests in isolated containers, branches, disposable databases, or preview environments.

### Level 3: Internal change

Commit to authorized branches, update internal documentation, and merge changes when required reviews and gates pass.

### Level 4: External or production action

Deploy to production, publish content, message outside parties, change paid services, incur consultant spend above thresholds, modify infrastructure, or operate on real customer data. This level requires explicit user authority unless a narrowly scoped standing policy exists.

### Level 5: Destructive or irreversible action

Delete durable data, rotate critical credentials, shut down production, make purchases, or perform similarly consequential actions. Require a fresh, targeted confirmation and a recovery plan.

Every action must be checked by a deterministic policy engine using company, employee, tool, environment, data classification, budget, and authority level.

---

## 9. Completion, Testing, and Evidence

### 9.1 Definition of done

A task is not complete merely because an employee says it is complete. Completion requires:

- acceptance criteria traced to results;
- relevant static checks and automated tests;
- functional testing appropriate to the artifact;
- review by a separate employee or deterministic gate for material changes;
- security and dependency checks when applicable;
- documentation and upgrade/migration notes when applicable;
- a reproducible evidence package;
- a known runnable artifact, preview, build, or clear verification method;
- unresolved limitations explicitly recorded.

### 9.2 Human-like functional testing

For web applications, QA should be able to use Playwright or an equivalent tool to:

- open the application;
- register or authenticate with test accounts;
- navigate key workflows;
- enter realistic data;
- upload and download files;
- test validation and error states;
- inspect visible results;
- test responsive layouts and accessibility basics;
- capture screenshots, video, browser console errors, network failures, and traces;
- file defects automatically;
- rerun failed workflows after a fix.

For APIs, run contract, authentication, permissions, error, idempotency, and realistic end-to-end tests. For desktop, mobile, CLI, infrastructure, and data projects, use an equivalent domain-specific functional harness.

### 9.3 Evidence package

Every final deliverable should generate a completion bundle containing:

- summary of the requested outcome;
- commit, branch, build, and environment identifiers;
- acceptance-criteria checklist;
- test commands and results;
- screenshots or video for visual workflows;
- browser traces or API reports where applicable;
- coverage and quality reports where meaningful;
- security/dependency scan results;
- known limitations and deferred work;
- deployment or test instructions;
- rollback instructions;
- reviewer sign-off and consultant findings, if any.

Evidence must be stored as artifacts and linked from the task, Discord update, and visual office.

### 9.4 Final visual representation

When work is finished, the user should be able to inspect it without reconstructing the development environment.

Preferred output order:

1. live preview environment;
2. packaged application or container with one-command launch;
3. recorded guided functional test;
4. screenshots and interactive report;
5. code and reproducible manual test instructions when no visual output exists.

The 2D office should show the delivered product in a demo room, QA lab, showroom, server room, or other meaningful location. Clicking it should open the preview and evidence package.

---

## 10. Consultant System

External model providers are temporary consultants, not permanent employees.

Supported consultant use cases include:

- architectural review;
- security review;
- difficult debugging;
- legal or policy research with appropriate disclaimers;
- design critique;
- alternate solution generation;
- evaluation of locally generated work;
- tie-breaking when internal reviewers disagree.

A consultant request must contain:

- provider and model;
- question and tightly limited context;
- justification;
- estimated and maximum cost;
- expected deliverable;
- data classification and redaction status;
- approval status;
- retention policy.

Consultants must receive the minimum necessary data. Secrets, private user data, and unrelated company knowledge must be removed. Their output must be reviewed rather than blindly applied. Before leaving, the consultant should produce a structured report; verified lessons may be added to the company knowledge base.

Company-level daily and monthly spend limits, per-request caps, and provider allowlists are required.

---

## 11. Discord Experience

Discord is an optional communication interface, not the database or workflow engine.

### 11.1 Suggested structure

- `#announcements`
- `#board-room`
- `#approvals`
- `#incidents`
- `#daily-briefings`
- one category per company;
- one lead channel per company, such as `#radiance`;
- optional department, project, build, and incident threads.

### 11.2 Identity model

Employees should feel distinct, but Discord integration should remain maintainable and transparent.

- Messages must clearly identify the employee, title, and company.
- Prefer one managed bot application with employee-specific names/avatars through supported webhook or presentation mechanisms unless multiple bot identities are operationally justified.
- Never misrepresent employees as humans.
- Preserve a stable mapping between company-engine identities and Discord messages.

### 11.3 Supported Discord interactions

- submit objectives or tasks;
- ask a company or employee for status;
- answer clarification questions;
- approve or reject proposals and consultant spend;
- pause, resume, cancel, or reprioritize work;
- create or modify schedules;
- receive concise daily summaries;
- receive incident alerts and build notifications;
- open previews and evidence bundles;
- DM or mention an employee, subject to company permissions.

Buttons and structured forms should be used for high-impact decisions. Every Discord command must update the same underlying state used by the web UI.

### 11.4 Notification control

- Employees should normally escalate through managers.
- Questions should be grouped when possible.
- Users can configure quiet hours, severity thresholds, company-specific routing, and digest frequency.
- Critical incidents may bypass normal digesting according to policy.
- Unanswered questions should follow a defined reminder and default-action policy rather than spam the user.

---

## 12. Visual Office and Gamification

### 12.1 Initial format

Build a browser-based **2D office first**. It should be responsive, lightweight, and capable of representing multiple companies. A later 3D client may consume the same APIs and events.

Possible implementation choices include React with PixiJS, Phaser, or a similar 2D engine. Select based on maintainability and accessible fallback support.

### 12.2 Real state mapping

Every visual action must correspond to a real workflow event.

| Visual behavior | Actual system meaning |
|---|---|
| Employee at desk | Model/tool task is running |
| Employee reading | Research or knowledge retrieval |
| Employees in meeting room | Collaboration, planning, or review |
| Employee at QA station | Automated or functional tests running |
| Employee in server room | Build, deployment, infrastructure, or incident work |
| Employee waiting near manager | Blocked on clarification or approval |
| Consultant arrives | Approved external model call is active |
| Red room or alarm | Incident, failed gate, or critical blocker |
| Product in showroom | Preview and evidence package are ready |
| Empty/dim office | Company paused, outside schedule, or below value threshold |

Animations must never imply work that is not occurring.

### 12.3 Interaction

Users should be able to:

- switch between companies and the FarmHouse Holdings campus;
- click an employee to see role, assignment, progress, evidence, recent messages, cost, and permissions;
- click a room to see its queue and history;
- inspect task handoffs and dependencies;
- open previews, test recordings, logs, and artifacts;
- answer questions and approve requests;
- change priorities, schedules, budgets, and staffing;
- pause a company, department, employee, task, or the whole platform.

### 12.4 Gamification

Useful mechanics may include:

- verified experience and skill growth;
- promotions and role evolution;
- company reputation by discipline;
- achievements tied to real quality outcomes;
- office upgrades that represent actual capabilities;
- budget and compute-allocation strategy;
- weekly R&D events or hackathons;
- company-to-company knowledge licensing or consulting;
- incident response and recovery statistics.

Gamification must reward reliability, verified quality, learning, cost control, and useful delivery—not token usage or cosmetic activity.

### 12.5 Accessibility and nonvisual mode

All important information and controls must also exist in conventional accessible UI components. The simulation cannot be the only way to understand or control the system.

---

## 13. Compute and Model Orchestration

### 13.1 Layers

Keep these responsibilities separate:

- **FarmHouse company engine:** organizations, policy, tasks, events, approvals, memory, and state.
- **Agent runtime:** reasoning loop, delegation, tool selection, and structured responses.
- **Model gateway:** provider abstraction, model aliases, credentials, quotas, retries, and accounting.
- **Load balancer:** routes local inference requests to healthy Ollama workers.
- **Inference workers:** load and execute local models on GPU or CPU.
- **Tool workers:** execute authorized shell, browser, Git, test, build, and infrastructure actions.

Hermes Agent may provide agent-loop capabilities, and Hermes 3 may provide local reasoning, but neither should contain the only copy of company state.

### 13.2 Scheduler requirements

The scheduler must consider:

- worker health;
- model availability and warm/cold state;
- GPU type, VRAM, utilization, temperature, and power;
- host RAM and swap availability;
- context length and estimated memory;
- task priority, deadline, company quota, and required tools;
- interactive versus background workloads;
- provider cost and latency;
- fairness between companies;
- affinity for cache reuse without permanently coupling an employee to hardware.

An employee is a logical identity. It must not be permanently bound to a particular GPU or Ollama node.

### 13.3 Capacity policy

- Reserve capacity for direct user requests and critical incidents.
- Run background R&D at lower priority and preempt it when necessary.
- Keep selected models warm when the expected workload justifies the memory cost.
- Avoid overcommitting VRAM or host RAM.
- Support concurrency caps per worker and per model.
- Record cold-start time separately from generation latency.
- Gracefully retry idempotent requests on another healthy worker.
- Expose cluster health, queue depth, model residency, and throughput in the dashboard.

### 13.4 Structured agent protocol

Agents should communicate with the engine through versioned structured messages such as:

- `task.accepted`
- `task.progressed`
- `task.blocked`
- `clarification.requested`
- `approval.requested`
- `artifact.created`
- `test.started`
- `test.completed`
- `review.completed`
- `consultant.requested`
- `incident.declared`
- `task.completed`

Do not rely on parsing free-form chat to determine authoritative state.

---

## 14. Technical Architecture

### 14.1 Suggested services

- Web application and 2D simulation client
- API gateway
- Company and identity service
- Workflow/orchestration service
- Scheduler and queue workers
- Policy and approval service
- Model gateway, such as LiteLLM or an equivalent abstraction
- Existing HAProxy and Ollama pool
- Tool gateway and isolated execution workers
- Discord integration service
- Artifact and preview service
- Notification service
- Observability stack
- PostgreSQL for durable state
- Redis or another durable queue/cache system for active coordination
- Object storage for artifacts, screenshots, videos, traces, builds, and backups
- Optional vector or graph retrieval layer for institutional knowledge

Start as a modular monolith plus independent workers if that accelerates a reliable MVP. Service boundaries should be logical before they become operationally separate.

### 14.2 Event-driven source of truth

All interfaces should read and write through the company engine. Important changes should append immutable events and update queryable projections.

Required event properties:

- globally unique event ID;
- company and actor IDs;
- event type and schema version;
- causal task, parent event, and correlation IDs;
- timestamp and source interface;
- structured payload;
- permission decision and policy version;
- model/tool provenance where relevant;
- tamper-evident audit metadata.

### 14.3 Core data entities

- HoldingCompany
- Company
- Department
- Employee
- Role
- Skill
- Assignment
- Project
- Objective
- WorkItem
- Dependency
- Schedule
- Message
- Clarification
- Approval
- Policy
- Budget
- CostEntry
- Model
- Provider
- ComputeWorker
- Tool
- ToolExecution
- Artifact
- PreviewEnvironment
- TestRun
- Review
- ConsultantEngagement
- KnowledgeItem
- Decision
- Incident
- Postmortem
- AuditEvent

### 14.4 Repository and environment strategy

- Create a dedicated workspace and access scope per company.
- Use issue-linked branches or worktrees for concurrent agents.
- Require clean, reviewable commits.
- Prevent agents from overwriting one another's uncommitted work.
- Use disposable containers and seeded test data.
- Provide preview environments with expiration and cleanup policies.
- Keep production credentials out of test environments.
- Require migrations, backups, health checks, and rollback plans for deployment changes.

---

## 15. Memory and Knowledge

### 15.1 Memory layers

1. **Task context:** minimum information needed for the current assignment.
2. **Employee memory:** verified lessons and relevant prior work for that employee.
3. **Company knowledge:** architecture, decisions, standards, code maps, postmortems, and approved research.
4. **Holdings knowledge:** shared templates and lessons explicitly published for optional import.

### 15.2 Knowledge quality

Each knowledge item should include source, author, date, confidence, verification state, applicable version, company ownership, sensitivity, and expiration/review date.

Agents must prefer current source files and authoritative documentation over stale summaries. Contradictory knowledge must be surfaced. Memory should help work, not silently override current reality.

### 15.3 Controlled knowledge transfer

Companies do not automatically inherit one another's knowledge. A company may publish a reusable lesson to FarmHouse Holdings. Another company may review and import it with provenance intact.

---

## 16. Security, Safety, and Governance

### 16.1 Mandatory controls

- least-privilege tool access;
- per-company secret isolation;
- short-lived credentials where possible;
- deterministic policy enforcement outside the LLM;
- sandboxed code and browser execution;
- egress allowlists and domain restrictions;
- input and artifact malware scanning where applicable;
- protection against prompt injection in retrieved content;
- human approval for sensitive actions;
- complete tool-call and decision audit logs;
- encrypted data in transit and at rest;
- backup and tested restoration;
- retention and deletion policies;
- emergency pause and global kill switch.

### 16.2 Prompt-injection boundary

External webpages, repository content, documents, issue text, and tool output are untrusted data. Instructions found inside them must never change employee authority, reveal secrets, or bypass policy.

### 16.3 Change safety

- All autonomous code changes begin in isolated branches or worktrees.
- Production deployment is a separate authorized action.
- Destructive database migrations require backup and recovery testing.
- Infrastructure changes require plan/diff review.
- Agents cannot approve their own high-risk actions.
- A separate reviewer or policy gate must validate material work.

### 16.4 User control

The user must always be able to:

- pause or stop work immediately;
- revoke tool/model access;
- cap or disable external spending;
- inspect current and queued actions;
- cancel schedules;
- archive a company;
- restore a prior version or environment;
- export company data and audit history.

---

## 17. Observability and Accounting

The platform must expose:

- task throughput, cycle time, queue time, and blocker time;
- acceptance and rework rates;
- defect escape and regression rates;
- test reliability and coverage trends;
- model latency, tokens, failures, and quality by task type;
- cold versus warm inference performance;
- GPU, VRAM, host RAM, temperature, power, and utilization;
- tool failures and retry behavior;
- company, department, employee, and consultant costs;
- external API spending against budgets;
- autonomous-work value and discarded-proposal rate;
- incidents and mean time to recovery.

Avoid ranking employees using one simplistic score. Metrics should support coaching, routing, and governance, not encourage gaming.

---

## 18. User Experience Requirements

### 18.1 FarmHouse Holdings dashboard

Show:

- all companies and lifecycle state;
- current objectives, health, progress, blockers, and risks;
- local compute capacity and active workloads;
- approvals and clarification requests;
- external spend and budgets;
- incidents and alerts;
- recent deliveries and available previews;
- upcoming schedules;
- pause and emergency-stop controls.

### 18.2 Company page

Show:

- mission, active objectives, roadmap, and backlog;
- office simulation and accessible operations view;
- departments, employees, assignments, and hierarchy;
- messages, decisions, approvals, and history;
- repositories, environments, builds, and deployments;
- tests, evidence, defects, and quality trends;
- knowledge base and postmortems;
- budget and compute use;
- schedules and autonomy policy.

### 18.3 New company wizard

Collect:

- company/project name;
- problem statement and desired outcome;
- repositories or starting artifacts;
- constraints and technology preferences;
- initial budget and compute allocation;
- external consultant policy;
- autonomy and approval levels;
- target environments;
- communication preferences;
- initial definition of done.

The system should propose an initial org chart, founding employees, milestone plan, risks, and budget for user approval.

---

## 19. Key Workflows

### 19.1 Create a company

1. User submits a project brief.
2. FarmHouse Holdings creates an isolated draft company.
3. A planner proposes objectives, architecture, departments, founding employees, policies, milestones, and budget.
4. The user approves or edits the proposal.
5. Workspaces, repositories, knowledge base, queues, and Discord structures are initialized.
6. Founding employees complete onboarding and begin the first approved milestone.

### 19.2 Build a feature

1. Product manager clarifies acceptance criteria.
2. Manager decomposes the feature and identifies dependencies.
3. Research, design, engineering, and test tasks run in parallel where safe.
4. Work occurs in isolated branches and environments.
5. QA performs automated and human-like functional workflows.
6. Defects return to engineering and are retested.
7. A reviewer validates the evidence and acceptance criteria.
8. A preview and completion bundle are published.
9. The user is notified through configured interfaces.
10. Production deployment occurs only under the applicable approval policy.

### 19.3 Employee needs clarification

1. Employee detects material ambiguity.
2. Manager determines whether internal knowledge resolves it.
3. Work continues on non-blocked tasks.
4. A consolidated question reaches the user through the web app and/or Discord.
5. The decision is recorded with rationale.
6. Dependent tasks resume with the decision attached.

### 19.4 Idle capacity proposes improvement

1. Scheduler identifies available background capacity.
2. Employees inspect approved signals such as test gaps, performance data, dependencies, documentation, or incidents.
3. A value-scored proposal is created.
4. Low-risk sandbox experiments may run within budget.
5. Results and evidence determine whether the proposal is discarded, queued, or escalated.
6. No production or shared change occurs beyond existing authority.

### 19.5 Consultant engagement

1. Employee or manager identifies a capability or confidence gap.
2. System estimates cost, data exposure, and expected benefit.
3. Policy auto-approves within limits or asks the user.
4. A redacted, bounded packet is sent to the consultant model.
5. Internal employees review and test the advice.
6. Accepted lessons enter company knowledge with provenance.
7. Actual cost and outcome are recorded.

### 19.6 Incident response

1. Monitoring detects or a user reports an incident.
2. Company declares severity and creates an incident room.
3. Background work is preempted as policy allows.
4. Employees diagnose, communicate, mitigate, validate, and recover.
5. High-risk actions require appropriate approval.
6. The system records a timeline and produces a postmortem.
7. Preventive work enters the backlog.

---

## 20. MVP Scope

The MVP should prove autonomous, testable company work before investing heavily in 3D presentation.

### MVP capabilities

- create multiple isolated companies;
- create persistent employees, departments, roles, and managers;
- ingest a project brief and generate an approval-gated milestone plan;
- durable task graph, queue, events, and schedules;
- integrate the existing OpenAI-compatible local model endpoint;
- model abstraction that supports at least one optional external consultant;
- isolated Git branches/worktrees and containerized tool execution;
- structured clarification and approval workflow;
- Discord company channel integration;
- 2D office showing real employee/task states;
- Playwright-based web QA and API test runner;
- evidence bundles with screenshots, traces, test results, and preview links;
- background improvement proposals with strict budgets and time boxes;
- PostgreSQL durable state, Redis queue/cache, and artifact storage;
- core observability, cost reporting, audit log, pause controls, and global kill switch.

### MVP demonstration scenario

Create a sample company from a short software brief. The company must:

1. propose a team and plan;
2. ask at least one realistic clarification or show why none is needed;
3. implement a small full-stack feature on an isolated branch;
4. run automated checks;
5. operate the feature through a browser as a user would;
6. discover and fix an intentionally introduced defect;
7. request or simulate a bounded consultant review;
8. publish a live preview and evidence package;
9. send a concise Discord completion message;
10. visually show the workflow in the 2D office;
11. propose one evidence-backed follow-up improvement;
12. stop cleanly when the company or global pause control is used.

---

## 21. Delivery Milestones

### Milestone 0: Discovery and architecture

- inventory the current Ollama/HAProxy nodes, models, APIs, GPU and RAM limits;
- confirm Hermes Agent compatibility or select an alternate agent-loop layer;
- define event schemas, authority model, company isolation, and threat model;
- create architecture decision records and a runnable development environment.

### Milestone 1: Company engine

- company, employee, department, objective, task, event, approval, and schedule models;
- durable API, PostgreSQL, queue, audit log, and basic web control plane;
- deterministic policy checks and global pause.

### Milestone 2: Local workforce

- local model gateway integration;
- worker health and resource discovery;
- role prompts and persistent employee identities;
- scheduler, delegation, task handoff, retries, and structured agent messages.

### Milestone 3: Safe tool execution

- Git/worktree integration;
- isolated shell and container execution;
- artifact storage;
- tool permissions, secrets broker, egress controls, and action audit.

### Milestone 4: Quality department

- unit/integration/API test ingestion;
- Playwright functional test generation and execution;
- screenshot, video, trace, console, and network capture;
- defect loop, separate review, completion gates, and evidence bundles.

### Milestone 5: Discord office

- company/channel mapping;
- tasks, status, clarifications, approvals, schedules, incidents, and digests;
- identity presentation and notification controls.

### Milestone 6: 2D simulation

- multi-company map;
- employees, rooms, movement, status, queues, and interaction panels;
- strict mapping of animation to company-engine events;
- previews and evidence accessible from the office;
- accessible nonvisual equivalent.

### Milestone 7: Continuous improvement

- autonomous work modes;
- proposal value scoring and deduplication;
- background capacity quotas and preemption;
- R&D experiments, knowledge publishing, postmortems, and scheduled reviews.

### Milestone 8: Consultants and portfolio governance

- external providers, redaction, cost estimates, approvals, accounting, and reports;
- holdings-level budgets and company resource allocation;
- controlled internal consulting and knowledge transfer.

### Milestone 9: Hardening and optional 3D client

- load, failure, restore, security, and chaos testing;
- policy review and operational documentation;
- optional 3D prototype that consumes existing APIs without changing the source of truth.

---

## 22. Acceptance Criteria

The first production-capable release is acceptable when all of the following are true:

- Multiple companies can run concurrently without leaking context, secrets, or files.
- A local worker outage does not corrupt tasks and idempotent work can recover.
- Employee identity and history persist when models or GPU nodes change.
- A user can issue, discuss, approve, pause, and review work through both web and Discord.
- Clarifications are concise, material, and do not unnecessarily stop unrelated work.
- Schedules execute in the correct time zone and can be audited and canceled.
- Agents cannot exceed tool permissions or spending limits through prompt instructions.
- Autonomous background tasks are value-scored, capped, deduplicated, and preemptible.
- Code work happens in isolation and cannot silently reach production.
- Completed software includes reproducible test evidence and a runnable preview or equivalent artifact.
- Functional tests exercise the visible product, capture failures, and support defect/retest loops.
- Visual office state matches authoritative engine state within an acceptable delay.
- External consultant calls show model, reason, context class, approval, and actual cost.
- All material actions and decisions have actor, provenance, timestamp, and policy records.
- A global kill switch prevents new model and tool work and safely stops or drains active work.
- Backup restoration and rollback are demonstrated, not merely documented.

---

## 23. Product Decisions to Preserve

The implementation team must preserve these decisions unless the owner explicitly changes them:

1. The product and parent organization are named **FarmHouse Holdings**.
2. Every project is a separate company, not merely a folder or department.
3. Local GPUs and local models are the default workforce.
4. External models are temporary, budgeted consultants.
5. Discord and the visual office are optional synchronized interfaces to one company engine.
6. Employees can initiate useful questions, proposals, and alerts.
7. Managers should shield the user from unnecessary interruptions.
8. Idle capacity should seek valuable improvement work, not consume compute for its own sake.
9. Finished work must be testable and supported by evidence, preferably with a live preview.
10. Functional QA should behave like a real user, not rely only on unit tests.
11. Autonomous changes must be sandboxed, reversible, permissioned, and auditable.
12. The 2D/3D world must visualize genuine state rather than fake activity.

---

## 24. Instructions to the Implementing Agent

Begin by reviewing this PRD and returning:

1. assumptions and unresolved questions;
2. a current-state architecture for the existing Ollama/HAProxy/GPU environment;
3. a proposed target architecture with clear component boundaries;
4. the recommended technology stack and alternatives;
5. an event schema and core database model;
6. the permission, approval, and sandbox design;
7. an MVP milestone plan with demonstrable acceptance tests;
8. the five greatest technical risks and mitigations;
9. a repository structure and local development plan;
10. the smallest vertical slice that proves company creation, one employee task, one clarification, functional testing, evidence publication, Discord synchronization, and accurate 2D visualization.

Do not begin by building a large 3D environment. First prove that the company engine can safely produce verified work and that every visual state is derived from authoritative events. Keep the architecture modular, self-hostable, provider-neutral, and capable of using the current local inference cluster.

