from __future__ import annotations

import re
import xml.dom.minidom
from pathlib import Path


SVG_DIR = Path("assets/github")
SVG_FILES = (
    "stats.svg",
    "top-langs.svg",
    "activity-graph.svg",
    "streak.svg",
)


def staticize(svg: str) -> str:
    """Make generated GitHub stat SVGs readable when animation is disabled.

    The character classes below must stop at BOTH quote characters:
    github-readme-stats cards use double-quoted XML attributes, but
    streak-stats.demolab.com emits single-quoted ones (style='...'). A
    class that only excluded '"' would eat straight through a closing
    single quote and the markup after it until the next ';', '"', or '}',
    truncating the file into invalid XML - exactly what corrupted the
    committed streak.svg on 2026-07-21.
    """
    # Bare 'opacity: 0' declarations (streak-stats writes a space after the
    # colon) hide nodes the animation would have faded in; drop them so the
    # static card is visible. The lookarounds keep 'stroke-opacity: 0' and
    # non-zero values like 'opacity: 0.85' intact.
    svg = re.sub(r"(?<![\w-])opacity:\s*0(?![.\d]);?", "", svg)
    svg = re.sub(r"animation:[^;\"'}]+;?", "", svg)
    svg = re.sub(r"animation-[^:\"'}]+:[^;\"'}]+;?", "", svg)
    svg = re.sub(r"@keyframes\s+[^{]+\{(?:[^{}]|\{[^{}]*\})*\}", "", svg)
    svg = svg.replace("stroke-dashoffset:5000;", "stroke-dashoffset:0;")
    svg = svg.replace("stroke-dasharray:5000;", "stroke-dasharray:none;")
    svg = re.sub(r"style=([\"'])\s*\1\s*", "", svg)
    svg = re.sub(r"\s+;", ";", svg)
    svg = re.sub(r"\{;", "{", svg)
    return svg


def staticize_file(path: Path) -> bool:
    """Staticize one SVG file in place; return True if it was rewritten.

    Belt-and-braces guard: regex staticizing is not XML-aware, so before
    writing anything the result is parsed with xml.dom.minidom. If it no
    longer parses, the original file is left byte-for-byte unchanged and a
    warning is printed - a stale-but-valid card is always better than a
    corrupted one.
    """
    source = path.read_text(encoding="utf-8")
    result = staticize(source)
    try:
        xml.dom.minidom.parseString(result)
    except Exception as exc:  # noqa: BLE001 - any parse failure means "do not publish"
        print(
            f"::warning::staticize_github_svgs: staticizing {path} produced "
            f"invalid XML ({exc}); keeping the original file unchanged."
        )
        return False
    path.write_text(result, encoding="utf-8")
    return True


def main() -> None:
    for file_name in SVG_FILES:
        staticize_file(SVG_DIR / file_name)


if __name__ == "__main__":
    main()
