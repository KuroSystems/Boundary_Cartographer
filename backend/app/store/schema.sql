-- Boundary Cartographer store schema (BE-03). SQLite via stdlib sqlite3, no ORM.
-- Evidence is append-only (triggers forbid UPDATE/DELETE). Approvals record
-- decisions only: `applied` defaults to 0 and no code path ever writes 1.

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS runs (
    run_id       TEXT PRIMARY KEY,
    scenario_id  TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('completed', 'failed')),
    payload      TEXT NOT NULL,              -- canonical JSON of the full RunResponse
    input_digest TEXT NOT NULL,
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_scenario ON runs (scenario_id);

CREATE TABLE IF NOT EXISTS evidence (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id TEXT NOT NULL,
    run_id      TEXT NOT NULL REFERENCES runs (run_id),
    kind        TEXT NOT NULL,
    source_id   TEXT NOT NULL,
    summary     TEXT NOT NULL,
    hash        TEXT NOT NULL,              -- sha256(prev_hash + canonical_json(record))
    prev_hash   TEXT,                       -- NULL for the first record of a run
    record      TEXT NOT NULL,              -- canonical JSON of the full EvidenceRecord
    captured_at TEXT NOT NULL,
    UNIQUE (run_id, evidence_id)
);
CREATE INDEX IF NOT EXISTS idx_evidence_run ON evidence (run_id, seq);

-- Append-only enforcement: any UPDATE or DELETE on evidence aborts.
CREATE TRIGGER IF NOT EXISTS evidence_no_update
BEFORE UPDATE ON evidence
BEGIN
    SELECT RAISE(ABORT, 'evidence is append-only: UPDATE forbidden');
END;

CREATE TRIGGER IF NOT EXISTS evidence_no_delete
BEFORE DELETE ON evidence
BEGIN
    SELECT RAISE(ABORT, 'evidence is append-only: DELETE forbidden');
END;

CREATE TABLE IF NOT EXISTS approvals (
    approval_id  TEXT NOT NULL,
    run_id       TEXT NOT NULL REFERENCES runs (run_id),
    subject_type TEXT NOT NULL,
    subject_id   TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'approved', 'rejected')),
    requested_at TEXT NOT NULL,
    decided_by   TEXT,
    decided_at   TEXT,
    note         TEXT,
    applied      INTEGER NOT NULL DEFAULT 0 CHECK (applied IN (0, 1)),
    simulated    INTEGER NOT NULL DEFAULT 1 CHECK (simulated IN (0, 1)),
    effect       TEXT NOT NULL,
    PRIMARY KEY (run_id, approval_id)
);
CREATE INDEX IF NOT EXISTS idx_approvals_run ON approvals (run_id);
