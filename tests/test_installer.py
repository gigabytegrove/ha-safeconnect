"""Exercise Docker-host installer with a fake docker CLI (no actual HA host)."""
import os
from pathlib import Path
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parents[1]


def _mock(tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cli = bin_dir / "docker"
    cli.write_text(textwrap.dedent('''\
        #!/usr/bin/env python3
        import os, sys, shutil, subprocess
        from pathlib import Path
        args = sys.argv[1:]
        config = Path(os.environ['MOCK_HA_CONFIG'])
        log = Path(os.environ['MOCK_DOCKER_LOG'])
        with log.open('a') as out:
            print(' '.join(args), file=out)
        if args[0] == 'inspect':
            if '-f' in args:
                expr = args[args.index('-f')+1]
                if '.State.Running' in expr: print('true')
                elif '.Mounts' in expr: print('bind')
            sys.exit(0)
        if args[0] == 'exec':
            cmd = args[2:]
            if cmd[0] == 'test':
                destination = cmd[-1]
                mapped = config / destination.removeprefix('/config/').removeprefix('/config')
                if destination == '/config': mapped = config
                sys.exit(0 if (mapped.is_symlink() if cmd[1] == '-L' else mapped.exists()) else 1)
            if cmd[0] == 'mkdir':
                (config / cmd[-1].removeprefix('/config/')).mkdir(parents=True, exist_ok=True)
                sys.exit(0)
            if cmd[0] == 'rm':
                shutil.rmtree(config / cmd[-1].removeprefix('/config/'), ignore_errors=True)
                sys.exit(0)
            if cmd[0] == '/bin/sh' and cmd[1] == '-c':
                mapped_args = [str(config / v.removeprefix('/config/')) for v in cmd[4:]]
                proc = subprocess.run(['/bin/sh','-c',cmd[2],cmd[3],*mapped_args])
                sys.exit(proc.returncode)
        if args[0] == 'cp':
            src = Path(args[1]); target = args[2].split(':',1)[1]
            mapped = config / target.removeprefix('/config/')
            shutil.copytree(src, mapped)
            sys.exit(0)
        if args[0] == 'restart':
            print('fake-restart')
            sys.exit(0)
        sys.exit(2)
    '''), encoding="utf-8")
    cli.chmod(0o755)
    config = tmp_path / "config"
    config.mkdir()
    log = tmp_path / "docker.log"
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"], MOCK_HA_CONFIG=str(config), MOCK_DOCKER_LOG=str(log))
    return config, log, env


def test_install_and_refuse_overwrite(tmp_path):
    config, log, env = _mock(tmp_path)
    installer = ROOT / 'install-on-dockeradm.sh'
    first = subprocess.run(['bash', str(installer)], env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert (config / 'custom_components/safeford/manifest.json').is_file()
    assert 'restart' not in log.read_text()
    again = subprocess.run(['bash', str(installer)], env=env, capture_output=True, text=True)
    assert again.returncode == 3
    assert 'Refusing to overwrite' in again.stderr


def test_explicit_restart_only(tmp_path):
    config, log, env = _mock(tmp_path)
    r = subprocess.run(['bash', str(ROOT / 'install-on-dockeradm.sh'), '--restart'], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert 'restart homeassistant' in log.read_text()


def test_safe_update_preserves_config_and_backs_up(tmp_path):
    import json
    config, log, env = _mock(tmp_path)
    install = ROOT / 'install-on-dockeradm.sh'
    upgrade = ROOT / 'update-on-dockeradm.sh'
    r = subprocess.run(['bash', str(install)], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    installed = config / 'custom_components/safeford'
    manifest = installed / 'manifest.json'
    data = json.loads(manifest.read_text())
    data['version'] = '0.1.0'
    manifest.write_text(json.dumps(data))
    storage = config / '.storage'
    storage.mkdir()
    (storage / 'safeford.persisted').write_text('token-store-must-survive')
    r = subprocess.run(['bash', str(upgrade), '--restart'], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(manifest.read_text())['version'] == '0.1.1'
    backups = list((config / '.safeford-backups').glob('safeford-*'))
    assert len(backups) == 1
    assert json.loads((backups[0] / 'manifest.json').read_text())['version'] == '0.1.0'
    assert (storage / 'safeford.persisted').read_text() == 'token-store-must-survive'
    assert 'restart homeassistant' in log.read_text()

def test_update_does_not_restart_without_explicit_flag(tmp_path):
    config, log, env = _mock(tmp_path)
    r = subprocess.run(['bash', str(ROOT / 'install-on-dockeradm.sh')], env=env, capture_output=True, text=True)
    assert r.returncode == 0
    r = subprocess.run(['bash', str(ROOT / 'update-on-dockeradm.sh')], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert 'restart homeassistant' not in log.read_text()

def test_updater_refuses_missing_original(tmp_path):
    config, log, env = _mock(tmp_path)
    (config / 'custom_components').mkdir()
    r = subprocess.run(['bash', str(ROOT / 'update-on-dockeradm.sh')], env=env, capture_output=True, text=True)
    assert r.returncode == 3, r.stderr
    assert 'not installed' in r.stderr
    assert not (config / '.safeford-backups').exists()
