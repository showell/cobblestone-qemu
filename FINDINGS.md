# What building on bare metal has turned up

## 1. The plug-built compiler types EVERY comparison `error`, where bare metal says `boolean`

**Found 2026-09-04, the first day this repo existed, by diffing the IR the two
arms produce for the same file.**

`codexir` is the Codex compiler transpiled by the zig plug. Feed it a chapter
with six comparisons and every one comes back typed `error`; compile the same
file through the seed on bare metal and every one is `boolean`.

    a : Integer -> Boolean
    a (n) = n < 2          -- and <=, >, >=, ==, /=

| operator | bare metal | plug-built codexir |
|---|---|---|
| `lt` `le` `gt` `ge` `eq` `ne` | `boolean` | **`error`** |

`error` is `ErrorTy` — `mcopy-type`'s unsafe escape, the same signature as
finding 70's hosted check-compact defect. It is on the ARM, which is where a
plug defect belongs, and not on the oracle.

**This was already known and recorded BACKWARDS.** The ladder's `ir_to_wire`
rung had been reporting it since Update 55, and both `PRIORITIES.md` and
`U55.log` said bare metal produced `error` and the zig arm `boolean` — the
alarming direction, which is why it sat parked. `ast/plug_arm_lib.sh:70` runs
`diff <(truth) zigout`, so the left column was always bare metal.

**What the rung could not tell us, and thirty lines can.** The rung's subject is
`fib`, which contains exactly one comparison, so "is it this comparison or all
of them" was unanswerable. It is all of them, universally, and the test costs
0.09 seconds against the rung's four minutes.

**Reproduce:**

    ./build.sh codexir                       # ~5 minutes, once
    $SANDBOX/codexir < cmps.codex 2>out.ir   # 0.09 seconds, thereafter

## 2. The two arms disagree on the chapter name

Same file, same run: bare metal writes `(chapter "Program")` and the plug-built
compiler writes `(chapter "Cmps")` — the chapter's own name. The `(title ...)`
field is correct in both.

**Not yet chased, and there is a confound to rule out first**: the two arms were
not handed byte-identical input. The bare-metal path wraps the source in a blob
with an `IR-CCE decks=172` header for the ring transport; `codexir` reads raw
source on stdin. That header could be what makes the driver name the unit
generically.

**How it stayed hidden for a day:** the two differences cancel in length.
`"Program"` is seven characters against `"WarmupFib"`'s nine; `boolean` is seven
against `error`'s five. Both files came out at exactly 1,214 bytes, so a size
check — which is the cheap check anyone reaches for first — said they matched.
