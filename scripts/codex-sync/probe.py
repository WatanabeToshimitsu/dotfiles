#!/usr/bin/env python3
"""Probe native discovery in a disposable merged fixture, without model turns."""

import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading

import generate
import install


class Rpc:
    def __init__(self, state, cwd):
        env = {k: os.environ[k] for k in ('PATH', 'LANG', 'TMPDIR') if k in os.environ}
        env['CODEX_HOME'] = str(state)
        self.errors = tempfile.TemporaryFile(mode='w+')
        self.proc = subprocess.Popen(['codex', 'app-server', '--listen', 'stdio://'], cwd=cwd, env=env,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors,
                                     text=True, bufsize=1)
        self.messages = queue.Queue()
        self.sequence = 0
        threading.Thread(target=self.read, daemon=True).start()
        self.call('initialize', {'clientInfo': {'name': 'dotfiles_sync_probe', 'version': '1.0.0'},
                                 'capabilities': {'experimentalApi': True}})
        self.send({'method': 'initialized', 'params': {}})

    def read(self):
        for line in self.proc.stdout:
            self.messages.put(json.loads(line))
        self.messages.put(None)

    def send(self, message):
        self.proc.stdin.write(json.dumps(message) + '\n')
        self.proc.stdin.flush()

    def call(self, method, params):
        self.sequence += 1
        self.send({'id': self.sequence, 'method': method, 'params': params})
        while True:
            message = self.messages.get(timeout=30)
            if message is None:
                raise RuntimeError('native app-server closed before responding')
            if message.get('id') == self.sequence:
                if 'error' in message:
                    raise RuntimeError(message['error'])
                return message['result']

    def close(self):
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        self.proc.stdout.close()
        self.errors.close()


def run():
    output = generate.build(generate.ROOT)
    generate.scan_public(output)
    manifest = json.loads(output['manifest.json'])
    report = {'runtime': subprocess.check_output(['codex', '--version'], text=True, stderr=subprocess.DEVNULL).strip(),
              'fixture_merge_only': True, 'model_turns': 0, 'checks': []}
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        report['checks'].append(name)
    with tempfile.TemporaryDirectory(prefix='codex-sync-runtime-') as temporary:
        workspace = Path(temporary).resolve()
        repo, home, project = workspace / 'repo', workspace / 'user', workspace / 'project'
        repo.mkdir(); home.mkdir(); project.mkdir()
        entries = generate.tracked(generate.ROOT)
        for name in manifest['inputs']:
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(generate.read(generate.ROOT, name, entries))
        generate.git(repo, 'init', '-q', '-b', 'main')
        generate.git(repo, 'config', 'user.name', 'Sync fixture')
        generate.git(repo, 'config', 'user.email', 'sync@example.invalid')
        generate.git(repo, 'config', 'commit.gpgsign', 'false')
        generate.git(repo, 'add', 'claude', 'codex')
        generate.write(repo, output)
        generate.git(repo, 'add', 'codex/generated')
        generate.git(repo, 'commit', '-qm', 'Disposable sync fixture')
        generate.git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
        for references in manifest['local_dependencies'].values():
            for source in references.values():
                path = home / source
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('Disposable reference fixture; no real connector identifiers.\n')
        state = home / '.codex'
        state.mkdir()
        (state / 'AGENTS.md').write_text('# Local fixture instructions\nPreserve this suffix.\n')
        config = '[features]\nhooks = true\n[analytics]\nenabled = false\n'
        (state / 'config.toml').write_text(config)
        hook = state / 'hooks.json'
        hook.write_text(json.dumps({'hooks': {'PreToolUse': [{'matcher': 'Bash', 'hooks': [
            {'type': 'command', 'command': 'printf codex-sync-probe', 'timeout': 1}]}]}}))
        hook_before = hook.read_bytes()
        install.apply(install.plan(repo, home))
        check('native_config_unchanged', (state / 'config.toml').read_text() == config)
        check('native_hook_definition_unchanged', hook.read_bytes() == hook_before)
        check('local_instructions_preserved_last', (state / 'AGENTS.md').read_text().endswith('Preserve this suffix.\n'))
        rpc = Rpc(state, project)
        try:
            rpc.call('skills/extraRoots/set', {'extraRoots': [str(home / '.agents/skills')]})
            params = {'cwds': [str(project)], 'forceReload': True}
            listed = rpc.call('skills/list', params)['data'][0]
            paths = {p['name']: p for p in listed['skills'] if Path(p['path']).resolve().is_relative_to(home)}
            if not set(manifest['skills']) <= paths.keys():
                diagnostic = [(p['name'], p.get('scope'), Path(p['path']).resolve().is_relative_to(home))
                              for p in listed['skills'] if p['name'] in manifest['skills']]
                raise AssertionError('skill discovery: ' + str(diagnostic))
            check('all_generated_skills_discovered', set(manifest['skills']) <= paths.keys())
            check('no_skill_parse_errors', not listed['errors'])
            hooks = rpc.call('hooks/list', {'cwds': [str(project)]})['data'][0]
            own_hooks = [p for p in hooks['hooks'] if p['sourcePath'] == str(hook)]
            check('new_hook_remains_untrusted', len(own_hooks) == 1 and own_hooks[0]['trustStatus'] == 'untrusted')
            hook.write_bytes(hook_before.replace(b'printf codex-sync-probe', b'printf changed-codex-sync-probe'))
            changed = rpc.call('hooks/list', {'cwds': [str(project)]})['data'][0]
            changed_hooks = [p for p in changed['hooks'] if p['sourcePath'] == str(hook)]
            check('changed_hook_does_not_gain_trust', len(changed_hooks) == 1 and
                  changed_hooks[0]['trustStatus'] in ('untrusted', 'modified') and
                  changed_hooks[0]['currentHash'] != own_hooks[0]['currentHash'])
            hook.write_bytes(hook_before)
            started = rpc.call('thread/start', {'cwd': str(project), 'ephemeral': True,
                                               'sandbox': 'read-only', 'approvalPolicy': 'never'})
            check('new_thread_loads_installed_agents', str(state / 'AGENTS.md') in started['instructionSources'])
            report['skills'] = sorted(paths.keys() & set(manifest['skills']))
            report['instruction_source_loaded'] = True
        finally:
            rpc.close()
        install.restore(home)
        check('restore_preserves_original_instructions', (state / 'AGENTS.md').read_text() == '# Local fixture instructions\nPreserve this suffix.\n')
    report['result'] = 'passed'
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = generate.json_bytes(run())
    if args.output:
        args.output.write_bytes(report)
    print(report.decode(), end='')
