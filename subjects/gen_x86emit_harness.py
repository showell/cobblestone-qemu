#!/usr/bin/env python3
"""Generate X86EmitHarness.codex: the x86-64 back end over fib.

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

# The chapter name and walker prefix reach the compiled unit as Codex
# identifiers and are not this subject's name; they stay as the ladder had them.
out = harness_source('FibxHarness', 'fibx', [('x86emit_on_fib', FIB)])
dest = out_root() / 'X86EmitHarness.codex'
dest.write_text(out)
print(f'{dest}: {len(out)} bytes, subject x86emit_on_fib')
