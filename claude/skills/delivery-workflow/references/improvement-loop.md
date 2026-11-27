# Improvement loop

Use this when the user asks to fix a recurring harness friction on evidence:
pick one friction, fix it with a before-and-after comparison, re-measure it
later, then keep or revert the change. Track each step in its own issue under
one epic. The replays below feed recorded inputs to code; compare a change to
instruction text as [Instruction changes](#instruction-changes) describes.

## 1. Pick one friction

- Read this repository's session transcripts once and table up to five
  friction candidates. Publish counts and categories only, never command text.
- Give each candidate a deterministic replay: a recorded input fed to the
  current code, shown to reproduce the friction before any change.
- The user picks one.

## 2. Fix it with a before-and-after comparison

- Before designing, replay the recorded inputs through the baseline commit
  and confirm which code path produces the friction. The proposed fix can
  target the wrong path.
- For a safety hook, write in the issue before starting who the hook guards
  against and what counts as blocking. Copy that text unchanged into every
  review request; a wider request brings back findings the issue ruled out.
- Replay every recorded input through the baseline and the changed code. Post
  the changed counts, by category, as a PR comment with a verdict: better,
  worse, or undetermined. Hand the merge to the user only on better.

## 3. Start the clock at pickup, not at merge

Hooks run from the main checkout through `~/.claude` links. The after-window
starts when the main checkout picks up the merge; its reflog shows when.

## 4. Re-measure, then accept or revert

- After 14 days or 20 new sessions, count the same friction the same way over
  before and after windows of equal length. Record the window bounds and how
  sessions are assigned to windows in the issue.
- Run the affected tests.
- Replay the inputs the baseline denied and the change allows. Deny again, in
  a follow-up, any high-risk form on that list before accepting.
- Accept if the count did not rise and the tests pass. Otherwise open a revert
  PR and leave its merge to the user.

## Reading the counts

- A friction seen only a few times reads 0 before and after in a 14-day
  window. That means "not worse", not that the change worked.
- Work on a hook trips that hook the most, so the before-window count includes
  the sessions that fixed it.
- In both rounds so far, the PR-stage replay predicted the re-measurement;
  treat it as the stronger evidence of an effect.

## Instruction changes

`scripts/instruction-eval.py` runs each case in `test/instruction-evals/`
through `claude plugin eval`, once with today's instructions and once with the
passage the case's `ablation.json` names removed. CI does not run it: each run
is a paid model session.

- Base a case on an instruction that was broken in practice, and cite the PR,
  issue, or feedback memory in its `description`.
- Keep a case only if today's version passes every run and the version without
  the passage fails most runs. A case that passes without its passage tests
  nothing; record that result instead, as a sign the passage may be redundant.
- Before editing a passage a case covers, run that case; after the edit, run
  every case.
- When settings, a hook, or a test enforces a rule, show it enforcing, then
  delete the rule's text and any case that covers it.
- Runs see both CLAUDE.md files and the skills, but not a long session, so a
  pass says less about long sessions.
