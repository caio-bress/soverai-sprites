#!/usr/bin/env python3
"""
Embeds Archon's 5x8 SE & NW transparent master sheets into both the inline
artifact previewer and the standalone desktop/GitHub Pages HTML previewer.
"""

from __future__ import annotations
import base64
import io
import json
import re
from pathlib import Path
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SPRITES_DIR = REPO / "sprites"
BRAIN_DIR = Path(
    "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/ff7f66f4-8693-48db-8219-5ca19e947042"
)

ARTIFACT_HTML = BRAIN_DIR / "archon_isometric_previewer.html"
REPO_HTML = REPO / "archon_isometric_previewer.html"
REPO_INDEX = REPO / "index.html"

MAPPING = {
    "archon_se": ("archon_isometric_se_5row_master.png", "archon_se_idle_turibulo_shield_strip.png"),
    "archon_nw": ("archon_isometric_nw_5row_master.png", "archon_nw_idle_turibulo_shield_strip.png"),
}

STANDALONE_STYLE = """  <title>Archon (The Old Faith — First Light) — Isometric Sprite, Weapon Idle &amp; Combat Previewer</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {
      --background: #0f1117;
      --content: #161922;
      --card: #1c202b;
      --card-border: #2e3446;
      --border: #384057;
      --foreground: #e2e8f0;
      --muted-foreground: #94a3b8;
      --primary: #eab308;
      --primary-foreground: #0f172a;
    }
    body {
      background-color: var(--background) !important;
      color: var(--foreground) !important;
      font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
      padding: 1.25rem !important;
      max-width: 1120px;
      margin: 0 auto !important;
    }
    #isoCanvas {
      height: 520px !important;
    }
    canvas {
      image-rendering: pixelated;
      image-rendering: crisp-edges;
    }
  </style>"""


def main() -> None:
    data: dict[str, str] = {}
    for k, (master_f, tur_idle_f) in MAPPING.items():
        m_im = Image.open(SPRITES_DIR / master_f).convert("RGBA")
        tur_im = Image.open(SPRITES_DIR / tur_idle_f).convert("RGBA")
        full = Image.new("RGBA", (2048, 340 * 6), (0, 0, 0, 0))
        full.paste(m_im, (0, 0))
        full.paste(tur_im, (0, 340 * 5))
        small = full.resize((1024, 170 * 6), Image.Resampling.NEAREST).quantize(
            colors=64, method=Image.Quantize.FASTOCTREE
        )
        buf = io.BytesIO()
        small.save(buf, format="PNG", optimize=True)
        data[k] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        print(f"Encoded {k}: {len(buf.getvalue())} bytes")

    js_assign = "window.SPRITE_SHEETS = " + json.dumps(data) + ";"
    html = ARTIFACT_HTML.read_text(encoding="utf-8")
    if "/*__SPRITE_DATA_PLACEHOLDER__*/" in html:
        html_embedded = html.replace("/*__SPRITE_DATA_PLACEHOLDER__*/", js_assign, 1)
    else:
        pattern = re.compile(r"window\.SPRITE_SHEETS\s*=\s*\{.*?\};", re.DOTALL)
        html_embedded = pattern.sub(lambda _: js_assign, html, count=1)

    ARTIFACT_HTML.write_text(html_embedded, encoding="utf-8")
    print(f"Updated {ARTIFACT_HTML}")

    html_standalone = html_embedded.replace(
        """  <style>
    canvas {
      image-rendering: pixelated;
      image-rendering: crisp-edges;
    }
  </style>""",
        STANDALONE_STYLE,
    ).replace('style="height: 315px;"', 'style="height: 520px;"')

    for target in [REPO_HTML, REPO_INDEX]:
        target.write_text(html_standalone, encoding="utf-8")
        print(f"Updated {target}")


if __name__ == "__main__":
    main()
