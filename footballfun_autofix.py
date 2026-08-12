#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import re
import sys

ROOT = Path(sys.argv[1]).resolve()
changes = []

def log(msg):
    changes.append(msg)

def replace_in_file(path: Path, old: str, new: str, label: str, max_count: int = 0):
    if not path.exists():
        return 0
    txt = path.read_text(encoding="utf-8")
    count = txt.count(old)
    if count:
        if max_count > 0 and count > max_count:
            count = max_count
            txt = txt.replace(old, new, max_count)
        else:
            txt = txt.replace(old, new)
        path.write_text(txt, encoding="utf-8")
        log(f"{label}: {count}x in {path.relative_to(ROOT)}")
    return count

main = ROOT / "app/src/main/java/com/asappfactory/footballfun/MainActivity.java"

# ----------------------------------------------------------------------
# SAFE FIX 1 — compact fallback text
# ----------------------------------------------------------------------
# Keep compact badges short and never allow "Termin us..." style truncation.
replace_in_file(
    main,
    '"Termin uskoro"',
    '"Uskoro"',
    'Shortened compact fallback "Termin uskoro" -> "Uskoro"'
)

# Also repair the already-truncated literal if it ever exists in source.
replace_in_file(
    main,
    '"Termin us..."',
    '"Uskoro"',
    'Repaired truncated compact fallback "Termin us..." -> "Uskoro"'
)

# ----------------------------------------------------------------------
# SAFE FIX 2 — club names must show up to two full lines
# ----------------------------------------------------------------------
# Target the exact two key variables guarded by footballfun_qa.py:
#   clubName  = competition participant rows
#   clubTitle = club center hero title
#
# We only modify their local setEllipsize(...) call, not every TextView in the app.

if main.exists():
    txt = main.read_text(encoding="utf-8")
    before = txt

    patterns = [
        (
            r'(TextView\s+clubName\s*=.*?setMaxLines\(2\)\s*;\s*)'
            r'clubName\.setEllipsize\(android\.text\.TextUtils\.TruncateAt\.END\)\s*;',
            r'\1clubName.setEllipsize(null);',
            'Removed ellipsis from competition club-name field'
        ),
        (
            r'(TextView\s+clubTitle\s*=.*?setMaxLines\(2\)\s*;\s*)'
            r'clubTitle\.setEllipsize\(android\.text\.TextUtils\.TruncateAt\.END\)\s*;',
            r'\1clubTitle.setEllipsize(null);',
            'Removed ellipsis from Club Center title field'
        ),
    ]

    for pattern, replacement, label in patterns:
        txt, n = re.subn(pattern, replacement, txt, flags=re.S)
        if n:
            log(f"{label}: {n}x in {main.relative_to(ROOT)}")

    # Fallback for compact one-line formatting where both calls sit on one line.
    direct_replacements = [
        (
            'clubName.setMaxLines(2);clubName.setEllipsize(android.text.TextUtils.TruncateAt.END);',
            'clubName.setMaxLines(2);clubName.setEllipsize(null);',
            'Removed ellipsis from compact clubName formatting'
        ),
        (
            'clubTitle.setMaxLines(2);clubTitle.setEllipsize(android.text.TextUtils.TruncateAt.END);',
            'clubTitle.setMaxLines(2);clubTitle.setEllipsize(null);',
            'Removed ellipsis from compact clubTitle formatting'
        ),
    ]

    for old, new, label in direct_replacements:
        n = txt.count(old)
        if n:
            txt = txt.replace(old, new)
            log(f"{label}: {n}x in {main.relative_to(ROOT)}")

    if txt != before:
        main.write_text(txt, encoding="utf-8")

# ----------------------------------------------------------------------
# SAFE FIX 3 — oversized bundled crest PNGs
# ----------------------------------------------------------------------
# Only downscale excessively large logo PNGs. Never upscale small crests.
drawable_dirs = [p for p in (ROOT / "app/src/main/res").glob("drawable*") if p.is_dir()]

for d in drawable_dirs:
    for p in d.glob("logo_*.png"):
        try:
            im = Image.open(p).convert("RGBA")
        except Exception:
            continue

        if max(im.size) > 768:
            im.thumbnail((512, 512), Image.Resampling.LANCZOS)

            canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            x = (512 - im.width) // 2
            y = (512 - im.height) // 2
            canvas.alpha_composite(im, (x, y))
            canvas.save(p, optimize=True)

            log(f"Normalized oversized crest: {p.relative_to(ROOT)}")

# ----------------------------------------------------------------------
# FINAL SELF-CHECK
# ----------------------------------------------------------------------
# If the exact two club-name ellipsis problems still remain, fail here rather
# than letting Custom QA discover that the Auto-Fix silently did nothing.
if main.exists():
    txt = main.read_text(encoding="utf-8")
    leftovers = []

    if re.search(
        r'TextView\s+clubName=.*?setMaxLines\(2\).*?'
        r'setEllipsize\(android\.text\.TextUtils\.TruncateAt\.END\)',
        re.sub(r"\s+", " ", txt)
    ):
        leftovers.append("clubName")

    if re.search(
        r'TextView\s+clubTitle=.*?setMaxLines\(2\).*?'
        r'setEllipsize\(android\.text\.TextUtils\.TruncateAt\.END\)',
        re.sub(r"\s+", " ", txt)
    ):
        leftovers.append("clubTitle")

    if leftovers:
        print("FOOTBALL FUN AUTO-FIX")
        for c in changes:
            print("FIX:", c)
        print("ERROR: Auto-Fix could not repair:", ", ".join(leftovers))
        sys.exit(1)

print("FOOTBALL FUN AUTO-FIX")
if changes:
    for c in changes:
        print("FIX:", c)
else:
    print("No safe auto-fixes were needed.")
