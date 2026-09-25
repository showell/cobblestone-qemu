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

# **UPSTREAM'S OWN BUNDLING, NOT A COPY OF IT.** This used to repeat
# Build-TranspilerPlug's chapter list by hand, and U63 showed what that costs:
# upstream began stripping the declaration chapters' new `cites Codex chapter
# Phase Allocator` (the plug's Plug Types supplies what they cite it for), the
# copy did not, and the ring plug failed to bundle ("quire 'Codex' is not
# registered"). So the zig plug's own build line is read from the checkout
# and Build-TranspilerPlug is called with it, the ring body standing in for
# ZigPlug -- the one thing that differs. Its compile step is Windows tooling
# this ladder does not run (the ring compiles the bundle), so it is replaced
# after the library is loaded: PowerShell resolves the name at the call.
function Build-PlugCdx {
    param($BundleSrc, $OutFile, $LogFile, $PlugName, $Survey, $Decks)
}

$zigBuild = Get-Content -Raw (Join-Path $repo 'codex/plugs/zig/build.ps1')
if ($zigBuild -notmatch 'Build-TranspilerPlug\s[^\n]*-Chapters\s+@\(([^)]*)\)') {
    throw "codex/plugs/zig/build.ps1 no longer calls Build-TranspilerPlug with -Chapters; read it before bundling"
}
$zigChapters = @([regex]::Matches($Matches[1], "'([^']+)'") | ForEach-Object { $_.Groups[1].Value })
if ($zigChapters[-1] -ne 'ZigPlug') { throw "the zig plug's body is no longer its last chapter ($($zigChapters -join ', '))" }
$compilerChapters = @()
if ($zigBuild -match '-CompilerChapters\s+@\(([^)]*)\)') {
    $compilerChapters = @([regex]::Matches($Matches[1], "'([^']+)'") | ForEach-Object { $_.Groups[1].Value })
}

# The plug directory Build-TranspilerPlug reads its own chapters from, staged
# in the sandbox: upstream's zig chapters, and this repo's body in place of
# ZigPlug. Its build-output lands there too, never in the checkout.
$stage = Join-Path $out "$PlugName-plugdir"
Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $stage | Out-Null
$chapters = @()
foreach ($c in $zigChapters[0..($zigChapters.Count - 2)]) {
    Copy-Item (Join-Path $repo "codex/plugs/zig/$c.codex") (Join-Path $stage "$c.codex")
    $chapters += $c
}
$bodyName = [System.IO.Path]::GetFileNameWithoutExtension($Body)
Copy-Item (Join-Path $src $Body) (Join-Path $stage "$bodyName.codex")
$chapters += $bodyName

Build-TranspilerPlug -PlugDir $stage -PlugName 'zig' -Chapters $chapters -CompilerChapters $compilerChapters | Out-Host
Copy-Item (Join-Path $stage 'build-output/plug-source.codex') (Join-Path $out $OutName)
Write-Host "[$PlugName] bundled by upstream's Build-TranspilerPlug: $($chapters -join ', ')"
