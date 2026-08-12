#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import sys

ROOT = Path(sys.argv[1]).resolve()
changes = []

def replace_in_file(path: Path, old: str, new: str, label: str):
    if not path.exists():
        return 0
    txt = path.read_text(encoding="utf-8")
    count = txt.count(old)
    if count:
        path.write_text(txt.replace(old, new), encoding="utf-8")
        changes.append(f"{label}: {count}x in {path.relative_to(ROOT)}")
    return count

main = ROOT / "app/src/main/java/com/asappfactory/footballfun/MainActivity.java"

replace_in_file(
    main,
    '"Termin uskoro"',
    '"Uskoro"',
    'Shortened compact fallback "Termin uskoro" -> "Uskoro"'
)

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
            changes.append(f"Normalized oversized crest: {p.relative_to(ROOT)}")

print("FOOTBALL FUN AUTO-FIX")
if changes:
    for c in changes:
        print("FIX:", c)
else:
    print("No safe auto-fixes were needed.")
