#!/usr/bin/env -S python3 -B
"""Build every subject and run every checker, in one fresh sandbox.

    ./run_all.py [label]           build a fresh sandbox, then check it
    SANDBOX=<dir> ./run_all.py     check a sandbox that already exists

**Every line is timestamped**, with wall clock and elapsed, because the whole
point of a fifteen-minute unattended run is reading the log afterwards and
knowing what took the time. The steps announce themselves; the substeps come
from build.sh, which times each guest itself.

Measured 2026-09-04 against `u56-candidate`: about thirteen minutes for four
subjects and four checkers. `codexir` and `x86emit` are eleven of those minutes
between them, because each is 2.6 MB of bundled source and the seed's cost is
what it READS.

A FRESH SANDBOX EVERY TIME, and never a reused one. One sandbox, one commit: a
run attributed to a tree that has moved underneath it is worse than no run. The
sandbox carries its own PROVENANCE and `rm -rf` is the whole cleanup.

CHECKING A SANDBOX SOMETHING ELSE BUILT. `$SANDBOX` naming a directory that
already has a PROVENANCE means check that one rather than build a new one --
the same contract build.sh uses, so there is no flag to remember. The checkers
already read `$SANDBOX`, and a build run through `build.sh` directly left them
no way in, which cost a whole rebuild to get a verdict. The sha in that
PROVENANCE must still be CODEX_ROOT's, for the same reason build.sh refuses
otherwise, and RESULT records that this run did not build what it checked.

BUILDS STOP AT THE FIRST FAILURE, CHECKERS DO NOT. The build order is
cheapest-first and the failure modes are shared, so a deck wall on fib means the
same wall on codexir and there is nothing to learn from proving it twice. The
checkers are independent questions about artifacts that already exist, so one
failing is a reason to run the rest, not to stop.
"""
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
CHECKERS = [
    ('zig', 'verify_fib_with_zig.py'),
    ('qemu', 'verify_fib_with_qemu.py'),
    ('x86', 'verify_fib_with_x86.py'),
    ('boot', 'verify_fib_by_booting.py'),
]
START = time.time()
LOGFILE = None      # set once the sandbox exists; every line goes to both


def log(line=''):
    if line:
        el = time.time() - START
        line = (f'{time.strftime("%H:%M:%S")}  '
                f'{int(el) // 60:2d}m{int(el) % 60:02d}s  {line}')
    print(line, flush=True)
    if LOGFILE:
        # Unbuffered to the file as well as the terminal: an unattended run that
        # dies is exactly when the last few lines matter, and they are the ones
        # a buffer eats.
        LOGFILE.write(line + '\n')
        LOGFILE.flush()


def stream(cmd, env, tag):
    """Run a child and timestamp every line it prints, as it prints it."""
    p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in p.stdout:
        line = line.rstrip()
        if line:
            log(f'  [{tag}] {line}')
    return p.wait()


def main():
    root = os.environ.get('CODEX_ROOT')
    if not root:
        raise SystemExit('CODEX_ROOT is not set. It names the checkout to build from.')
    root = str(pathlib.Path(root).expanduser().resolve())
    sha = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'],
                         capture_output=True, text=True).stdout.strip()
    branch = subprocess.run(['git', '-C', root, 'rev-parse', '--abbrev-ref', 'HEAD'],
                            capture_output=True, text=True).stdout.strip()

    qemu_sha = subprocess.run(['git', '-C', str(HERE), 'rev-parse', 'HEAD'],
                              capture_output=True, text=True).stdout.strip()
    if subprocess.run(['git', '-C', str(HERE), 'status', '--porcelain'],
                      capture_output=True, text=True).stdout.strip():
        qemu_sha += '-DIRTY'

    named = os.environ.get('SANDBOX')
    existing = None
    if named:
        cand = pathlib.Path(named).expanduser().resolve()
        if (cand / 'PROVENANCE').is_file():
            existing = cand
    if existing:
        sandbox = existing
        was = [l.split('\t', 1)[1].strip()
               for l in (sandbox / 'PROVENANCE').read_text().splitlines()
               if l.split('\t')[0] == 'codex-sha']
        if not was or was[0] != sha:
            raise SystemExit(
                f'REFUSING: {sandbox} was cut against {(was[0][:12] if was else "nothing")} '
                f'and CODEX_ROOT is now {sha[:12]}.')
    else:
        label = sys.argv[1] if len(sys.argv) > 1 else 'all'
        sandbox = pathlib.Path.home() / 'runs' / f'{time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())}-{label}'
        sandbox.mkdir(parents=True)
    global LOGFILE
    LOGFILE = open(sandbox / 'run_all.log', 'a' if existing else 'w')

    env = dict(os.environ, CODEX_ROOT=root, SANDBOX=str(sandbox),
               PYTHONDONTWRITEBYTECODE='1')

    log(f'codex     {sha[:12]}  {branch}')
    log(f'sandbox   {sandbox}')
    log(f'log       {sandbox / "run_all.log"}')
    log()

    results = []

    if existing:
        log('BUILD  skipped -- checking the sandbox that is already here')
        rc = 0
    else:
        log('BUILD  four subjects, cheapest first, stopping at the first failure')
        rc = stream([str(HERE / 'build.sh'), 'all'], env, 'build')
        results.append(('build all', rc == 0))
    if rc != 0:
        log('BUILD FAILED -- not running the checkers, which have nothing to check')
    else:
        log()
        log('CHECK  four routes to the same seven-line answer')
        for name, script in CHECKERS:
            t0 = time.time()
            rc = stream([str(HERE / 'fib_checkers' / script)], env, name)
            results.append((f'verify {name}', rc == 0))
            log(f'  [{name}] {"PASS" if rc == 0 else "FAIL"} in {time.time() - t0:.1f}s')

    log()
    for n, o in results:
        log(f'{"PASS" if o else "FAIL"}  {n}')
    total = time.time() - START
    ok = all(o for _, o in results)
    log(f'{"GREEN" if ok else "RED"} -- {sum(o for _, o in results)}/{len(results)} '
        f'in {int(total) // 60}m{int(total) % 60:02d}s')

    # RESULT is what makes a sandbox readable a week later, and what tells the
    # next person whether it finished. A sandbox with no RESULT and no running
    # process is a broken one and should be deleted.
    (sandbox / 'RESULT').write_text(
        f'codex\t{sha}\n'
        f'branch\t{branch}\n'
        f'elapsed\t{int(total)}s\n'
        f'verdict\t{"GREEN" if ok else "RED"}\n'
        f'checkers\t{qemu_sha[:12]}\n'
        + ('built\tnot by this run\n' if existing else '')
        + ''.join(f'{"PASS" if o else "FAIL"}\t{n}\n' for n, o in results))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
