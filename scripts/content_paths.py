#!/usr/bin/env python3
"""content_paths.py — single resolver for the kiro-content-pipeline config.

Loads two JSON configs and resolves logical keys so skills never hardcode paths
or user-specific values:

  config/content-paths.local.json   (paths)      -> workspace_root, content_root, item layout
  config/pipeline.local.json        (non-path)   -> style corpus, guidelines, aliases, etc.

If a *.local.json is absent, the matching *.sample.json is used as a fallback, so a
fresh clone resolves (its defaults point at the bundled examples/ tree) instead of
crashing. Override the paths config with CONTENT_PATHS_CONFIG and the pipeline config
with PIPELINE_CONFIG.

Stdlib only. Token expansion: ${HOME}, ${workspace_root}, ${content_root}.

Python usage:
    from content_paths import content_root, item_dir, channel_dir, style_corpus_dir
    DRAFTS = content_root()                       # Path
    blog = channel_dir("2026-07-02-foo", "blog")  # Path

CLI usage (for shell / SKILL.md docs):
    python3 content_paths.py get content_root
    python3 content_paths.py get style_corpus_dir
    python3 content_paths.py item-dir 2026-07-02-foo
    python3 content_paths.py channel-dir 2026-07-02-foo blog
    python3 content_paths.py aliases
    python3 content_paths.py dump
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CFG_DIR = _REPO_ROOT / "config"


def _pick(local_name: str, sample_name: str, env_var: str) -> Path:
    env = os.environ.get(env_var)
    if env:
        return Path(env)
    local = _CFG_DIR / local_name
    return local if local.exists() else _CFG_DIR / sample_name


PATHS_CONFIG = _pick("content-paths.local.json", "content-paths.sample.json", "CONTENT_PATHS_CONFIG")
PIPELINE_CONFIG = _pick("pipeline.local.json", "pipeline.sample.json", "PIPELINE_CONFIG")

# top-level path keys resolvable via `get`/`dump`
_SIMPLE_KEYS = ("workspace_root", "content_root")
# top-level pipeline path-like keys (may be "" = optional/disabled)
_PIPELINE_PATH_KEYS = ("style_corpus_dir", "prior_work_dir", "image_guidelines_path",
                       "voice_profile_path")


def load_config(path: Path | str | None = None) -> dict:
    p = Path(path) if path else PATHS_CONFIG
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_pipeline(path: Path | str | None = None) -> dict:
    p = Path(path) if path else PIPELINE_CONFIG
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _expand(value: str, cfg: dict) -> str:
    """Expand ${HOME}, ${REPO}, ${workspace_root}, ${content_root} tokens (order matters)."""
    out = value.replace("${HOME}", os.path.expanduser("~"))
    out = out.replace("${REPO}", str(_REPO_ROOT))
    if "${workspace_root}" in out:
        wr = cfg.get("workspace_root", "")
        wr = wr.replace("${HOME}", os.path.expanduser("~")).replace("${REPO}", str(_REPO_ROOT))
        out = out.replace("${workspace_root}", wr)
    if "${content_root}" in out:
        cr = _expand(cfg.get("content_root", ""), cfg)
        out = out.replace("${content_root}", cr)
    return out


def resolve(key: str, cfg: dict | None = None) -> Path:
    """Resolve a simple top-level path key from content-paths to an absolute Path."""
    cfg = cfg or load_config()
    if key not in cfg:
        raise KeyError(f"content-paths config has no key '{key}'")
    return Path(_expand(cfg[key], cfg))


# --- content-paths accessors ----------------------------------------------

def workspace_root(cfg: dict | None = None) -> Path:
    return resolve("workspace_root", cfg)


def content_root(cfg: dict | None = None) -> Path:
    """The per-item draft folders root."""
    return resolve("content_root", cfg)


def item_dir(slug: str, cfg: dict | None = None) -> Path:
    """A content-item draft folder, e.g. content_root()/<date>-<slug>."""
    return content_root(cfg) / slug


def channel_subfolder(channel: str, cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    subs = cfg.get("item_subfolders", {})
    if channel not in subs:
        raise KeyError(f"unknown channel '{channel}' (have: {sorted(subs)})")
    return subs[channel]


def channel_dir(slug: str, channel: str, cfg: dict | None = None) -> Path:
    """Per-item channel subfolder, e.g. .../<date>-<slug>/blog."""
    cfg = cfg or load_config()
    return item_dir(slug, cfg) / channel_subfolder(channel, cfg)


def manifest_path(slug: str, cfg: dict | None = None) -> Path:
    """The per-item content-item.md manifest path."""
    cfg = cfg or load_config()
    name = cfg.get("item_files", {}).get("manifest", "content-item.md")
    return item_dir(slug, cfg) / name


# --- pipeline (non-path) accessors ----------------------------------------

def _pipeline_path(key: str, pcfg: dict | None = None):
    """Resolve an optional path-like pipeline value. Returns Path, or None if empty/absent."""
    pcfg = pcfg or load_pipeline()
    raw = pcfg.get(key, "")
    if not raw:
        return None
    # expand ${HOME}/${REPO}; ${workspace_root} resolved against the paths config
    val = raw.replace("${HOME}", os.path.expanduser("~")).replace("${REPO}", str(_REPO_ROOT))
    if "${workspace_root}" in val:
        val = val.replace("${workspace_root}", str(workspace_root()))
    return Path(val)


def style_corpus_dir(pcfg: dict | None = None):
    return _pipeline_path("style_corpus_dir", pcfg)


def prior_work_dir(pcfg: dict | None = None):
    return _pipeline_path("prior_work_dir", pcfg)


def image_guidelines_path(pcfg: dict | None = None):
    return _pipeline_path("image_guidelines_path", pcfg)


def voice_profile_path(pcfg: dict | None = None):
    return _pipeline_path("voice_profile_path", pcfg)


def site_public_base_url(pcfg: dict | None = None) -> str:
    pcfg = pcfg or load_pipeline()
    return (pcfg.get("site_public_base_url") or "").strip()


def user_aliases(pcfg: dict | None = None) -> list[str]:
    pcfg = pcfg or load_pipeline()
    vals = pcfg.get("user_aliases") or []
    return [a for a in vals if a]


# --- CLI -------------------------------------------------------------------

def _main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "get" and len(argv) == 2:
        key = argv[1]
        cfg = load_config()
        if key in cfg:
            print(resolve(key, cfg))
            return 0
        # try pipeline
        if key in _PIPELINE_PATH_KEYS:
            p = _pipeline_path(key)
            print(p if p else "")
            return 0
        if key == "site_public_base_url":
            print(site_public_base_url())
            return 0
        raise KeyError(f"no key '{key}' in content-paths or pipeline config")
    if cmd == "item-dir" and len(argv) == 2:
        print(item_dir(argv[1]))
        return 0
    if cmd == "channel-dir" and len(argv) == 3:
        print(channel_dir(argv[1], argv[2]))
        return 0
    if cmd == "manifest" and len(argv) == 2:
        print(manifest_path(argv[1]))
        return 0
    if cmd == "aliases":
        print(",".join(user_aliases()))
        return 0
    if cmd == "dump":
        cfg = load_config()
        for k in _SIMPLE_KEYS:
            print(f"{k:22s} {resolve(k, cfg)}")
        for ch in cfg.get("item_subfolders", {}):
            print(f"  channel:{ch:12s} {channel_subfolder(ch, cfg)}")
        print("--- pipeline ---")
        for k in _PIPELINE_PATH_KEYS:
            p = _pipeline_path(k)
            print(f"{k:22s} {p if p else '(unset — step optional)'}")
        print(f"{'site_public_base_url':22s} {site_public_base_url() or '(unset — step optional)'}")
        print(f"{'user_aliases':22s} {user_aliases() or '(none)'}")
        return 0
    sys.stderr.write(
        "usage: content_paths.py {get KEY|item-dir SLUG|channel-dir SLUG CHANNEL|"
        "manifest SLUG|aliases|dump}\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
