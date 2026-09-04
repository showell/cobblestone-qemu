#!/usr/bin/env python3
"""Generate X86EmitHarness.codex: the x86-64 back end over one subject.

**THIS SUBJECT IS SHAPED DIFFERENTLY FROM THE OTHER TWO, and the difference is
the back end's, not a shortcut here.** `codexir` and `zigemit` are filters --
stdin in, an answer on stderr -- because their entry points take a parsed
chapter and hand back Text. `x86-64-emit-cdx` does not: it needs the deck seal
and lift setup that `emit_harness.py` builds around it, so the subject is
compiled IN rather than read at run time. What comes out is a program that emits
one known subject's machine code, which is what the ladder's `ir_to_x86` rung
was, minus the rung.

fib is chosen for what it does NOT need. Integers are machine words, so its
arithmetic is a bare `add`; its two self-calls are its only fixup surface; and it
touches no rodata, no runtime helper and no absolute address. `double` rides
along as a five-byte frameless leaf.

The ladder's version carried a second subject -- a real compiler chapter, under
`ir_to_x86_on_cce` -- so that one bundle answered two questions. That one is not
here yet. It is the obvious next addition and it is deliberately not day one.
"""
import os
import pathlib
import sys

from emit_harness import harness_source

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from roots import out_root  # noqa: E402

FIB = (
    'Chapter: Fib\n'
    '\n'
    'Section: Math\n'
    '  fib : Integer -> Integer\n'
    '  fib (n) =\n'
    '   if n <= 1 then n\n'
    '   else fib (n - 1) + fib (n - 2)\n'
    '\n'
    '  double : Integer -> Integer\n'
    '  double (n) = n + n\n'
    '\n'
    'Section: Main\n'
    '  opening : [Console] Nothing = act\n'
    '   print-line-uni (show (fib 20))\n'
    '  end\n'
)

# ADDROF asks what `address-of` answers when the program runs on REAL x86 with
# bare metal's own value representation, which is the one thing no hosted arm
# can tell us. It is trimmed to what fib already proves the back end can do --
# integers, `show`, self-contained constructors -- because a probe that fails to
# boot for an unrelated reason answers nothing. No text literal on purpose: the
# harness note above says fib was chosen for touching no rodata.
ADDROF = (
    'Chapter: AddrOfProbe\n'
    '\n'
    'Section: Subjects\n'
    '  Mode =\n'
    '   | MA\n'
    '   | MB\n'
    '   | MC\n'
    '\n'
    '  Wrapped =\n'
    '   | WNone\n'
    '   | WSome (Integer)\n'
    '\n'
    'Section: Main\n'
    '  opening : [Console] Nothing = act\n'
    '   print-line-uni (show (address-of MA))\n'
    '   print-line-uni (show (address-of MB))\n'
    '   print-line-uni (show (address-of MC))\n'
    '   print-line-uni (show (address-of WNone))\n'
    '   print-line-uni (show (address-of (WSome 5)))\n'
    '   print-line-uni (show (address-of (WSome 5)))\n'
    '   print-line-uni (show (address-of 7))\n'
    '  end\n'
)

SUBJECTS = {'fib': FIB, 'addrof': ADDROF}

# The chapter name and walker prefix reach the compiled unit as Codex
# identifiers and are not this subject's name; they stay as the ladder had them.
want = os.environ.get('X86EMIT_SUBJECT', 'fib')
if want not in SUBJECTS:
    raise SystemExit(f"X86EMIT_SUBJECT={want!r}: known subjects are {sorted(SUBJECTS)}")
out = harness_source('FibxHarness', 'fibx', [(f'x86emit_on_{want}', SUBJECTS[want])])
dest = out_root() / 'X86EmitHarness.codex'
dest.write_text(out)
print(f'{dest}: {len(out)} bytes, subject x86emit_on_{want}')
