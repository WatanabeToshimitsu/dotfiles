import io
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts/codex-sync'
sys.path.insert(0, str(SCRIPTS))
import generate
import install
import publish


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
             'enabledPlugins': {'new-plugin': True}, 'permissions': {'allow': ['Bash(*)']}},
            {'language': 'Japanese'},
        ):
            self.put('claude/settings.json', json.dumps(settings))
            output = self.generate()
            self.assertEqual({p: v for p, v in output.items() if p != 'manifest.json'},
                             {p: v for p, v in baseline.items() if p != 'manifest.json'})
            self.assertNotIn(b'PRIVATE_', b''.join(output.values()))
        self.put('claude/settings.json', '{"language":"English"}')
        self.assertIn(b'Response language: English.', self.generate()['AGENTS.md'])
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
        for name in ('generate.py', 'install.py'):
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
        for name in ('generate.py', 'install.py'):
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

    def test_executable_skill_resource_survives_generation_install_and_publish(self):
        self.put('claude/skills/demo/run.sh', '#!/bin/sh\nprintf resource-ok\n')
        script = self.root / 'claude/skills/demo/run.sh'
        script.chmod(0o755)
        git(self.root, 'add', 'claude/skills/demo/run.sh')
        self.merged()
        install.apply(install.plan(self.root, self.home))
        executable = self.home / '.agents/skills/demo/run.sh'
        self.assertEqual(subprocess.check_output([str(executable)], text=True), 'resource-ok')
        self.put('claude/CLAUDE.md', '# Updated\n')
        commit = publish.make_commit(self.root, git(self.root, 'rev-parse', 'HEAD'), generate.build(self.root))
        self.assertTrue(git(self.root, 'ls-tree', commit, 'codex/generated/skills/demo/run.sh').startswith('100755'))

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
        for name in ('generate.py', 'install.py'):
            shutil.copyfile(SCRIPTS / name, self.root / 'scripts/codex-sync' / name)
        for name in ('install.sh', 'symlink-manifest.sh'):
            shutil.copyfile(ROOT / name, self.root / name)
        install.apply(install.plan(self.root, self.home))
        (self.home / '.codex/AGENTS.md').write_text('HAND EDIT\n')
        result = subprocess.run(['bash', str(self.root / 'install.sh'), '--symlinks-only'],
                                env=dict(os.environ, HOME=str(self.home)), capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b'Symlink setup complete!', result.stdout)


class PublisherTest(RepositoryCase):
    def publisher_fixture(self):
        for name in ('.github/workflows/ci.yml', 'scripts/codex-sync/generate.py', 'claude/hooks/remote-mutation-guard.py'):
            self.put(name, '# Trusted fixture implementation\n')
            git(self.root, 'add', name)
        self.merged()
        self.bare = self.root.parent / 'remote.git'
        git(self.root.parent, 'init', '--bare', '-q', str(self.bare))
        git(self.root, 'switch', '-qc', 'feature')
        self.put('claude/CLAUDE.md', '# PR source revision\n')
        git(self.root, 'add', 'claude/CLAUDE.md')
        git(self.root, 'commit', '-qm', 'Revise source without regenerating')
        self.expected = git(self.root, 'rev-parse', 'HEAD')
        git(self.root, 'push', '-q', str(self.bare), 'HEAD:refs/heads/feature')
        git(self.root, 'switch', '-q', 'main')
        git(self.root, 'remote', 'add', 'origin', 'https://github.com/owner/repo.git')
        self.dispatches = []
        real_run = subprocess.run
        def transport(args, **kwargs):
            args = list(args)
            if 'fetch' in args and 'https://github.com/owner/repo.git' in args:
                args[args.index('https://github.com/owner/repo.git')] = str(self.bare)
            if 'push' in args and 'origin' in args:
                args[args.index('origin')] = str(self.bare)
            result = real_run(args, **kwargs)
            if 'push' in args and result.returncode:
                raise AssertionError(result.stderr)
            return result
        self.transport = transport

    def fake_api(self, repo, suffix, token, data=None):
        if suffix == '/pulls/1':
            return {'state': 'open', 'base': {'ref': 'main'}, 'user': {'login': 'author'},
                    'head': {'repo': {'full_name': 'owner/repo'},
                             'sha': git(self.bare, 'rev-parse', 'refs/heads/feature'), 'ref': 'feature'}}
        self.assertEqual(suffix, '/actions/workflows/ci.yml/dispatches')
        self.dispatches.append(data)

    def test_full_publisher_generates_same_branch_and_dispatches_final_sha(self):
        self.publisher_fixture()
        with patch.object(publish.subprocess, 'run', side_effect=self.transport), patch.object(publish, 'api', side_effect=self.fake_api):
            result = publish.publish(self.root, 'owner/repo', 1, self.expected, 'test-token-placeholder')
        self.assertEqual(git(self.bare, 'rev-parse', 'feature'), result)
        self.assertEqual(git(self.root, 'rev-parse', result + '^'), self.expected)
        self.assertEqual(self.dispatches, [{'ref': 'feature', 'inputs': {'expected_sha': result}}])
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')
        paths = git(self.root, 'diff-tree', '--name-only', '--no-commit-id', '-r', result).splitlines()
        self.assertTrue(all(p.startswith('codex/generated/') for p in paths))

    def test_dispatch_failure_reports_pushed_sha_and_retry_does_not_commit_again(self):
        self.publisher_fixture()
        def fail_dispatch(repo, suffix, token, data=None):
            if suffix.endswith('/dispatches'):
                raise OSError('Simulated dispatch outage')
            return self.fake_api(repo, suffix, token, data)
        with patch.object(publish.subprocess, 'run', side_effect=self.transport), patch.object(publish, 'api', side_effect=fail_dispatch):
            with self.assertRaisesRegex(ValueError, 'was pushed') as failure:
                publish.publish(self.root, 'owner/repo', 1, self.expected, 'test-token-placeholder')
        pushed = git(self.bare, 'rev-parse', 'feature')
        self.assertIn(pushed, str(failure.exception))
        self.assertNotEqual(pushed, self.expected)
        with patch.object(publish.subprocess, 'run', side_effect=self.transport), patch.object(publish, 'api', side_effect=self.fake_api):
            result = publish.publish(self.root, 'owner/repo', 1, pushed, 'test-token-placeholder')
        self.assertEqual(result, pushed)
        self.assertEqual(self.dispatches, [{'ref': 'feature', 'inputs': {'expected_sha': pushed}}])

    def assert_protected_implementation_outcome(self, path, *, deleted=False):
        self.publisher_fixture()
        git(self.root, 'switch', '-q', 'feature')
        if deleted:
            git(self.root, 'rm', '-q', path)
        else:
            self.put(path, '# Unreviewed PR implementation\n')
            git(self.root, 'add', path)
        git(self.root, 'commit', '-qm', 'Change protected implementation')
        head = git(self.root, 'rev-parse', 'HEAD')
        git(self.root, 'push', '-q', str(self.bare), 'HEAD:refs/heads/feature')
        git(self.root, 'switch', '-q', 'main')
        with patch.object(publish.subprocess, 'run', side_effect=self.transport), \
             patch.object(publish, 'api', side_effect=self.fake_api), \
             patch.object(generate, 'ROOT', self.root), \
             patch.object(generate, 'build') as build, \
             patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'GH_TOKEN': 'test-token-placeholder'}), \
             patch.object(sys, 'argv', ['publish.py', '--repo', 'owner/repo', '--pr', '1', '--expected-head', head]), \
             patch.object(sys, 'stdout', new_callable=io.StringIO) as output, \
             patch.object(sys, 'stderr', new_callable=io.StringIO) as error:
            result = publish.main()
        self.assertEqual(result, 1 if deleted else 0)
        if deleted:
            self.assertIn('codex sync publisher:', error.getvalue())
            self.assertNotIn('skipped', output.getvalue())
        else:
            self.assertIn('::notice::Automatic Codex sync skipped', output.getvalue())
            self.assertEqual(error.getvalue(), '')
        build.assert_not_called()
        self.assertEqual(git(self.bare, 'rev-parse', 'feature'), head)
        self.assertEqual(self.dispatches, [])
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')

    def test_changed_ci_is_skipped_before_publication(self):
        self.assert_protected_implementation_outcome('.github/workflows/ci.yml')

    def test_changed_generator_is_skipped_before_publication(self):
        self.assert_protected_implementation_outcome('scripts/codex-sync/generate.py')

    def test_changed_guard_is_skipped_before_publication(self):
        self.assert_protected_implementation_outcome('claude/hooks/remote-mutation-guard.py')

    def test_unreadable_protected_input_still_fails_before_publication(self):
        self.assert_protected_implementation_outcome('claude/hooks/remote-mutation-guard.py', deleted=True)

    def test_pr_boundary_refuses_forks_dependabot_and_stale_heads(self):
        pr = {'state': 'open', 'base': {'ref': 'main'}, 'user': {'login': 'author'},
              'head': {'repo': {'full_name': 'owner/repo'}, 'sha': 'a' * 40, 'ref': 'feature'}}
        self.assertEqual(publish.validate_pr(pr, 'owner/repo', 'a' * 40), 'feature')
        for category in ('fork', 'dependabot', 'race'):
            candidate = json.loads(json.dumps(pr))
            if category == 'fork':
                candidate['head']['repo']['full_name'] = 'fork/repo'
            elif category == 'dependabot':
                candidate['user']['login'] = 'dependabot[bot]'
            else:
                candidate['head']['sha'] = 'b' * 40
            with self.assertRaises(ValueError):
                publish.validate_pr(candidate, 'owner/repo', 'a' * 40)

    def test_generated_commit_changes_only_owned_paths_without_touching_worktree(self):
        self.merged()
        self.put('claude/CLAUDE.md', '# Updated source\n')
        git(self.root, 'add', 'claude/CLAUDE.md')
        git(self.root, 'commit', '-qm', 'Change source')
        head = git(self.root, 'rev-parse', 'HEAD')
        before = git(self.root, 'status', '--porcelain')
        commit = publish.make_commit(self.root, head, generate.build(self.root))
        self.assertEqual(git(self.root, 'rev-parse', commit + '^'), head)
        self.assertEqual(git(self.root, 'rev-parse', 'HEAD'), head)
        self.assertEqual(git(self.root, 'status', '--porcelain'), before)
        paths = git(self.root, 'diff-tree', '--no-commit-id', '--name-only', '-r', commit).splitlines()
        self.assertTrue(paths)
        self.assertTrue(all(p.startswith('codex/generated/') for p in paths))

    def test_normal_push_succeeds_and_stale_advertised_head_is_refused(self):
        self.merged()
        bare = self.root.parent / 'remote.git'
        subprocess.run(['git', 'init', '--bare', '-q', str(bare)], check=True)
        git(self.root, 'remote', 'add', 'origin', str(bare))
        head = git(self.root, 'rev-parse', 'HEAD')
        git(self.root, 'push', '-q', 'origin', 'HEAD:refs/heads/feature')
        self.put('claude/CLAUDE.md', '# Revision one\n')
        first = publish.make_commit(self.root, head, generate.build(self.root))
        publish.push(self.root, first, 'feature', head)
        self.assertEqual(git(bare, 'rev-parse', 'refs/heads/feature'), first)
        self.put('claude/CLAUDE.md', '# Revision two\n')
        second = publish.make_commit(self.root, first, generate.build(self.root))
        with self.assertRaisesRegex(ValueError, 'raced'):
            publish.push(self.root, second, 'feature', head)
        self.assertEqual(git(bare, 'rev-parse', 'refs/heads/feature'), first)


if __name__ == '__main__':
    unittest.main()
