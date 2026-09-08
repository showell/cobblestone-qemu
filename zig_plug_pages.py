#!/usr/bin/env python3
"""The pages of Chapter: Zig Emitter, in order, read from the checkout.

This used to be a hand-maintained list, and Update 56 is what it cost. Upstream
carried the emitter as four files on our u56-candidate branch and as one file on
their own master; the list named the four, so the bundle asked for
`ZigEmitterExpressions.codex` and pwsh died on a missing file three steps into a
build that had already booted a guest.

A chapter that spans k files foots every page with `Page N of M` (CDX3004), and
a single-page chapter foots `Page 1`. That footer is the order, written by the
author of the chapter, so it does not need a second copy over here that can
disagree with it. Nothing is guessed: a gap in the numbering, a disagreement
about M, or two files claiming one page is a REFUSAL, because a bundle missing a
page reads as a pile of undefined names inside the guest rather than an error
here -- 17 of them, all naming `emit-zig-expr`, measured 2026-09-03.
"""

import pathlib
import re
import sys

import roots

CHAPTER = 'Zig Emitter'
FOOT = re.compile(r'^Page[ \t]+(\d+)(?:[ \t]+of[ \t]+(\d+))?$')


class PageError(RuntimeError):
    """The chapter's own footers do not describe a whole chapter."""


def emitter_pages(plug_dir):
    found = {}
    for f in sorted(plug_dir.glob('*.codex')):
        text = f.read_text()
        head = re.search(r'^Chapter:[ \t]*(.+?)[ \t]*$', text[:4096], re.M)
        if not head or head.group(1) != CHAPTER:
            continue
        foot = FOOT.match(text.rstrip().splitlines()[-1].strip())
        if not foot:
            raise PageError(f'{f.name} declares Chapter: {CHAPTER} but its last line is not a page footer')
        n = int(foot.group(1))
        of = int(foot.group(2)) if foot.group(2) else 1
        if n in found:
            raise PageError(f'{f.name} and {found[n][0]} both claim page {n}')
        found[n] = (f.stem, of)

    if not found:
        raise PageError(f'no page under {plug_dir} declares Chapter: {CHAPTER}')
    claimed = {of for _, of in found.values()}
    if len(claimed) != 1:
        raise PageError(f'pages disagree about the length of the chapter: {sorted(claimed)}')
    total = claimed.pop()
    if sorted(found) != list(range(1, total + 1)):
        raise PageError(f'pages {sorted(found)} do not make a whole chapter of {total}')
    return [found[n][0] for n in sorted(found)]


if __name__ == '__main__':
    try:
        for stem in emitter_pages(roots.codex_root() / 'codex' / 'plugs' / 'zig'):
            print(stem)
    except (roots.RootError, PageError) as why:
        print(f'REFUSING: {why}', file=sys.stderr)
        sys.exit(2)
