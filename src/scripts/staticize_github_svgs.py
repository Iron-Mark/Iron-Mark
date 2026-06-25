from __future__ import annotations

import re
from pathlib import Path


SVG_DIR = Path("assets/github")
SVG_FILES = (
    "stats.svg",
    "top-langs.svg",
    "activity-graph.svg",
    "streak.svg",
)


def staticize(svg: str) -> str:
    """Make generated GitHub stat SVGs readable when animation is disabled."""
    svg = re.sub(r"opacity:0;?", "", svg)
    svg = re.sub(r"animation:[^;\"}]+;?", "", svg)
    svg = re.sub(r"animation-[^:]+:[^;\"}]+;?", "", svg)
    svg = re.sub(r"@keyframes\s+[^{]+\{(?:[^{}]|\{[^{}]*\})*\}", "", svg)
    svg = svg.replace("stroke-dashoffset:5000;", "stroke-dashoffset:0;")
    svg = svg.replace("stroke-dasharray:5000;", "stroke-dasharray:none;")
    svg = re.sub(r'style=""\s*', "", svg)
    svg = re.sub(r"\s+;", ";", svg)
    svg = re.sub(r"\{;", "{", svg)
    return svg


def main() -> None:
    for file_name in SVG_FILES:
        path = SVG_DIR / file_name
        source = path.read_text(encoding="utf-8")
        path.write_text(staticize(source), encoding="utf-8")


if __name__ == "__main__":
    main()
