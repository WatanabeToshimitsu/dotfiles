# Loop contract: <name>

- Status: `draft` (`approved` is required before any write)
- Owner: <person responsible for the run>
- Approved by: <person who approved this contract>
- Last reviewed: YYYY-MM-DD

Until the status is `approved`, the loop may inspect and report but must not
edit files, change external state, or create a branch or pull request.

## Work to discover and how to select it

- Target work: <the kind of task this loop may pick up>
- Discovery source and command: <Issue query, file, API, or event>
- Selection order: <priority and tie-break rules>
- Maximum work per run: <normally one item>

## Changes that are allowed

- Allowed paths: <repository-relative paths or a narrow pattern>
- Allowed actions: <edits and external writes>
- Required isolation: <worktree, branch naming, or clean checkout rule>

## Areas and actions that are forbidden

- Forbidden paths and data: <secrets, credentials, private data, or other scope>
- Forbidden operations: <production changes, deletion, automatic merge, etc.>
- Concurrent-work rule: <how ownership and overlapping changes are detected>

## Evidence that proves success

- Commands: <tests, lint, build, or validation commands>
- Logs and CI: <required checks and where their output is retained>
- Artifact: <PR, report, package, or other inspectable result>

## Stop conditions and budget

- Success: <observable terminal condition>
- Timeout: <maximum elapsed time>
- Maximum rounds: <bounded discovery, implementation, or repair attempts>
- Usage ceiling: <token, run, credit, or other measurable limit>
- Stop on risk: <security, scope, ambiguity, or destructive-action threshold>

## Hand work back to a person when

- <approval, permission, product decision, or external coordination is needed>
- <the evidence is inconclusive or a stop condition is met>
- Handoff destination: <Issue, PR, person, or team>

## Durable state and resumption

- System of record: <Issue, PR, or repository file>
- Record after each run: <selection, branch, evidence, usage, and stop reason>
- Resume from: <fields the next run must read before doing anything>

## Rollback

- Reversible changes: <revert command, PR, or configuration toggle>
- State cleanup: <branch, label, task, or temporary artifact cleanup>
