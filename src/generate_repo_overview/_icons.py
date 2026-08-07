from __future__ import annotations


def _bazel_svg(extra_attrs: str) -> str:
    """Return a self-contained Bazel SVG icon."""
    return (
        f'<svg viewBox="0 0 72 72" {extra_attrs} aria-label="Bazel">'
        '<polygon points="36,4 60,16 68,40 52,64 20,64 4,40 12,16" fill="#43A047"/>'
        '<polygon points="36,18 50,24 54,40 44,54 28,54 18,40 22,24" fill="#76D275"/>'
        '<polygon points="36,28 44,32 46,40 40,48 32,48 26,40 28,32" fill="#fff"/>'
        "</svg>"
    )
