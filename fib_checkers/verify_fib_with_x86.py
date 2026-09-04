#!/usr/bin/env python3
"""Does fib come out right as MACHINE CODE? The emitted bytes are executed.

The other two verifiers run a binary that zig linked. This one takes the x86-64
the Codex back end emitted, mmaps it executable, and CALLS it -- so it is the
only one that tests the code generator's actual output rather than a zig
translation of the same program.

    x86emit                     -> a CDX dump plus a symbol map
    f3_run <dump>               -> mmap, find `fib`, call it, check the answers

Nothing is patched: `finalize` resolved every call before serialising, which is
the difference between this and a pre-finalize dump.
"""
import os
import re
import sys

import common as c

S = c.sandbox()
x86emit = c.need(S / 'x86emit', 'run ./build.sh x86emit')
zig = os.environ.get('ZIG', os.path.expanduser('~/zig-0.16.0/zig'))

work = S / 'fib_checkers'
work.mkdir(exist_ok=True)
dump = work / 'x86-fib.cdx'
runner = work / 'f3_run'

# The emitter prints to stderr, as every Codex program here does.
r = c.run([str(x86emit)])
out = r.stderr or r.stdout
if not out.strip():
    c.fail(f'x86emit printed nothing (rc={r.returncode})')
dump.write_text(out)

if not runner.exists():
    b = c.run([zig, 'build-exe', str(c.REPO / 'fib_checkers' / 'f3_run.zig'),
               f'-femit-bin={runner}'], cwd=work)
    if b.returncode:
        c.fail(f'building f3_run failed:\n{b.stderr[:400]}')

got = c.run([str(runner), str(dump)])
report = (got.stdout + got.stderr).strip()
if got.returncode != 0 or 'F3 PASS' not in report:
    c.fail(f'executing the emitted machine code:\n{report[:600]}')

syms = len(re.findall(r'^0x[0-9a-f]+ ', out, re.M))
print(f'PASS  emitted x86-64, executed: {report.splitlines()[-1]}')
print(f'      {len(out)} bytes of dump, {syms} symbols')
sys.exit(0)
