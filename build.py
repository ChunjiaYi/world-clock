"""Reproducible Windows build with isolated DLL discovery."""
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
env = os.environ.copy()
base = Path(sys.base_prefix)
windows = Path(os.environ.get('SystemRoot', r'C:\Windows'))
env['PATH'] = os.pathsep.join(map(str, [Path(sys.executable).parent, base, windows / 'System32', windows]))
env.pop('PYTHONPATH', None)
env.pop('PYTHONHOME', None)
env['PYINSTALLER_CONFIG_DIR'] = str(root / 'build' / 'cache')
subprocess.run([
    sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
    '--onedir', '--windowed', '--noupx', '--name', 'WorldClock',
    '--hidden-import', 'self_test',
    '--collect-all', 'tzdata',
    '--distpath', str(root / 'dist'), '--workpath', str(root / 'build'),
    '--specpath', str(root / 'build'),
    str(root / 'world_clock.py'),
], cwd=root, env=env, check=True)
toc = (root / 'build' / 'WorldClock' / 'Analysis-00.toc').read_text(encoding='utf-8')
for foreign in ('codex-runtimes', 'libheif', 'poppler'):
    if foreign in toc.lower():
        raise RuntimeError('Build contaminated by unrelated DLL search paths: ' + foreign)
print('Built:', root / 'dist' / 'WorldClock' / 'WorldClock.exe')
