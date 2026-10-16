import html
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts/codex-sync'
sys.path.insert(0, str(SCRIPTS))
import generate
import install


def markdown_prose(text):
    lines, fence = [], None
    for line in text.splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if marker and fence is None:
            fence = marker[1]
            lines.append('')
        elif fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not line[marker.end():].strip():
                fence = None
            lines.append('')
        else:
            lines.append(line)
    return '\n'.join(lines)


def markdown_anchors(text):
    # GitHub heading IDs: https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#section-links
    anchors = set()
    for heading in re.findall(r'(?m)^ {0,3}#{1,6}\s+(.+?)(?:\s+#+)?$', markdown_prose(text)):
        heading = re.sub(r'(\*\*|__|[*_]|`)(.+?)\1', r'\2', heading)
        stem = re.sub(r'[^\w -]', '', html.unescape(heading).lower()).strip().replace(' ', '-')
        anchor, suffix = stem, 1
        while anchor in anchors:
            anchor = f'{stem}-{suffix}'
            suffix += 1
        anchors.add(anchor)
    return anchors


def instruction_reference_errors(root):
    root = root.resolve()
    # Only prose inline links and explicitly named skills are checked, not arbitrary Markdown or command examples.
    # The ticket reference is machine-local and may contain private data; never read it or its aliases.
    local_reference = root / 'claude/skills/ticket/reference.md'
    paths = [root / 'CLAUDE.md', root / 'claude/CLAUDE.md']
    paths += [path for directory in ('rules', 'skills', 'agents')
              for path in (root / 'claude' / directory).rglob('*.md')]
    skills = {path.parent.name for path in (root / 'claude/skills').glob('*/SKILL.md')}
    try:
        sources = (root / 'agent-skills.txt').read_text().splitlines()
    except (OSError, UnicodeError):
        return ['agent-skills.txt: external skill inventory is unavailable']
    if not sources or any(not re.fullmatch(r'[^:\s]+:[a-z0-9-]+', s) for s in sources):
        return ['agent-skills.txt: invalid external skill inventory']
    external_skills = [s.rsplit(':', 1)[1] for s in sources]
    if len(set(external_skills)) != len(external_skills) or skills.intersection(external_skills):
        return ['agent-skills.txt: duplicate or repository-managed external skill name']
    skills.update(external_skills)
    # Bundled skill names, not runtime availability: https://code.claude.com/docs/en/skills#bundled-skills
    skills.update({'batch', 'claude-api', 'code-review', 'debug', 'doctor', 'loop', 'simplify', 'verify'})
    marked_name = r'(?:`[a-z0-9-]+`|\*\*[a-z0-9-]+\*\*)'
    errors = []
    for path in paths:
        if path == local_reference or path.resolve() == local_reference or not path.exists():
            continue
        if not path.resolve().is_relative_to(root):
            errors.append(f'{path.relative_to(root)}: instruction file leaves repository')
            continue
        for number, line in enumerate(markdown_prose(path.read_text()).splitlines(), 1):
            location = f'{path.relative_to(root)}:{number}'
            names = re.findall(r'See skill:\s*(?:`|\*\*)?([a-z0-9-]+)', line)
            for group in re.findall(r'((?:' + marked_name + r'\s*(?:(?:,|and|と)\s*)?)+)\s+skills?\b', line):
                names += [left or right for left, right in re.findall(r'`([a-z0-9-]+)`|\*\*([a-z0-9-]+)\*\*', group)]
            for name in set(names) - skills:
                errors.append(f'{location}: unknown skill {name}; check local skills, agent-skills.txt, or bundled allowlist')
            link_line = re.sub(r'(`+).*?\1', '', line)
            for link in re.findall(r'\[[^\]]*\]\(([^\s)]+)(?:\s+["\'][^"\']*["\'])?\)', link_line):
                # External URLs, home paths, and explicit placeholder tokens are nonportable examples.
                if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', link) or link.startswith(('//', '~')) or re.search(r'[<>{}$]', link):
                    continue
                destination, _, fragment = link.partition('#')
                destination = unquote(destination.partition('?')[0])
                fragment = unquote(fragment)
                target = path if not destination else (root / destination.lstrip('/') if destination.startswith('/') else path.parent / destination)
                target = Path(os.path.abspath(target))
                if target == local_reference or target.resolve() == local_reference:
                    continue
                if not target.is_relative_to(root) or not target.resolve().is_relative_to(root):
                    errors.append(f'{location}: link leaves repository: {link}')
                    continue
                cursor = root
                for part in target.relative_to(root).parts:
                    if not cursor.resolve().is_relative_to(root) or not cursor.is_dir() or part not in {child.name for child in cursor.iterdir()}:
                        break
                    cursor /= part
                else:
                    if cursor.exists():
                        if fragment:
                            anchors = markdown_anchors(cursor.read_text()) if cursor.is_file() else set()
                            if fragment not in anchors:
                                errors.append(f'{location}: missing anchor {fragment}; available: {sorted(anchors)}')
                        continue
                errors.append(f'{location}: missing or wrong-case link: {link}')
    return errors


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


class RepositoryCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.home = Path(self.temp.name) / 'user'
        self.home.mkdir()
        git(self.root, 'init', '-q', '-b', 'main')
        git(self.root, 'config', 'user.name', 'Sync test')
        git(self.root, 'config', 'user.email', 'sync@example.invalid')
        git(self.root, 'config', 'commit.gpgsign', 'false')
        self.put('claude/CLAUDE.md', '# Common instructions\nKeep exact bytes.\n')
        self.put('claude/rules/python.md', '---\npaths:\n  - "**/*.py"\n---\n\nPython only.\n')
        self.put('claude/skills/demo/SKILL.md', '---\nname: demo\ndescription: A test skill.\n---\n\nTest instructions.\n')
        self.put('claude/settings.json', '{"language": "Japanese", "permissions": {"allow": []}}\n')
        self.put('codex/skill-adaptations.json', '{}\n')
        self.put('codex/adaptations.md', '# Codex adaptations\nKeep native permissions.\n')
        git(self.root, 'add', 'claude', 'codex')
        git(self.root, 'commit', '-qm', 'Source')

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def generate(self):
        output = generate.build(self.root)
        generate.write(self.root, output)
        return output

    def merged(self):
        self.generate()
        git(self.root, 'add', 'claude', 'codex')
        git(self.root, 'commit', '-qm', 'Generated')
        git(self.root, 'update-ref', 'refs/remotes/origin/main', 'HEAD')


class InstructionReferenceTest(RepositoryCase):
    def setUp(self):
        super().setUp()
        self.put('agent-skills.txt', 'fixture/skills:external-demo\n')
        self.put('claude/skills/demo/guide.md', '## Known\n')

    def test_missing_file_anchor_and_skill_references_are_rejected(self):
        for text in (
            '[missing](gone.md)',
            '[anchor](skills/demo/guide.md#missing)',
            'See skill: `missing-skill`',
            'Use `missing-skill` skill.',
            'Use **missing-skill** skill.',
        ):
            with self.subTest(text=text):
                self.put('claude/CLAUDE.md', text)
                self.assertTrue(instruction_reference_errors(self.root))

    def test_supported_references_and_nonportable_examples_are_accepted(self):
        self.put('claude/skills/demo/guide #space.md',
                 '# 常用の`設定`と安全！\n## A _known_ `section`!\n## Repeat\n## Repeat\n')
        self.put('claude/CLAUDE.md', '''# Here
[self](#here)
[title](skills/demo/guide%20%23space.md#a-known-section "Guide")
[Japanese](skills/demo/guide%20%23space.md#常用の設定と安全)
[duplicate](skills/demo/guide%20%23space.md#repeat-1)
[directory](skills/demo)
See skill: `demo`
See skill: `external-demo`
See skill: `loop`
Use `demo` and `external-demo` skills.
Use **external-demo** skill.
[machine-local](skills/ticket/reference.md)
[external](https://example.invalid/missing#absent)
[placeholder](<project>/guide.md)
[placeholder]({project}/guide.md)
[home](~/local.md)
`[example](absent.md)`
```markdown
[example](absent.md)
See skill: `missing-skill`
```
''')
        self.put('CLAUDE.md', '[source](claude/CLAUDE.md)\n')
        self.put('claude/rules/demo.md', '[guide](../skills/demo/guide.md#known)\n')
        self.put('claude/agents/demo.md', '[guide](../skills/demo/guide.md#known)\n')
        local = self.root / 'claude/skills/ticket/reference.md'
        local.parent.mkdir()
        local.write_bytes(b'\xff')
        self.assertEqual(instruction_reference_errors(self.root), [])

    def test_wrong_case_escaped_paths_and_code_block_anchors_are_rejected(self):
        self.put('claude/skills/demo/guide.md', '## Known\n```\n## Example\n```\n')
        for link in ('skills/demo/Guide.md', '../../user/local.md', 'skills/demo/guide.md#example'):
            with self.subTest(link=link):
                self.put('claude/CLAUDE.md', '[invalid](' + link + ')')
                self.assertTrue(instruction_reference_errors(self.root))

    def test_unrecognized_external_skill_inventory_is_reported(self):
        for value in ('', 'invalid\n', 'fixture/skills:demo\n',
                      'fixture/skills:external-demo\nother/skills:external-demo\n'):
            with self.subTest(value=value):
                self.put('agent-skills.txt', value)
                self.assertTrue(instruction_reference_errors(self.root))
        (self.root / 'agent-skills.txt').unlink()
        self.assertTrue(instruction_reference_errors(self.root))

    def test_repository_instruction_references_are_valid(self):
        self.assertEqual(instruction_reference_errors(ROOT), [])

    def test_external_install_targets_both_clients_and_reports_partial_roots(self):
        self.put('agent-skills.txt', 'fixture/one:first\r\nfixture/two:second\nfixture/three:third\n'
                 'fixture/four:shared\nfixture/five:dangling-claude\nfixture/six:dangling-codex\nfixture/seven:last')
        reports = [self.home / '.agents/skills/second/reports/r.md', self.home / '.claude/skills/third/reports/r.md']
        for report in reports:
            report.parent.mkdir(parents=True)
            report.write_text('local report')
        (self.home / '.agents/skills/shared').mkdir()
        (self.home / '.claude/skills/shared').symlink_to('../../.agents/skills/shared')
        (self.home / '.claude/skills/dangling-claude').symlink_to('../missing')
        (self.home / '.agents/skills/dangling-codex').symlink_to('../missing')
        function = re.search(r'(?ms)^setup_agent_skills\(\) \{.*?^\}', (ROOT / 'install.sh').read_text())[0]
        calls = self.home / 'npx-calls'
        result = subprocess.run(['/bin/bash', '-c', '''
DOTFILES_DIR="$1"
CALLS="$2"
npx() { printf '%s\\n' "$*" >> "$CALLS"; cat > /dev/null; }
''' + function + '\nsetup_agent_skills', 'bash', str(self.root), str(calls)],
            env=dict(os.environ, HOME=str(self.home)), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls.read_text().splitlines(), [
            '-y skills add fixture/one -g -y -s first -a claude-code -a codex',
            '-y skills add fixture/seven -g -y -s last -a claude-code -a codex'])
        self.assertIn('exists: shared', result.stdout)
        for skill in ('second', 'third', 'dangling-claude', 'dangling-codex'):
            self.assertIn('partial: ' + skill + ' ', result.stderr)
        self.assertEqual([report.read_text() for report in reports], ['local report'] * 2)
        self.assertEqual(os.readlink(self.home / '.claude/skills/dangling-claude'), '../missing')
        self.assertEqual(os.readlink(self.home / '.agents/skills/dangling-codex'), '../missing')


class SyncTest(RepositoryCase):
    def test_generation_preserves_source_and_is_nonmutating_when_checked(self):
        self.put('claude/skills/demo/private.md', 'PRIVATE_SENTINEL')
        expected = generate.build(self.root)
        self.assertFalse((self.root / 'codex/generated').exists())
        self.assertEqual(expected, generate.build(self.root))
        self.assertTrue(expected['AGENTS.md'].startswith((self.root / 'claude/CLAUDE.md').read_bytes()))
        self.assertFalse({'source/CLAUDE.md', 'inventory.json', 'rule-index.json'} & expected.keys())
        self.assertNotIn(b'PRIVATE_SENTINEL', b''.join(expected.values()))
        generate.write(self.root, expected)
        self.assertEqual(generate.changes(self.root, expected), [])

    def test_source_edits_additions_deletions_and_renames(self):
        self.generate()
        self.put('claude/CLAUDE.md', '# Changed\n')
        git(self.root, 'mv', 'claude/skills/demo', 'claude/skills/renamed')
        self.put('claude/skills/renamed/SKILL.md', '---\nname: renamed\ndescription: Renamed skill.\n---\nDone.\n')
        self.put('claude/rules/new.md', '---\npaths:\n  - "**/*.rs"\n---\nRust.\n')
        git(self.root, 'add', 'claude/rules/new.md')
        out = self.generate()
        self.assertIn('skills/renamed/SKILL.md', out)
        self.assertFalse((self.root / 'codex/generated/skills/demo/SKILL.md').exists())
        self.assertIn('rules/new.md', out)

    def test_manual_output_edit_and_unknown_output_are_not_overwritten(self):
        out = self.generate()
        self.put('codex/generated/AGENTS.md', 'HAND_EDIT')
        with self.assertRaisesRegex(ValueError, 'edited'):
            generate.write(self.root, out)
        self.assertEqual((self.root / 'codex/generated/AGENTS.md').read_text(), 'HAND_EDIT')

    def test_native_settings_can_change_without_registration_or_export(self):
        baseline = self.generate()
        for settings in (
            {'language': 'Japanese', 'model': 'PRIVATE_MODEL_SENTINEL',
             'newKey': {'env': 'PRIVATE_SETTING_SENTINEL'},
             'enabledPlugins': {'new-plugin': True}, 'permissions': {'allow': ['Bash(*)']}, 'theme': 'dark'},
            {'language': 'Japanese'},
        ):
            self.put('claude/settings.json', json.dumps(settings))
            output = self.generate()
            self.assertEqual(output, baseline)
            self.assertNotIn(b'PRIVATE_', b''.join(output.values()))
        self.put('claude/settings.json', '{"language":"English"}')
        english = self.generate()
        self.assertIn(b'Response language: English.', english['AGENTS.md'])
        self.assertNotEqual(json.loads(english['manifest.json'])['inputs']['claude/settings.json'],
                            json.loads(baseline['manifest.json'])['inputs']['claude/settings.json'])
        self.put('claude/settings.json', '{"theme":"light"}')
        removed = self.generate()
        self.assertNotIn(b'Response language:', removed['AGENTS.md'])
        self.assertNotEqual(json.loads(removed['manifest.json'])['inputs']['claude/settings.json'],
                            json.loads(english['manifest.json'])['inputs']['claude/settings.json'])
        git(self.root, 'rm', '-f', 'claude/settings.json')
        self.assertNotIn(b'Response language:', self.generate()['AGENTS.md'])

    def test_input_symlinks_and_private_tracked_reference_are_rejected(self):
        path = self.root / 'claude/CLAUDE.md'
        path.unlink()
        path.symlink_to('/etc/hosts')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            generate.build(self.root)
        path.unlink()
        self.put('claude/CLAUDE.md', '# Common\n')
        self.put('claude/skills/ticket/reference.md', 'PRIVATE_SENTINEL')
        git(self.root, 'add', 'claude/skills/ticket/reference.md')
        with self.assertRaisesRegex(ValueError, 'private'):
            generate.build(self.root)

    def test_rule_patterns_are_preserved_without_custom_glob_restrictions(self):
        patterns = ['**/*.py', '**/*.{ts,tsx}', '.github/actions/**/*.{yml,yaml}',
                    '**/{test,tests}/**', '**/[ab]*.py', '!vendor/**']
        rule = '---\npaths:\n' + ''.join('  - "' + p + '"\n' for p in patterns) + '---\nOriginal rule.\n'
        self.put('claude/rules/python.md', rule)
        output = self.generate()
        self.assertEqual(output['rules/python.md'], rule.encode())
        index_line = '- rules/python.md: ' + ', '.join('`' + p + '`' for p in patterns)
        self.assertIn(index_line.encode(), output['AGENTS.md'])

    def test_skill_changes_do_not_require_annotation_updates(self):
        self.put('claude/skills/demo/SKILL.md', '---\nname: demo\ndescription: Demo.\nallowed-tools: Read\nargument-hint: path\n---\nOriginal instructions.\n')
        out = self.generate()
        self.assertEqual(out['skills/demo/SKILL.md'], (self.root / 'claude/skills/demo/SKILL.md').read_bytes())
        self.put('codex/skill-adaptations.json', json.dumps({'demo': {'note': 'Host note.'}}))
        self.assertIn(b'Host note.', self.generate()['skills/demo/SKILL.md'])
        git(self.root, 'rm', '-f', 'claude/skills/demo/SKILL.md')
        out = self.generate()
        self.assertFalse(any(p.startswith('skills/demo/') for p in out))
        self.assertNotIn(b'Host note.', b''.join(out.values()))

    def test_install_preserves_local_suffix_and_protected_files_then_restores(self):
        self.merged()
        codex = self.home / '.codex'
        codex.mkdir()
        (codex / 'AGENTS.md').write_text('# Local wins\n')
        (codex / 'config.toml').write_text('model = "private-choice"\n')
        (codex / 'hooks.json').write_text('{"private":"hook-trust-sentinel"}\n')
        (codex / 'auth.json').write_text('{"private":"authentication-sentinel"}\n')
        plan = install.plan(self.root, self.home)
        self.assertEqual((codex / 'AGENTS.md').read_text(), '# Local wins\n')
        install.apply(plan)
        self.assertTrue((codex / 'AGENTS.md').read_text().endswith('# Local wins\n'))
        self.assertEqual((codex / 'config.toml').read_text(), 'model = "private-choice"\n')
        self.assertEqual((codex / 'hooks.json').read_text(), '{"private":"hook-trust-sentinel"}\n')
        self.assertEqual((codex / 'auth.json').read_text(), '{"private":"authentication-sentinel"}\n')
        self.assertTrue((self.home / '.agents/skills/demo').is_symlink())
        self.assertEqual(install.plan(self.root, self.home)['changes'], [])
        install.restore(self.home)
        self.assertEqual((codex / 'AGENTS.md').read_text(), '# Local wins\n')
        self.assertFalse((self.home / '.agents/skills/demo').exists())

    def test_unrelated_commit_does_not_require_reapply_or_create_backup(self):
        self.merged()
        install.apply(install.plan(self.root, self.home))
        state_path = self.home / install.STATE
        before = state_path.read_bytes()
        backups = sorted((self.home / install.BASE / 'backups').iterdir())
        self.put('codex/README.md', '# Documentation only\n')
        git(self.root, 'add', 'codex/README.md')
        git(self.root, 'commit', '-qm', 'Update documentation')
        git(self.root, 'update-ref', 'refs/remotes/origin/main', 'HEAD')

        checked = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'install.py'), 'check',
                                  '--root', str(self.root), '--home', str(self.home)],
                                 capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertEqual(checked.stdout, '')
        self.assertEqual(state_path.read_bytes(), before)
        prepared = install.plan(self.root, self.home)
        self.assertEqual(prepared['changes'], [])
        self.assertIsNone(install.apply(prepared))
        self.assertEqual(state_path.read_bytes(), before)
        self.assertEqual(sorted((self.home / install.BASE / 'backups').iterdir()), backups)

    def test_real_changes_after_unrelated_commit_record_current_head(self):
        self.merged()
        install.apply(install.plan(self.root, self.home))
        self.put('codex/README.md', '# Documentation only\n')
        git(self.root, 'add', 'codex/README.md')
        git(self.root, 'commit', '-qm', 'Update documentation')
        git(self.root, 'update-ref', 'refs/remotes/origin/main', 'HEAD')

        link = self.home / '.agents/skills/demo'
        link.unlink()
        prepared = install.plan(self.root, self.home)
        self.assertIn('.agents/skills/demo', prepared['changes'])
        self.assertIn(install.STATE, prepared['changes'])
        install.apply(prepared)
        self.assertTrue(link.is_symlink())
        self.assertEqual(install.load_state(self.home.resolve())['commit'], git(self.root, 'rev-parse', 'HEAD'))

        self.put('claude/CLAUDE.md', '# Updated shared instructions\n')
        self.merged()
        prepared = install.plan(self.root, self.home)
        self.assertIn('.codex/AGENTS.md', prepared['changes'])
        install.apply(prepared)
        self.assertIn('# Updated shared instructions', (self.home / '.codex/AGENTS.md').read_text())
        self.assertEqual(install.load_state(self.home.resolve())['commit'], git(self.root, 'rev-parse', 'HEAD'))

    def test_state_repairs_after_unrelated_commit_record_current_head(self):
        self.merged()
        install.apply(install.plan(self.root, self.home))
        state_path = self.home / install.STATE
        for change in ('mode', 'format', 'missing_commit'):
            with self.subTest(change=change):
                self.put('codex/README.md', '# Documentation: ' + change + '\n')
                git(self.root, 'add', 'codex/README.md')
                git(self.root, 'commit', '-qm', 'Update documentation')
                git(self.root, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
                state = install.load_state(self.home.resolve())
                if change == 'mode':
                    state_path.chmod(0o644)
                elif change == 'format':
                    state_path.write_text(json.dumps(state))
                else:
                    del state['commit']
                    state_path.write_bytes(generate.json_bytes(state))

                prepared = install.plan(self.root, self.home)
                self.assertEqual(prepared['changes'], [install.STATE])
                install.apply(prepared)
                self.assertEqual(install.load_state(self.home.resolve())['commit'], git(self.root, 'rev-parse', 'HEAD'))
                self.assertEqual(state_path.stat().st_mode & 0o777, 0o600)

    def test_install_conflict_is_atomic_and_uninstall_preserves_foreign_link(self):
        self.merged()
        collision = self.home / '.agents/skills/demo'
        collision.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'collision'):
            install.plan(self.root, self.home)
        self.assertFalse((self.home / '.codex').exists())
        collision.rmdir()
        install.apply(install.plan(self.root, self.home))
        collision.unlink()
        collision.symlink_to(self.root)
        install.uninstall(self.home)
        self.assertTrue(collision.is_symlink())
        self.assertEqual(collision.resolve(), self.root.resolve())

    def test_disabled_skill_not_reenabled_and_only_merged_objects_are_read(self):
        self.merged()
        codex = self.home / '.codex'
        codex.mkdir()
        skill = self.home / '.agents/skills/demo/SKILL.md'
        config = '[[skills.config]]\npath = ' + json.dumps(str(skill)) + '\nenabled = false\n'
        (codex / 'config.toml').write_text(config)
        p = install.plan(self.root, self.home)
        self.assertIn('demo', p['skipped'])
        install.apply(p)
        self.assertFalse(skill.exists())
        self.put('claude/CLAUDE.md', '# Unmerged local change\n')
        self.assertNotIn(b'Unmerged local change', install.plan(self.root, self.home)['files']['AGENTS.md'])
        git(self.root, 'switch', '-qc', 'feature')
        with self.assertRaisesRegex(ValueError, 'unmerged'):
            install.plan(self.root, self.home)

    def test_local_ticket_reference_is_linked_only_locally_and_missing_means_unavailable(self):
        git(self.root, 'mv', 'claude/skills/demo', 'claude/skills/ticket')
        self.put('claude/skills/ticket/SKILL.md', '---\nname: ticket\ndescription: Needs private reference.\n---\nRead reference.md first.\n')
        self.put('codex/skill-adaptations.json', json.dumps({'ticket': {
            'note': 'Missing reference means unavailable.',
            'local_dependencies': {'reference.md': '.claude/skills/ticket/reference.md'},
        }}))
        self.merged()
        missing = install.plan(self.root, self.home)
        self.assertIn('ticket', missing['skipped'])
        install.apply(missing)
        reference = self.home / '.claude/skills/ticket/reference.md'
        reference.parent.mkdir(parents=True)
        reference.write_text('PRIVATE_REFERENCE_SENTINEL')
        available = install.plan(self.root, self.home)
        self.assertNotIn('ticket', available['skipped'])
        install.apply(available)
        link = self.home / '.agents/skills/ticket/reference.md'
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.read_text(), 'PRIVATE_REFERENCE_SENTINEL')
        self.assertNotIn(b'PRIVATE_REFERENCE_SENTINEL', b''.join(available['files'].values()))
        install.uninstall(self.home)
        self.assertEqual(reference.read_text(), 'PRIVATE_REFERENCE_SENTINEL')

    def test_snapshot_edits_and_global_override_are_detected(self):
        self.merged()
        install.apply(install.plan(self.root, self.home))
        (self.home / '.agents/skills/demo/SKILL.md').write_text('LOCAL EDIT')
        with self.assertRaisesRegex(ValueError, 'manually edited'):
            install.plan(self.root, self.home)

    def test_check_and_dry_run_leave_missing_home_untouched(self):
        self.merged()
        missing_home = self.home / 'not-created'
        prepared = install.plan(self.root, missing_home)
        self.assertTrue(prepared['changes'])
        self.assertFalse(missing_home.exists())

    def test_concurrent_local_edit_and_unsafe_parent_do_not_overwrite(self):
        self.merged()
        p = install.plan(self.root, self.home)
        codex = self.home / '.codex'
        codex.mkdir()
        (codex / 'AGENTS.md').write_text('Concurrent instructions\n')
        with self.assertRaisesRegex(ValueError, 'concurrent'):
            install.apply(p)
        self.assertEqual((codex / 'AGENTS.md').read_text(), 'Concurrent instructions\n')
        other = self.home / 'other'
        other.mkdir()
        (self.home / '.agents').symlink_to(other)
        with self.assertRaisesRegex(ValueError, 'unsafe parent'):
            install.plan(self.root, self.home)

    def test_frontmatter_controls_and_secret_values_do_not_pass_silently(self):
        self.put('claude/skills/demo/SKILL.md', '---\nname: demo\ndescription: A demo.\ndisable-model-invocation: true\n---\nDemo.\n')
        with self.assertRaisesRegex(ValueError, 'unclassified skill frontmatter'):
            generate.build(self.root)
        with self.assertRaisesRegex(ValueError, 'value withheld') as failure:
            generate.scan_public({'demo.md': ('ghp_' + 'x' * 40).encode()})
        self.assertNotIn('x' * 40, str(failure.exception))

    def test_install_shell_entrypoint_and_uninstaller_use_owned_state(self):
        self.merged()
        (self.root / 'scripts/codex-sync').mkdir(parents=True)
        for name in ('generate.py', 'install.py', 'python-runtime.sh'):
            shutil.copyfile(SCRIPTS / name, self.root / 'scripts/codex-sync' / name)
        for name in ('install.sh', 'uninstall.sh', 'symlink-manifest.sh'):
            shutil.copyfile(ROOT / name, self.root / name)
        env = dict(os.environ, HOME=str(self.home))
        subprocess.run(['bash', str(self.root / 'install.sh'), '--codex-only', '--dry-run'],
                       env=env, check=True, capture_output=True)
        self.assertFalse((self.home / '.codex').exists())
        subprocess.run(['bash', str(self.root / 'install.sh'), '--codex-only'],
                       env=env, check=True, capture_output=True)
        self.assertTrue((self.home / '.agents/skills/demo').is_symlink())
        subprocess.run(['bash', str(self.root / 'uninstall.sh'), '--dry-run'],
                       env=env, check=True, capture_output=True)
        self.assertTrue((self.home / '.agents/skills/demo').is_symlink())
        subprocess.run(['bash', str(self.root / 'uninstall.sh')], env=env, check=True, capture_output=True)
        self.assertFalse((self.home / '.agents/skills/demo').exists())

    def test_write_failure_rolls_back_prior_operations(self):
        self.merged()
        prepared = install.plan(self.root, self.home)
        real_replace = install.replace
        def fail_agents(path, value):
            if path.name == 'AGENTS.md' and value['kind'] == 'file' and path.parent.name == '.codex':
                raise OSError('simulated write failure')
            return real_replace(path, value)
        with patch.object(install, 'replace', side_effect=fail_agents):
            with self.assertRaisesRegex(OSError, 'simulated'):
                install.apply(prepared)
        self.assertFalse((self.home / '.agents/skills/demo').is_symlink())
        self.assertFalse((self.home / '.codex/dotfiles-sync/current').is_symlink())
        self.assertFalse((self.home / '.codex/dotfiles-sync/state.json').exists())


class RegressionTest(RepositoryCase):
    def test_native_hooks_and_agents_are_ignored_without_registration(self):
        settings = json.loads((self.root / 'claude/settings.json').read_text())
        settings['hooks'] = {'SessionStart': [{'hooks': [{'type': 'command', 'command': 'PRIVATE_HOOK_SENTINEL'}]}]}
        self.put('claude/settings.json', json.dumps(settings))
        self.put('claude/agents/new-agent.md', 'PRIVATE_AGENT_SENTINEL\n')
        self.put('claude/hooks/new-hook.py', 'raise RuntimeError("Do not execute this hook")\n')
        git(self.root, 'add', 'claude/agents', 'claude/hooks')
        output = self.generate()
        self.assertNotIn(b'PRIVATE_', b''.join(output.values()))
        inputs = json.loads(output['manifest.json'])['inputs']
        self.assertFalse(any(p.startswith(('claude/agents/', 'claude/hooks/')) for p in inputs))
        git(self.root, 'rm', '-rf', 'claude/agents', 'claude/hooks')
        self.assertEqual(output, self.generate())

    def test_global_override_blocks_apply_and_restore_refuses_later_local_edits(self):
        self.merged()
        override = self.home / '.codex/AGENTS.override.md'
        override.parent.mkdir()
        override.write_text('Local override wins\n')
        with self.assertRaisesRegex(ValueError, 'takes precedence'):
            install.plan(self.root, self.home)
        self.assertFalse((self.home / install.STATE).exists())
        override.unlink()
        install.apply(install.plan(self.root, self.home))
        agents = self.home / '.codex/AGENTS.md'
        with agents.open('a') as f:
            f.write('Later local instructions\n')
        with self.assertRaisesRegex(ValueError, 'changed since backup'):
            install.restore(self.home)
        install.uninstall(self.home)
        self.assertEqual(agents.read_text(), 'Later local instructions\n')

    def test_update_fetches_merged_snapshot_preserves_dirty_source_and_git_hooks(self):
        for name in ('generate.py', 'install.py', 'python-runtime.sh'):
            path = self.root / 'scripts/codex-sync' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SCRIPTS / name, path)
        updater = self.root / '.shell-utils/dotfiles-update'
        updater.parent.mkdir()
        shutil.copyfile(ROOT / '.shell-utils/dotfiles-update', updater)
        git(self.root, 'add', 'scripts', '.shell-utils')
        self.merged()
        install.apply(install.plan(self.root, self.home))
        bare, author = self.root.parent / 'remote.git', self.root.parent / 'author'
        git(self.root.parent, 'clone', '--bare', '-q', str(self.root), str(bare))
        git(self.root, 'remote', 'add', 'origin', str(bare))
        git(self.root.parent, 'clone', '-q', str(bare), str(author))
        git(author, 'config', 'user.name', 'Fixture author')
        git(author, 'config', 'user.email', 'author@example.invalid')
        git(author, 'config', 'commit.gpgsign', 'false')
        (author / 'claude/CLAUDE.md').write_text('# Merged upstream instructions\n')
        generate.write(author, generate.build(author))
        git(author, 'add', 'claude/CLAUDE.md', 'codex/generated')
        git(author, 'commit', '-qm', 'Reviewed upstream update')
        git(author, 'push', '-q', 'origin', 'main')
        private_settings = '{"language":"Japanese","model":"local-only-choice"}\n'
        self.put('claude/settings.json', private_settings)
        marker = self.home / 'hook-ran'
        hook = self.root / '.git/hooks/post-merge'
        hook.write_text('#!/bin/sh\nprintf preserved > ' + shlex.quote(str(marker)) + '\n')
        hook.chmod(0o755)
        original_hook = hook.read_bytes()
        (self.home / '.shell-utils').symlink_to(updater.parent)
        subprocess.run(['bash', str(self.home / '.shell-utils/dotfiles-update')],
                       env=dict(os.environ, HOME=str(self.home)), check=True, capture_output=True)
        self.assertIn('Merged upstream instructions', (self.home / '.codex/AGENTS.md').read_text())
        self.assertNotIn('local-only-choice', (self.home / '.codex/AGENTS.md').read_text())
        self.assertEqual((self.root / 'claude/settings.json').read_text(), private_settings)
        self.assertEqual(hook.read_bytes(), original_hook)
        self.assertEqual(marker.read_text(), 'preserved')
        self.assertEqual(install.plan(self.root, self.home)['changes'], [])

    def test_removing_and_renaming_skills_updates_only_owned_links(self):
        self.merged()
        install.apply(install.plan(self.root, self.home))
        git(self.root, 'mv', 'claude/skills/demo', 'claude/skills/renamed')
        self.put('claude/skills/renamed/SKILL.md', '---\nname: renamed\ndescription: Renamed skill.\n---\nDone.\n')
        self.merged()
        install.apply(install.plan(self.root, self.home))
        self.assertFalse((self.home / '.agents/skills/demo').is_symlink())
        self.assertTrue((self.home / '.agents/skills/renamed').is_symlink())
        install.restore(self.home)
        self.assertTrue((self.home / '.agents/skills/demo').is_symlink())
        self.assertFalse((self.home / '.agents/skills/renamed').is_symlink())

    def test_missing_generated_file_and_manifest_edit_are_refused(self):
        out = self.generate()
        removed = self.root / 'codex/generated/rules/python.md'
        removed.unlink()
        with self.assertRaisesRegex(ValueError, 'manually edited'):
            generate.write(self.root, out)
        removed.write_bytes(out['rules/python.md'])
        self.put('codex/generated/manifest.json', '{"files": {}, "version": 1}')
        with self.assertRaisesRegex(ValueError, 'manifest'):
            generate.write(self.root, out)

    def test_executable_skill_resource_survives_generation_and_install(self):
        self.put('claude/skills/demo/run.sh', '#!/bin/sh\nprintf resource-ok\n')
        script = self.root / 'claude/skills/demo/run.sh'
        script.chmod(0o755)
        git(self.root, 'add', 'claude/skills/demo/run.sh')
        self.merged()
        install.apply(install.plan(self.root, self.home))
        executable = self.home / '.agents/skills/demo/run.sh'
        self.assertEqual(subprocess.check_output([str(executable)], text=True), 'resource-ok')
        self.assertTrue(git(self.root, 'ls-tree', 'HEAD', 'codex/generated/skills/demo/run.sh').startswith('100755'))

    def test_disabled_directory_and_quoted_duplicate_name_are_protected(self):
        self.merged()
        config = self.home / '.codex/config.toml'
        config.parent.mkdir()
        config.write_text('[[skills.config]]\npath = ' + json.dumps(str(self.home / '.agents/skills/demo')) + '\nenabled = false\n')
        self.assertIn('demo', install.plan(self.root, self.home)['skipped'])
        config.write_text('')
        foreign = self.home / '.codex/skills/foreign/SKILL.md'
        foreign.parent.mkdir(parents=True)
        foreign.write_text('---\nname: "demo"\ndescription: Local skill\n---\nLocal content\n')
        with self.assertRaisesRegex(ValueError, 'collision'):
            install.plan(self.root, self.home)

    def test_agents_edit_during_planning_is_not_overwritten(self):
        self.merged()
        agents = self.home / '.codex/AGENTS.md'
        agents.parent.mkdir()
        agents.write_text('Original local text\n')
        def concurrent_edit(*args):
            agents.write_text('New local text\n')
        with patch.object(install, 'check_duplicate_names', side_effect=concurrent_edit):
            prepared = install.plan(self.root, self.home)
        with self.assertRaisesRegex(ValueError, 'concurrent'):
            install.apply(prepared)
        self.assertEqual(agents.read_text(), 'New local text\n')

    def test_file_created_at_managed_link_during_planning_is_preserved(self):
        self.merged()
        link = self.home.resolve() / '.agents/skills/demo'
        link.parent.mkdir(parents=True, exist_ok=True)
        real_capture = install.capture
        def edit_after_capture(path):
            before = real_capture(path)
            if path == link:
                link.write_text('Concurrent local data\n')
            return before
        with patch.object(install, 'capture', side_effect=edit_after_capture):
            prepared = install.plan(self.root, self.home)
        with self.assertRaisesRegex(ValueError, 'concurrent'):
            install.apply(prepared)
        self.assertEqual(link.read_text(), 'Concurrent local data\n')

    def test_state_changed_during_uninstall_planning_is_preserved(self):
        self.merged()
        install.apply(install.plan(self.root, self.home))
        state_path = self.home / install.STATE
        real_load_state = install.load_state
        def update_after_load(home):
            state = real_load_state(home)
            state_path.write_text(json.dumps(dict(state, commit='f' * 40)))
            return state
        with patch.object(install, 'load_state', side_effect=update_after_load):
            with self.assertRaisesRegex(ValueError, 'concurrent'):
                install.uninstall(self.home)
        self.assertEqual(json.loads(state_path.read_text())['commit'], 'f' * 40)
        self.assertTrue((self.home / '.agents/skills/demo').is_symlink())

    def test_agents_edit_during_transaction_is_preserved_on_rollback(self):
        self.merged()
        prepared = install.plan(self.root, self.home)
        agents = self.home / '.codex/AGENTS.md'
        real_replace = install.replace
        def edit_after_first_link(path, value):
            real_replace(path, value)
            if path.name == 'current' and value['kind'] == 'link':
                agents.write_text('Concurrent local instructions\n')
        with patch.object(install, 'replace', side_effect=edit_after_first_link):
            with self.assertRaisesRegex(ValueError, 'concurrent'):
                install.apply(prepared)
        self.assertEqual(agents.read_text(), 'Concurrent local instructions\n')
        self.assertFalse((self.home / '.codex/dotfiles-sync/current').is_symlink())

    def test_symlinks_entrypoint_propagates_sync_failure(self):
        self.merged()
        (self.root / 'scripts/codex-sync').mkdir(parents=True)
        for name in ('generate.py', 'install.py', 'python-runtime.sh'):
            shutil.copyfile(SCRIPTS / name, self.root / 'scripts/codex-sync' / name)
        for name in ('install.sh', 'symlink-manifest.sh'):
            shutil.copyfile(ROOT / name, self.root / name)
        install.apply(install.plan(self.root, self.home))
        (self.home / '.codex/AGENTS.md').write_text('HAND EDIT\n')
        result = subprocess.run(['bash', str(self.root / 'install.sh'), '--symlinks-only'],
                                env=dict(os.environ, HOME=str(self.home)), capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b'Symlink setup complete!', result.stdout)



class PythonRuntimeTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'repo'
        self.home = Path(temporary.name) / 'home'
        self.bin = Path(temporary.name) / 'bin'
        self.bin.mkdir()
        state = self.home / '.codex/dotfiles-sync/state.json'
        state.parent.mkdir(parents=True)
        state.write_text('{}\n')
        shutil.copytree(SCRIPTS, self.root / 'scripts/codex-sync')
        for name in ('install.sh', 'uninstall.sh', 'symlink-manifest.sh',
                     '.shell-utils/dotfiles-doctor.sh', '.shell-utils/dotfiles-update'):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        (self.home / '.shell-utils').symlink_to(self.root / '.shell-utils')
        for name in ('bash', 'dirname', 'date', 'readlink', 'uname'):
            (self.bin / name).symlink_to(shutil.which(name))
        self.script('whoami', '#!/bin/bash\nprintf "fixture-user\\n"\n')
        self.script('git', '#!/bin/bash\n'
                    'printf "%s\\n" "$*" >> "$HOME/git-calls"\n'
                    'case "$*" in *"branch --show-current") printf "main\\n" ;; esac\n')
        (self.root / 'scripts/codex-sync/install.py').write_text(
            'import os, sys, tomllib\n'
            'print("sync fixture current")\n'
            'print(" ".join(sys.argv[1:]))\n'
            'raise SystemExit(int(os.environ.get("FIXTURE_EXIT", "0")))\n')
        self.commands = {
            'doctor': ['bash', '-c', 'source "$1"; check_codex_sync; finish', 'bash',
                       str(self.home / '.shell-utils/dotfiles-doctor.sh')],
            'install': ['bash', str(self.root / 'install.sh'), '--codex-only', '--dry-run'],
            'uninstall': ['bash', str(self.root / 'uninstall.sh'), '--dry-run'],
            'update': ['bash', str(self.home / '.shell-utils/dotfiles-update')],
        }

    def script(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def supported_python(self, name):
        self.script(name, '#!/bin/bash\n'
                    'if [ "$1" != -c ]; then\n'
                    f'  printf "%s\\n" {shlex.quote(name)} >> "$HOME/runtime-log"\n'
                    'fi\n'
                    f'exec {shlex.quote(sys.executable)} "$@"\n')

    def run_entry(self, command, fixture_exit=0):
        return subprocess.run(command, text=True, capture_output=True,
                              env={'HOME': str(self.home), 'PATH': str(self.bin),
                                   'FIXTURE_EXIT': str(fixture_exit)})

    def test_entrypoints_select_supported_alias_or_report_unmet_requirement(self):
        for situation in ('old-plus-alias', 'unsupported-only', 'missing'):
            for name in ('python3', 'python3.13'):
                (self.bin / name).unlink(missing_ok=True)
            if situation != 'missing':
                self.script('python3', '#!/bin/bash\n'
                            'if [ "$1" = -c ]; then exit 1; fi\n'
                            'printf "UNSUPPORTED_RUNTIME_EXECUTED\\n" >&2\nexit 1\n')
            if situation == 'old-plus-alias':
                self.supported_python('python3.13')

            for entry, command in self.commands.items():
                with self.subTest(situation=situation, entry=entry):
                    runtime_log = self.home / 'runtime-log'
                    runtime_log.unlink(missing_ok=True)

                    result = self.run_entry(command)
                    output = result.stdout + result.stderr

                    self.assertNotIn('UNSUPPORTED_RUNTIME_EXECUTED', output)
                    self.assertNotIn('Traceback', output)
                    if situation == 'old-plus-alias':
                        self.assertEqual(result.returncode, 0, output)
                        self.assertEqual(result.stderr, '')
                        self.assertEqual(runtime_log.read_text(), 'python3.13\n')
                        self.assertIn('sync fixture current', output)
                        if entry in ('install', 'uninstall'):
                            self.assertIn('--dry-run', output)
                    else:
                        expected_exit = 127 if situation == 'missing' and entry != 'doctor' else 1
                        self.assertEqual(result.returncode, expected_exit, output)
                        self.assertFalse(runtime_log.exists())
                        self.assertNotIn('sync fixture current', output)
                        self.assertIn('Python 3.11+', output)
                        message = ('Python is not installed' if situation == 'missing'
                                   else 'Python 3.11+ is unavailable')
                        self.assertIn(message, output)
                    if entry == 'update':
                        calls = (self.home / 'git-calls').read_text().splitlines()[-3:]
                        self.assertEqual(calls, [f'-C {self.root} branch --show-current',
                                                f'-C {self.root} fetch --prune origin main',
                                                f'-C {self.root} merge --ff-only origin/main'])

    def test_entrypoints_preserve_selected_installer_failure_status(self):
        self.supported_python('python3')
        commands = dict(self.commands)
        commands['symlinks'] = ['bash', str(self.root / 'install.sh'), '--symlinks-only']

        for entry, command in commands.items():
            with self.subTest(entry=entry):
                result = self.run_entry(command, fixture_exit=23)

                expected_exit = 1 if entry in ('doctor', 'symlinks') else 23
                self.assertEqual(result.returncode, expected_exit, result.stdout + result.stderr)
                self.assertNotIn('Symlink setup complete!', result.stdout)

    def test_uninstall_without_owned_state_does_not_require_python(self):
        (self.home / '.codex/dotfiles-sync/state.json').unlink()

        result = self.run_entry(self.commands['uninstall'])

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('Python', result.stdout + result.stderr)
        self.assertFalse((self.home / 'runtime-log').exists())


class SkillManifestTest(RepositoryCase):
    def manifest_errors(self, root):
        output = subprocess.check_output(
            ['bash', '-c', r'source "$1"; printf "%s\0" "${MANIFEST_CLAUDE_FILES[@]}"',
             'manifest', str(root / 'symlink-manifest.sh')], text=True)
        declared = {'claude/' + name for name in output.split('\0') if name.startswith('skills/')}
        tracked = set(filter(None, git(root, 'ls-files', '-z', '--', 'claude/skills').split('\0')))
        private = {name for name in declared | tracked if name.endswith('/reference.md') or
                   re.search(r'(^|/)(\.env.*|credentials[^/]*|secrets[^/]*)$', name)}
        return ([f'Private resource must not be tracked or distributed: {name}' for name in sorted(private)] +
                [f'Tracked skill resource and manifest disagree: {name}' for name in sorted((declared ^ tracked) - private)])

    def test_repository_public_skill_resources_are_distributed(self):
        self.assertEqual(self.manifest_errors(ROOT), [])

    def test_tracked_resource_omissions_and_private_entries_are_detected(self):
        manifest = 'MANIFEST_CLAUDE_FILES=(CLAUDE.md skills/demo/SKILL.md%s)\n'
        self.put('symlink-manifest.sh', manifest % '')
        self.put('claude/skills/ticket/reference.md', 'local fixture')
        self.assertEqual(self.manifest_errors(self.root), [])

        self.put('claude/skills/demo/guide.md', 'public fixture')
        git(self.root, 'add', 'claude/skills/demo/guide.md')
        self.assertEqual(len(self.manifest_errors(self.root)), 1)
        self.put('symlink-manifest.sh', manifest % ' skills/demo/guide.md')
        self.assertEqual(self.manifest_errors(self.root), [])

        git(self.root, 'add', 'claude/skills/ticket/reference.md')
        for entry in ('', ' skills/ticket/reference.md'):
            with self.subTest(entry=entry):
                self.put('symlink-manifest.sh', manifest % (' skills/demo/guide.md' + entry))
                self.assertEqual(self.manifest_errors(self.root), [
                    'Private resource must not be tracked or distributed: claude/skills/ticket/reference.md'])

    def test_public_template_install_and_uninstall_preserve_local_files(self):
        for name in ('install.sh', 'uninstall.sh', 'symlink-manifest.sh', 'scripts/codex-sync/python-runtime.sh'):
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, self.root / name)
        self.put('claude/skills/ticket/reference.example.md', 'public template')
        self.put('claude/skills/ticket/reference.md', 'private source fixture')
        env = dict(os.environ, HOME=str(self.home))
        template = self.home / '.claude/skills/ticket/reference.example.md'
        reference = template.with_name('reference.md')

        subprocess.run(['bash', str(self.root / 'install.sh'), '--symlinks-only'],
                       env=env, check=True, capture_output=True)
        self.assertTrue(template.is_symlink())
        self.assertEqual(template.read_text(), 'public template')
        self.assertFalse(reference.exists() or reference.is_symlink())
        subprocess.run(['bash', str(self.root / 'uninstall.sh')], env=env, check=True, capture_output=True)
        self.assertFalse(template.exists() or template.is_symlink())

        reference.write_text('machine-local fixture')
        for foreign_link in (False, True):
            with self.subTest(foreign_link=foreign_link):
                if foreign_link:
                    template.symlink_to(reference)
                else:
                    template.write_text('machine-local fixture')
                subprocess.run(['bash', str(self.root / 'uninstall.sh')], env=env, check=True, capture_output=True)
                self.assertEqual(template.is_symlink(), foreign_link)
                if foreign_link:
                    self.assertEqual(os.readlink(template), str(reference))
                self.assertEqual(template.read_text(), 'machine-local fixture')
                self.assertEqual(reference.read_text(), 'machine-local fixture')
                template.unlink()


if __name__ == '__main__':
    unittest.main()
