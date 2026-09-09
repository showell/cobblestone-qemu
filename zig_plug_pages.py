#!/usr/bin/env python3
"""The pages of Chapter: Zig Emitter, in order, read from the checkout.

Every bundler needs the chapter's pages, and the chapter already names them: a
chapter spanning k files foots every page with `Page N of M` (CDX3004), and a
single-page chapter foots `Page 1`. That footer is the order, written by the
author of the chapter, so no second copy is kept here to disagree with it --
and the page count differs between checkouts, so a copy is wrong for all but
one of them.

Nothing is guessed. A gap in the numbering, a disagreement about M, or two
files claiming one page is a REFUSAL: a bundle missing a page reads as a pile
of undefined names inside the guest rather than an error out here.
"""

import pathlib
import re

# This repository has no ignore rules, so an imported module must not leave a
# __pycache__ behind. `-B` in a shebang covers ./name.py only, and every caller
# here runs `python3 name.py`, so the guard belongs in the file and must be set
# before the first local import.
import sys
sys.dont_write_bytecode = True

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
