# What building on bare metal has turned up

## 1. SENT as [issue 126](https://github.com/damiant3/Cobblestone/issues/126). The plug-built compiler types EVERY comparison `error`, where bare metal says `boolean`

**CLOSED upstream at Update 60 (`9fff850c`), and measured here on 2026-09-13.**
`codexir` built from that checkout by `./build.sh codexir` types all six
comparisons `boolean`, and its IR for the six-comparison chapter is
byte-identical to the seed's when both read the same unit. Which change
flipped it on our road is not measured. What follows is the finding as it
was found.

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

**IT DOES NOT CHANGE THE EMITTED PROGRAM, on this evidence.** `fib`'s single
comparison is typed `error` by the hosted compiler, and the zig emitted from
that IR is BYTE-IDENTICAL to the zig emitted from bare metal's correctly-typed
IR. So the wrong type is inert for code generation here. Stated rather than
implied, because the alternative is claiming severity we have not shown.

PR 117's history is the argument for not shrugging anyway: there an `ErrorTy`
binding cascaded -- `lower` had no parameter type, `n + n` became an error node,
nine rungs went red off one cause. A type that is wrong but currently unread is
one consumer away from mattering.

**It is a SECOND SITE, not a regression.** PR 117's `hosted-kind` guard is in
the tree these measurements come from, and the symptom it fixed is gone: top-
level bindings type correctly. What remains is the same signature on comparison
EXPRESSIONS. We have not located the site, and that is a hypothesis rather than
a finding.

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

## 3. WATCHING, not a finding: the two cite resolvers

Opened 2026-09-13 at Update 60 (`9fff850c`). Steve's ask: track these without
hand-waving, and complain if upstream makes bundles cluttered or less
transparent. Each entry separates what is measured from what is read from code,
and says what would make it a finding.

Every unit our harnesses build passes through two resolvers:

| resolver | file | who calls it here | when "already present" counts |
|---|---|---|---|
| `Resolve-PlugForewords` | `codex/plugs/common/plug-build-lib.ps1` | every bundler in `subjects/`, and codex-zig-transpiler's | asked FIRST, before the registry. That is OUR PR 69, landed 2026-08-19 (`a061c173`) |
| `Resolve-CiteOrder` | `build/quire-map.ps1` | `assemble_unit.ps1` here, as upstream's `build/compile.ps1` and `build/bundle-app.ps1` call it | for a manifest quire, first. For a per-chapter quire such as Foreword, ONLY when the chapter's file is missing (since Update 35, `faf1c639`); otherwise only a `Quire--Name` header, through `SeedSeen`, stops a second copy |

| `load` / `resolve` | rust-codex-compiler `src/bundle.rs` | `bundle`, and `codexrun`, `irdump`, `desugardump`, `rocemit` on every unit they read | by BARE chapter name (`Quire--` is stripped), like `Resolve-PlugForewords`. It adds `IMPLICIT` (Foreword ListUtils, Tuple) to the cites, as upstream does, and resolves whatever is missing against `CODEX_ROOT`, lazily |

None of this changed in Updates 59 or 60. U59 put the first `for` into a
chapter we bundle, and that is what made 3b bite.

**The third row is OURS, and its fallback is the ambient-checkout trap.** A
unit short of any cited or implicit chapter is quietly re-resolved against
whatever `CODEX_ROOT` holds. This box exports one globally, pointing at another
tree. Measured 2026-09-13: every unit in the curated `cobblestone` (28) and
`roc` (46) dirs and in safari's `units/` (54) carries ListUtils and Tuple, so
only a missing cited chapter could reach the fallback. The Rust-side arms run
with `CODEX_ROOT` unset, which turns that case into a loud refusal.

The same day, the global export was deleted from `~/.bashrc` (Steve's call).
His direction for the third row: Rust does ALL its own resolution, with no
fallthroughs. The fallback and `CODEXC_RAW` are slated to go, and the design
comes before the code.

### 3a. A foreword present under another prefix goes in twice

Read from code: the table's last cell.

Measured at U60 on codex-zig-transpiler's transpiler subject. Its bundler
listed Maybe, Wrap64, Fat16, ImportGate and FactDisk as `Parsmi--<name>`.
`Resolve-PlugForewords` counted them present; `Resolve-CiteOrder` resolved all
five again, 2,749 lines, and `compile.ps1`'s own WARNING named them. That
bundler now leaves the five to `Resolve-PlugForewords`, which brings them in as
`Foreword--<name>` (codex-zig-transpiler `953e39d`).

This is the defect PR 69 described ("presence satisfies a cite only as a
fallback"), in the resolver PR 69 did not touch. `plug-build-lib`'s comment
"Same rule as Resolve-CiteOrder's, same helper" is true of the helper, not of
the order.

Would make it a finding: a bundle upstream actually builds that carries a
chapter under one prefix and cites it under another. PR 69 argued that a plug
bundle built through `Build-TranspilerPlug` cannot. NOT checked: apps through
`bundle-app.ps1`, and `concat-codex-self.ps1`, which prefixes by directory.

### 3b. Every unit carries ListUtils and Tuple, and they reach the emitted zig

Read from code: `Resolve-CiteOrder` walks Foreword ListUtils and Tuple for
every unit, unconditionally (since Update 36, `b1c50258`), because the
desugarer writes `map-list` for a `for` and `MkTup<N>` for a tuple. Its comment
prices this at "a fixed 5 KB per unit". `compile.ps1` exempts the two from its
WARNING.

Measured at U60 on fib, which uses neither sugar. The comparison is native
`codexir` on `fib.codex` against the same tool on the unit bare metal reads,
then `zigemit` on each:

    unit          +3,731 bytes, 123 lines ahead of fib
    IR            1,214 -> 1,863 bytes
      (sections)    "Main" -> seven names, six of them not fib's
      (ctors)       empty -> MkTup2 MkTup3 MkTup4 MkTup5
      (type-defs)   empty -> Tup2 Tup3 Tup4 Tup5
      row var ids   in `opening`, 6 -> 460 and 15 -> 469
    zig           14,877 -> 15,491 bytes: 24 lines added at the top, the
                  generic type functions Tup2..Tup5, and nothing else changed

Pruning removes the unused definitions, but not the type defs, the ctor list or
the section names. Checking the implicit chapters also shifts the ids minted for
the program's own rows. fib's output is unchanged on every route.

What to watch is transparency, not correctness. A program's IR and zig
describe types the program never mentions, and a comparison that forgets the
implicit pair reads the difference as a real one. The QEMU checker did, once
(fixed in `72c9b5c`). The row-id shift is the kind of difference the counters
see: anything keyed on variable ids moves when the implicit set does.

Would be worth raising upstream: the implicit set growing past these two, or
the same shape costing a comparison or a gate on their side.
