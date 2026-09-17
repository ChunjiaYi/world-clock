"""Run with the same Python environment that holds requirements-build.txt."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
subprocess.run([
    sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
    '--onefile', '--windowed', '--name', 'WorldClock',
    '--collect-all', 'tzdata',
    '--distpath', str(root / 'dist'), '--workpath', str(root / 'build'),
    '--specpath', str(root / 'build'),
    str(root / 'world_clock.py'),
], cwd=root, check=True)
print('Built:', root / 'dist' / 'WorldClock.exe')
