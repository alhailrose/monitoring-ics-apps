import subprocess
import sys


def test_cli_version_works_without_questionary_installed():
    script = """
import builtins
import sys

real_import = builtins.__import__

def blocked_import(name, *args, **kwargs):
    if name == 'questionary':
        raise ModuleNotFoundError("No module named 'questionary'")
    return real_import(name, *args, **kwargs)

builtins.__import__ = blocked_import
sys.argv = ['monitoring-hub', '--version']

import src.app.cli.bootstrap as cli

cli.main()
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "AWS Monitoring Hub" in result.stdout
    assert "v1.4.0" in result.stdout


def test_cli_default_mode_shows_helpful_error_without_questionary():
    script = """
import builtins
import sys

real_import = builtins.__import__

def blocked_import(name, *args, **kwargs):
    if name == 'questionary':
        raise ModuleNotFoundError("No module named 'questionary'")
    return real_import(name, *args, **kwargs)

builtins.__import__ = blocked_import
sys.argv = ['monitoring-hub']

import src.app.cli.bootstrap as cli

cli.main()
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )

    combined_output = result.stdout + result.stderr
    assert result.returncode == 2
    assert "Install TUI dependencies" in combined_output
    assert "Traceback" not in combined_output
