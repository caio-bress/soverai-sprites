#!/usr/bin/env python3
"""
Slices and removes backgrounds from the Lancer (The Old Guild / Nômade) isometric
2x6 sprite sheets (Idle + Walk Cycle, SE & NW directions), stabilizing each frame's
horizontal center-of-mass and foot baseline for jitter-free tactical RPG playback.
"""

from __future__ import annotations
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "characters" / "lancer_old_guild"
BRAIN_DIR = Path(
    "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/ff7f66f4-8693-48db-8219-5ca19e947042"
)

FRAME_W = 224
FRAME_H = 360
COLS = 6
ROWS = 2


def remove_background_rgba(img_rgb: Image.Image, tol: float = 10.5) -> Image.Image:
    """Removes the flat dark background while preserving interior dark armor shading."""
    arr = np.array(img_rgb, dtype=np.float32)
    h, w, _ = arr.shape
    border = np.concatenate([arr[0, :], arr[-1, :], arr[:, 0], arr[:, -1]])
    bg = np.median(border, axis=0)
    dist = np.sqrt(np.sum((arr - bg) ** 2, axis=2))

    grad_y = np.abs(np.diff(arr, axis=0, prepend=arr[:1, :])).max(axis=2)
    grad_x = np.abs(np.diff(arr, axis=1, prepend=arr[:, :1])).max(axis=2)
    grad = np.maximum(grad_x, grad_y)

    visited = np.zeros((h, w), dtype=bool)
    is_bg = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    seeds = []
    for x in range(w):
        for y in [0, h - 1, h // 2]:
            seeds.append((y, x))
    for y in range(h):
        for x in [0, w - 1]:
            seeds.append((y, x))

    for y, x in seeds:
        if dist[y, x] < tol * 1.4 and not visited[y, x]:
            visited[y, x] = True
            q.append((y, x))

    while q:
        cy, cx = q.popleft()
        is_bg[cy, cx] = True
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                if dist[ny, nx] < tol and grad[ny, nx] < 12:
                    visited[ny, nx] = True
                    q.append((ny, nx))

    # Clear truly flat enclosed pockets (e.g., gap between arm and waist) where std < 1.5 and grad < 4
    flat_cand = (dist < 6.0) & (grad < 4.0) & (~is_bg)
    f_vis = np.zeros((h, w), dtype=bool)
    for y in range(h):
        for x in range(w):
            if flat_cand[y, x] and not f_vis[y, x]:
                comp = []
                fq = deque([(y, x)])
                f_vis[y, x] = True
                while fq:
                    cy, cx = fq.popleft()
                    comp.append((cy, cx))
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and flat_cand[ny, nx] and not f_vis[ny, nx]:
                            f_vis[ny, nx] = True
                            fq.append((ny, nx))
                if len(comp) >= 18:
                    vals = np.array([arr[cy, cx] for cy, cx in comp])
                    if np.max(np.std(vals, axis=0)) < 1.8:
                        for cy, cx in comp:
                            is_bg[cy, cx] = True

    # Remove tiny isolated dust specks (< 12 pixels)
    fg = ~is_bg
    c_vis = np.zeros((h, w), dtype=bool)
    for y in range(h):
        for x in range(w):
            if fg[y, x] and not c_vis[y, x]:
                comp = []
                cq = deque([(y, x)])
                c_vis[y, x] = True
                while cq:
                    cy, cx = cq.popleft()
                    comp.append((cy, cx))
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and fg[ny, nx] and not c_vis[ny, nx]:
                            c_vis[ny, nx] = True
                            cq.append((ny, nx))
                if len(comp) < 12:
                    for cy, cx in comp:
                        is_bg[cy, cx] = True

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(arr, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.where(is_bg, 0, 255)
    return Image.fromarray(rgba, "RGBA")


def slice_and_align_sheet(
    src_path: Path, char_name: str, direction: str
) -> Path:
    """Slices a 2x6 sprite sheet into stabilized 224x360 frames and saves individual + packed PNGs."""
    src_im = Image.open(src_path).convert("RGB")
    rgba_im = remove_background_rgba(src_im)
    arr = np.array(rgba_im)
    h, w, _ = arr.shape

    row_h = h // ROWS
    col_w = w / float(COLS)

    char_dir = OUT_DIR / char_name / direction
    char_dir.mkdir(parents=True, exist_ok=True)

    packed = Image.new("RGBA", (FRAME_W * COLS, FRAME_H * ROWS), (0, 0, 0, 0))
    row_names = ["idle", "walk"]

    for r in range(ROWS):
        for c in range(COLS):
            cx0 = int(round(c * col_w))
            cx1 = int(round((c + 1) * col_w))
            cy0 = r * row_h
            cy1 = (r + 1) * row_h

            cell = arr[cy0:cy1, cx0:cx1]
            alpha = cell[:, :, 3] > 0
            ys, xs = np.where(alpha)
            frame_im = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))

            if len(ys) > 0:
                y_min, y_max = int(ys.min()), int(ys.max())
                x_min, x_max = int(xs.min()), int(xs.max())
                # Use upper torso/head horizontal center (top 55% of sprite) to prevent leg stride from shifting torso X
                torso_cut = y_min + int((y_max - y_min) * 0.55)
                t_ys, t_xs = np.where(alpha[y_min:torso_cut, :])
                center_x = int(round(np.median(t_xs))) if len(t_xs) > 0 else (x_min + x_max) // 2

                sprite_crop = Image.fromarray(cell[y_min : y_max + 1, x_min : x_max + 1], "RGBA")
                # Place torso center at FRAME_W // 2, and anchor foot baseline / top consistently
                dest_x = (FRAME_W // 2) - (center_x - x_min)
                if r == 0:
                    # Idle: anchor feet at y = FRAME_H - 14
                    dest_y = (FRAME_H - 14) - (y_max - y_min)
                else:
                    # Walk: preserve natural vertical bob relative to row top while keeping within frame
                    dest_y = max(8, min(FRAME_H - (y_max - y_min) - 6, y_min - 18))

                frame_im.paste(sprite_crop, (dest_x, dest_y), sprite_crop)

            frame_file = char_dir / f"{row_names[r]}_{c}.png"
            frame_im.save(frame_file)
            packed.paste(frame_im, (c * FRAME_W, r * FRAME_H), frame_im)

    sheet_out = OUT_DIR / f"{char_name}_isometric_{direction}_sheet.png"
    packed.save(sheet_out)
    print(f"Saved {sheet_out} ({packed.size[0]}x{packed.size[1]}) + 12 frames in {char_dir}")
    return sheet_out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheets = [
        (BRAIN_DIR / "male_lancer_isometric_sheet_v2_1794768628483.jpg", "male_lancer", "se"),
        (BRAIN_DIR / "male_lancer_isometric_nw_sheet_1794768880681.jpg", "male_lancer", "nw"),
        (BRAIN_DIR / "female_lancer_isometric_sheet_1794768546242.jpg", "female_lancer", "se"),
        (BRAIN_DIR / "female_lancer_isometric_nw_sheet.jpg", "female_lancer", "nw"),
    ]
    for src, cname, d in sheets:
        if src.exists():
            slice_and_align_sheet(src, cname, d)

    showcase_src = BRAIN_DIR / "lancers_isometric_showcase_v2_1794768612710.jpg"
    if showcase_src.exists():
        showcase_rgba = remove_background_rgba(Image.open(showcase_src).convert("RGB"))
        showcase_out = OUT_DIR / "lancers_isometric_showcase.png"
        showcase_rgba.save(showcase_out)
        print(f"Saved {showcase_out}")


if __name__ == "__main__":
    main()
import math
import numpy as np
from PIL import Image
import sys
sys.path.insert(0, "/home/antigravity/caio-bress/soverai-tacticalRPG/tools")
from slice_lancer_sprites import remove_background_rgba

brain = "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/ff7f66f4-8693-48db-8219-5ca19e947042"
out_dir = "/home/antigravity/caio-bress/soverai-tacticalRPG/assets/characters/lancer_old_guild"

fw, fh = 224, 360

# First, load the Male Lancer's native SE run frames from male_lancer_isometric_run_sheet_1794780376445.jpg
male_run_raw = Image.open(f"{brain}/male_lancer_isometric_run_sheet_1794780376445.jpg").convert("RGB")
male_run_rgba = np.array(remove_background_rgba(male_run_raw))
mh, mw, _ = male_run_rgba.shape
m_row_h = mh // 2
m_col_w = mw / 6.0

# Extract the 6 flying crimson gold-fringed sashes from the Male Lancer's native SE run row!
# In each cell of the top row, the flying crimson sash is on the left side (x < center_x - 28, y in waist..knee)
flying_sashes = []
male_se_frames = []

for c in range(6):
    cx0, cx1 = int(round(c * m_col_w)), int(round((c + 1) * m_col_w))
    cell = male_run_rgba[0:m_row_h, cx0:cx1]
    alpha = cell[:, :, 3] > 0
    ys, xs = np.where(alpha)
    f_im = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    if len(ys) > 0:
        y_min, y_max = int(ys.min()), int(ys.max())
        x_min, x_max = int(xs.min()), int(xs.max())
        t_cut = y_min + int((y_max - y_min) * 0.55)
        t_xs = np.where(alpha[y_min:t_cut, :])[1]
        center_x = int(round(np.median(t_xs))) if len(t_xs) > 0 else (x_min + x_max) // 2
        crop = Image.fromarray(cell[y_min:y_max+1, x_min:x_max+1], "RGBA")
        dest_x = (fw // 2) - (center_x - x_min)
        # Apply a slight extra vertical bounce to emphasize the sprint rhythm
        extra_bob = [1, 6, -2, -10, 5, -4][c]
        dest_y = max(4, min(fh - (y_max - y_min) - 4, y_min - 14 + extra_bob))
        f_im.paste(crop, (dest_x, dest_y), crop)
    male_se_frames.append(f_im)

    # Extract the flying crimson sash from f_im (x in 0..86, y in 140..255)
    f_arr = np.array(f_im)
    sash_box = f_arr[140:255, 4:88].copy()
    # Keep only the sash & tassel pixels (y > 30 in box, or x < 62)
    for sy in range(sash_box.shape[0]):
        for sx in range(sash_box.shape[1]):
            if sash_box[sy, sx, 3] == 0:
                continue
            # Exclude upper forearm skin if sy < 26 and sx > 48
            if sy < 26 and sx > 48:
                sash_box[sy, sx, 3] = 0
            elif sx > 72:
                sash_box[sy, sx, 3] = int(sash_box[sy, sx, 3] * max(0.0, (86 - sx) / 14.0))
    flying_sashes.append(Image.fromarray(sash_box, "RGBA"))


def smooth_step(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / max(1e-5, edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def articulate_smooth_sprint(
    frame_rgba: np.ndarray,
    frame_idx: int,
    facing_right: bool = True,
    sash_im: Image.Image = None,
    sash_offset_x: int = 0,
    sash_offset_y: int = 0,
) -> Image.Image:
    """
    Smooth, seam-free biomechanical sprint warper using C1-continuous displacement fields
    and nearest-neighbor pixel lookup.
    """
    h, w, _ = frame_rgba.shape
    alpha = frame_rgba[:, :, 3] > 0
    ys, xs = np.where(alpha)
    if len(ys) == 0:
        return Image.fromarray(frame_rgba, "RGBA")

    y_min, y_max = int(ys.min()), int(ys.max())
    char_h = max(1, y_max - y_min)
    cx = int(np.median(xs))

    # 6-frame sprint cycle parameters:
    # 0: Contact Strike | 1: Deep Cushion | 2: Drive | 3: AIRBORNE FLIGHT | 4: Opposite Cushion | 5: Opposite Launch
    bob_y = [1, 12, -5, -18, 11, -7][frame_idx]
    lean_px = [14.0, 17.0, 15.5, 13.0, 17.0, 15.0][frame_idx]
    stride_scale = [1.22, 1.08, 1.18, 1.28, 1.08, 1.20][frame_idx]
    back_kick_y = [14.0, 6.0, 20.0, 26.0, 6.0, 22.0][frame_idx]
    front_lift_y = [6.0, 0.0, 12.0, 20.0, 0.0, 14.0][frame_idx]

    dir_sign = 1.0 if facing_right else -1.0
    waist_y = y_min + char_h * 0.46

    out = np.zeros_like(frame_rgba)

    for y_out in range(h):
        y_ref = y_out - bob_y
        if y_ref < y_min - 28 or y_ref > y_max + 28:
            continue

        # Normalized vertical position u in [0..1] from top of head to bottom of feet
        u = (y_ref - y_min) / float(char_h)

        # Smooth forward torso lean above the waist (bell/ramp that tapers smoothly to 0 at waist u=0.50)
        upper_weight = 1.0 - smooth_step(0.12, 0.54, u)
        # Slightly less lean at the very top of the head so head looks forward
        head_damp = 0.72 + 0.28 * smooth_step(0.0, 0.18, u)
        shift_x_torso = lean_px * upper_weight * head_damp * dir_sign

        # Smooth lower-body leg stride & high-knee/heel-kick weight (ramps smoothly from 0 at u=0.45 to 1 at u=0.95)
        leg_weight = smooth_step(0.45, 0.92, u)
        horiz_scale = 1.0 + (stride_scale - 1.0) * leg_weight

        for x_out in range(w):
            rel_x = (x_out - shift_x_torso) - cx
            sx_rel = rel_x / horiz_scale

            # Smooth transition between back-leg kick and front-leg knee drive across rel_x = 0
            front_blend = smooth_step(-14.0, 14.0, rel_x * dir_sign)
            lift_y = leg_weight * ((1.0 - front_blend) * back_kick_y + front_blend * front_lift_y)

            # In cushion frames (1, 4), slightly compress lower legs
            if frame_idx in (1, 4):
                lift_y -= 4.0 * leg_weight * front_blend

            sx = int(round(cx + sx_rel))
            sy = int(round(y_ref + lift_y))

            if 0 <= sy < h and 0 <= sx < w:
                out[y_out, x_out] = frame_rgba[sy, sx]

    # Remove any isolated 1-pixel specks
    out_im = Image.fromarray(out, "RGBA")

    if sash_im is not None:
        s_use = sash_im if facing_right else sash_im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        canvas_under = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if facing_right:
            sx_pos = int(cx - 86 + sash_offset_x)
        else:
            sx_pos = int(cx + 8 + sash_offset_x)
        sy_pos = int(waist_y + bob_y - 16 + sash_offset_y)
        canvas_under.paste(s_use, (sx_pos, sy_pos), s_use)
        canvas_under.alpha_composite(out_im)
        out_im = canvas_under

    return out_im


# 1. Build Male Lancer Run Sheet (Top Row: native SE run with sprint bounce; Bottom Row: NW rear sprint with flying sash)
male_run_packed = Image.new("RGBA", (fw * 6, fh * 2), (0, 0, 0, 0))
male_run_bg = Image.new("RGB", (fw * 6, fh * 2), (36, 36, 37))

male_se_run_dir = f"{out_dir}/male_lancer/se"
male_nw_run_dir = f"{out_dir}/male_lancer/nw"

male_nw_walk_sheet = np.array(Image.open(f"{out_dir}/male_lancer_isometric_nw_sheet.png"))

for c in range(6):
    im_se = male_se_frames[c]
    im_se.save(f"{male_se_run_dir}/run_{c}.png")
    male_run_packed.paste(im_se, (c * fw, 0), im_se)
    male_run_bg.paste(im_se, (c * fw, 0), im_se)

    cell_nw = male_nw_walk_sheet[fh:fh*2, c*fw:(c+1)*fw]
    im_nw = articulate_smooth_sprint(
        cell_nw, c, facing_right=False, sash_im=flying_sashes[c], sash_offset_x=4, sash_offset_y=2
    )
    im_nw.save(f"{male_nw_run_dir}/run_{c}.png")
    male_run_packed.paste(im_nw, (c * fw, fh), im_nw)
    male_run_bg.paste(im_nw, (c * fw, fh), im_nw)

male_run_packed.save(f"{out_dir}/male_lancer_isometric_run_sheet.png")
male_run_packed.save(f"{brain}/male_lancer_isometric_run_sheet.png")
male_run_bg.save(f"{brain}/male_lancer_isometric_run_sheet_v2.jpg", quality=96)

# 2. Build Female Lancer Run Sheet (Top Row: SE sprint with flying sash; Bottom Row: NW rear sprint with flying sash)
fem_se_walk_sheet = np.array(Image.open(f"{out_dir}/female_lancer_isometric_se_sheet.png"))
fem_nw_walk_sheet = np.array(Image.open(f"{out_dir}/female_lancer_isometric_nw_sheet.png"))

fem_run_packed = Image.new("RGBA", (fw * 6, fh * 2), (0, 0, 0, 0))
fem_run_bg = Image.new("RGB", (fw * 6, fh * 2), (36, 36, 37))

fem_se_run_dir = f"{out_dir}/female_lancer/se"
fem_nw_run_dir = f"{out_dir}/female_lancer/nw"

for c in range(6):
    cell_se = fem_se_walk_sheet[fh:fh*2, c*fw:(c+1)*fw]
    im_se = articulate_smooth_sprint(
        cell_se, c, facing_right=True, sash_im=flying_sashes[c], sash_offset_x=10, sash_offset_y=6
    )
    im_se.save(f"{fem_se_run_dir}/run_{c}.png")
    fem_run_packed.paste(im_se, (c * fw, 0), im_se)
    fem_run_bg.paste(im_se, (c * fw, 0), im_se)

    cell_nw = fem_nw_walk_sheet[fh:fh*2, c*fw:(c+1)*fw]
    im_nw = articulate_smooth_sprint(
        cell_nw, c, facing_right=False, sash_im=flying_sashes[c], sash_offset_x=0, sash_offset_y=6
    )
    im_nw.save(f"{fem_nw_run_dir}/run_{c}.png")
    fem_run_packed.paste(im_nw, (c * fw, fh), im_nw)
    fem_run_bg.paste(im_nw, (c * fw, fh), im_nw)

fem_run_packed.save(f"{out_dir}/female_lancer_isometric_run_sheet.png")
fem_run_packed.save(f"{brain}/female_lancer_isometric_run_sheet.png")
fem_run_bg.save(f"{brain}/female_lancer_isometric_run_sheet.jpg", quality=96)
print("Successfully generated smooth, seam-free Male and Female isometric run sheets!")
