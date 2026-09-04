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


def dump_body(out):
    """An emitter's output with the harness banner trimmed off.

    The harness prints `=== subject <name> ===` before the dump proper, because
    its unit can carry several subjects. Both x86 checkers hit this and both
    would otherwise carry their own slice; the ladder had a whole
    `split_truth.py` for the same job because its unit really did carry two.
    """
    lines = out.splitlines(keepends=True)
    start = next((i for i, l in enumerate(lines) if l.startswith('check-errors')), None)
    if start is None:
        fail(f'no `check-errors` line -- this is not an emitter dump:\n{out[:300]}')
    return ''.join(lines[start:])


def check(got, route, extra=''):
    """got is the program's output. Every verifier ends here so that a pass and
    a failure are printed the same way by all three."""
    lines = [l.strip() for l in got.strip().splitlines() if l.strip()]
    if lines != WANT:
        fail(f'{route}: fib printed {lines}, want {WANT}')
    print(f'PASS  {route}: fib prints {" and ".join(WANT)}{extra}')
    return 0


# ---------------------------------------------------------------------------
# Booting an emitted dump. Extracted here on its SECOND caller, not its first:
# `verify_fib_by_booting.py` asserts one number, and the address-of probe reads
# whatever comes out. The parsing and reassembly are identical; only the
# question differs, so only the question stays in the callers.
# ---------------------------------------------------------------------------


def sections(text):
    """Carve `header`, `content` and `tail` out of an x86 dump.

    Fails loud on every shape that is not a clean dump. The lengths are declared
    in the head and the bytes come as decimal lists, so a section that does not
    match its declared length is a CORRUPT dump rather than a short one, and
    saying so beats an IndexError twenty lines later.

    Two head shapes are not `key value`. `emit-diags N` is followed by N diag
    lines and a `.`; the ladder's parser walked straight into that `.` with
    `int('')` and had been dead for weeks, silently, because nothing in the
    sweep called it. And `CODEGEN-HALTED` means a bag with errors gated the byte
    sections off entirely, so there is nothing to carve.
    """
    lines = text.splitlines()
    lens, out, i = {}, {}, 0

    while i < len(lines) and not lines[i].startswith('---'):
        line = lines[i]
        if line.startswith('CODEGEN-HALTED'):
            fail(f'{line} -- emission halted, so there are no sections to boot')
        key, _, val = line.partition(' ')
        try:
            lens[key] = int(val)
        except ValueError:
            fail(f'expected `key count` in the dump head, got {line!r}')
        i += 1
        if key == 'emit-diags':
            i += lens[key]
            if i >= len(lines) or lines[i] != '.':
                fail(f'{lens[key]} diags declared, list ends at '
                       f'{lines[i] if i < len(lines) else "end of dump"!r} instead of "."')
            i += 1

    while i < len(lines):
        # The harness closes with `=== end <subject> ===`. Stop there rather
        # than reading it as a section name -- which is what it did, and the
        # refusal named the footer, which is how this was found in one run.
        if lines[i].startswith('==='):
            break
        name = lines[i].strip('- ')
        i += 1
        body = []
        while i < len(lines) and lines[i] != '.':
            body.append(lines[i])
            i += 1
        i += 1
        if name == 'symbols':
            continue
        by = bytes(int(t) for line in body for t in line.split())
        want = lens.get(f'{name}-len')
        if want is None:
            fail(f'section {name!r} has no {name}-len in the head')
        if len(by) != want:
            fail(f'{name}: head says {want} bytes, dump carries {len(by)}')
        out[name] = by

    for need in ('header', 'content', 'tail'):
        if need not in out:
            fail(f'dump has no {need} section')
    return out



def boot_emitted(x86emit, work, name):
    """Run an x86emit tool, reassemble its dump, boot it, return what it printed.

    The reassembly is what the compiler's own `emit-binary-tail` does: header,
    then content, then tail. The VM prints its own bookkeeping alongside the
    program's output, and those lines are dropped rather than matched around --
    a caller comparing against them would be comparing against the harness.
    """
    import codex_vm

    r = run([str(x86emit)])
    dump = r.stderr or r.stdout
    if not dump.strip():
        fail(f'x86emit printed nothing (rc={r.returncode})')

    s = sections(dump_body(dump))
    cdx = s['header'] + s['content'] + s['tail']
    if not cdx.startswith(b'CDX1'):
        fail(f'reassembled file does not start with CDX1: {cdx[:8]!r}')

    work.mkdir(exist_ok=True)
    binary = work / f'booted-{name}.cdx'
    binary.write_bytes(cdx)
    print(f'      reassembled {len(cdx)} bytes '
          f'({len(s["header"])} header + {len(s["content"])} content + {len(s["tail"])} tail)')

    out = codex_vm.run_cdx(str(binary), timeout=300, idle_timeout=120)
    return '\n'.join(
        l.rstrip('\r') for l in out.decode(errors='replace').splitlines()
        if not l.startswith(('WD:', 'HEAP:', 'STACK:'))).strip()
