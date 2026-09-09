#!/bin/bash
# Rebuild WGSL kernels from the checkout's OWN plug, on this box, and naga-check
# each. This is how a candidate branch's boxing, reals and emitter changes are
# proven not to break the shaders Firefox accepts -- the plug is bundled and run
# from CODEX_ROOT, so whatever the candidate changed is exercised end to end.
#
#   CODEX_ROOT=~/showell_repos/cobblestone-u58 ./wgsl/regen.sh
#       regenerate the kernels check.sh reports RED, into a sandbox, naga each.
#
#   CODEX_ROOT=... ./wgsl/regen.sh apps/globe/kernels/GlobeKernels [more...]
#       regenerate named kernels (path with no extension).
#
#   CODEX_ROOT=... ./wgsl/regen.sh --write <target...>
#       after naga passes, copy the regenerated .wgsl back into CODEX_ROOT --
#       the staged fix. Without --write nothing in CODEX_ROOT changes.
#
# Each kernel is source.codex -> IR (codexir) -> wgsl plug UNDER QEMU -> .wgsl.
# A guest boots per kernel, so this is minutes each; that is why the default is
# only what check.sh found red. The plug bundle is built once, up front.
set -uo pipefail
T="$(cd "$(dirname "$0")" && pwd)"
: "${CODEX_ROOT:?set CODEX_ROOT to the Codex checkout to build from}"
PWSH="${PWSH:-$HOME/.local/pwsh/pwsh}"
QEMU_BIN="${QEMU_BIN:-/usr/bin/qemu-system-x86_64}"
NAGA="${NAGA:-$HOME/.cargo/bin/naga}"
export CODEX_ROOT QEMU_BIN
for f in "$PWSH" "$QEMU_BIN" "$NAGA"; do
  [ -x "$f" ] || { echo "missing executable: $f" >&2; exit 2; }
done
CODEX_SHA="$(git -C "$CODEX_ROOT" rev-parse HEAD)"

write=0
if [ "${1:-}" = "--write" ]; then write=1; shift; fi

# Targets: the named ones, or (default) every .wgsl naga rejects, mapped back to
# its .codex source beside it.
targets=("$@")
if [ "${#targets[@]}" -eq 0 ]; then
  while IFS= read -r w; do
    "$NAGA" "$w" >/dev/null 2>&1 || targets+=("${w%.wgsl}")
  done < <(find "$CODEX_ROOT/apps" -name '*.wgsl' | sort)
fi
if [ "${#targets[@]}" -eq 0 ]; then echo "nothing to regenerate: check.sh is green"; exit 0; fi

# One sandbox, stamped with the commit it was cut against.
SANDBOX="${SANDBOX:-$HOME/runs/$(date -u +%Y%m%dT%H%M%SZ)-wgsl}"
mkdir -p "$SANDBOX"
printf 'tool\twgsl/regen.sh\ncodex-sha\t%s\ncheckout\t%s\nwhen\t%s\n' \
  "$CODEX_SHA" "$CODEX_ROOT" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$SANDBOX/PROVENANCE"
echo "sandbox $SANDBOX  (codex $CODEX_SHA)"

echo "[plug] bundling the wgsl plug from $CODEX_ROOT"
# The pwsh scripts resolve cites and foreword paths RELATIVE to the working
# directory (`./codex/foreword/...`), not to CODEX_ROOT -- a Linux quirk that
# fails "Unresolvable cite Foreword ListUtils" from any other cwd. Run them
# FROM the checkout. cobblestone-qemu exists partly to absorb quirks like this.
( cd "$CODEX_ROOT" && "$PWSH" codex/plugs/wgsl/build.ps1 ) >"$SANDBOX/plug-build.log" 2>&1 \
  || { echo "plug build FAILED, see $SANDBOX/plug-build.log" >&2; exit 1; }

fail=0
for t in "${targets[@]}"; do
  name="$(basename "$t")"
  src="$CODEX_ROOT/$t.codex"; [ -f "$src" ] || src="$t.codex"
  [ -f "$src" ] || { echo "  $name: no source .codex at $src" >&2; fail=$((fail+1)); continue; }
  out="$SANDBOX/$name.wgsl"
  echo "[regen] $name  (guest boot, minutes)"
  if ! ( cd "$CODEX_ROOT" && "$PWSH" codex/plugs/wgsl/run.ps1 -Src "$src" -Out "$out" ) >"$SANDBOX/$name.log" 2>&1; then
    echo "  $name: plug run FAILED, see $SANDBOX/$name.log" >&2; fail=$((fail+1)); continue
  fi
  if "$NAGA" "$out" >/dev/null 2>&1; then
    echo "  $name: naga OK ($(wc -c <"$out") bytes)"
    if [ "$write" -eq 1 ]; then
      dst="$CODEX_ROOT/$t.wgsl"; [ -e "$dst" ] || dst="$t.wgsl"
      cp "$out" "$dst"; echo "    written -> ${dst#"$CODEX_ROOT"/}"
    fi
  else
    echo "  $name: naga FAILS after regen -- a real emitter gap, not staleness:"; "$NAGA" "$out" 2>&1 | head -4 | sed 's/^/    /'
    fail=$((fail+1))
  fi
done
echo
[ "$fail" -eq 0 ] && echo "regen clean" || { echo "regen: $fail problem(s)"; exit 1; }
