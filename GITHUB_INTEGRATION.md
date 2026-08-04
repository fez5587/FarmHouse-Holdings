# GitHub Integration Plan

GitHub org exists; no repos or connections yet. This maps PRD §14.4 (repository strategy) and §8 (authority levels) onto GitHub concretely.

---

## 1. Repository layout

| Repo | Purpose |
|---|---|
| `farmhouse-platform` | The platform itself: engine, agent loop, dashboard, tool workers. Monorepo. |
| `company-template` | GitHub **template repo**: scaffolding every new company repo is stamped from (README, CI workflow, `.farmhouse/company.yml` metadata, branch protection defaults) |
| `<company-slug>` (e.g. `radiance-wellness`) | One repo per subsidiary company, created by the engine via API at company creation (PRD §19.1 step 5) |

One repo per company keeps the PRD's isolation guarantee (§6.2) at the platform boundary: a company-scoped token physically cannot see another company's code.

## 2. Authentication — GitHub App, not PATs

- [ ] Create one **GitHub App** ("FarmHouse Engine") owned by the org
- [ ] Permissions: contents (RW), pull requests (RW), issues (RW), checks (RW), administration (repo creation), webhooks
- [ ] Engine mints **installation access tokens scoped per company repo** at tool-execution time — short-lived (1 h), matching PRD §16.1 "short-lived credentials"
- [ ] Employees never see tokens; the tool gateway injects them per authorized git operation
- [ ] Webhook endpoint on the engine: push, PR, check-run events flow into the event log so external human commits also appear in company history

## 3. Branch and PR model → authority levels

| PRD authority level | GitHub mechanism |
|---|---|
| Level 1 (Propose) | Draft PR from task branch; no merge rights |
| Level 2 (Sandbox) | Branch `task/<work-item-id>-<slug>`; CI runs; local worktree per agent prevents clobbering (PRD §14.4) |
| Level 3 (Internal change) | PR merge to `main` allowed only when: CI green + review by a *different* employee recorded in engine + policy engine sign-off posted as a required **check run** |
| Level 4 (Production) | Deploys from tags only; tag creation requires engine-recorded user approval |
| Level 5 (Destructive) | Repo deletion/history rewrite blocked for the App entirely; human-only |

- [ ] Branch protection on `main` in every company repo: require the FarmHouse policy check + CI, no force push, no direct push
- Key point: the **required check run posted by the engine** is how the deterministic policy engine (PRD §8) gets enforcement teeth inside GitHub — an agent can open a PR but the merge gate is server-side and outside the LLM.

## 4. Setup order

1. [ ] Create `farmhouse-platform` repo, push ADRs + these markdown docs as the first commit
2. [ ] Create `company-template` with: CI workflow (lint + test + placeholder policy check), `.farmhouse/company.yml`, branch protection config (applied via API on stamp)
3. [ ] Register the GitHub App, install on org, store credentials in the engine's secret store (never in a company repo)
4. [ ] Smoke test from a script: create repo from template → branch → commit → PR → check run → merge via API. This script becomes the engine's `git` tool worker.

## 5. Local execution detail

- Agents work in **worktrees** under the engine's workspace dir (`/work/<company>/<work-item-id>/`), one per active task — concurrent agents on the same repo never share a checkout (PRD §14.4)
- Commits authored as `<Employee Name> (FarmHouse) <employee-id@farmhouse.local>` so `git blame` maps to the employee record; App identity is the committer
- Worktrees pruned when the work item closes; unpushed work older than a policy TTL is flagged, not silently deleted

## 6. Deliberately skipped for now

- GitHub Projects/Issues as the backlog — the engine's Postgres backlog is the source of truth (PRD §23.5); mirror to Issues later only if browsing there proves useful
- GitHub Actions self-hosted runners — company CI runs on GitHub-hosted runners first; move to self-hosted when GPU-adjacent CI or cost demands it
- Fine-grained per-employee GitHub identities — one App with engine-side attribution is simpler and sufficient; revisit if external collaborators join a company repo
