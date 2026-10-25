"""Run local acceptance checks, including steering; derive totals from discovery.

Node is only needed for JS verification. No fixed test total is maintained.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import re
import unittest
root=Path(__file__).resolve().parents[1]
if not shutil.which('node'):
    sys.exit('FAIL: Node is required for browser-engine/UI tests (not for demo or generation).')
suite = unittest.defaultTestLoader.discover(str(root/'tests'))
result = unittest.TextTestRunner(verbosity=2).run(suite)
browser = subprocess.run(['node','tests/browser.test.js'], cwd=root, capture_output=True, text=True)
print(browser.stdout, end='')
print(browser.stderr, end='', file=sys.stderr)
js_passed = len(re.findall(r'^PASS ', browser.stdout, re.MULTILINE))
failed = len(result.failures) + len(result.errors) + int(browser.returncode != 0)
passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped) + js_passed
print(f'Acceptance suite: {passed} passed, {failed} failed, {len(result.skipped)} skipped.')
sys.exit(0 if result.wasSuccessful() and browser.returncode == 0 else 1)
