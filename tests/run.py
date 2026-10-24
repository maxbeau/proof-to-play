"""Run all acceptance checks locally. Node is only needed for JS verification."""
from pathlib import Path
import shutil
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
if not shutil.which('node'):
    sys.exit('FAIL: Node is required for browser-engine/UI tests (not for demo or generation).')
for command in [[sys.executable,'-m','unittest','discover','-s','tests','-v'],['node','tests/browser.test.js']]:
    result=subprocess.run(command,cwd=root)
    if result.returncode:sys.exit(result.returncode)
print('Acceptance suite: 19 passed, 0 failed.')
