#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import re
import sys

ROOT = Path(sys.argv[1]).resolve()
changes = []

def add_change(msg):
    changes.append(msg)

main = ROOT / "app/src/main/java/com/asappfactory/footballfun/MainActivity.java"

# ----------------------------------------------------------------------
# SAFE FIX 1 — compact fallback text
# ----------------------------------------------------------------------
if main.exists():
    txt = main.read_text(encoding="utf-8")

    replacements = [
        ('"Termin uskoro"', '"Uskoro"', 'Shortened "Termin uskoro" -> "Uskoro"'),
        ('"Termin us..."', '"Uskoro"', 'Repaired "Termin us..." -> "Uskoro"'),
    ]
    for old, new, label in replacements:
        n = txt.count(old)
        if n:
            txt = txt.replace(old, new)
            add_change(f"{label}: {n}x")

    # ------------------------------------------------------------------
    # SAFE FIX 2 — exact clubName / clubTitle ellipsis calls only
    # ------------------------------------------------------------------
    # Do NOT use a broad regex across the whole method/file.
    # Replace only calls on the exact variables.
    exact_patterns = [
        (
            r'\bclubName\.setEllipsize\(\s*android\.text\.TextUtils\.TruncateAt\.END\s*\)\s*;',
            'clubName.setEllipsize(null);',
            'Removed ellipsis from clubName'
        ),
        (
            r'\bclubTitle\.setEllipsize\(\s*android\.text\.TextUtils\.TruncateAt\.END\s*\)\s*;',
            'clubTitle.setEllipsize(null);',
            'Removed ellipsis from clubTitle'
        ),
    ]

    for pattern, repl, label in exact_patterns:
        txt, n = re.subn(pattern, repl, txt)
        if n:
            add_change(f"{label}: {n}x")

    main.write_text(txt, encoding="utf-8")

# ----------------------------------------------------------------------
# SAFE FIX 3 — oversized crest PNGs
# ----------------------------------------------------------------------
drawable_dirs = [p for p in (ROOT / "app/src/main/res").glob("drawable*") if p.is_dir()]

for d in drawable_dirs:
    for p in d.glob("logo_*.png"):
        try:
            im = Image.open(p).convert("RGBA")
        except Exception:
            continue

        # Only downscale huge files; never upscale small crests.
        if max(im.size) > 768:
            im.thumbnail((512, 512), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            x = (512 - im.width) // 2
            y = (512 - im.height) // 2
            canvas.alpha_composite(im, (x, y))
            canvas.save(p, optimize=True)
            add_change(f"Normalized oversized crest: {p.relative_to(ROOT)}")

print("FOOTBALL FUN AUTO-FIX v2")
if changes:
    for c in changes:
        print("FIX:", c)
else:
    print("No safe auto-fixes were needed.")
