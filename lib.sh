# Building something on bare metal: bundle it, compile it to IR with the seed
# under QEMU, push that IR through the ring plug, build the emitted zig.
#
# Four steps, and only the last is not a VM. That is the whole point of building
# codexir and zigemit at all -- afterwards
#
#     codexir <prog.codex 2>prog.ir && zigemit <prog.ir 2>prog.zig
#
# is two native processes and no guest.
#
# Both tools read /dev/stdin and neither looks at argv, so the redirects are not
# style: `codexir prog.codex` aborts with a core dump, because the empty read
# takes the 10-byte CCE path. Output lands on stderr because print-text is
# std.debug.print; that is a wart, not a design.
#
# EVERYTHING WRITTEN HERE GOES TO $SANDBOX. Nothing lands beside these scripts.

seed_compile() {   # <blob> <out>   -- one guest
    python3 -u "$T/ring_compile.py" "$1" "$2" 2>&1 | tail -3
}

ring_transpile() {  # <ir> <zig> <log>   -- one guest
    python3 -u "$T/plug_run_ring.py" "$1" "$2" > "$3" 2>&1
}

# The transpile boots the RING plug, so a stale ringplug.cdx silently stamps
# yesterday's emitter onto today's tools. Rebuild before the first build_one;
# plug_run_ring.py refuses a stale one as the backstop. It is a CALL and not a
# line in this file because sourcing a library must not start a guest.
ring_plug_fresh() {
    echo "############ ring plug"
    cd "$S"
    rm -f ringplug-source.codex
    out=$("$PWSH" -NoProfile -File "$T/subjects/bundle_ringplug.ps1" 2>&1) \
        || { printf '%s\n' "$out" | tail -5; return 1; }
    printf '%s\n' "$out" | tail -1
    python3 -c "
src = open('$S/ringplug-source.codex','rb').read()
open('$S/ringplug-cdx.blob','wb').write(b'CDX map\n' + src + b'\x04')
print(f'blob: {len(src)} bytes')"
    # Content, never mtime: the bundle is deterministic and the fingerprint IS
    # its sha, so a match means this exact plug is already compiled.
    want=$(sha256sum "$S/ringplug-source.codex" | awk '{print $1}')
    if [ -s "$S/ringplug.cdx" ] && [ "$(cat "$S/ringplug.cdx.fp" 2>/dev/null)" = "$want" ]; then
        echo "ringplug.cdx already matches this bundle -- not recompiling"
        return 0
    fi
    rm -f "$S/ringplug.cdx"
    # KEEP THE WHOLE OUTPUT. Piping this through a grep for "error|SIZE"
    # discards every other reason a compile can fail, and the two that actually
    # happen say neither word: a host with no CODEX_LADDER_VENUE, and
    # a guest that will not start.
    python3 -u "$T/ring_compile.py" "$S/ringplug-cdx.blob" "$S/ringplug.cdx" \
        > "$S/ringplug-compile.log" 2>&1
    grep -E "error|SIZE" "$S/ringplug-compile.log" | head -10 || true
    [ -s "$S/ringplug.cdx" ] || {
        echo "PLUG COMPILE FAILED; last lines of ringplug-compile.log:"
        tail -15 "$S/ringplug-compile.log" | sed 's/^/    /'; return 1; }
    printf '%s\n' "$want" > "$S/ringplug.cdx.fp"
    echo "ringplug.cdx built ($(echo "$want" | head -c 12))"
}

# <name> <generator or ""> <bundler or ""> <bundled subject filename>
build_one() {
    local name=$1 gen=$2 bundle=$3 subject=$4
    echo "############ $name"
    cd "$S"
    [ -n "$gen" ] && python3 "$T/subjects/$gen"

    if [ -n "$bundle" ]; then
        rm -f "$subject"
        "$PWSH" -NoProfile -File "$T/subjects/$bundle" | tail -1
        [ -s "$subject" ] || { echo "BUNDLE FAILED: no $subject"; return 1; }
    fi

    python3 -c "
src = open('$S/$subject','rb').read()
open('$S/$name-ir.blob','wb').write(b'IR-CCE decks=172\n' + src + b'\x04')
print(f'blob: {len(src)} bytes of source')"

    echo "--- compiling $name to IR (seed, QEMU)"
    rm -f "$S/$name.ir"
    seed_compile "$S/$name-ir.blob" "$S/$name.ir"
    [ -s "$S/$name.ir" ] || { echo "COMPILE FAILED: no $name.ir"; return 1; }

    echo "--- transpiling $name through the plug (QEMU)"
    rm -f "$S/$name.zig"
    ring_transpile "$S/$name.ir" "$S/$name.zig" "$S/$name.transport.log" \
        || { echo "TRANSPORT FAILED ($name):"; tail -5 "$S/$name.transport.log"; return 1; }

    # A marker means the plug could not translate a CONSTRUCT, and the build must
    # not proceed to a binary quietly missing it. The prelude's own comptime
    # preconditions are not that -- prelude-comptime-guards.txt lists them.
    local markers
    markers=$(grep -o '@compileError("[^"]*")' "$S/$name.zig" \
        | grep -vxF -f <(grep -v '^#' "$T/prelude-comptime-guards.txt") \
        | sort | uniq -c || true)
    if [ -n "$markers" ]; then
        echo "REFUSED: untranslated constructs in $name.zig"
        echo "$markers"
        return 1
    fi

    echo "--- building the native binary"
    "$ZIG" build-exe "$S/$name.zig" -femit-bin="$S/$name"
    ls -la "$S/$name" | awk '{print "    " $NF, $5, "bytes"}'
    echo "############ $name built"
}
