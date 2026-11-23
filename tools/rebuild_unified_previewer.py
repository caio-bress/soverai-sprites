#!/usr/bin/env python3
"""
Builds the unified Soverai All-Classes Interactive Isometric Previewer
(Male Lancer, Female Lancer, Bastion, Archon — all movement, weapon-ready idles, and combat animations)
for both GitHub Pages (index.html) and the compact inline artifact previewer.
"""

from __future__ import annotations
import base64
import io
import json
import re
from pathlib import Path
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
BRAIN_DIR = Path(
    "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/ff7f66f4-8693-48db-8219-5ca19e947042"
)
ARTIFACT_HTML = BRAIN_DIR / "soverai_unified_previewer.html"
REPO_INDEX = REPO / "index.html"

ATLAS_SPECS = {
    "male_lancer_se": [
        REPO / "lancer/sprites/male_lancer_isometric_se_5row_master.png",
        REPO / "lancer/sprites/male_lancer_se_idle_sword_strip.png",
        REPO / "lancer/sprites/male_lancer_se_idle_bow_strip.png",
    ],
    "male_lancer_nw": [
        REPO / "lancer/sprites/male_lancer_isometric_nw_5row_master.png",
        REPO / "lancer/sprites/male_lancer_nw_idle_sword_strip.png",
        REPO / "lancer/sprites/male_lancer_nw_idle_bow_strip.png",
    ],
    "female_lancer_se": [
        REPO / "lancer/sprites/female_lancer_isometric_se_5row_master.png",
        REPO / "lancer/sprites/female_lancer_se_idle_sword_strip.png",
        REPO / "lancer/sprites/female_lancer_se_idle_bow_strip.png",
    ],
    "female_lancer_nw": [
        REPO / "lancer/sprites/female_lancer_isometric_nw_5row_master.png",
        REPO / "lancer/sprites/female_lancer_nw_idle_sword_strip.png",
        REPO / "lancer/sprites/female_lancer_nw_idle_bow_strip.png",
    ],
    "bastion_se": [
        REPO / "bastion/sprites/bastion_isometric_se_5row_master.png",
        REPO / "bastion/sprites/bastion_se_idle_sword_shield_strip.png",
        REPO / "bastion/sprites/bastion_se_idle_glaive_strip.png",
    ],
    "bastion_nw": [
        REPO / "bastion/sprites/bastion_isometric_nw_5row_master.png",
        REPO / "bastion/sprites/bastion_nw_idle_sword_shield_strip.png",
        REPO / "bastion/sprites/bastion_nw_idle_glaive_strip.png",
    ],
    "archon_se": [
        REPO / "archon/sprites/archon_isometric_se_5row_master.png",
        REPO / "archon/sprites/archon_se_idle_turibulo_shield_strip.png",
    ],
    "archon_nw": [
        REPO / "archon/sprites/archon_isometric_nw_5row_master.png",
        REPO / "archon/sprites/archon_nw_idle_turibulo_shield_strip.png",
    ],
}

STANDALONE_STYLE = """  <title>Soverai — Unified Isometric Tactical RPG Sprite Previewer</title>
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
      max-width: 1160px;
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
    for k, parts in ATLAS_SPECS.items():
        imgs = [Image.open(p).convert("RGBA") for p in parts]
        total_h = sum(im.height for im in imgs)
        full = Image.new("RGBA", (2048, total_h), (0, 0, 0, 0))
        y = 0
        for im in imgs:
            full.paste(im, (0, y))
            y += im.height
        rows = total_h // 340
        small = full.resize((1024, 170 * rows), Image.Resampling.NEAREST).quantize(
            colors=64, method=Image.Quantize.FASTOCTREE
        )
        buf = io.BytesIO()
        small.save(buf, format="PNG", optimize=True)
        data[k] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        print(f"Encoded {k} ({rows} rows): {len(buf.getvalue()):,} bytes")

    js_assign = "window.SOVERAI_ATLASES = " + json.dumps(data) + ";"
    html = ARTIFACT_HTML.read_text(encoding="utf-8")
    if "/*__SOVERAI_ATLAS_PLACEHOLDER__*/" in html:
        html_embedded = html.replace("/*__SOVERAI_ATLAS_PLACEHOLDER__*/", js_assign, 1)
    else:
        pattern = re.compile(r"window\.SOVERAI_ATLASES\s*=\s*\{.*?\};", re.DOTALL)
        html_embedded = pattern.sub(lambda _: js_assign, html, count=1)

    ARTIFACT_HTML.write_text(html_embedded, encoding="utf-8")
    print(f"Updated {ARTIFACT_HTML} ({ARTIFACT_HTML.stat().st_size:,} bytes)")

    html_standalone = html_embedded.replace(
        """  <title>Soverai — Unified Isometric Sprite Previewer</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    canvas {
      image-rendering: pixelated;
      image-rendering: crisp-edges;
    }
  </style>""",
        STANDALONE_STYLE,
    ).replace('style="height: 315px;"', 'style="height: 520px;"')

    REPO_INDEX.write_text(html_standalone, encoding="utf-8")
    print(f"Updated {REPO_INDEX} ({REPO_INDEX.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
