#!/bin/bash
# Serve the checkout for the WGSL eye test, loopback only.
#
#   CODEX_ROOT=~/showell_repos/cobblestone-u58 ./wgsl/serve.sh
#
# WebGPU is exposed only in a SECURE CONTEXT, so plain http to the droplet IP
# reports no WebGPU at all -- which is not the bug under test. The page must be
# reached over an SSH tunnel so the browser sees `localhost`. See README.md for
# the tunnel command and the pages to open. Bind is loopback for that reason.
set -uo pipefail
: "${CODEX_ROOT:?set CODEX_ROOT to the Codex checkout to serve}"
PORT="${PORT:-9202}"
[ -f "$CODEX_ROOT/apps/gpushow/web/index.html" ] || { echo "no apps/gpushow/web in $CODEX_ROOT" >&2; exit 2; }
echo "serving $CODEX_ROOT on 127.0.0.1:$PORT"
echo "tunnel from your machine:  ssh -N -L $PORT:localhost:$PORT steve@143.244.172.148"
echo "then open in Firefox:      http://localhost:$PORT/apps/gpushow/web/index.html"
cd "$CODEX_ROOT"
exec python3 -m http.server "$PORT" --bind 127.0.0.1
