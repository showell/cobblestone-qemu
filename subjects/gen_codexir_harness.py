#!/usr/bin/env python3
"""Generate CodexIrHarness.codex: the compiler as a program that emits IR.

zigc emits a CDX, which is what the Codex compiler is for. This emits IR-CCE
instead, which is what the PLUG is fed -- and that is the piece that takes the
seed out of the pipeline. With this and ZigEmitHosted, the chain

    prog.codex -> prog.ir -> prog.zig -> ELF

is three native processes and no VM at all.

**THE DRIVER IS UPSTREAM'S, CALLED, NOT COPIED (since U62).** The body is
`emit-ir-uni` (opening.codex): `compile-frontend-ir`, then
`prepare-method-ir`, then `emit-ir-chapter` over what it prepared. The subject
carries Chapter: Opening (`bundle_codexir.ps1` asks for `-WithDriver`), which
Update 55's split of `opening` into EntryPoint.codex made possible.

Until U62 this file stood in for the driver with its own copy of the
sequence, and the copy drifted three times that we know of:

  - 2026-08-25: it pruned to four of the driver's six emit roots, missing
    `fat16-servicer-read` and `fat16-servicer-write`. CodexZigHarness
    inherited the truncation, so both arms agreed and nothing saw it.
  - COMPILER-44 onward: the driver attaches the instantiated equality helpers
    (`eq-attach-helpers`) before emitting IR. The copy never did.
  - U62: IR emission became `prepare-method-ir`, which runs
    `method-materialize` and fills IRTextMeta's new `method-templates` field.
    The copy did not compile.

What stays ours is only the output shape: the IR text alone on the wire (the
driver frames it with IR-BEGIN/IR-END and heap marks), and the halt message.
The source goes in as read, as it always has here; the driver's mode line,
utf8-to-cce and quotation split belong to its stdin protocol, not to this
tool's.
"""
import pathlib
import sys

from emit_harness import halt_formatter

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from roots import out_root  # noqa: E402
OUT = out_root()

out = f'''Chapter: CodexIrHarness

Section: Halt

 The driver does not emit when the bag has errors -- emit-ir-uni prints the
 codegen header and then `if bag-has-errors (prepared.bag) then
 print-line-uni "CODEGEN-HALTED: errors in bag; no IR emitted"`. This harness
 did not, until 2026-08-26, and that is not a cosmetic gap.

 What it cost. native/codexir accepted a three-line program the seed refuses
 with CDX2001, and we reported that to Damian's compiler lane first as a
 soundness hole in their type checker and then as a miscompile in our plug.
 It was neither: native/codexzig, the same compiler from the same plug whose
 harness DOES read the bag, refuses it with the same code and the same
 wording. Their lane ran a four-seed sweep with a positive control to tell us
 we were wrong. The checker was never broken; this harness was deaf.

 What it costs quietly. corpus_run.py runs this tool, so a corpus program
 carrying a compiler error emitted IR anyway and we built, ran and scored its
 zig. Expect the clean count to FALL when this lands -- that is the gate
 working, not a regression.

{halt_formatter('irc', 'IR')}

Section: Driver

 emit-ir-uni's sequence with compile-flags-default, printing the IR alone.

  opening : [Console, FileSystem] Nothing = act
    src <- read-file-uni "/dev/stdin"
    let fe = compile-frontend-ir src "Program" compile-flags-default
    in let prepared = prepare-method-ir fe compile-flags-default
    in if bag-has-errors (prepared.bag) then print-text (irc-halted (bag-errors (prepared.bag)))
    else print-text (emit-ir-chapter (prepared.chapter) (prepared.meta) (prepared.type-defs))
  end
'''

dest = OUT / 'CodexIrHarness.codex'
dest.write_text(out)
print(f'{dest}: {len(out)} bytes')
