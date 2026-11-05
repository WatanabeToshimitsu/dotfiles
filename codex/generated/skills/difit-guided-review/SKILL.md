---
name: difit-guided-review
description: Open a change in difit with a Japanese reading guide and preloaded explanation comments, so the user can review it. Use when the user wants to look at or review a change in difit, such as 「レビューしたい」, 「difit 起動して」, 「difit で見せて」, 「PR の差分を見たい」, or a PR URL with a request to review it. Prefer this over the generic difit and difit-review skills for this flow.
---

# difit guided review

Launch difit on the right diff and help the user read it: a file-by-file
explanation and reading order in chat, and Japanese explanation comments inside
difit. Command conventions follow the external `difit` and `difit-review`
skills; run `difit --help` first and use only the flags it lists.

## Steps

1. **Find the target.** A PR URL or number, a branch, or a worktree. Prefer the
   local worktree that has the PR head checked out (`git worktree list`,
   `gh pr view <n> --json headRefName,baseRefName`). Run `git fetch origin`,
   take the base from the PR, or from the repository default branch
   (`trunk` or `main`), and compare against `origin/<base>`.
2. **Read the diff** with `git diff origin/<base>...HEAD` in that worktree, plus
   the surrounding code you need to explain it.
3. **Launch difit** from the worktree, in the background, with the merge base so
   the view matches the PR diff:

   ```bash
   memgate run -- <difit-command> HEAD origin/<base> --merge-base --background --no-open \
     --comment '<json>' --comment '<json>'
   ```

   `<difit-command>` is `difit` if `command -v difit` succeeds, else
   `npx difit`. `--background` prints JSON with the URL; open it with
   `open <url>`. Never post anything to GitHub.
4. **Comments.** Each is
   `{"type":"thread","filePath":"...","position":{"side":"new","line":N},"body":"..."}`;
   use `{"start":a,"end":b}` for a range. Write bodies in Japanese. Attach:
   - to each test case or table-driven test row: what it verifies, why it
     exists, and a Japanese translation of its description string;
   - to each code comment and JSDoc block in the added lines: its Japanese
     translation.

   Review findings stay out of difit unless the user asks; put them in chat.
   Never copy secrets, tokens, or credentials into a body or any argument.
5. **Reply in Japanese**: the difit URL, a short explanation of each changed
   file, and a recommended reading order with the reason for that order. If no
   comments were attached, say so. Checking the launched page is not required.
