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
# `-B` in the shebang only applies when this is run as ./name.py. Run as
# `python3 name.py` it does not, and the import below then writes a __pycache__
# into a repository that has no ignore rules on purpose -- which is how five
# .pyc files once reached a commit. Set before the first import, not after.
import sys
sys.dont_write_bytecode = True


import common as c

# fib 20. The subject prints one number only it prints, so the boot has a
# specific answer to be right about rather than merely "some output".
WANT = '6765'

S = c.sandbox()
c.need_codex_root(S)
x86emit = c.need(S / 'x86emit', 'run ./build.sh x86emit')

sys.path.insert(0, str(c.REPO))

printed = c.boot_emitted(x86emit, S / 'fib_checkers', 'fib')
if printed != WANT:
    c.fail(f'the emitted binary booted and printed {printed!r}, want {WANT!r}')
print(f'PASS  emitted x86-64, BOOTED: prints {WANT} (fib 20)')
sys.exit(0)
