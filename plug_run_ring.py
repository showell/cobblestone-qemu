#!/usr/bin/env python3
"""Ring-fed zig plug runner: feed an IR-CCE file into ringplug.cdx over
the serial ring (the compiler's own intake) and save the decoded zig
text. The TCP transport costs ~130 bytes of guest heap per IR byte
before the parser sees anything (IrmemHarness); the ring intake is a
machine-code loop at one byte per byte, which is what admits IRs past
the TCP ceiling (ir_to_x86 at 13.1 MB under the u47 seed; sizes move per Update).

Since U63 the guest streams its zig text with print-uni (UTF-8, not
CCE) and ends it with a RINGPLUG-END line, so compile_ring captures in
sentinel mode and the payload is decoded here as UTF-8; anything that
is not valid UTF-8 fails the run rather than landing in a .zig file.

Usage: plug_run_ring.py <ir> <out.zig> [plug_cdx]
"""
import hashlib
import os
import pathlib
import subprocess

# This repository has no ignore rules, so an imported module must not leave a
# __pycache__ behind. `-B` in a shebang covers ./name.py only, and every caller
# here runs `python3 name.py`, so the guard belongs in the file and must be set
# before the first local import.
import sys
sys.dont_write_bytecode = True

import ring_compile
from roots import out_root


def refuse_stale_ringplug(out):
    """A stale ring plug silently transpiles with yesterday's emitter -- it did
    on 2026-08-19, stamping the pre-multibyte prelude onto freshly built native
    tools. The bundle is deterministic, so re-bundle to a scratch name and
    compare against the fingerprint the build recorded; any mismatch means the
    checkout's plug sources moved since the cdx was built.

    `out` is the SANDBOX. The plug and its fingerprint are artifacts and live
    there; the bundler that reproduces them is source and lives in this repo.
    """
    fp_file = out / "ringplug.cdx.fp"
    if not fp_file.is_file():
        raise SystemExit(f"no {fp_file}; run build.sh, which builds the ring plug first")
    check = out / "ringplug-source-check.codex"
    bundler = pathlib.Path(__file__).resolve().parent / "subjects" / "bundle_ringplug.ps1"
    pwsh = os.environ.get("PWSH", os.path.expanduser("~/.local/pwsh/pwsh"))
    subprocess.run([pwsh, "-NoProfile", "-File", str(bundler), "-OutName", check.name],
                   cwd=out, check=True, capture_output=True)
    got = hashlib.sha256(check.read_bytes()).hexdigest()
    check.unlink()
    if got != fp_file.read_text().strip():
        raise SystemExit(f"{out / 'ringplug.cdx'} is stale against the checkout's "
                         "plug sources; rebuild it")


def run_ring_plug(ir_path, out_path, plug_cdx=None, mem_mb=None, timeout=1800):
    if mem_mb is None:
        mem_mb = ring_compile.MEM_MB
    out = out_root()
    if plug_cdx is None:
        refuse_stale_ringplug(out)
    plug_cdx = plug_cdx or str(out / "ringplug.cdx")
    ir = open(ir_path, "rb").read()
    if b"\x00" in ir:
        raise SystemExit(f"{ir_path}: contains NUL; read-serial-cce would stop early")
    blob_path = str(out_path) + ".blob"
    with open(blob_path, "wb") as f:
        f.write(b"RING zig\n" + ir + b"\x00")
    # SINCE U63 THE PLUG STREAMS (see subjects/ZigPlugRing.codex): no SIZE
    # line, the capture ends at the RINGPLUG-END sentinel, and the stream is
    # printed with print-uni, so it arrives as text and is not CCE-decoded.
    raw_path = str(out_path) + ".raw"
    ok = ring_compile.compile_ring(blob_path, raw_path, mem_mb=mem_mb,
                                   timeout=timeout, seed=plug_cdx,
                                   sentinel=b"\nRINGPLUG-END")
    if not ok:
        return False
    payload = open(raw_path, "rb").read()
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as e:
        raise SystemExit(f"{raw_path}: not UTF-8 at byte {e.start}: "
                         f"{payload[max(0, e.start - 40):e.start + 40]!r}")
    open(out_path, "w").write(text)
    print(f"wrote {out_path} ({len(text)} chars from {len(payload)} bytes)")
    return True


if __name__ == "__main__":
    ok = run_ring_plug(sys.argv[1], sys.argv[2],
                       sys.argv[3] if len(sys.argv) > 3 else None)
    sys.exit(0 if ok else 1)
