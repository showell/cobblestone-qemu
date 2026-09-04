#!/usr/bin/env python3
"""Does fib come out right through BARE METAL? Two guests, about eight seconds.

    fib.codex --(seed, QEMU)--> IR --(ring plug, QEMU)--> zig --> a binary

This is the slow route and the authoritative one. Everything else in this repo
exists to avoid needing it; this is what says avoiding it was safe.

It also DIFFS ITS IR AGAINST THE NATIVE TOOL'S when codexir is available, which
is where this stops being a smoke test. On 2026-09-04 that comparison is how we
found that the plug-built compiler types every comparison `error` where bare
metal says `boolean` -- see FINDINGS.md. A verifier that only checked 55 and 610
would have passed both ways round, because the wrong type does not change what
fib computes.
"""
import os
import subprocess
import sys

import common as c

REPO = c.REPO
S = c.sandbox()
c.need_codex_root(S)
plug = c.need(S / 'ringplug.cdx', 'run ./build.sh fib -- it builds the ring plug first')

work = S / 'fib_checkers'
work.mkdir(exist_ok=True)
blob, ir, zg, exe = (work / 'qemu-fib.blob', work / 'qemu-fib.ir',
                     work / 'qemu-fib.zig', work / 'qemu-fib')

src = c.FIB.read_bytes()
blob.write_bytes(b'IR-CCE decks=172\n' + src + b'\x04')

env = dict(os.environ, SANDBOX=str(S))
r = c.run([sys.executable, '-u', str(REPO / 'ring_compile.py'), str(blob), str(ir)], env=env)
if not ir.exists() or not ir.stat().st_size:
    c.fail(f'bare-metal compile produced no IR:\n{r.stdout[-400:]}{r.stderr[-400:]}')

r = c.run([sys.executable, '-u', str(REPO / 'plug_run_ring.py'), str(ir), str(zg)], env=env)
if not zg.exists() or not zg.stat().st_size:
    c.fail(f'ring-plug transpile produced no zig:\n{r.stdout[-400:]}{r.stderr[-400:]}')

zig = os.environ.get('ZIG', os.path.expanduser('~/zig-0.16.0/zig'))
b = c.run([zig, 'build-exe', str(zg), f'-femit-bin={exe}'], cwd=work)
if b.returncode:
    c.fail(f'zig build-exe failed:\n{b.stderr[:400]}')

extra = ''
native = S / 'codexir'
if native.exists():
    # The IR bare metal produced is CCE; the native tool's is text. Decode
    # before comparing, or the diff is an encoding difference wearing a hat.
    sys.path.insert(0, str(REPO))
    from cce import decode
    nat = work / 'qemu-fib-native.ir'
    with open(c.FIB, 'rb') as f, open(nat, 'wb') as o:
        subprocess.run([str(native)], stdin=f, stdout=subprocess.DEVNULL, stderr=o)
    bm = decode(ir.read_bytes())
    if bm == nat.read_text():
        extra = '  (IR identical to the native tool)'
    else:
        a = bm.splitlines()
        b2 = nat.read_text().splitlines()
        first = next((i for i, (x, y) in enumerate(zip(a, b2)) if x != y), None)
        extra = f'  (IR DIFFERS from the native tool, first at line {first + 1 if first is not None else "?"})'

got = c.run([str(exe)])
sys.exit(c.check(got.stdout + got.stderr, 'bare metal (seed + ring plug)', extra))
