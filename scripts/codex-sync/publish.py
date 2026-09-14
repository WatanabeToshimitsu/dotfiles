#!/usr/bin/env python3
"""Trusted base-branch publisher: read PR blobs as data; never execute PR code."""

import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import generate


POST_PUSH_ATTEMPTS = 6
POST_PUSH_RETRY_SECONDS = 2


def api(repo, suffix, token, data=None):
    request = Request('https://api.github.com/repos/' + repo + suffix,
                      data=json.dumps(data).encode() if data is not None else None,
                      headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                               'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json'})
    with urlopen(request, timeout=30) as response:
        body = response.read()
        return json.loads(body) if body else None


def validate_pr(pr, repo, expected):
    if pr['state'] != 'open' or pr['head']['repo']['full_name'] != repo or pr['base']['ref'] != 'main':
        raise ValueError('only open same-repository PRs targeting main can be updated')
    if pr['user']['login'] == 'dependabot[bot]':
        raise ValueError('Dependabot is read-only')
    if pr['head']['sha'] != expected:
        raise ValueError('PR head changed; wait for the next synchronization run')
    branch = pr['head']['ref']
    if branch == 'main' or branch.startswith('-') or not re.fullmatch(r'[A-Za-z0-9_./-]+', branch):
        raise ValueError('unsupported PR branch')
    subprocess.run(['git', 'check-ref-format', 'refs/heads/' + branch], check=True, capture_output=True)
    return branch


def wait_for_published_head(repo: str, number: int, branch: str, previous: str,
                            commit: str, token: str) -> None:
    for attempt in range(POST_PUSH_ATTEMPTS):
        pr = api(repo, f'/pulls/{number}', token)
        observed = pr['head']['sha']
        expected = commit if observed == commit else previous
        if validate_pr(pr, repo, expected) != branch:
            raise ValueError('PR branch changed after push')
        if observed == commit:
            return
        if attempt + 1 < POST_PUSH_ATTEMPTS:
            time.sleep(POST_PUSH_RETRY_SECONDS)
    raise TimeoutError('PR head still reports the previous commit after push')


def dispatch_ci(repo, branch, commit, token):
    try:
        api(repo, '/actions/workflows/ci.yml/dispatches', token,
            {'ref': branch, 'inputs': {'expected_sha': commit}})
    except OSError as error:
        raise ValueError('commit is already pushed, but CI dispatch failed; rerun CI on ' + commit) from error


def make_commit(root, parent, output):
    with tempfile.TemporaryDirectory(prefix='codex-sync-index-') as temporary:
        env = os.environ.copy()
        env.update({'GIT_INDEX_FILE': str(Path(temporary) / 'index'),
                    'GIT_AUTHOR_NAME': 'github-actions[bot]', 'GIT_COMMITTER_NAME': 'github-actions[bot]',
                    'GIT_AUTHOR_EMAIL': '41898282+github-actions[bot]@users.noreply.github.com',
                    'GIT_COMMITTER_EMAIL': '41898282+github-actions[bot]@users.noreply.github.com'})
        def git(*args, input=None):
            return subprocess.check_output(['git', '-C', str(root), *args], input=input, env=env).strip()
        git('read-tree', parent)
        executables = json.loads(output['manifest.json']).get('executables', [])
        for path in generate.tracked(root, parent):
            if path.startswith(generate.OUTPUT + '/'):
                git('update-index', '--force-remove', '--', path)
        for name, data in sorted(output.items()):
            generate.safe_name(name)
            blob = git('hash-object', '-w', '--stdin', input=data).decode()
            mode = '100755' if name in executables else '100644'
            git('update-index', '--add', '--cacheinfo', mode, blob, generate.OUTPUT + '/' + name)
        tree = git('write-tree').decode()
        commit = git('-c', 'commit.gpgsign=false', 'commit-tree', tree, '-p', parent,
                     input=b'chore: sync Codex configuration\n\nCodex-Sync: generated-only\n').decode()
        changed = git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).decode().splitlines()
        if not changed or any(not p.startswith(generate.OUTPUT + '/') for p in changed):
            raise ValueError('publisher may only change generated paths')
        return commit


def push(root, commit, branch, expected, env=None):
    with tempfile.TemporaryDirectory(prefix='codex-sync-hooks-') as temporary:
        hook = Path(temporary) / 'pre-push'
        hook.write_text('''#!/usr/bin/env python3
import os, sys
rows = [line.split() for line in sys.stdin if line.strip()]
ok = len(rows) == 1 and len(rows[0]) == 4
ok = ok and rows[0][2] == os.environ['SYNC_REMOTE_REF']
ok = ok and rows[0][3] == os.environ['SYNC_EXPECTED_HEAD']
if not ok:
    print('PR branch changed before push; refusing update', file=sys.stderr)
sys.exit(0 if ok else 1)
''')
        hook.chmod(0o700)
        push_env = dict(os.environ if env is None else env)
        push_env.update({'SYNC_EXPECTED_HEAD': expected, 'SYNC_REMOTE_REF': 'refs/heads/' + branch})
        result = subprocess.run(['git', '-C', str(root), '-c', 'core.hooksPath=' + temporary,
                                 '-c', 'push.followTags=false', 'push', '--porcelain', 'origin',
                                 commit + ':refs/heads/' + branch], env=push_env, capture_output=True)
        if result.returncode:
            raise ValueError('normal push failed or PR head raced; nothing was force-pushed')


def publish(root, repo, number, expected, token):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or not re.fullmatch(r'[a-f0-9]{40}', expected):
        raise ValueError('invalid repository or head SHA')
    pr = api(repo, f'/pulls/{number}', token)
    branch = validate_pr(pr, repo, expected)
    trusted = generate.git(root, 'rev-parse', 'HEAD').decode().strip()
    env = os.environ.copy()
    credential = base64.b64encode(('x-access-token:' + token).encode()).decode()
    env.update({'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'http.https://github.com/.extraheader',
                'GIT_CONFIG_VALUE_0': 'AUTHORIZATION: basic ' + credential})
    subprocess.run(['git', '-C', str(root), 'fetch', '--no-tags', '--depth=1',
                    'https://github.com/' + repo + '.git', expected], env=env, check=True, capture_output=True)
    # Only the base implementation runs with the token. The dispatched CI is read-only.
    for path in ('.github/workflows/ci.yml', 'scripts/codex-sync/generate.py', 'claude/hooks/remote-mutation-guard.py'):
        if generate.git(root, 'show', trusted + ':' + path) != generate.git(root, 'show', expected + ':' + path):
            print('::notice::Automatic Codex sync skipped: CI, generator, or publication guard differs from the reviewed base; '
                  'regenerate locally and use ordinary PR checks.')
            return None
    output = generate.build(root, ref=expected)
    generate.scan_public(output)
    entries = generate.tracked(root, expected)
    old = {p.removeprefix(generate.OUTPUT + '/'): generate.read(root, p, entries, expected)
           for p in entries if p.startswith(generate.OUTPUT + '/')}
    generate.validate_previous(old, output)
    if old == output:
        message = generate.git(root, 'show', '-s', '--format=%B', expected).decode()
        if 'Codex-Sync: generated-only' in message.splitlines():
            dispatch_ci(repo, branch, expected, token)
            print('Generation is current; final-commit CI dispatched again: ' + expected)
        else:
            print('Generated files are current; no commit or duplicate CI run needed.')
        return expected
    commit = make_commit(root, expected, output)
    validate_pr(api(repo, f'/pulls/{number}', token), repo, expected)
    remote = generate.git(root, 'remote', 'get-url', 'origin').decode().strip()
    if remote not in ('https://github.com/' + repo, 'https://github.com/' + repo + '.git'):
        raise ValueError('publisher origin must be the current repository HTTPS remote')
    push(root, commit, branch, expected, env)
    phase = 'PR head confirmation'
    try:
        wait_for_published_head(repo, number, branch, expected, commit, token)
        phase = 'CI dispatch'
        dispatch_ci(repo, branch, commit, token)
    except (OSError, ValueError) as error:
        cause = error.__cause__ or error
        if isinstance(cause, HTTPError):
            detail = f'HTTP {cause.code}'
            cause.close()
        else:
            detail = type(cause).__name__
        raise ValueError(f'generated commit was pushed, but {phase} failed ({detail}); '
                         'inspect the PR head and approve or rerun CI on ' + commit) from None
    print('Generated commit pushed: ' + commit + '. CI dispatched; inspect final-head checks before merge.')
    return commit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--pr', type=int, required=True)
    parser.add_argument('--expected-head', required=True)
    args = parser.parse_args()
    try:
        if os.environ.get('GITHUB_ACTIONS') != 'true':
            raise ValueError('publisher only runs in the reviewed GitHub Actions job')
        publish(generate.ROOT, args.repo, args.pr, args.expected_head, os.environ['GH_TOKEN'])
        return 0
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print('codex sync publisher: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
