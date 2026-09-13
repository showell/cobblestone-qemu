# cobblestone-qemu

**Run Codex on real x86 and tell me what came out.**

Bare metal under QEMU — no host runtime, no interpreter, no plug standing in for
a machine. It is the only arm that can answer questions about memory, the deck,
`address-of` and boxing, because it is the only one where those things are real.

## How do I build codexir and zigemit with bare metal?

```sh
export CODEX_ROOT=~/showell_repos/u56-candidate-friday   # the checkout to build from
./build.sh all
```

That builds three subjects, cheapest first, stopping at the first failure:

| subject | what it is | why it is here |
|---|---|---|
| `fib` | one self-contained chapter | the smoke test — exercises the whole transport with none of the bundling |
| `zigemit` | the plug, as a native tool: `.ir` → `.zig` | |
| `codexir` | the compiler, as a native tool: `.codex` → `.ir` | |
| `x86emit` | the x86-64 back end over fib | roughly the ladder's `ir_to_x86` rung, minus the rung |

`x86emit` is shaped differently from the other two tools and the difference is
the back end's, not a shortcut: `codexir` and `zigemit` are filters because
their entry points take a parsed chapter and return Text, while
`x86-64-emit-cdx` needs the deck seal `emit_harness.py` builds around it. So its
subject is compiled IN rather than read at run time, and what comes out is a
program that emits one known subject's machine code.

`./build.sh fib` on its own is the thing to run when you want to know whether
the transport works at all: it builds the ring plug, compiles `WarmupFib`
through the seed under QEMU, transpiles that IR through the plug under QEMU, and
links a native binary that prints `55` and `610`.

**Measured on the ladder droplet, 2026-09-04, against `u56-candidate`:**

| step | | |
|---|---|---|
| ring plug | | 23 s |
| **fib** | 4 s compile, 3 s transpile | **7 s** |
| **zigemit** | 25 s compile, 14 s transpile | **41 s** |
| **codexir** | 2 m 46 s compile, 1 m 52 s transpile | **4 m 43 s** |
| `./build.sh all` | | **~6 minutes** |

The whole sandbox is 52 MB. `codexir` is the expensive one because its bundled
subject is 2.6 MB of source and its IR is 9.5 MB; everything else is small.

Six minutes, not the hour this was braced for.

**What you get, and why it is worth an hour of QEMU.** After a build,

```sh
codexir <prog.codex 2>prog.ir && zigemit <prog.ir 2>prog.zig && zig build-exe prog.zig
```

is three native processes and no guest. Building these two tools is how QEMU
leaves the pipeline for everything downstream, and the difference is not
marginal: **`fib` takes 7 seconds through QEMU and 0.09 seconds through the
native chain**, and the emitted zig is byte-identical either way.

Both read `/dev/stdin` and neither looks at `argv`, so the redirects are not
style: `codexir prog.codex` aborts with a core dump, because the empty read
takes the 10-byte CCE path. Output is on stderr because `print-text` is
`std.debug.print` — a wart, not a design.

## Checking that fib still works, three ways

`fib_checkers/` holds one script per route. Three scripts rather than one with a
flag, because the routes cost 0.1 seconds, eight seconds and a build apiece, and
a flag would hide that from whoever is choosing.

| script | route | needs |
|---|---|---|
| `verify_fib_with_zig.py` | native `codexir \| zigemit`, no guest | the two tools. **No checkout at all** — which is what building them bought |
| `verify_fib_with_qemu.py` | seed + ring plug, two guests | a checkout, and it must be *the* one |
| `verify_fib_with_x86.py` | mmap the emitted machine code and **call it** | `x86emit` |
| `verify_fib_by_booting.py` | reassemble the whole binary and **boot it** | `x86emit`, a checkout, QEMU |

The two x86 ones are the only checks in the toolchain that test the code
generator's actual output rather than a zig translation of the same program, and
they are not the same check. Calling a carved-out function proves the
instructions are real; it says nothing about the binary around them -- the
header, the entry point, `__start`, the runtime init, the serial path. **A code
generator can emit a perfect function inside a file that will not start.**
Booting is the stronger claim and the slower one.

Both descend from the ladder's `f3_run.zig` and `f4_boot.py`, whose names
encoded a position in a brainstorming sequence -- F1 fib through the front end,
F2 through the x86 back end, F3 run it, F4 boot it -- that stopped existing when
F1 and F2 dissolved into rungs. They are named for their question now.

**The QEMU one also diffs its IR against the native tool's**, which is where it
stops being a smoke test — that comparison is what turned up the divergence in
`FINDINGS.md`. A verifier that only checked `55` and `610` passes both ways
round, because the wrong type does not change what fib computes.

**And it refuses a `CODEX_ROOT` that is not the sandbox's tree.** This box
exports one globally; the verifier used it silently on its first run and failed
on a chapter that does not exist in that tree. It reads the sandbox's
PROVENANCE now and refuses by name, with both shas.

## Where the artifacts go

**A sandbox, never this repository.** `build.sh` cuts one under `~/runs/` unless
`$SANDBOX` names one, and writes a `PROVENANCE` beside it recording the Codex
sha, branch, subject line and seed hash it was cut against.

**One sandbox, one commit.** If `CODEX_ROOT` moves after a sandbox is cut, the
next build against that sandbox refuses. A measurement attributed to a tree that
is no longer there is worse than no measurement — that failure cost 1,793
seconds of correct bare-metal measurement once already.

**`.gitignore` has no rules, on purpose.** A dirty `git status` in this checkout
means a script wrote where it should not have. That is the alarm; adding a rule
would silence it.

## The four steps

Every subject goes through the same pipeline, and only the last is not a VM:

1. **bundle** — assemble the subject and everything it cites (`pwsh`, upstream's
   own `plug-build-lib.ps1`)
2. **compile** — push it through the seed under QEMU, out comes IR
   (`ring_compile.py`). The seed reads what upstream's `build/compile.ps1`
   would send it: `assemble_unit.ps1` runs the checkout's own cite resolver
   over the bundle and puts what it adds ahead of it. For a complete bundle
   that is Foreword ListUtils and Tuple, which every unit gets because `for`
   desugars to `map-list` and a tuple to `MkTup<N>`.
3. **transpile** — push that IR through the ring plug under QEMU, out comes zig
   (`plug_run_ring.py`)
4. **build** — `zig build-exe`, on the host

The ring plug is rebuilt from source before the first subject, because a stale
`ringplug.cdx` silently stamps yesterday's emitter onto today's tools.

## The transport, and why it is the valuable part

`ring_compile.py` feeds a guest through a ring buffer, injecting the write
position over the gdbstub and verifying the ring head. Around it sit guards that
are each a recorded ouch rather than a precaution:

- the guest stall at exactly `RING_SIZE` on the first wrap **fires spuriously** —
  it stalled once, then built clean on the next three tries from byte-identical
  input. One red means nothing. Retry before concluding.
- memory bounds, added after an emitted binary ballooned past 3 GB and livelocked
  the whole host twice
**There is no compute lock.** There was one, it served its purpose, and it was
never rock solid — so it is gone rather than half-trusted. One guest at a time is
a thing we do by being careful. A `zig run` started beside a guest is still
enough to stall it; if that burns us again we will add something back, and it
will be something we believe.

## What is deliberately not here

The rungs. This repo answers "what did bare metal produce", not "does bare metal
agree with the zig plug about stage seven". Comparison belongs to whoever asked
the question.

`codexzig` is still built in **codex-zig-transpiler**, and some transport
machinery is duplicated there for now. That is a known overlap and a short-term
one.
