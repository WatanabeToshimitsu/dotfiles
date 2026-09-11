#!/usr/bin/env python3
"""Apply committed, merged Codex artifacts without replacing native settings."""

import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import tomllib
import uuid

import generate


BASE = '.codex/dotfiles-sync'
STATE = BASE + '/state.json'
BEGIN = '<!-- BEGIN dotfiles Claude sync -->'
END = '<!-- END dotfiles Claude sync -->'


def encoded(data):
    return base64.b64encode(data).decode()


def target(home, relative):
    generate.safe_name(relative)
    path = home
    for part in Path(relative).parts[:-1]:
        path = path / part
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ValueError(f'unsafe parent for managed path: {relative}')
    return home / relative


def capture(path):
    if path.is_symlink():
        return {'kind': 'link', 'target': os.readlink(path)}
    if path.is_file():
        return {'kind': 'file', 'data': encoded(path.read_bytes()), 'mode': path.stat().st_mode & 0o777}
    if path.exists():
        return {'kind': 'directory'}
    return {'kind': 'absent'}


def file_value(data, mode=0o600):
    return {'kind': 'file', 'data': encoded(data), 'mode': mode}


def load_state(home):
    path = target(home, STATE)
    if path.is_symlink():
        raise ValueError('state collision: foreign symlink')
    if not path.exists():
        return None
    state = json.loads(path.read_text())
    if state.get('version') != 1:
        raise ValueError('unsupported installed state')
    for name, value in state['links'].items():
        if name != BASE + '/current' and not re.fullmatch(r'\.agents/skills/[a-z0-9-]+', name):
            raise ValueError('unsafe owned link in state')
        if not value.startswith(str(home / BASE) + '/'):
            raise ValueError('unsafe owned target in state')
    return state


def local_text(home, value=None):
    value = capture(target(home, '.codex/AGENTS.md')) if value is None else value
    if value['kind'] not in ('file', 'absent'):
        raise ValueError('AGENTS.md collision: existing symlink or directory')
    return base64.b64decode(value['data']).decode() if value['kind'] == 'file' else ''


def merge_block(existing, block, state):
    if BEGIN in existing or END in existing:
        if existing.count(BEGIN) != 1 or existing.count(END) != 1:
            raise ValueError('ambiguous AGENTS.md managed block')
        start, end = existing.index(BEGIN), existing.index(END) + len(END)
        if start != 0 or end < len(BEGIN) or not state or existing[start:end] != state['block']:
            raise ValueError('AGENTS.md managed block was manually edited or is unowned')
        return block + existing[end:]
    if state and state.get('block'):
        raise ValueError('AGENTS.md managed block was removed; restore or uninstall before applying')
    return block + '\n\n' + existing


def disabled_skills(home):
    config_path = home / '.codex/config.toml'
    if not config_path.exists():
        return set()
    config = tomllib.loads(config_path.read_text())
    disabled = set()
    for entry in config.get('skills', {}).get('config', []):
        if entry.get('enabled') is False and isinstance(entry.get('path'), str):
            path = Path(entry['path']).expanduser()
            directory = path.parent if path.name == 'SKILL.md' else path
            disabled.add(directory.name)
            name = skill_name(directory / 'SKILL.md')
            if name:
                disabled.add(name)
    return disabled


def skill_name(path):
    if not path.is_file():
        return None
    with path.open() as stream:
        text = stream.read(4096)
    match = re.search(r'''^name:\s*(?:"([a-z0-9-]+)"|'([a-z0-9-]+)'|([a-z0-9-]+))(?:\s+\#.*)?\s*$''', text, re.M)
    return next((v for v in match.groups() if v), None) if match else None


def check_duplicate_names(home, skills, owned):
    for base in (home / '.agents/skills', home / '.codex/skills'):
        if not base.is_dir():
            continue
        for entry in base.iterdir():
            if str(entry.relative_to(home)) in owned:
                continue
            name = skill_name(entry / 'SKILL.md')
            if name in skills:
                raise ValueError(f'skill name collision: {name}')


def verify_snapshot(home, state):
    snapshot = Path(state['links'][BASE + '/current'])
    target(home, snapshot.relative_to(home).as_posix())
    if snapshot.is_symlink() or not snapshot.is_dir():
        raise ValueError('installed snapshot is missing or changed')
    manifest_path = generate.regular_path(snapshot, 'manifest.json')
    data = manifest_path.read_bytes()
    if generate.digest(data) != state['generation']:
        raise ValueError('snapshot manifest was manually edited')
    manifest = json.loads(data)
    names = set(manifest['files']) | {'manifest.json'} | set(state['dependencies'])
    actual = {p.relative_to(snapshot).as_posix() for p in snapshot.rglob('*') if p.is_file() or p.is_symlink()}
    if actual != names:
        raise ValueError('snapshot files were manually edited')
    for name, expected in manifest['files'].items():
        path = generate.regular_path(snapshot, name)
        mode = 0o700 if name in manifest.get('executables', []) else 0o600
        if generate.digest(path.read_bytes()) != expected.removeprefix('sha256:') or path.stat().st_mode & 0o777 != mode:
            raise ValueError(f'snapshot was manually edited: {name}')
    for name, source in state['dependencies'].items():
        if capture(target(snapshot, name)) != {'kind': 'link', 'target': source}:
            raise ValueError('machine-local reference link was changed')


def plan(root, home):
    root, home = root.resolve(), home.resolve()
    head = generate.git(root, 'rev-parse', 'HEAD').decode().strip()
    branch = generate.git(root, 'branch', '--show-current').decode().strip()
    merged = generate.git(root, 'rev-parse', 'refs/remotes/origin/main').decode().strip()
    if branch != 'main' or head != merged:
        raise ValueError('apply requires main at the last fetched origin/main; no unmerged branches')
    output = generate.build(root, ref=head)
    entries = generate.tracked(root, head)
    committed = {p.removeprefix(generate.OUTPUT + '/'): generate.read(root, p, entries, head)
                 for p in entries if p.startswith(generate.OUTPUT + '/')}
    if committed != output:
        raise ValueError('committed generation is stale; regenerate in a PR')
    state_before = capture(target(home, STATE))
    state = load_state(home)
    if state and state['root'] != str(root):
        raise ValueError('installation belongs to another checkout; uninstall it before switching')
    if state:
        verify_snapshot(home, state)
    override = home / '.codex/AGENTS.override.md'
    if override.exists() and override.read_bytes().strip():
        raise ValueError('AGENTS.override.md takes precedence; reconcile it before installing shared instructions')
    prior_agents = capture(target(home, '.codex/AGENTS.md'))
    existing = local_text(home, prior_agents)
    manifest = json.loads(output['manifest.json'])
    generation = generate.digest(output['manifest.json'])
    snapshot = home / BASE / 'snapshots' / generation
    current = home / BASE / 'current'
    if target(home, BASE + '/snapshots').is_symlink():
        raise ValueError('snapshot directory collision')
    disabled = disabled_skills(home)
    skipped = {s: 'disabled in native Codex settings' for s in manifest['skills'] if s in disabled}
    dependencies = {}
    for skill, references in manifest['local_dependencies'].items():
        for relative, source in references.items():
            if not (home / source).is_file():
                skipped[skill] = 'missing machine-local dependency: ' + source
            else:
                dependencies[f'skills/{skill}/{relative}'] = str(home / source)
    active = set(manifest['skills']) - set(skipped)
    owned = state['links'] if state else {}
    check_duplicate_names(home, active, owned)
    if state and (set(state['skills']) - set(manifest['skills'])) & disabled:
        if (set(manifest['skills']) - set(state['skills'])) - disabled:
            raise ValueError('review a possible disabled skill rename before enabling the new name')

    # Local references change snapshot identity without entering any public artifact.
    snapshot_key = generate.digest(output['manifest.json'] + generate.json_bytes(dependencies))
    snapshot = snapshot.parent / snapshot_key
    block_text = output['AGENTS.md'].decode().replace('~/.codex/dotfiles-sync/current/', str(current) + '/')
    block = BEGIN + '\n' + block_text.rstrip() + '\n' + END
    merged_text = merge_block(existing, block, state)
    if len(merged_text.encode()) > 30000:
        raise ValueError('global instructions approach the default discovery budget; review manually')
    links = {BASE + '/current': str(snapshot)}
    links.update({f'.agents/skills/{s}': str(current / 'skills' / s) for s in sorted(active)})
    operations = []
    def add(name, after, before=None):
        before = capture(target(home, name)) if before is None else before
        if before != after:
            operations.append({'path': name, 'before': before, 'after': after})
    for name in sorted(owned.keys() | links.keys()):
        before = capture(target(home, name))
        expected = {'kind': 'link', 'target': owned.get(name)}
        if before['kind'] != 'absent' and before != expected:
            raise ValueError(f'managed link collision: {name}')
        add(name, {'kind': 'link', 'target': links[name]} if name in links else {'kind': 'absent'})
    add('.codex/AGENTS.md', file_value(merged_text.encode(), prior_agents.get('mode', 0o600)), prior_agents)
    new_state = {'version': 1, 'root': str(root), 'commit': head, 'generation': generation,
                 'links': links, 'block': block, 'skills': manifest['skills'], 'skipped': skipped,
                 'dependencies': dependencies,
                 'agents_was_absent': state['agents_was_absent'] if state else prior_agents['kind'] == 'absent'}
    add(STATE, file_value(generate.json_bytes(new_state)), state_before)
    for op in operations:
        if op['before']['kind'] == 'directory':
            raise ValueError(f'directory collision: {op["path"]}')
    return {'home': str(home), 'snapshot': str(snapshot), 'files': output, 'dependencies': dependencies,
            'ops': operations, 'changes': [o['path'] for o in operations], 'skipped': skipped}


def replace(path, value):
    if value['kind'] == 'absent':
        if path.exists() or path.is_symlink():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / ('.codex-sync-' + uuid.uuid4().hex)
    try:
        if value['kind'] == 'link':
            temporary.symlink_to(value['target'])
        elif value['kind'] == 'file':
            with temporary.open('xb') as stream:
                os.chmod(temporary, value['mode'])
                stream.write(base64.b64decode(value['data']))
                stream.flush()
                os.fsync(stream.fileno())
        else:
            raise ValueError('unsupported transaction operation')
        os.replace(temporary, path)
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


@contextmanager
def locked(home):
    base = target(home, BASE)
    if base.is_symlink():
        raise ValueError('installation directory collision')
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = target(home, BASE + '/lock')
    if lock.is_symlink():
        raise ValueError('lock collision')
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def transaction(home, operations):
    for op in operations:
        if capture(target(home, op['path'])) != op['before']:
            raise ValueError(f'concurrent local change: {op["path"]}')
    backup = target(home, BASE + '/backups')
    if backup.is_symlink():
        raise ValueError('backup directory collision')
    backup.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex + '.json'
    backup = backup / name
    replace(backup, file_value(generate.json_bytes({'version': 1, 'ops': operations})))
    applied = []
    try:
        for op in operations:
            if capture(target(home, op['path'])) != op['before']:
                raise ValueError(f'concurrent local change: {op["path"]}')
            replace(target(home, op['path']), op['after'])
            applied.append(op)
    except BaseException:
        for op in reversed(applied):
            if capture(target(home, op['path'])) == op['after']:
                replace(target(home, op['path']), op['before'])
        raise
    return backup


def apply(prepared):
    if not prepared['ops']:
        return None
    home = Path(prepared['home'])
    with locked(home):
        snapshot = Path(prepared['snapshot'])
        target(home, snapshot.relative_to(home).as_posix())
        if snapshot.is_symlink():
            raise ValueError('snapshot collision')
        executables = json.loads(prepared['files']['manifest.json']).get('executables', [])
        expected = {name: file_value(data, 0o700 if name in executables else 0o600)
                    for name, data in prepared['files'].items()}
        expected.update({name: {'kind': 'link', 'target': source} for name, source in prepared['dependencies'].items()})
        if snapshot.exists():
            actual_names = {p.relative_to(snapshot).as_posix() for p in snapshot.rglob('*') if p.is_file() or p.is_symlink()}
            if actual_names != set(expected) or any(capture(snapshot / name) != value for name, value in expected.items()):
                raise ValueError('snapshot was manually edited')
        else:
            snapshot.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            temporary = Path(tempfile.mkdtemp(prefix='.building-', dir=snapshot.parent))
            try:
                for name, value in expected.items():
                    generate.safe_name(name)
                    replace(temporary / name, value)
                os.rename(temporary, snapshot)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
        return transaction(home, prepared['ops'])


def restore(home, dry_run=False):
    home = home.resolve()
    backups = sorted(target(home, BASE + '/backups').glob('*.json'))
    if not backups:
        raise ValueError('no sync backup found')
    document = json.loads(backups[-1].read_text())
    if document.get('version') != 1:
        raise ValueError('unsupported backup')
    operations = []
    for op in reversed(document['ops']):
        name = op['path']
        if name not in (STATE, BASE + '/current', '.codex/AGENTS.md') and not re.fullmatch(r'\.agents/skills/[a-z0-9-]+', name):
            raise ValueError('unsafe backup path')
        if capture(target(home, name)) != op['after']:
            raise ValueError(f'changed since backup; restore manually: {name}')
        operations.append({'path': name, 'before': op['after'], 'after': op['before']})
    if not dry_run:
        with locked(home):
            transaction(home, operations)
    return [o['path'] for o in operations]


def uninstall(home, dry_run=False):
    home = home.resolve()
    state = load_state(home)
    if not state:
        return []
    operations = []
    for name, link in state['links'].items():
        before = capture(target(home, name))
        if before == {'kind': 'link', 'target': link}:
            operations.append({'path': name, 'before': before, 'after': {'kind': 'absent'}})
    before = capture(target(home, '.codex/AGENTS.md'))
    if before['kind'] == 'file':
        text = base64.b64decode(before['data']).decode()
        prefix = state['block'] + '\n\n'
        if text.startswith(prefix):
            suffix = text[len(prefix):]
            after = {'kind': 'absent'} if not suffix and state['agents_was_absent'] else file_value(suffix.encode(), before['mode'])
            operations.append({'path': '.codex/AGENTS.md', 'before': before, 'after': after})
        elif BEGIN in text or END in text:
            raise ValueError('managed instructions were edited; leaving installation unchanged')
    operations.append({'path': STATE, 'before': capture(target(home, STATE)), 'after': {'kind': 'absent'}})
    if not dry_run:
        with locked(home):
            transaction(home, operations)
    return [o['path'] for o in operations]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('apply', 'check', 'restore', 'uninstall'))
    parser.add_argument('--root', type=Path, default=generate.ROOT)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        if args.command in ('apply', 'check'):
            prepared = plan(args.root, args.home)
            for path in prepared['changes']:
                print('update ' + path)
            for skill, reason in prepared['skipped'].items():
                print(f'unavailable {skill}: {reason}')
            if args.command == 'check':
                return int(bool(prepared['changes']))
            if not args.dry_run:
                backup = apply(prepared)
                if backup:
                    print('Applied merged snapshot. Backup: ' + str(backup))
        else:
            for path in globals()[args.command](args.home, args.dry_run):
                print(args.command + ' ' + path)
        return 0
    except (ValueError, OSError, KeyError, generate.subprocess.CalledProcessError) as error:
        print(f'codex sync: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
