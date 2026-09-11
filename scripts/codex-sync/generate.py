#!/usr/bin/env python3
"""Generate reviewed, portable Codex instructions from public tracked inputs."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = 'codex/generated'
POLICY = 'codex/sync-policy.json'
ADAPTATIONS = 'codex/adaptations.md'
LIMIT = 512 * 1024


def git(root, *args, input=None):
    return subprocess.check_output(['git', '-C', str(root), *args], input=input)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()


def safe_name(name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or '..' in path.parts or str(path) != name:
        raise ValueError('unsafe relative path')
    if not re.fullmatch(r'[A-Za-z0-9_./-]+', name):
        raise ValueError('unsupported path characters')
    return path


def regular_path(root, name):
    safe_name(name)
    path = root
    for part in PurePosixPath(name).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f'symlink is not a public regular input: {name}')
    return path


def tracked(root, ref=None):
    if ref:
        rows = git(root, 'ls-tree', '-rz', ref).split(b'\0')
        return {name.decode(): metadata.split()[0].decode()
                for row in rows if row for metadata, name in [row.split(b'\t', 1)]}
    rows = git(root, 'ls-files', '--stage', '-z').split(b'\0')
    result = {}
    for row in filter(None, rows):
        metadata, name = row.split(b'\t', 1)
        mode, _, stage = metadata.decode().split()
        if stage != '0':
            raise ValueError('resolve index conflicts before generation')
        result[name.decode()] = mode
    return result


def read(root, name, entries, ref=None):
    if name not in entries:
        raise ValueError(f'input must be tracked: {name}')
    safe_name(name)
    if entries[name] not in ('100644', '100755'):
        raise ValueError(f'symlink or non-regular input: {name}')
    data = git(root, 'show', f'{ref}:{name}') if ref else regular_path(root, name).read_bytes()
    if len(data) > LIMIT:
        raise ValueError(f'input exceeds size limit: {name}')
    data.decode('utf-8')
    return data


def leaves(value, prefix=''):
    if isinstance(value, dict) and value:
        for key, child in value.items():
            token = key.replace('~', '~0').replace('/', '~1')
            yield from leaves(child, prefix + '/' + token)
    elif isinstance(value, list) and any(isinstance(v, (dict, list)) for v in value):
        for index, child in enumerate(value):
            yield from leaves(child, prefix + '/' + str(index))
    else:
        yield prefix


def classify(actual, policy, category):
    actual = set(actual)
    unknown, retired = actual - set(policy), set(policy) - actual
    if unknown or retired:
        raise ValueError(f'unclassified or retired {category}: ' + ', '.join(sorted(unknown | retired)))
    for key, rule in policy.items():
        if set(rule) != {'mode', 'reason'} or rule['mode'] not in ('share', 'adapt', 'exclude') or not rule['reason']:
            raise ValueError(f'invalid {category} policy: {key}')


def scopes(data, name):
    text = data.decode()
    match = re.match(r'\A---\npaths:\n((?:  - "[^"\n]+"\n)+)---(?:\n|$)', text)
    if not match:
        raise ValueError(f'unsupported rule frontmatter: {name}')
    patterns = re.findall(r'^  - "(.+)"$', match[1], re.M)
    for pattern in patterns:
        scope_regex(pattern)
    return patterns


def scope_regex(pattern):
    if '[' in pattern or '!' in pattern or '\\' in pattern or pattern.startswith('/') or '..' in pattern.split('/'):
        raise ValueError(f'unsupported scope: {pattern}')
    def translate(value):
        parts, index = [], 0
        while index < len(value):
            if value.startswith('**/', index):
                parts.append('(?:.*/)?'); index += 3
            elif value.startswith('**', index):
                parts.append('.*'); index += 2
            elif value[index] == '*':
                parts.append('[^/]*'); index += 1
            elif value[index] == '?':
                parts.append('[^/]'); index += 1
            elif value[index] == '{':
                end = value.find('}', index)
                if end < 0 or '{' in value[index + 1:end]:
                    raise ValueError(f'unsupported scope: {pattern}')
                parts.append('(?:' + '|'.join(translate(p) for p in value[index + 1:end].split(',')) + ')')
                index = end + 1
            else:
                parts.append(re.escape(value[index])); index += 1
        return ''.join(parts)
    return re.compile('^' + translate(pattern) + '$')


def matches(pattern, path):
    return bool(scope_regex(pattern).fullmatch(path))


def build(root, ref=None):
    entries = tracked(root, ref)
    inputs = {name: read(root, name, entries, ref) for name in entries if
              name in (POLICY, ADAPTATIONS, 'claude/CLAUDE.md', 'claude/settings.json') or
              name.startswith(('claude/rules/', 'claude/skills/', 'claude/agents/'))}
    for required in (POLICY, ADAPTATIONS, 'claude/CLAUDE.md', 'claude/settings.json'):
        if required not in inputs:
            raise ValueError(f'missing tracked input: {required}')
    policy = json.loads(inputs[POLICY])
    if set(policy) != {'version', 'settings', 'hooks', 'agents', 'skills'} or policy['version'] != 1:
        raise ValueError('unsupported sync policy schema')
    settings = json.loads(inputs['claude/settings.json'])
    classify(leaves(settings), policy['settings'], 'settings')
    # Values are never copied wholesale: native permissions, auth and trust stay local.
    for key, disposition in policy['settings'].items():
        if disposition['mode'] != 'exclude' and key != '/language':
            raise ValueError(f'unsupported settings adaptation: {key}')
    hook_ids = []
    for event, groups in settings.get('hooks', {}).items():
        for group_index, group in enumerate(groups):
            for hook_index, _ in enumerate(group.get('hooks', [])):
                hook_ids.append(f'{event}/{group_index}/{hook_index}')
    classify(hook_ids, policy['hooks'], 'hooks')
    agents = [p.removeprefix('claude/agents/') for p in inputs if p.startswith('claude/agents/')]
    classify(agents, policy['agents'], 'agents')
    if any(p['mode'] != 'exclude' for p in [*policy['hooks'].values(), *policy['agents'].values()]):
        raise ValueError('native hook and agent installation is unsupported')

    output = {'source/CLAUDE.md': inputs['claude/CLAUDE.md']}
    index, skill_names = [], {}
    for name, data in sorted(inputs.items()):
        if name.startswith('claude/rules/'):
            if not name.endswith('.md'):
                raise ValueError(f'unsupported rule input: {name}')
            relative = name.removeprefix('claude/')
            index.append({'file': relative, 'paths': scopes(data, name)})
            output[relative] = data
        elif name.startswith('claude/skills/'):
            relative = name.removeprefix('claude/')
            if name.endswith('/reference.md') or re.search(r'(^|/)(\.env.*|credentials[^/]*|secrets[^/]*)$', name):
                raise ValueError(f'private input must never be tracked: {name}')
            if re.search(rb'/(?:Users|home)/[^/\s]+/', data):
                raise ValueError(f'machine-local absolute path in skill: {name}')
            output[relative] = data
            if name.endswith('/SKILL.md'):
                if len(PurePosixPath(name).parts) != 4:
                    raise ValueError(f'nested skill entrypoint is unsupported: {name}')
                skill = PurePosixPath(name).parent.name
                match = re.match(rb'\A---\nname: ([a-z0-9-]+)\ndescription: [^\n]+\n', data)
                if not match or match[1].decode() != skill or skill in skill_names:
                    raise ValueError(f'unsupported or duplicate skill metadata: {name}')
                frontmatter = data.decode().split('---', 2)[1]
                keys = set(re.findall(r'^([a-z-]+):', frontmatter, re.M))
                if keys - {'name', 'description', 'argument-hint', 'allowed-tools'}:
                    raise ValueError(f'unclassified skill frontmatter: {name}')
                if ('allowed-tools' in keys or 'argument-hint' in keys) and skill not in policy['skills']:
                    raise ValueError(f'skill metadata needs an explicit host adaptation: {name}')
                skill_names[skill] = relative
    for skill, disposition in policy['skills'].items():
        if skill not in skill_names:
            raise ValueError(f'retired skill adaptation: {skill}')
        if set(disposition) != {'reason', 'note', 'local_dependencies'}:
            raise ValueError(f'unsupported skill adaptation: {skill}')
        for relative, source in disposition['local_dependencies'].items():
            safe_name(relative); safe_name(source)
            if (skill, relative, source) != ('ticket', 'reference.md', '.claude/skills/ticket/reference.md'):
                raise ValueError(f'unsupported local dependency: {skill}')
        path = skill_names[skill]
        output[path] = output[path].rstrip() + ('\n\n## Codex portability\n\n' + disposition['note'] + '\n').encode()
    output['rule-index.json'] = json_bytes(index)
    output['inventory.json'] = json_bytes({
        'settings': policy['settings'], 'hooks': policy['hooks'], 'agents': policy['agents'],
        'skills': {s: policy['skills'].get(s, {'reason': 'Shared portable instructions; no native permissions are granted.'}) for s in sorted(skill_names)},
    })
    text = inputs['claude/CLAUDE.md'].decode().rstrip() + '\n\n# Shared scoped rules\n\n'
    text += ('Before editing a file, read every matching rule below, in the listed order. '
             'Patterns use repository-relative paths, ** spans directories, and braces list alternatives. '
             'Do not apply unmatched rules. These are prompt instructions, not native Claude conditional loading. '
             'Rule files live under ~/.codex/dotfiles-sync/current/. Repository and local Codex instructions retain their normal precedence.\n\n')
    for rule in index:
        text += '- ' + rule['file'] + ': ' + ', '.join('`' + p + '`' for p in rule['paths']) + '\n'
    text += '\n' + inputs[ADAPTATIONS].decode().rstrip() + '\n'
    language = settings.get('language')
    if language and policy['settings']['/language']['mode'] == 'adapt':
        if not isinstance(language, str) or not re.fullmatch(r'[A-Za-z -]{1,40}', language):
            raise ValueError('unsupported response language')
        text += '\nResponse language: ' + language + '.\n'
    output['AGENTS.md'] = text.encode()
    if len(output['AGENTS.md']) > 20000:
        raise ValueError('shared instructions exceed the 20 KB budget; review discovery limits')
    output['manifest.json'] = json_bytes({
        'version': 1,
        'inputs': {p: 'sha256:' + digest(data) for p, data in sorted(inputs.items())},
        'files': {p: 'sha256:' + digest(data) for p, data in sorted(output.items())},
        'executables': sorted(p.removeprefix('claude/') for p in inputs
                              if p.startswith('claude/skills/') and entries[p] == '100755'),
        'skills': sorted(skill_names),
        'local_dependencies': {s: p['local_dependencies'] for s, p in policy['skills'].items() if p['local_dependencies']},
    })
    return output


def existing(root):
    base = regular_path(root, OUTPUT)
    if not base.exists():
        return {}
    result = {}
    for path in base.rglob('*'):
        name = path.relative_to(base).as_posix()
        if path.is_symlink():
            raise ValueError(f'generated symlink is not managed: {name}')
        if path.is_file():
            safe_name(name)
            result[name] = path.read_bytes()
    return result


def changes(root, output):
    old = existing(root)
    changed = {p for p in old.keys() | output.keys() if old.get(p) != output.get(p)}
    executables = set(json.loads(output['manifest.json']).get('executables', []))
    for name in old.keys() & output.keys():
        if bool(regular_path(root, OUTPUT + '/' + name).stat().st_mode & 0o111) != (name in executables):
            changed.add(name)
    return sorted(changed)


def write(root, output):
    old = existing(root)
    validate_previous(old, output)
    executables = set(json.loads(output['manifest.json']).get('executables', []))
    for name in old.keys() - output.keys():
        regular_path(root, OUTPUT + '/' + name).unlink()
    for name, data in output.items():
        target = regular_path(root, OUTPUT + '/' + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if old.get(name) != data:
            target.write_bytes(data)
        target.chmod(0o755 if name in executables else 0o644)


def validate_previous(old, output):
    if not old:
        return
    try:
        manifest = json.loads(old['manifest.json'])
        required = {'version', 'inputs', 'files', 'skills', 'local_dependencies'}
        if not required <= manifest.keys() or manifest.keys() - required - {'executables'} or manifest['version'] != 1:
            raise ValueError('invalid manifest schema')
        owned = manifest['files']
        if not isinstance(owned, dict) or set(old) != set(owned) | {'manifest.json'}:
            raise ValueError('generated files were manually edited or removed')
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('generated manifest was manually edited or is missing') from error
    for name, data in old.items():
        if name == 'manifest.json':
            continue
        if not isinstance(owned.get(name), str) or digest(data) != owned[name].removeprefix('sha256:'):
            raise ValueError(f'generated output was manually edited or is unowned: {name}')


def scan_public(output):
    spec = importlib.util.spec_from_file_location('publication_guard', ROOT / 'claude/hooks/remote-mutation-guard.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    for name, data in output.items():
        if guard.secret_findings(data.decode()):
            raise ValueError(f'possible secret in generated file: {name}; value withheld')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true')
    group.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        output = build(args.root)
        scan_public(output)
        changed = changes(args.root, output)
        for path in changed:
            print(f'update {OUTPUT}/{path}')
        if args.check:
            return int(bool(changed))
        validate_previous(existing(args.root), output)
        if not args.dry_run:
            write(args.root, output)
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'codex sync: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
