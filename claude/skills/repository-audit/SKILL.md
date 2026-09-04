---
name: repository-audit
description: Audit or refactor a repository for dead code, unused files, exports, and dependencies. Use when asked to inspect a repository, assess repository health, clean up, simplify, reduce, or refactor. When the requested scope includes a JavaScript or TypeScript package graph, include Knip. Do not use for feature work that does not involve inspection or refactoring.
---

# Repository Audit

Match the requested authority. An inspection or audit is read-only unless the user also asks for changes.

## JavaScript and TypeScript

Treat Knip as required evidence when the requested inspection or refactoring scope includes a JavaScript or TypeScript package graph:

1. Inspect the package manager, workspace layout, package scripts, local Knip dependency, and Knip configuration.
2. Prefer the repository's existing script and locked local version.
3. If Knip is not available locally, ask before downloading an explicit version for a temporary run. Do not modify a manifest or lockfile solely to make that temporary run available.
4. Record the command and Knip version. Run it from the workspace where its entry points and package manifest are defined.
5. Address configuration hints first. Read findings from their root cause: unused files, unresolved imports, unused exports, then dependencies.

A Knip finding is evidence of an unreachable item, not permission to delete it. Check framework entry points, dynamic imports, generated files, scripts, public package exports, and other external consumers. Prefer teaching Knip about a real entry point over adding a broad ignore.

For a refactoring change, capture a baseline before editing, change one coherent category at a time, rerun Knip, and run the repository's relevant tests and build. When authorized cleanup removes a dependency, update its manifest and lockfile together. Treat the work as incomplete until Knip has run or the final report explains why it could not run.

## Other ecosystems

Knip does not apply when the requested scope has no JavaScript or TypeScript package graph. Use the relevant ecosystem's native dead-code and dependency checks and state that Knip was not applicable.

## Report

Return findings with the command, tool version, relevant locations, and the reachability reason. Separate confirmed dead code from configuration gaps and items that need a human decision. Report changes only when they were authorized, along with post-change Knip and test results.
