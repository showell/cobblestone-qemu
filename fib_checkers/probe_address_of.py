#!/usr/bin/env -S python3 -B
"""What does `address-of` answer when the program runs on REAL x86?

`address-of` is typed `forall a. a -> Integer` and emitted on bare metal by
`emit-identity-builtin` -- the value itself, no load. Every hosted plug has to
forge that answer, and the three forgeries disagree: the C# plug emits the
constant `0L`, the wasm plug passes the argument through, the zig plug returns
a heap-relative offset. This asks the only arm that is not forging anything.

It matters because the compiler reads the answer. `Types/Unifier.codex` tests
`address-of x == 0` in ten places to mean ABSENT, and `mkey-type` mixes
address-of answers into a hash-cons key that `cons-probe-at` matches in FULL
and then ADOPTS on, with no structural re-check. If the first constructor of a
payload-free union answers 0, then `mode-ordinal OvError` and
`real-width-ordinal RwF64` -- both first constructors -- return the absent
answer for a value that is present.

The zig arm answers 0 for MA, 0 for the integer 0, and 0 for every text
literal. This says whether bare metal does the same. It prints rather than
asserts: there is no gold here, the answer IS the finding.

Needs `X86EMIT_SUBJECT=addrof ./build.sh x86emit` -- the x86 harness compiles
its subject IN, so the fib-subject tool cannot answer this.
"""
# `-B` in the shebang only applies when this is run as ./name.py. Run as
# `python3 name.py` it does not, and the import below then writes a __pycache__
# into a repository that has no ignore rules on purpose -- which is how five
# .pyc files once reached a commit. Set before the first import, not after.
import sys
sys.dont_write_bytecode = True


import common as c

LABELS = ['payload-free MA', 'payload-free MB', 'payload-free MC',
          'mixed WNone', 'mixed WSome 5', 'mixed WSome 5 again', 'integer 7']

S = c.sandbox()
c.need_codex_root(S)
x86emit = c.need(S / 'x86emit', 'X86EMIT_SUBJECT=addrof ./build.sh x86emit')
sys.path.insert(0, str(c.REPO))
printed = c.boot_emitted(x86emit, S / 'fib_checkers', 'addrof')

vals = printed.splitlines()
# The line count is also what tells a fib-subject x86emit from an addrof one:
# PROVENANCE records the target and not the subject, so the tool cannot be
# identified before it runs. fib prints one line, this prints seven.
if len(vals) != len(LABELS):
    c.fail(f'expected {len(LABELS)} lines, the booted probe printed {len(vals)} -- '
           f'if this is one line, the sandbox holds a fib-subject x86emit and needs '
           f'X86EMIT_SUBJECT=addrof:\n{printed}')

print('      bare metal, booted on real x86:')
for label, v in zip(LABELS, vals):
    flag = '   <-- collides with the `== 0` absence sentinel' if v.strip() == '0' else ''
    print(f'        {label:<22} {v.strip()}{flag}')

zero = [l for l, v in zip(LABELS, vals) if v.strip() == '0']
same = vals[4].strip() == vals[5].strip()
print()
print(f'      {len(zero)} of {len(LABELS)} answer 0' + (f': {", ".join(zero)}' if zero else ''))
print(f'      two separately built `WSome 5`: '
      f'{"THE SAME answer" if same else "DIFFERENT answers"} '
      f'({vals[4].strip()} and {vals[5].strip()})')
sys.exit(0)
