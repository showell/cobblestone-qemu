# The hosted-compiler subject: the whole rung's chapters, a different driver.
# Identical chapter set to bundle_passes_to_x86.ps1 for the same reason
# that one wraps bundle_ir_to_x86.ps1 -- one list, kept in one place, and that
# list is the checkout's build/compiler-order.txt. -WithDriver carries Chapter:
# Opening (and with it the middle end), because the harness CALLS the driver's
# IR front door rather than copying it: see gen_codexir_harness.py.
#
# bundle_codexzig.ps1 calls this with MoreChapters for the same reason again:
# it wants this list plus the plug's emitter.
param(
    [string]$Harness = 'CodexIrHarness.codex',
    [string]$OutName = 'codexir-subject.codex',
    [string]$PlugName = 'codexir-subject',
    [string[]]$MoreChapters = @(),
    [hashtable]$ExtraDrops = @{}
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'bundle_ir_to_x86.ps1') `
    -Harness $Harness `
    -OutName $OutName `
    -PlugName $PlugName `
    -ExtraDrops $ExtraDrops `
    -WithDriver `
    -ExtraChapters $MoreChapters
