#!/usr/bin/env python3
"""
Exports crisp animated GIFs (individual transparent looping GIFs + isometric
tile showcase GIFs) for ALL 5 Lancer animations: Idle, Walk, Run, Sword Attack,
and Bow Attack across SE and NW directions.
"""

from __future__ import annotations
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent
SPRITES_DIR = REPO / "sprites"
GIFS_DIR = REPO / "gifs"
BRAIN_DIR = Path(
    "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/ff7f66f4-8693-48db-8219-5ca19e947042"
)

CELL_W = 256
CELL_H = 340
COLS = 8

DURATIONS_MS = {
    "idle": 140,   # ~7 FPS
    "walk": 100,   # 10 FPS
    "run": 83,     # 12 FPS
    "sword": 90,   # ~11 FPS punchy slash
    "bow": 110,    # ~9 FPS draw-hold-release
}


def rgba_frames_to_transparent_gif(frames_rgba: list[Image.Image], out_path: Path, duration_ms: int) -> None:
    """Converts a list of RGBA PIL images into a clean, zero-ghosting transparent GIF."""
    strip = Image.new("RGBA", (frames_rgba[0].width * len(frames_rgba), frames_rgba[0].height), (0, 0, 0, 0))
    for i, f in enumerate(frames_rgba):
        strip.paste(f, (i * f.width, 0))

    rgb_strip = Image.new("RGB", strip.size, (36, 36, 38))
    rgb_strip.paste(strip, (0, 0), strip)
    pal_img = rgb_strip.quantize(colors=255, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    palette = pal_img.getpalette()[: 255 * 3]
    while len(palette) < 255 * 3:
        palette.extend([0, 0, 0])
    palette.extend([255, 0, 255])

    pal_ref = Image.new("P", (1, 1))
    pal_ref.putpalette(palette)

    gif_frames: list[Image.Image] = []
    for f in frames_rgba:
        arr = np.array(f)
        alpha_mask = arr[:, :, 3] < 128
        rgb = f.convert("RGB")
        quant = rgb.quantize(palette=pal_ref, dither=Image.Dither.NONE)
        q_arr = np.array(quant, dtype=np.uint8)
        q_arr[alpha_mask] = 255
        p_frame = Image.fromarray(q_arr, mode="P")
        p_frame.putpalette(palette)
        gif_frames.append(p_frame)

    gif_frames[0].save(
        out_path,
        save_all=True,
        append_images=gif_frames[1:],
        loop=0,
        duration=duration_ms,
        transparency=255,
        disposal=2,
        optimize=False,
    )


def draw_iso_stage(w: int, h: int, centers: list[tuple[int, int]], labels: list[str]) -> Image.Image:
    bg = Image.new("RGBA", (w, h), (22, 25, 34, 255))
    draw = ImageDraw.Draw(bg)
    tw, th = 148, 74
    for (cx, cy), label in zip(centers, labels):
        top = (cx, cy - th // 2)
        right = (cx + tw // 2, cy)
        bottom = (cx, cy + th // 2)
        left = (cx - tw // 2, cy)
        depth = 12
        draw.polygon([left, bottom, (bottom[0], bottom[1] + depth), (left[0], left[1] + depth)], fill=(30, 34, 46, 255), outline=(58, 66, 86, 255))
        draw.polygon([right, bottom, (bottom[0], bottom[1] + depth), (right[0], right[1] + depth)], fill=(24, 28, 38, 255), outline=(58, 66, 86, 255))
        draw.polygon([top, right, bottom, left], fill=(44, 49, 64, 255), outline=(88, 102, 130, 255))
        itw, ith = tw - 24, th - 12
        draw.polygon([(cx, cy - ith // 2), (cx + itw // 2, cy), (cx, cy + ith // 2), (cx - itw // 2, cy)], outline=(66, 76, 98, 255))
        bbox = draw.textbbox((0, 0), label)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw // 2, cy + th // 2 + 18), label, fill=(176, 190, 212, 255))
    return bg


def build_combat_showcase_gif(char_name: str, title: str, direction: str, out_path: Path) -> None:
    """Side-by-side 2-tile showcase GIF showing Sword Slash & Bow Shot simultaneously."""
    sheet = Image.open(SPRITES_DIR / f"{char_name}_isometric_{direction}_5row_master.png")
    w, h = 580, 395
    centers = [(155, 316), (425, 316)]
    labels = [f"SWORD SLASH ({direction.upper()})", f"BOW SHOT ({direction.upper()})"]
    stage = draw_iso_stage(w, h, centers, labels)

    hdraw = ImageDraw.Draw(stage)
    hdraw.text((22, 16), f"{title} - 8-Frame Sword & Bow Attacks ({direction.upper()})", fill=(226, 232, 240, 255))

    frames: list[Image.Image] = []
    for step in range(COLS):
        frame = stage.copy()
        fdraw = ImageDraw.Draw(frame)
        for row_idx, (cx, cy) in zip([3, 4], centers):
            cell = sheet.crop((step * CELL_W, row_idx * CELL_H, (step + 1) * CELL_W, (row_idx + 1) * CELL_H))
            fdraw.ellipse((cx - 38, cy - 16, cx + 38, cy + 20), fill=(10, 12, 18, 165))
            frame.alpha_composite(cell, dest=(cx - CELL_W // 2, cy - CELL_H + 22))
        frames.append(frame.convert("RGB").quantize(colors=192, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE))

    frames[0].save(out_path, save_all=True, append_images=frames[1:], loop=0, duration=95, optimize=True)


def build_duo_combat_showcase_gif(out_path: Path) -> None:
    """Both Lancers cycling Sword Slash -> Bow Shot in SE & NW."""
    sheets = {
        ("male", "se"): Image.open(SPRITES_DIR / "male_lancer_isometric_se_5row_master.png"),
        ("male", "nw"): Image.open(SPRITES_DIR / "male_lancer_isometric_nw_5row_master.png"),
        ("female", "se"): Image.open(SPRITES_DIR / "female_lancer_isometric_se_5row_master.png"),
        ("female", "nw"): Image.open(SPRITES_DIR / "female_lancer_isometric_nw_5row_master.png"),
    }

    w, h = 580, 395
    centers = [(160, 316), (420, 316)]
    base_stage = draw_iso_stage(w, h, centers, ["MALE LANCER", "FEMALE LANCER"])

    sequence = [
        ("se", 3, "SWORD SLASH (8F) | SE", 2, 92),
        ("se", 4, "BOW SHOT (8F)    | SE", 2, 108),
        ("nw", 3, "SWORD SLASH (8F) | NW", 2, 92),
        ("nw", 4, "BOW SHOT (8F)    | NW", 2, 108),
    ]

    frames: list[Image.Image] = []
    durations: list[int] = []
    for direction, row, badge, loops, dur in sequence:
        for _ in range(loops):
            for c in range(COLS):
                frame = base_stage.copy()
                fdraw = ImageDraw.Draw(frame)
                fdraw.rounded_rectangle((18, 14, 248, 38), radius=6, fill=(32, 38, 52, 255), outline=(56, 189, 248, 255))
                fdraw.text((28, 21), f"{badge}  [{c+1}/8]", fill=(226, 232, 240, 255))
                for char_key, (cx, cy) in zip(["male", "female"], centers):
                    cell = sheets[(char_key, direction)].crop((c * CELL_W, row * CELL_H, (c + 1) * CELL_W, (row + 1) * CELL_H))
                    fdraw.ellipse((cx - 38, cy - 16, cx + 38, cy + 20), fill=(10, 12, 18, 165))
                    frame.alpha_composite(cell, dest=(cx - CELL_W // 2, cy - CELL_H + 22))
                frames.append(frame.convert("RGB").quantize(colors=192, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE))
                durations.append(dur)

    frames[0].save(out_path, save_all=True, append_images=frames[1:], loop=0, duration=durations, optimize=True)


def main() -> None:
    GIFS_DIR.mkdir(parents=True, exist_ok=True)
    # 1. Individual transparent looping GIFs for Sword & Bow (8 files)
    for char_name in ["male_lancer", "female_lancer"]:
        for direction in ["se", "nw"]:
            sheet = Image.open(SPRITES_DIR / f"{char_name}_isometric_{direction}_5row_master.png")
            for row_idx, rname in [(3, "sword"), (4, "bow")]:
                frames = [
                    sheet.crop((c * CELL_W, row_idx * CELL_H, (c + 1) * CELL_W, (row_idx + 1) * CELL_H))
                    for c in range(COLS)
                ]
                out_p = GIFS_DIR / f"{char_name}_{direction}_{rname}.gif"
                rgba_frames_to_transparent_gif(frames, out_p, DURATIONS_MS[rname])
                print(f"Exported transparent GIF: {out_p.name} ({out_p.stat().st_size // 1024} KB)")

    # 2. Combat showcase GIFs (Sword & Bow side by side per character & direction)
    for char_name, title in [("male_lancer", "Male Lancer"), ("female_lancer", "Female Lancer")]:
        for direction in ["se", "nw"]:
            out_p = GIFS_DIR / f"{char_name}_{direction}_combat_showcase.gif"
            build_combat_showcase_gif(char_name, title, direction, out_p)
            (BRAIN_DIR / out_p.name).write_bytes(out_p.read_bytes())
            print(f"Exported combat showcase GIF: {out_p.name} ({out_p.stat().st_size // 1024} KB)")

    # 3. Master Duo Combat Showcase GIF
    duo_c = GIFS_DIR / "lancers_isometric_duo_combat_showcase.gif"
    build_duo_combat_showcase_gif(duo_c)
    (BRAIN_DIR / duo_c.name).write_bytes(duo_c.read_bytes())
    print(f"Exported duo combat showcase GIF: {duo_c.name} ({duo_c.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
