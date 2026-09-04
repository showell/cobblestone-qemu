#!/bin/bash
# Build a Codex subject on BARE METAL: real x86 under QEMU, no host runtime.
#
#   ./build.sh fib        the smoke test -- one self-contained chapter, minutes
#   ./build.sh codexir    the compiler, as a native tool: .codex -> .ir
#   ./build.sh zigemit    the plug, as a native tool:    .ir    -> .zig
#   ./build.sh all        all three, cheapest first, stopping at the first red
#
# CHEAPEST FIRST AND STOP ON THE FIRST FAILURE, because the failure modes are
# shared: a deck overflow or a ring-size wall hits every subject the same way,
# and finding that out on fib costs minutes where finding it out on codexir
# costs an hour.
#
# EVERY ARTIFACT GOES TO A SANDBOX. This script cuts one under ~/runs unless
# $SANDBOX names one, writes a PROVENANCE beside it, and writes nothing at all
# into this repository. There are no .gitignore rules here on purpose: if a
# `git status` in this checkout is ever dirty after a build, something wrote
# where it should not have, and you want to know immediately.
#
# ONE SANDBOX, ONE COMMIT. The sandbox records the Codex sha it was cut against
# and refuses to continue if the checkout moves underneath it. A measurement
# attributed to a tree that is no longer there is worse than no measurement.
set -euo pipefail
T="$(cd "$(dirname "$0")" && pwd)"

# Named rather than assumed on PATH: neither is, on this box, and a bare `pwsh`
# fails as "command not found" three steps into a build that has already booted
# a guest.
PWSH="${PWSH:-$HOME/.local/pwsh/pwsh}"
ZIG="${ZIG:-$HOME/zig-0.16.0/zig}"
export PWSH ZIG
[ -x "$PWSH" ] || { echo "no pwsh at $PWSH; set PWSH" >&2; exit 2; }
[ -x "$ZIG" ]  || { echo "no zig at $ZIG; set ZIG" >&2; exit 2; }

: "${CODEX_ROOT:?set CODEX_ROOT to the Codex checkout to build from}"
: "${CODEX_LADDER_VENUE:?set CODEX_LADDER_VENUE -- a host without it is not a compute venue}"
CODEX_SHA="$(git -C "$CODEX_ROOT" rev-parse HEAD)"

want="${1:-all}"
case "$want" in fib|codexir|zigemit|all) ;; *) echo "usage: build.sh [fib|codexir|zigemit|all]" >&2; exit 2 ;; esac

if [ -z "${SANDBOX:-}" ]; then
    SANDBOX="$HOME/runs/$(date -u +%Y%m%dT%H%M%SZ)-$want"
fi
export SANDBOX
S="$SANDBOX"
mkdir -p "$S"

if [ -f "$S/PROVENANCE" ]; then
    was="$(awk -F'\t' '$1=="codex-sha"{print $2}' "$S/PROVENANCE")"
    if [ "$was" != "$CODEX_SHA" ]; then
        echo "REFUSING: this sandbox was cut against ${was:0:12} and CODEX_ROOT is now ${CODEX_SHA:0:12}."
        echo "  One sandbox, one commit. Cut a new one rather than reusing this."
        exit 1
    fi
else
    { printf 'created\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      printf 'host\t%s\n' "$(hostname)"
      printf 'target\t%s\n' "$want"
      printf 'codex-repo\t%s\n' "$CODEX_ROOT"
      printf 'codex-sha\t%s\n' "$CODEX_SHA"
      printf 'codex-subject\t%s\n' "$(git -C "$CODEX_ROOT" log --oneline -1 | cut -c1-90)"
      printf 'codex-branch\t%s\n' "$(git -C "$CODEX_ROOT" rev-parse --abbrev-ref HEAD)"
      printf 'seed-sha256\t%s\n' "$(sha256sum "$CODEX_ROOT/seed/Codex.cdx" | awk '{print $1}')"
      printf 'qemu-repo\t%s\n' "$T"
      printf 'qemu-sha\t%s\n' "$(git -C "$T" rev-parse HEAD 2>/dev/null || echo '(not a git repo)')"
    } > "$S/PROVENANCE"
fi
echo "sandbox   $S"
echo "codex     ${CODEX_SHA:0:12}  $(git -C "$CODEX_ROOT" rev-parse --abbrev-ref HEAD)"
echo

. "$T/lib.sh"

# fib needs no bundler: WarmupFib cites nothing, so the subject IS the chapter.
# That is what makes it the smoke test -- it exercises the whole transport
# (ring compile, plug transpile, zig build) with none of the bundling.
if [ "$want" = fib ] || [ "$want" = all ]; then
    cp "$T/subjects/fib.codex" "$S/fib-subject.codex"
    ring_plug_fresh
    build_one fib "" "" fib-subject.codex
fi

if [ "$want" = zigemit ] || [ "$want" = all ]; then
    [ "$want" = zigemit ] && ring_plug_fresh
    build_one zigemit "" bundle_zigemit.ps1 zigemit-source.codex
fi

if [ "$want" = codexir ] || [ "$want" = all ]; then
    [ "$want" = codexir ] && ring_plug_fresh
    build_one codexir gen_codexir_harness.py bundle_codexir.ps1 codexir-subject.codex
fi

echo
echo "############ done -- artifacts in $S"
