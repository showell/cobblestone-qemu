#!/bin/bash
# The Firefox gate: does every committed WGSL kernel pass naga?
#
#   CODEX_ROOT=~/showell_repos/cobblestone-u58 ./wgsl/check.sh
#
# naga is Firefox's own WGSL front end (naga-cli), offline and in milliseconds.
# Chrome's Tint is the more permissive of the two, so "renders in Chrome, fails
# in Firefox" is the expected direction and this is the only offline oracle for
# it. Run it every Update: a kernel that fails here is a shader Firefox rejects,
# and `regen.sh` rebuilds it from the checkout's own plug.
#
# This reads only the checkout; it boots no guest and takes under a second.
set -uo pipefail
: "${CODEX_ROOT:?set CODEX_ROOT to the Codex checkout to check}"
NAGA="${NAGA:-$HOME/.cargo/bin/naga}"
[ -x "$NAGA" ] || { echo "no naga at $NAGA; set NAGA (cargo install naga-cli)" >&2; exit 2; }

pass=0; fail=0; failed=()
while IFS= read -r w; do
  if "$NAGA" "$w" >/dev/null 2>&1; then pass=$((pass+1))
  else fail=$((fail+1)); failed+=("${w#"$CODEX_ROOT"/}"); fi
done < <(find "$CODEX_ROOT/apps" -name '*.wgsl' | sort)

echo "naga over $CODEX_ROOT: $pass pass, $fail fail"
for f in "${failed[@]:-}"; do [ -n "$f" ] && echo "  FAIL  $f"; done
[ "$fail" -eq 0 ]
