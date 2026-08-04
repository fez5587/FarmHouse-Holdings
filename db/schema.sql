-- FarmHouse Holdings — core schema v1 (Slice 1 subset, PRD §14.3)
-- Postgres 15+. Deferred entities (Schedule, KnowledgeItem, Incident, ...) added when their slice needs them.

CREATE TABLE company (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            text NOT NULL UNIQUE,
    name            text NOT NULL,
    description     text NOT NULL DEFAULT '',
    lifecycle_state text NOT NULL DEFAULT 'draft'
                    CHECK (lifecycle_state IN ('draft','active','paused','archived')),
    -- repo, discord channel, office theme, autonomy policy, tz override
    config          jsonb NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE employee (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      uuid NOT NULL REFERENCES company(id),
    name            text NOT NULL,
    title           text NOT NULL,
    department      text NOT NULL DEFAULT '',
    manager_id      uuid REFERENCES employee(id),
    hermes_profile  text,                       -- Hermes profile name (ADR-001)
    model_alias     text NOT NULL DEFAULT 'local-default',
    authority_level int  NOT NULL DEFAULT 2 CHECK (authority_level BETWEEN 0 AND 5),
    soul_version    int  NOT NULL DEFAULT 1,    -- versioned system prompt (PRD §6.6)
    status          text NOT NULL DEFAULT 'idle'
                    CHECK (status IN ('idle','working','blocked','offline')),
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (company_id, name)
);

CREATE TABLE work_item (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      uuid NOT NULL REFERENCES company(id),
    parent_id       uuid REFERENCES work_item(id),
    type            text NOT NULL CHECK (type IN
                    ('objective','milestone','epic','task','subtask','defect',
                     'clarification','approval','research','proposal','experiment',
                     'review','incident','postmortem')),
    title           text NOT NULL,
    description     text NOT NULL DEFAULT '',
    status          text NOT NULL DEFAULT 'backlog' CHECK (status IN
                    ('backlog','ready','in_progress','blocked','review','done','cancelled')),
    priority        text NOT NULL DEFAULT 'medium' CHECK (priority IN
                    ('critical','high','medium','low','debt','research','experiment','idea')),
    owner_id        uuid REFERENCES employee(id),
    acceptance_criteria jsonb NOT NULL DEFAULT '[]',
    -- runaway caps, engine-enforced (PRD_ADDENDUM §3): max_iterations, max_tokens, max_wall_seconds
    budget          jsonb NOT NULL DEFAULT '{"max_iterations":15,"max_tokens":100000,"max_wall_seconds":1800}',
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX work_item_dispatch_idx ON work_item (company_id, status, priority);

-- Append-only event log: single source of truth for history (PRD §14.2).
CREATE TABLE event (
    event_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      uuid REFERENCES company(id),        -- NULL = holdings-level
    actor           text NOT NULL,                      -- 'employee:<uuid>' | 'user:philip' | 'system'
    event_type      text NOT NULL,                      -- see engine/schemas/events.py
    schema_version  int  NOT NULL DEFAULT 1,
    work_item_id    uuid REFERENCES work_item(id),
    parent_event_id uuid REFERENCES event(event_id),
    correlation_id  uuid,                               -- groups one logical exchange
    source          text NOT NULL DEFAULT 'engine'
                    CHECK (source IN ('engine','web','api','discord','hermes','scheduler','cli')),
    payload         jsonb NOT NULL DEFAULT '{}',
    policy_decision jsonb,                              -- {allowed, rule_id, level, reason}
    provenance      jsonb,                              -- {model, worker, tool, hermes_run_id}
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX event_company_time_idx ON event (company_id, created_at);
CREATE INDEX event_work_item_idx ON event (work_item_id) WHERE work_item_id IS NOT NULL;

CREATE FUNCTION event_immutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'event log is append-only'; END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER event_no_update BEFORE UPDATE OR DELETE ON event
    FOR EACH ROW EXECUTE FUNCTION event_immutable();

CREATE TABLE approval (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      uuid NOT NULL REFERENCES company(id),
    work_item_id    uuid REFERENCES work_item(id),
    requested_by    uuid NOT NULL REFERENCES employee(id),
    level           int  NOT NULL CHECK (level BETWEEN 3 AND 5),
    summary         text NOT NULL,
    options         jsonb NOT NULL DEFAULT '[]',        -- clarification options (PRD §7.6)
    status          text NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','approved','rejected','expired')),
    decided_by      text,                               -- 'user:philip' | 'policy:<rule_id>'
    rationale       text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    decided_at      timestamptz
);

CREATE TABLE artifact (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      uuid NOT NULL REFERENCES company(id),
    work_item_id    uuid REFERENCES work_item(id),
    kind            text NOT NULL CHECK (kind IN
                    ('evidence_bundle','screenshot','video','trace','test_report',
                     'build','preview','document','diff')),
    uri             text NOT NULL,                      -- file path or object-store URI
    meta            jsonb NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tool_execution (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      uuid NOT NULL REFERENCES company(id),
    employee_id     uuid NOT NULL REFERENCES employee(id),
    work_item_id    uuid REFERENCES work_item(id),
    tool            text NOT NULL,
    args            jsonb NOT NULL DEFAULT '{}',
    authority_level int  NOT NULL,
    policy_decision jsonb NOT NULL,                     -- always recorded (PRD §16.1)
    status          text NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running','ok','error','denied','timeout')),
    result_summary  text,
    started_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz
);

CREATE TABLE cost_entry (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      uuid NOT NULL REFERENCES company(id),
    employee_id     uuid REFERENCES employee(id),
    work_item_id    uuid REFERENCES work_item(id),
    kind            text NOT NULL CHECK (kind IN ('local_inference','consultant','tool','storage')),
    tokens_in       bigint NOT NULL DEFAULT 0,
    tokens_out      bigint NOT NULL DEFAULT 0,
    wall_seconds    numeric NOT NULL DEFAULT 0,
    usd             numeric NOT NULL DEFAULT 0,         -- 0 for local; real for consultants
    meta            jsonb NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX cost_company_time_idx ON cost_entry (company_id, created_at);

-- Deterministic policy: most specific enabled rule wins (company+employee > company > global).
-- Engine denies by default when no rule matches (PRD §8: enforced in code, not prompts).
CREATE TABLE policy_rule (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      uuid REFERENCES company(id),        -- NULL = global
    employee_id     uuid REFERENCES employee(id),       -- NULL = any employee
    tool_pattern    text NOT NULL DEFAULT '*',          -- glob: 'git.*', 'shell', '*'
    environment     text NOT NULL DEFAULT 'sandbox'
                    CHECK (environment IN ('sandbox','internal','external','production')),
    max_level       int  NOT NULL CHECK (max_level BETWEEN 0 AND 5),
    enabled         boolean NOT NULL DEFAULT true,
    note            text NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Global defaults: read/propose/sandbox anywhere; nothing above level 2 without an explicit rule.
INSERT INTO policy_rule (tool_pattern, environment, max_level, note) VALUES
    ('*', 'sandbox',    2, 'global default: full sandbox freedom'),
    ('*', 'internal',   1, 'global default: propose-only against internal env'),
    ('*', 'external',   0, 'global default: observe-only external'),
    ('*', 'production', 0, 'global default: observe-only production');
