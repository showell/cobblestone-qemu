#!/usr/bin/env -S python3 -B
"""Does the emitted binary BOOT? The strongest check here, and the slowest.

`verify_fib_with_x86.py` carves `fib` out of the emitted content, drops it in
executable memory and calls it. That proves the instructions are real and says
nothing about the binary around them -- the header, the entry point, `__start`,
the runtime init, the serial path. A code generator can emit a perfect function
inside a file that will not start.

This reassembles the whole file the way the compiler's own `emit-binary-tail`
does -- header, then content, then tail -- boots it under QEMU, and expects
fib's own program to say 6765.

WHAT IT DOES NOT DO, and the old version did: boot BOTH arms' dumps. In the
ladder this ran the bare-metal truth and the zig-plug output and compared, which
is what made it "the one check that does not depend on the two arms sharing a
mistake". Here there is one dump, because `x86emit` is the plug-built tool and
nothing yet runs the x86 back end on bare metal. That property is not carried
over, and pretending otherwise would be the more expensive mistake.

Descended from the ladder's `f4_boot.py`, rewritten. The old name encoded a
position in a brainstorming sequence -- F1 fib through the front end, F2 through
the x86 back end, F3 run it, F4 boot it -- that stopped existing when F1 and F2
dissolved into rungs. Nobody could tell what F4 was without finding a README
paragraph 1,800 lines in. It is named for its question now.
"""
import os
import sys

import common as c

# fib 20. The subject prints one number only it prints, so the boot has a
# specific answer to be right about rather than merely "some output".
WANT = '6765'

S = c.sandbox()
c.need_codex_root(S)
x86emit = c.need(S / 'x86emit', 'run ./build.sh x86emit')

sys.path.insert(0, str(c.REPO))
import codex_vm  # noqa: E402


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
            c.fail(f'{line} -- emission halted, so there are no sections to boot')
        key, _, val = line.partition(' ')
        try:
            lens[key] = int(val)
        except ValueError:
            c.fail(f'expected `key count` in the dump head, got {line!r}')
        i += 1
        if key == 'emit-diags':
            i += lens[key]
            if i >= len(lines) or lines[i] != '.':
                c.fail(f'{lens[key]} diags declared, list ends at '
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
            c.fail(f'section {name!r} has no {name}-len in the head')
        if len(by) != want:
            c.fail(f'{name}: head says {want} bytes, dump carries {len(by)}')
        out[name] = by

    for need in ('header', 'content', 'tail'):
        if need not in out:
            c.fail(f'dump has no {need} section')
    return out


r = c.run([str(x86emit)])
dump = r.stderr or r.stdout
if not dump.strip():
    c.fail(f'x86emit printed nothing (rc={r.returncode})')

s = sections(c.dump_body(dump))
cdx = s['header'] + s['content'] + s['tail']
if not cdx.startswith(b'CDX1'):
    c.fail(f'reassembled file does not start with CDX1: {cdx[:8]!r}')

work = S / 'fib_checkers'
work.mkdir(exist_ok=True)
binary = work / 'booted-fib.cdx'
binary.write_bytes(cdx)
print(f'      reassembled {len(cdx)} bytes '
      f'({len(s["header"])} header + {len(s["content"])} content + {len(s["tail"])} tail)')

out = codex_vm.run_cdx(str(binary), timeout=300, idle_timeout=120)
# The VM prints its own bookkeeping alongside the program's output.
printed = '\n'.join(
    l.rstrip('\r') for l in out.decode(errors='replace').splitlines()
    if not l.startswith(('WD:', 'HEAP:', 'STACK:'))).strip()

if printed != WANT:
    c.fail(f'the emitted binary booted and printed {printed!r}, want {WANT!r}')
print(f'PASS  emitted x86-64, BOOTED: prints {WANT} (fib 20)')
sys.exit(0)
