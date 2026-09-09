# wgsl — the Firefox eye test, on bare metal

Chrome uses Tint; Firefox uses naga; naga is the stricter of the two. A WGSL
kernel that renders in Chrome and is refused by Firefox is the expected failure,
and Steve is the one who sees it. This directory turns that into something we
run every Update instead of finding out in the browser.

Three steps, cheapest first.

## 1. The gate — does Firefox accept what is committed?

```sh
CODEX_ROOT=~/showell_repos/cobblestone-u58 ./wgsl/check.sh
```

Runs `naga` (Firefox's own front end, offline) over every `.wgsl` under the
checkout's `apps/`. Under a second, no guest. A red line here is a shader
Firefox will reject. Run it on every new Update — a kernel can go stale when
the emitter improves and the committed output is not regenerated, which is
exactly how `GlobeKernels.wgsl` sat broken from Update 55 to 58.

## 2. Regenerate from the candidate — and prove boxing/reals did no harm

```sh
CODEX_ROOT=~/showell_repos/cobblestone-u58 ./wgsl/regen.sh            # whatever check.sh found red
CODEX_ROOT=... ./wgsl/regen.sh apps/globe/kernels/GlobeKernels        # a named kernel
CODEX_ROOT=... ./wgsl/regen.sh --write apps/globe/kernels/GlobeKernels  # stage the fix into CODEX_ROOT
```

Bundles the wgsl plug from the checkout and runs each kernel `source.codex ->
IR -> plug UNDER QEMU -> .wgsl`, then naga-checks it. Because the plug is built
and run from `CODEX_ROOT`, this exercises whatever the candidate branch changed
— the zig plug's boxing, the reals conversions, the emitter — and a kernel that
comes out naga-clean is proof those changes did not break the shaders. A guest
boots per kernel, so it is minutes each; the default only regenerates what the
gate reported red. Everything goes to a `~/runs` sandbox with a PROVENANCE;
`--write` copies the naga-clean result back into `CODEX_ROOT` as the fix.

If a kernel still fails naga *after* regeneration, that is a real emitter gap,
not staleness, and the message says so.

## 3. Eye-test it in Firefox

```sh
CODEX_ROOT=~/showell_repos/cobblestone-u58 ./wgsl/serve.sh
```

Serves the checkout on `127.0.0.1:9202`. WebGPU needs a secure context, so it
must be reached over a tunnel — plain http to the droplet IP reports no WebGPU
at all, which is not the bug. From your machine (the key is in WSL, so run this
in the WSL terminal and open Firefox on Windows):

```
ssh -N -L 9202:localhost:9202 steve@143.244.172.148
```

Then open, in Firefox on Windows:

- the gallery: `http://localhost:9202/apps/gpushow/web/index.html`
- the globe: `http://localhost:9202/apps/globe/web/globe-codex.html`
- two known-good: `http://localhost:9202/apps/gpushow/web/reflect.html` and `.../ssao.html`

naga (step 1) already tells you which will fail before you open the browser, so
the eye test is confirmation and a look at the actual pixels, not discovery.

## Requirements on this box

`naga` at `~/.cargo/bin/naga` (`cargo install naga-cli`), `pwsh` at
`~/.local/pwsh/pwsh`, `qemu-system-x86_64`. Override with `NAGA`, `PWSH`,
`QEMU_BIN`.
