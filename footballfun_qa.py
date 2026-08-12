#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import re, sys, xml.etree.ElementTree as ET

ROOT = Path(sys.argv[1]).resolve()
errors = []
warnings = []

def err(msg): errors.append(msg)
def warn(msg): warnings.append(msg)

main = ROOT / "app/src/main/java/com/asappfactory/footballfun/MainActivity.java"
gradle = ROOT / "app/build.gradle"

if not main.exists():
    err("MainActivity.java not found.")
if not gradle.exists():
    err("app/build.gradle not found.")

if main.exists():
    txt = main.read_text(encoding="utf-8")
    for s in ["Termin us...", "Termin uskoro"]:
        if s in txt:
            err(f'Forbidden compact UI text remains: "{s}"')

    compact = re.sub(r"\s+", " ", txt)
    key_patterns = [
        r'TextView\s+clubName=.*?setMaxLines\(2\).*?setEllipsize\(android\.text\.TextUtils\.TruncateAt\.END\)',
        r'TextView\s+clubTitle=.*?setMaxLines\(2\).*?setEllipsize\(android\.text\.TextUtils\.TruncateAt\.END\)',
    ]
    for pat in key_patterns:
        if re.search(pat, compact):
            err("A key club-name field still ellipsizes text instead of showing up to two full lines.")

    refs = set(re.findall(r'"(logo_[A-Za-z0-9_]+)"', txt))
    res_names = {p.stem for p in (ROOT / "app/src/main/res").rglob("*")
                 if p.is_file() and (p.parent.name.startswith("drawable") or p.parent.name.startswith("mipmap"))}
    for name in sorted(refs - res_names):
        err(f"Missing referenced local crest resource: {name}")

for p in (ROOT / "app/src/main/res").rglob("*.xml"):
    try:
        ET.parse(p)
    except Exception as e:
        err(f"Invalid XML {p.relative_to(ROOT)}: {e}")

for p in (ROOT / "app/src/main/res").rglob("logo_*.png"):
    try:
        im = Image.open(p).convert("RGBA")
    except Exception as e:
        err(f"Unreadable crest {p.relative_to(ROOT)}: {e}")
        continue

    w, h = im.size
    if w < 96 or h < 96:
        warn(f"Very low-resolution crest: {p.relative_to(ROOT)} ({w}x{h})")

    alpha = im.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        bw, bh = bbox[2]-bbox[0], bbox[3]-bbox[1]
        content_ratio = max(bw / max(w,1), bh / max(h,1))
        if content_ratio < 0.38:
            err(f"Crest content is too small inside its canvas: {p.relative_to(ROOT)} "
                f"(visible content only {content_ratio:.0%} of canvas).")
        elif content_ratio < 0.52:
            warn(f"Crest may appear smaller than others: {p.relative_to(ROOT)} "
                 f"(visible content {content_ratio:.0%} of canvas).")

if gradle.exists():
    g = gradle.read_text(encoding="utf-8")
    vc = re.search(r"versionCode\s+(\d+)", g)
    vn = re.search(r"versionName\s+['\"]([^'\"]+)['\"]", g)
    if not vc: err("versionCode not found.")
    if not vn: err("versionName not found.")
    if vc and int(vc.group(1)) < 1: err("Invalid versionCode.")

data_dir = ROOT / "app/src/main/java/com/asappfactory/footballfun/data"
for f in sorted(data_dir.glob("*2627Data.java")):
    t = f.read_text(encoding="utf-8")
    start = t.find("private static final String DATA")
    if start < 0:
        continue
    end = t.find(";\n", start)
    if end < 0:
        continue
    block = t[start:end]
    pieces = re.findall(r'"([^"]*)"', block)
    joined = "".join(pieces).replace("\\n", "\n")
    matches = [ln.split("|") for ln in joined.splitlines()
               if re.match(r"^\d{4}-\d{2}-\d{2}", ln)]
    if not matches:
        continue
    teams = sorted({x[2] for x in matches} | {x[3] for x in matches})
    expected = len(teams) * (len(teams)-1)
    if len(matches) != expected:
        err(f"{f.name}: schedule has {len(matches)} matches, expected {expected} for {len(teams)} teams.")
    rounds = {}
    for x in matches:
        try:
            r = int(x[1])
        except Exception:
            err(f"{f.name}: invalid round value in row: {'|'.join(x)}")
            continue
        rounds[r] = rounds.get(r, 0) + 1
    expected_per_round = len(teams)//2
    bad = {r:c for r,c in rounds.items() if c != expected_per_round}
    if bad:
        err(f"{f.name}: malformed round sizes: {bad}")

print("FOOTBALL FUN CUSTOM QA")
for w in warnings:
    print("WARNING:", w)
for e in errors:
    print("ERROR:", e)

print(f"SUMMARY: {len(errors)} errors, {len(warnings)} warnings")
if errors:
    sys.exit(1)
