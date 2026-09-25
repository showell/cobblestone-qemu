# Bundle the ir_to_x86 subject: lower's chapter set plus the whole x86-64
# back end -- Lir, ResolveTypes, the real Builtins table, EmitAllocator,
# CdxWriter and all fourteen X86_64 pages -- so the harness runs the
# driver's own x86-64-emit-cdx and finalize over each of its programs and
# dumps the CDX it emits. bundle_passes_to_x86.ps1 calls this with extra
# chapters and its own harness; README "The twelve units" says what each
# holds.
param(
    [string]$Harness = 'IrToX86Harness.codex',
    [string]$OutName = 'ir_to_x86-subject.codex',
    [string]$PlugName = 'ir_to_x86-subject',
    # Chapters appended after the list below, and the BootPaint to carry.
    # The whole-compiler rung adds the middle end and swaps the stub for the
    # real painter; everything else about the unit is identical, so it stays
    # one list rather than two that have to be kept in step.
    [string[]]$ExtraChapters = @(),
    # Sections to drop from a named ExtraChapter. A plug chapter carries its
    # own copies of helpers it cannot cite when it is bundled standalone; in a
    # bundle that already has the originals those copies are duplicates, and a
    # duplicate TYPE is CDX3001, a hard error. Same mechanism the BootPaint and
    # AstNodes 'Deck Copies' drop already use.
    [hashtable]$ExtraDrops = @{},
    [string]$BootPaint = 'BootPaintStubs.codex',
    # OPT IN to carrying Chapter: Opening. A subject only wants the driver if
    # its harness CALLS the driver; carrying it otherwise costs a fifth of the
    # subject's lines and every byte of that is compiled by a guest. zigc asks
    # for it, the rungs still standing in for the driver do not.
    [switch]$WithDriver,
    # OPT IN to the middle end: the IR pipeline run-ir-pipeline drives, plus
    # LirTargets and the Codex emitter. The codexir subject runs it; x86emit
    # does not, and every line it would add is compiled by a guest.
    [switch]$WithMiddleEnd
)
$ErrorActionPreference = 'Stop'
$ladder = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path  # ladder-root-bootstrap: reaches the LADDER only; the checkout comes from ladder_root
$repo = (& python3 (Join-Path $ladder 'roots.py') codex).Trim()
# TWO DIRECTORIES, NOT ONE. $src is where the hand-written chapters live
# (this repo); $out is the sandbox everything generated goes to. They used to
# be one variable called $here, which is exactly the conflation that let a
# source repo grow a build directory -- and it broke on the first run here,
# looking for ZigPlugRing.codex in the sandbox.
$src = $PSScriptRoot
$out = if ($env:SANDBOX) { $env:SANDBOX } else { throw "no SANDBOX: nowhere to write" }

. "$repo/codex/plugs/common/plug-build-lib.ps1"

$lines = [System.Collections.Generic.List[string]]::new()
# This milestone swaps LexStubs for the real Core/PhaseAllocator.codex,
# and the reason is the cite rather than the functions. Desugarer.codex
# cites 'Codex chapter Phase Allocator', which LexStubs cannot satisfy
# whatever it defines -- a cite names a chapter, not a symbol. Carrying
# both would then define deck-record and deck-short-of twice, so the stub
# steps aside. Nothing else in the unit cites Phase Allocator, which is
# why lex and parse never needed it.
#
# The real deck-short-of reads __deck-pos where the stub did not, and that
# is harmless here: the harness passes a 0 ceiling, for which both answer
# False.
# CCE is NOT listed here, though it was until Update 46 made it fail.
# plug-build-lib carries a foreword chapter automatically once something
# cites it, and this bundle cites it, so listing it as well put CCE in twice
# -- once as Foreword--CCE and once as Parsmi--CCE. Two quires, two copies of
# every definition in it.
#
# That was visible the whole time as CDX3006 warnings and we read past them.
# The value duplicates only warn; CharClass is a TYPE, and Update 46 makes a
# duplicate type definition CDX3001, a hard error. lir lists CCE too and is
# right to: nothing there cites it, so the explicit copy is the only one.
# ListUtils is NOT listed here. Core/Collections.codex cites Foreword
# chapter ListUtils and Resolve-PlugForewords resolves that cite, so this
# bundle already carries Foreword--ListUtils; listing it again put a second
# copy in the Parsmi quire: two chapters
# defining list-map, fold-list, list-take and the rest, which is what every
# CDX3006 in this rung's log was telling us. See bundle_parse.ps1, where the
# explicit listing IS the only copy and stays.
#
# THE COMPILER'S CHAPTERS COME FROM THE CHECKOUT: build/compiler-order.txt,
# in its order. Upstream's concat-codex-self.ps1 refuses any .codex under
# codex/compiler without a row there, so it is the whole compiler by
# construction. What is kept HERE is only what we leave OUT, each with its
# reason, so a chapter upstream adds arrives without an edit on this side.
#
# That is the lesson of U62, which added IR/ConstShare and
# IR/MethodSpecialization. This file used to name the 64 chapters it
# carried, both new chapters were read by chapters on that list without a
# cite (B5: one flat namespace), and codexir compiled to nine CDX3002s.
# U63 added IR/IRFidelity, the typed IR graded against the checker: only the
# driver cites it (opening.codex, `ir-fidelity-bag`), and it cites IRCheck, so
# it is middle end too. Carried without IRCheck it failed x86emit's bundle
# ("cited Codex chapter 'IRCheck' ... not present in the unit").
$middleEnd = @('codex/compiler/IR/Occurrence.codex',
               'codex/compiler/IR/IRCheck.codex',
               'codex/compiler/IR/IRFidelity.codex',
               'codex/compiler/IR/LambdaLifting.codex',
               'codex/compiler/IR/Simplify.codex',
               'codex/compiler/IR/Passes.codex',
               'codex/compiler/IR/LirTargets.codex',
               'codex/compiler/Emit/CodexEmitter.codex')
$leftOut = @{
    # A stub stands in (see $BootPaint): bp-rtc-seconds is a wall clock, and a
    # rung whose truth changes between two identical runs is not an oracle.
    'codex/compiler/Core/BootPaint.codex' = $true
    # Always the harness's: every subject here defines its own `opening`.
    'codex/compiler/EntryPoint.codex' = $true
}
if (-not $WithDriver) { $leftOut['codex/compiler/opening.codex'] = $true }
if (-not ($WithMiddleEnd -or $WithDriver)) { foreach ($m in $middleEnd) { $leftOut[$m] = $true } }
$orderFile = Join-Path $repo 'build/compiler-order.txt'
$order = Get-Content $orderFile | ForEach-Object { $_.Trim() } |
    Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object { $_ -replace '\\', '/' }
foreach ($known in @($leftOut.Keys) + $middleEnd) {
    if ($order -notcontains $known) { throw "$known has no row in $orderFile -- upstream moved it; read their change before editing this list" }
}
foreach ($ch in $order) {
    if ($leftOut.ContainsKey($ch)) { continue }
    $drop = if ($ExtraDrops.ContainsKey($ch)) { $ExtraDrops[$ch] } else { @() }
    Add-PlugChapter -Lines $lines -Path (Join-Path $repo $ch) -Quire 'Parsmi' -DropSections $drop
}
# Update 42 gave PhaseAllocator a cite of Codex chapter BootPaint, and a cite
# names a chapter, so the unit has to carry one. See BootPaintStubs.codex for
# why it is a stub and not the real 341-line screen painter.
foreach ($ch in $ExtraChapters) {
    $drop = if ($ExtraDrops.ContainsKey($ch)) { $ExtraDrops[$ch] } else { @() }
    Add-PlugChapter -Lines $lines -Path (Join-Path $repo $ch) -Quire 'Parsmi' -DropSections $drop
}
# THE DRIVER, carried only when the harness CALLS it.
#
# Update 55 split the entry point out -- opening.codex defines `codex-opening`
# and a fourteen-line EntryPoint.codex holds `opening` -- so Chapter: Opening is
# bundlable by a subject that supplies its own entry point. A harness that
# carries it can call `compile-frontend-cdx` instead of reimplementing it, and a
# moved signature then becomes a compile error at a call we did not write.
#
# The foreword chapters the driver cites are carried REAL, and they are NOT
# named here. assemble_unit.ps1 runs the checkout's own cite resolver over the
# bundle, as build/compile.ps1 does, and puts what it adds ahead of it -- at U62
# twenty-two Foreword chapters, the six opening.codex cites and their closure.
# This block used to list those six by hand, from before assemble_unit resolved
# cites (U60, b7dcd33); with no caller it went unnoticed until codexir took the
# driver at U62 and every type in them came out twice (CDX3001, __eq_Maybe and
# fourteen more). BootPaint is the one that must stay a stub -- `bp-rtc-seconds`
# is a wall clock and a rung whose truth changes between two identical runs is
# not an oracle.
#
# The middle end comes with the driver because the driver READS it without
# citing it: B5 gives a bundle one flat namespace, so upstream never notices
# `opening.codex` using `run-ir-pipeline` while citing nothing that defines it.
# It is -WithMiddleEnd's list, above. A wrapper that also passes those paths as
# ExtraChapters must stop, because ADD-PLUGCHAPTER DOES NOT DE-DUPLICATE ACROSS
# CALLS -- the result is CDX3004, "spans 2 files, but this page carries no
# Page N of M marker", once per chapter.
$bootPaintPath = if ($BootPaint -match '/') { Join-Path $repo $BootPaint } else { Join-Path $src $BootPaint }
Add-PlugChapter -Lines $lines -Path $bootPaintPath -Quire 'Parsmi'
Add-PlugChapter -Lines $lines -Path (Join-Path $out $Harness) -Quire 'Parsmi'

# There used to be a rename of deck-record to subj-deck-record here. It was
# right when it was written: the seed's emitter hijacked any 1-arg call
# literally named deck-record into __deck-enter/__deck-exit, which corrupts
# memory in a subject that lacks the phase-allocator runtime, and renaming
# sidestepped it.
#
# Update 43 fixed that properly, on our report: the intercept now fires only
# when deck-record and init-phase-allocator are defined in the SAME chapter,
# so a bundle without the Phase Allocator gets the plain identity it declared
# and needs no help from us.
#
# Leaving the rename in place then became the bug. The seed doing the
# compiling is upstream's, so the name it looks for is `deck-record`; we had
# renamed ours out from under it, dr-slug came back empty, and the flag was
# False for every bundle here. That switched the deck discipline off across
# the whole bundled compiler, hundreds of call sites, and stayed invisible for
# thirteen rungs because a clean compile never needs a value to outlive
# emit-all-defs's per-function __heap-restore. clamp does: bag-add parks the
# diagnostic bag on the deck, the bag was freed at the bracket instead, and
# the second diagnostic read a dangling spine.
#
# LexStubs declares deck-record unrenamed, so the stub bundles still resolve.

# All 14 pages of the X86-64 Code Generator chapter are present, so the
# 'Page N of 14' trailers stand as written; the rewrite below is inherited
# from the lir bundle and self-adjusts, a no-op here.
$pageCount = ($lines | Where-Object { $_ -match '^Page \d+ of 14$' }).Count
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^Page \d+ of 14$') {
        $lines[$i] = $lines[$i] -replace 'of 14$', "of $pageCount"
    }
}
$preLines = Resolve-PlugForewords $lines
Bundle-PlugSource -PreLines $preLines -Lines $lines -BundleSrc (Join-Path $out $OutName) -PlugName $PlugName
