#!/usr/bin/env -S python3 -B
"""Does fib come out right through the NATIVE chain? No QEMU at all.

    codexir < fib.codex 2> fib.ir && zigemit < fib.ir 2> fib.zig && zig build-exe

This is the cheap one -- 0.09 seconds for the two Codex tools, plus whatever
zig takes to link -- and it is the whole reason those two tools are built on
bare metal in the first place. Everything downstream of a build gets to use
this instead of a guest.
"""
import subprocess
import sys

import common as c

S = c.sandbox()
codexir = c.need(S / 'codexir', 'run ./build.sh codexir')
zigemit = c.need(S / 'zigemit', 'run ./build.sh zigemit')
zig = c.need(__import__('os').environ.get('ZIG', __import__('os').path.expanduser('~/zig-0.16.0/zig')),
             'set ZIG to your zig binary')

work = S / 'fib_checkers'
work.mkdir(exist_ok=True)
ir, zg, exe = work / 'zig-fib.ir', work / 'zig-fib.zig', work / 'zig-fib'

# Output is on stderr for both tools: print-text is cx_print is std.debug.print.
with open(c.FIB, 'rb') as f, open(ir, 'wb') as o:
    r = subprocess.run([str(codexir)], stdin=f, stdout=subprocess.DEVNULL, stderr=o)
if not ir.stat().st_size:
    c.fail('codexir produced no IR')
with open(ir, 'rb') as f, open(zg, 'wb') as o:
    subprocess.run([str(zigemit)], stdin=f, stdout=subprocess.DEVNULL, stderr=o)
if not zg.stat().st_size:
    c.fail('zigemit produced no zig')

b = c.run([str(zig), 'build-exe', str(zg), f'-femit-bin={exe}'], cwd=work)
if b.returncode:
    c.fail(f'zig build-exe failed:\n{b.stderr[:400]}')

got = c.run([str(exe)])
sys.exit(c.check(got.stdout + got.stderr, 'native codexir | zigemit',
                 f'  ({ir.stat().st_size} bytes of IR)'))
