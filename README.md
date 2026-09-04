# codex-qemu

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
   (`ring_compile.py`)
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
