from __future__ import annotations

import re
from pathlib import Path

_TEMPLATES = Path(__file__).parent / "templates"

# Inner content of the official Bazel SVG (paths only, no outer <svg> tag).
# Source: https://blog.bazel.build/images/bazel-icon.svg (bazelbuild/bazel-blog)
_BAZEL_SVG_INNER = re.sub(
    r"<svg[^>]*>|</svg>",
    "",
    (_TEMPLATES / "bazel-icon.svg").read_text(encoding="utf-8"),
).strip()


def _bazel_svg(extra_attrs: str) -> str:
    """Return the official Bazel SVG icon with caller-supplied attributes."""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" {extra_attrs} aria-label="Bazel">{_BAZEL_SVG_INNER}</svg>'
