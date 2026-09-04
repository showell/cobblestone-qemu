#!/usr/bin/env python3
"""The two directories this repo needs: what to READ, and where to WRITE.

CODEX is the checkout under test. `$CODEX_ROOT` names it. Nothing is guessed --
a directory qualifies only by holding the compiler's driver, and a failed search
raises rather than falling back to a plausible-looking path. A build silently
pointed at the wrong checkout would produce a tool nobody can attribute.

OUT is where everything generated goes, and it is NEVER this repository. That is
the whole reason this file exists rather than each script deriving its own
paths: the repo this one was carved out of grew to 347 MB, of which 343 MB was
output written beside the scripts that produced it, invisible because
`.gitignore` covered for it. There are no ignore rules here. Anything that lands
in this checkout shows up in `git status`, immediately, and that is the alarm.

`$SANDBOX` names a run directory; `build.sh` cuts one. A missing sandbox is a
REFUSAL rather than a fallback -- a fallback that is convenient every time is a
rule enforced none of the time.
"""

import os
import pathlib

MARKER = pathlib.Path('codex') / 'compiler' / 'opening.codex'
HERE = pathlib.Path(__file__).resolve().parent


class RootError(RuntimeError):
    """A root was not named, or what was named is not what it claims to be."""


def codex_root():
    named = os.environ.get('CODEX_ROOT')
    if not named:
        raise RootError(
            'CODEX_ROOT is not set. It names the Codex checkout to build from.\n'
            '  export CODEX_ROOT=~/showell_repos/<a codex checkout>')
    path = pathlib.Path(named).expanduser().resolve()
    if not (path / MARKER).is_file():
        raise RootError(f'CODEX_ROOT={named} is not a Codex checkout: no {MARKER} under {path}')
    return path


def out_root():
    named = os.environ.get('SANDBOX')
    if not named:
        raise RootError(
            'no $SANDBOX, so there is nowhere to write. Generated files never go in\n'
            '  this repository. build.sh cuts a sandbox; or name one yourself:\n'
            '      SANDBOX=~/runs/<label> ./build.sh')
    path = pathlib.Path(named).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path



if __name__ == '__main__':
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else 'codex'
    try:
        print(codex_root() if which == 'codex' else out_root())
    except RootError as why:
        # A refusal is a message, not a stack trace. The shell and PowerShell
        # callers show what this prints, and a traceback buries the one line
        # that says what to do under seven that do not.
        print(f'REFUSING: {why}', file=sys.stderr)
        sys.exit(2)
