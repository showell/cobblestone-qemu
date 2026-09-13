# Assemble the unit the seed reads, the way upstream's build/compile.ps1 does:
# the mode line, every chapter the source's cites resolve to, the source, EOT.
#
#   pwsh -File assemble_unit.ps1 -Src <bundle.codex> -Mode 'IR-CCE decks=172' -Out <blob>
#
# **THE RESOLUTION IS UPSTREAM'S, CALLED RATHER THAN COPIED.** Resolve-CiteOrder
# and Format-CiteChapters come from the checkout's own build/quire-map.ps1, so
# what this adds is what compile.ps1 adds at that pin. For a complete bundle
# that is Foreword ListUtils and Tuple: the resolver walks both for EVERY unit,
# because the desugarer writes `map-list` for a `for` and `MkTup<N>` for a
# tuple, names no author cites. A blob of the bundle alone left both out, and
# the first bundled chapter to use `for` (Update 59's Zig emitter) stopped the
# ring plug with CDX3002 on map-list.
param(
    [Parameter(Mandatory=$true)] [string]$Src,
    [Parameter(Mandatory=$true)] [string]$Mode,
    [Parameter(Mandatory=$true)] [string]$Out
)
$ErrorActionPreference = 'Stop'

$repo = & python3 -B (Join-Path $PSScriptRoot 'roots.py') codex
if ($LASTEXITCODE -ne 0) { exit 2 }
$repo = "$repo".Trim()
. (Join-Path $repo 'build/quire-map.ps1')

# .NET resolves a relative path against its own working directory, which is
# not the shell's.
$Src = (Resolve-Path $Src).Path
$Out = [System.IO.Path]::GetFullPath($Out, (Get-Location).Path)

$srcLines = [System.IO.File]::ReadAllLines($Src)
# A bundled chapter carries its quire in its header, and compile.ps1 counts it
# as already seen.
$seedSeen = @{}
foreach ($line in $srcLines) {
    if ($line -match '^Chapter:\s*(\w+)--(.+?)\s*$') { $seedSeen["$($matches[1])::$($matches[2])"] = $true }
}
try {
    $ordered = Resolve-CiteOrder -RootLines $srcLines -Repo $repo -SeedSeen $seedSeen
} catch {
    [Console]::Error.WriteLine("error 3010: $($_.Exception.Message)")
    exit 8
}
# compile.ps1's own warning, kept: anything beyond the two implicit chapters
# is a cite the bundler did not answer.
$implicit = @('ListUtils', 'Tuple')
$unbundled = @($ordered | Where-Object { -not ($_.Quire -eq 'Foreword' -and $implicit -contains $_.Name) })
if ($unbundled.Count -gt 0 -and $seedSeen.Count -gt 0) {
    [Console]::Error.WriteLine("WARNING: resolved $($unbundled.Count) chapter(s) not in the bundle:")
    foreach ($extra in $unbundled) { [Console]::Error.WriteLine("  $($extra.Quire)::$($extra.Name) ($($extra.Path))") }
}

$prelude = Format-CiteChapters -Ordered $ordered
$w = [System.IO.StreamWriter]::new($Out, $false, [System.Text.UTF8Encoding]::new($false))
$w.Write($Mode); $w.Write("`n")
foreach ($l in $prelude) { $w.Write($l); $w.Write("`n") }
foreach ($l in $srcLines) { $w.Write($l); $w.Write("`n") }
$w.Write([char]4)
$w.Dispose()
$added = ($ordered | ForEach-Object { "$($_.Quire)::$($_.Name)" }) -join ', '
Write-Output "blob: $((Get-Item $Src).Length) bytes of source, $($prelude.Count) lines resolved ahead of it ($added)"
