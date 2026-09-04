"""What the three verifiers share: where the sandbox is, and how to say so.

Each verifier answers ONE question -- does fib come out right by this route --
and says which route in its name. They are deliberately three scripts rather
than one with a flag: the routes cost 0.1 seconds, 8 seconds and one build
apiece, and a flag would hide that from whoever is choosing.
"""
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
FIB = REPO / 'subjects' / 'fib.codex'
WANT = ['55', '610']          # WarmupFib prints fib 10 and fib 15


def sandbox():
    """$SANDBOX, or the newest ~/runs directory that has the tools in it."""
    named = os.environ.get('SANDBOX')
    if named:
        return pathlib.Path(named).expanduser().resolve()
    runs = sorted(pathlib.Path.home().glob('runs/*/PROVENANCE'),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    for prov in runs:
        return prov.parent
    fail('no $SANDBOX and nothing under ~/runs; run ./build.sh first')


def prov(sb, key):
    line = [l for l in (sb / 'PROVENANCE').read_text().splitlines()
            if l.split('\t')[0] == key]
    return line[0].split('\t', 1)[1].strip() if line else None


def need_codex_root(sb):
    """Only the bare-metal route needs a checkout, and it must be THE checkout.

    **This box exports CODEX_ROOT globally**, pointing at a shared tree, so a
    verifier that merely required the variable to be set would happily boot a
    guest against a different commit than the sandbox was built from. It did:
    the ambient value was a tree from before the emitter split, and the plug
    bundle failed on a chapter that does not exist there. Reading that as a
    verification failure would have been three wrong conclusions deep.

    So the sandbox's own PROVENANCE is the authority, and a mismatch refuses.
    """
    named = os.environ.get('CODEX_ROOT')
    if not named:
        fail('this route boots a guest and re-bundles the plug, so it needs a checkout.\n'
             f"  export CODEX_ROOT=<the tree this sandbox was built from>\n"
             f"  PROVENANCE says {prov(sb, 'codex-repo')}\n"
             '  (verify_fib_with_zig.py needs no checkout at all -- that is the point of it)')
    want = prov(sb, 'codex-sha')
    got = run(['git', '-C', named, 'rev-parse', 'HEAD']).stdout.strip()
    if want and got and want != got:
        fail('CODEX_ROOT is not the tree this sandbox was built from.\n'
             f'  sandbox   {want[:12]}  ({prov(sb, "codex-branch")})\n'
             f'  CODEX_ROOT {got[:12]}  {named}\n'
             '  One sandbox, one commit. Point CODEX_ROOT at the sandbox\'s tree,\n'
             f'  or build a new sandbox against the one you meant.')


def need(path, how):
    if not pathlib.Path(path).exists():
        fail(f'no {path}\n  {how}')
    return pathlib.Path(path)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return r


def fail(why):
    print(f'FAIL: {why}')
    sys.exit(1)


def check(got, route, extra=''):
    """got is the program's output. Every verifier ends here so that a pass and
    a failure are printed the same way by all three."""
    lines = [l.strip() for l in got.strip().splitlines() if l.strip()]
    if lines != WANT:
        fail(f'{route}: fib printed {lines}, want {WANT}')
    print(f'PASS  {route}: fib prints {" and ".join(WANT)}{extra}')
    return 0
