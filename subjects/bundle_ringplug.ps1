# Bundle the ring-fed zig plug: the transpiler-plug chapter set (same
# declarations, parser, and emitter as plugs/zig/build.ps1) with
# ZigPlugRing as the body instead of ZigPlug -- no Net or Kernel
# chapters, because the intake is the serial ring the compiler itself
# reads from.
param(
    [string]$OutName = 'ringplug-source.codex',
    # The body is the only thing that differs between the ring-fed plug and
    # the hosted one: same declarations, same parser, same emitter.
    [string]$Body = 'ZigPlugRing.codex',
    [string]$PlugName = 'ringplug'
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
foreach ($decl in @('codex/compiler/Core/Name.codex',
                    'codex/compiler/Core/SourceText.codex',
                    'codex/compiler/Types/CodexType.codex',
                    'codex/compiler/Ast/AstNodes.codex',
                    'codex/compiler/IR/IRChapter.codex')) {
    $drop = if ($decl -like '*AstNodes.codex') { @('Deck Copies') } else { @() }
    Add-PlugChapter -Lines $lines -Path (Join-Path $repo $decl) -Quire 'Zig' -DropSections $drop
}
Add-PlugChapter -Lines $lines -Path (Join-Path $repo 'codex/plugs/common/PlugTypes.codex') -Quire 'Zig'
Add-PlugChapter -Lines $lines -Path (Join-Path $repo 'codex/plugs/common/IRTextParser.codex') -Quire 'Zig'
# EVERY PAGE OF Chapter: Zig Emitter, READ FROM THE CHECKOUT. A bundle missing
# a page reports every definition on it as undefined, so the page set must come
# from the checkout being bundled rather than from a list kept here. The
# chapter's `Page N of M` footers are the order; zig_plug_pages.py refuses
# rather than guesses if they do not describe a whole chapter.
$pages = & python3 (Join-Path $ladder 'zig_plug_pages.py')
if ($LASTEXITCODE -ne 0) { throw "could not read the pages of Chapter: Zig Emitter" }
foreach ($zp in $pages) {
    Add-PlugChapter -Lines $lines -Path (Join-Path $repo "codex/plugs/zig/$($zp.Trim()).codex") -Quire 'Zig'
}
Add-PlugChapter -Lines $lines -Path (Join-Path $src $Body) -Quire 'Zig'

$preLines = Resolve-PlugForewords $lines
Bundle-PlugSource -PreLines $preLines -Lines $lines -BundleSrc (Join-Path $out $OutName) -PlugName $PlugName
