# The x86-64 back end over fib, as a program. Same chapter set as the ladder's
# ir_to_x86 bundle -- this only names the harness and the output.
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'bundle_ir_to_x86.ps1') `
    -Harness 'X86EmitHarness.codex' `
    -OutName 'x86emit-subject.codex' `
    -PlugName 'x86emit'
