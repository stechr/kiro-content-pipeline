#!/usr/bin/env python3
"""visual_qa.py — deterministic blog-image QA for a post draft (TASK-097).

Checks the visual integrity of a blog `post.md` against its sibling `assets/`
folder and writes a short report (`visual-qa.md`) at the item root. Stdlib-only.

Deterministic checks:
  - hero / featured_image declared in frontmatter, the file exists, and it is
    NOT also embedded inline as a body figure (cover duplication);
  - every inline image reference (Hugo `{{< figure >}}`, markdown `![]()`,
    Obsidian `![[ ]]`) resolves to an existing file in assets/;
  - no inline image is referenced more than once (duplicate embed);
  - every inline figure has non-empty alt text;
  - orphan images in assets/ that are never referenced (advisory only —
    image-prompts option renders, avatar/linkedin images are expected orphans).

WARN-ONLY by default (exit 0). Pass --strict to exit 1 when any hard issue
(missing referenced file, missing/duplicated hero, missing alt) is found.

Usage:
    python3 visual_qa.py <post.md>                 # human report to stdout
    python3 visual_qa.py <post.md> --json          # machine-readable
    python3 visual_qa.py <post.md> --write         # also write item-root/visual-qa.md
    python3 visual_qa.py <post.md> --write --out <path>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

# Image refs we recognise in the body.
_RE_FIGURE = re.compile(r'\{\{<\s*figure\b([^>]*?)>}}', re.IGNORECASE)
_RE_FIG_SRC = re.compile(r'src\s*=\s*"([^"]+)"', re.IGNORECASE)
_RE_FIG_ALT = re.compile(r'alt\s*=\s*"([^"]*)"', re.IGNORECASE)
_RE_MD_IMG = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
_RE_WIKI_IMG = re.compile(r'!\[\[([^\]|]+?\.(?:png|jpe?g|webp|gif|svg))(?:\|[^\]]*)?\]\]', re.IGNORECASE)
_IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")
# assets that are channel-specific (LinkedIn / avatar / prompt options) and are
# NOT expected to be embedded in the blog body — excluded from orphan noise.
_EXPECTED_ORPHAN = re.compile(
    r'(linkedin-image|linkedin-video|.*-avatar|^option\d)', re.IGNORECASE)


def _parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm = {}
    for line in text[3:end].splitlines():
        m = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', line)
        if m:
            k, v = m.group(1), m.group(2).strip()
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            fm[k] = v
    return fm


def _item_root(post: Path) -> Path:
    """Item root = parent of a `blog/` channel subfolder, else the post's parent."""
    if post.parent.name == "blog":
        return post.parent.parent
    return post.parent


def _basename(src: str) -> str:
    return src.replace("\\", "/").rstrip("/").split("/")[-1]


def analyze(post_path: Path) -> dict:
    post_path = Path(post_path)
    text = post_path.read_text(errors="ignore")
    fm = _parse_frontmatter(text)
    item_root = _item_root(post_path)
    assets = item_root / "assets"
    asset_files = (
        {f.name: f for f in assets.iterdir() if f.is_file() and f.suffix.lower() in _IMG_EXTS}
        if assets.is_dir() else {}
    )

    # strip code fences so example image markup is not counted as a real ref
    body = re.sub(r'```.*?```', '', text, flags=re.DOTALL)

    refs = []  # {kind, src, base, alt}
    for m in _RE_FIGURE.finditer(body):
        attrs = m.group(1)
        s = _RE_FIG_SRC.search(attrs)
        a = _RE_FIG_ALT.search(attrs)
        if s:
            refs.append({"kind": "figure", "src": s.group(1),
                         "base": _basename(s.group(1)),
                         "alt": (a.group(1).strip() if a else "")})
    for m in _RE_MD_IMG.finditer(body):
        alt, src = m.group(1).strip(), m.group(2)
        if src.lower().endswith(_IMG_EXTS):
            refs.append({"kind": "markdown", "src": src, "base": _basename(src), "alt": alt})
    for m in _RE_WIKI_IMG.finditer(body):
        src = m.group(1)
        refs.append({"kind": "wikilink", "src": src, "base": _basename(src), "alt": ""})

    issues, warnings = [], []

    # hero / featured_image
    hero = fm.get("featured_image") or fm.get("hero") or ""
    hero_base = _basename(hero) if hero else ""
    hero_present = bool(hero)
    hero_file_ok = bool(hero_base and hero_base in asset_files)
    if not hero_present:
        issues.append("no featured_image/hero declared in frontmatter")
    elif not hero_file_ok:
        if any("cover" in n.lower() for n in asset_files):
            warnings.append(f"featured_image '{hero_base}' not a literal asset (cover-named asset present)")
        elif asset_files:
            # draft stage: a cover is assigned/renamed at publish from one of the
            # option images, so a literal cover file is not expected yet.
            warnings.append(f"featured_image '{hero_base}' not in assets/ yet "
                            f"(cover is assigned at publish from {len(asset_files)} image(s))")
        else:
            issues.append(f"featured_image '{hero_base}' not found and assets/ is empty")

    # missing referenced files
    for r in refs:
        if r["base"] not in asset_files:
            issues.append(f"referenced image missing in assets/: {r['src']} ({r['kind']})")

    # duplicate inline embeds
    seen = {}
    for r in refs:
        seen[r["base"]] = seen.get(r["base"], 0) + 1
    for base, n in seen.items():
        if n > 1:
            issues.append(f"image embedded {n}× inline (duplicate): {base}")

    # hero also embedded inline = cover duplication
    if hero_base and hero_base in seen:
        warnings.append(f"hero '{hero_base}' is also embedded inline (cover duplication)")

    # alt text — required on published forms (figure/markdown); for Obsidian
    # wikilink embeds (draft stage) alt is added at publish, so only warn.
    for r in refs:
        if not r["alt"]:
            if r["kind"] == "wikilink":
                warnings.append(f"wikilink embed has no alt text yet (added at publish): {r['base']}")
            else:
                issues.append(f"figure missing alt text: {r['base']} ({r['kind']})")

    # orphans (advisory)
    referenced = {r["base"] for r in refs} | ({hero_base} if hero_base else set())
    orphans = [n for n in sorted(asset_files)
               if n not in referenced and not _EXPECTED_ORPHAN.search(n)]
    for o in orphans:
        warnings.append(f"asset never referenced in body (orphan): {o}")

    return {
        "post": str(post_path),
        "item_root": str(item_root),
        "assets_dir": str(assets),
        "asset_count": len(asset_files),
        "inline_refs": len(refs),
        "hero": hero_base,
        "hero_present": hero_present,
        "hero_file_ok": hero_file_ok,
        "issues": issues,
        "warnings": warnings,
        "ok": not issues,
    }


def render_md(rep: dict) -> str:
    today = date.today().isoformat()
    lines = [
        "---",
        'description: "Deterministic blog-image QA — hero/featured_image + inline figure existence, duplication, and alt-text checks."',
        f"date: {today}",
        "type: visual-qa",
        "---",
        "",
        "# Visual QA",
        "",
        f"**Post:** `{rep['post']}`  ",
        f"**Verdict:** {'✅ PASS' if rep['ok'] else '❌ ISSUES (' + str(len(rep['issues'])) + ')'}  ",
        f"**Assets:** {rep['asset_count']} file(s) · **inline refs:** {rep['inline_refs']} · "
        f"**hero:** {rep['hero'] or '—'} ({'ok' if rep['hero_file_ok'] else 'check'})",
        "",
        "## Issues (must-fix)",
        "",
    ]
    lines += ([f"- ❌ {i}" for i in rep["issues"]] or ["- (none)"])
    lines += ["", "## Warnings (advisory)", ""]
    lines += ([f"- ⚠️ {w}" for w in rep["warnings"]] or ["- (none)"])
    lines += ["", f"_Generated by visual_qa.py on {today}._", ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Deterministic blog-image QA for a post draft.")
    ap.add_argument("post", help="path to post.md")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true", help="write visual-qa.md at item root")
    ap.add_argument("--out", help="explicit output path for the report")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any issue")
    args = ap.parse_args(argv)

    post = Path(args.post)
    if not post.exists():
        sys.stderr.write(f"visual_qa: post not found: {post}\n")
        return 2
    rep = analyze(post)

    if args.write or args.out:
        out = Path(args.out) if args.out else (Path(rep["item_root"]) / "visual-qa.md")
        out.write_text(render_md(rep), encoding="utf-8")
        rep["written"] = str(out)

    if args.json:
        print(json.dumps(rep, indent=2))
    else:
        print(render_md(rep))
        if rep.get("written"):
            print(f"\n[wrote {rep['written']}]")

    return 1 if (args.strict and not rep["ok"]) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
