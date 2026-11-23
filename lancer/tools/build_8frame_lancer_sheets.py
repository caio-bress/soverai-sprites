#!/usr/bin/env python3
"""
Builds smooth 8-frame isometric sprite sheets (Row 0: 8-frame Breathing Idle,
Row 1: 8-frame Pose-Guided Walk, Row 2: 8-frame Pose-Guided Run) for both
Male and Female Lancers in SE and NW directions.
"""

from __future__ import annotations
import math
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SPRITES_DIR = REPO / "sprites"
ORIG_DIR = REPO / "originals"
BRAIN_DIR = Path(
    "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/ff7f66f4-8693-48db-8219-5ca19e947042"
)

FRAME_W = 192
FRAME_H = 304
COLS = 8
ROWS = 3  # 0: idle, 1: walk, 2: run
GROUND_ANCHOR_Y = FRAME_H - 18  # y=286 baseline inside each 192x304 cell


def smooth_step(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / max(1e-5, edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def remove_background_rgba(
    img_rgb: Image.Image, tol: float = 11.0, mask_watermark: bool = True
) -> Image.Image:
    """Removes the flat dark background and bottom-right watermark while preserving dark armor."""
    arr = np.array(img_rgb, dtype=np.float32)
    h, w, _ = arr.shape
    border = np.concatenate([arr[0, :], arr[-1, :], arr[:, 0], arr[:, -1]])
    bg = np.median(border, axis=0)

    if mask_watermark and w >= 1200 and h >= 700:
        # Clear tiny corner watermark outside sprite bounds
        arr[h - 46 :, w - 46 :] = bg

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
                if dist[ny, nx] < tol and grad[ny, nx] < 13:
                    visited[ny, nx] = True
                    q.append((ny, nx))

    # Clear truly flat enclosed holes (between arm & waist, or between legs)
    flat_cand = (dist < 6.5) & (grad < 4.5) & (~is_bg)
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
                if len(comp) >= 14:
                    vals = np.array([arr[cy, cx] for cy, cx in comp])
                    if np.max(np.std(vals, axis=0)) < 2.0:
                        for cy, cx in comp:
                            is_bg[cy, cx] = True

    # Remove tiny isolated dust specks (< 10 px)
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
                if len(comp) < 10:
                    for cy, cx in comp:
                        is_bg[cy, cx] = True

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(arr, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.where(is_bg, 0, 255)
    return Image.fromarray(rgba, "RGBA")


def generate_breathing_idle_frames(
    base_rgba: Image.Image, target_height: int, facing_se: bool = True
) -> list[Image.Image]:
    """
    Creates an 8-frame smooth pixel-art breathing idle animation from a single clean
    base sprite: feet stay glued to the isometric tile while the chest expands outward
    and rises smoothly on inhale, with 1-frame overlapping lag on head/hair/sashes and
    pulsing Archeotek glow.
    """
    arr0 = np.array(base_rgba)
    ys0, xs0 = np.where(arr0[:, :, 3] > 0)
    crop = base_rgba.crop((int(xs0.min()), int(ys0.min()), int(xs0.max()) + 1, int(ys0.max()) + 1))

    # Scale cleanly to match the exact Walk/Run height
    scale = target_height / float(crop.height)
    new_w = max(1, int(round(crop.width * scale)))
    new_h = max(1, int(round(crop.height * scale)))
    scaled = crop.resize((new_w, new_h), Image.Resampling.NEAREST)

    # Place centered on a FRAME_W x FRAME_H canvas anchored to GROUND_ANCHOR_Y
    base_canvas = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    s_arr = np.array(scaled)
    s_alpha = s_arr[:, :, 3] > 0
    t_cut = int(new_h * 0.55)
    t_xs = np.where(s_alpha[:t_cut, :])[1]
    cx_crop = int(round(np.median(t_xs))) if len(t_xs) > 0 else new_w // 2
    px0 = (FRAME_W // 2) - cx_crop
    py0 = GROUND_ANCHOR_Y - new_h
    base_canvas.paste(scaled, (px0, py0), scaled)

    src = np.array(base_canvas)
    ys, xs = np.where(src[:, :, 3] > 0)
    y_min, y_max = int(ys.min()), int(ys.max())
    char_h = max(1, y_max - y_min)
    cx = FRAME_W // 2

    frames: list[Image.Image] = []
    for i in range(COLS):
        # Smooth ease-in-out breathing curve (0 at rest, 1 at full inhale peak)
        theta = (2.0 * math.pi * i) / COLS
        b = 0.5 - 0.5 * math.cos(theta)
        # 1-frame delayed secondary motion for head, hair & sash follow-through
        theta_lag = (2.0 * math.pi * ((i - 1.1) % COLS)) / COLS
        b_lag = 0.5 - 0.5 * math.cos(theta_lag)
        sash_sway = math.sin(theta - 0.8)

        out = np.zeros_like(src)
        for y_out in range(FRAME_H):
            u = (y_out - y_min) / float(char_h)
            if u < -0.15 or u > 1.05:
                continue

            # 1. Vertical breathing rise: 0 at feet (u >= 0.78), ramps up smoothly through knees/hips to chest (-6.0px)
            # Head uses slightly lagged breathing curve so it settles 1 frame after the chest
            leg_to_waist = 1.0 - smooth_step(0.46, 0.80, u)
            chest_peak = 1.0 - smooth_step(0.32, 0.72, u)
            head_mask = 1.0 - smooth_step(0.14, 0.25, u)

            chest_rise = 7.5 * b * chest_peak + 2.2 * b * leg_to_waist
            head_rise = (5.0 * b + 2.8 * b_lag) * head_mask
            dy = chest_rise * (1.0 - head_mask) + head_rise

            # 2. Horizontal ribcage expansion (bell curve centered at chest u=0.33, 0 at neck & waist)
            chest_bell = smooth_step(0.16, 0.30, u) * (1.0 - smooth_step(0.38, 0.56, u))
            expand_scale = 1.0 + 0.072 * b * chest_bell

            # 3. Gentle crimson sash wind drift in lower half (u in 0.48..0.84)
            sash_band = smooth_step(0.46, 0.56, u) * (1.0 - smooth_step(0.76, 0.88, u))

            for x_out in range(FRAME_W):
                rel_x = x_out - cx
                # Shoulders/arms subtly lift slightly more with slight lag
                arm_mask = smooth_step(16.0, 26.0, abs(rel_x)) * smooth_step(0.18, 0.28, u) * (1.0 - smooth_step(0.50, 0.62, u))
                local_dy = dy + 1.8 * b_lag * arm_mask

                # Horizontal displacement: chest expands outward + subtle cloth sway on trailing side
                sx_rel = rel_x / expand_scale
                trailing_side = (rel_x < -12) if facing_se else (rel_x > 12)
                if trailing_side and sash_band > 0.0:
                    sx_rel -= sash_sway * 2.8 * sash_band

                sx = int(round(cx + sx_rel))
                sy = int(round(y_out + local_dy))
                if 0 <= sy < FRAME_H and 0 <= sx < FRAME_W:
                    px = src[sy, sx]
                    if px[3] > 0:
                        # Subtle emissive pulse on cyan/blue Archeotek orbs & canisters on inhale
                        r_v, g_v, b_v, a_v = int(px[0]), int(px[1]), int(px[2]), int(px[3])
                        is_glow = (b_v > 125 and b_v - r_v > 28) or (g_v > 145 and b_v > 140 and r_v < 115)
                        if is_glow and b > 0.05:
                            boost = int(round(28 * b))
                            r_v = min(255, r_v + boost // 2)
                            g_v = min(255, g_v + boost)
                            b_v = min(255, b_v + boost)
                        out[y_out, x_out] = (r_v, g_v, b_v, a_v)

        frames.append(Image.fromarray(out, "RGBA"))
    return frames


def extract_row_sprites_cc(row_rgba: np.ndarray, cols: int = COLS) -> list[np.ndarray]:
    """
    Segments a full row into `cols` clean sprites using 8-connected components so an
    outstretched fist or streaming sash is NEVER clipped onto a neighboring frame.
    """
    rh, rw, _ = row_rgba.shape
    fg = row_rgba[:, :, 3] > 0
    labels = np.zeros((rh, rw), dtype=np.int32)
    comps: list[tuple[int, float, int, int, int, int]] = []  # (label, cx, x0, y0, x1, y1, count)
    lbl = 0
    for y in range(rh):
        for x in range(rw):
            if fg[y, x] and labels[y, x] == 0:
                lbl += 1
                q = deque([(y, x)])
                labels[y, x] = lbl
                xs_sum = 0
                cnt = 0
                x0 = x1 = x
                y0 = y1 = y
                while q:
                    cy, cx = q.popleft()
                    xs_sum += cx
                    cnt += 1
                    if cx < x0: x0 = cx
                    if cx > x1: x1 = cx
                    if cy < y0: y0 = cy
                    if cy > y1: y1 = cy
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dy == 0 and dx == 0:
                                continue
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < rh and 0 <= nx < rw and fg[ny, nx] and labels[ny, nx] == 0:
                                labels[ny, nx] = lbl
                                q.append((ny, nx))
                comps.append((lbl, xs_sum / float(cnt), x0, y0, x1, y1, cnt))

    # Pick the `cols` largest components (the 8 main character bodies) sorted left-to-right
    main_comps = sorted(sorted(comps, key=lambda t: t[6], reverse=True)[:cols], key=lambda t: t[1])
    main_cxs = [m[1] for m in main_comps]
    main_labels = {m[0]: idx for idx, m in enumerate(main_comps)}

    # Assign any small detached pixel clusters (e.g., tassel bead) to the nearest main sprite center
    label_to_slot: dict[int, int] = dict(main_labels)
    for c_lbl, c_cx, x0, y0, x1, y1, cnt in comps:
        if c_lbl not in label_to_slot and cnt >= 4:
            nearest = min(range(cols), key=lambda idx: abs(c_cx - main_cxs[idx]))
            # Only attach if within 95px of that character's center
            if abs(c_cx - main_cxs[nearest]) < 95:
                label_to_slot[c_lbl] = nearest

    slot_masks = [np.zeros((rh, rw), dtype=bool) for _ in range(cols)]
    for c_lbl, slot in label_to_slot.items():
        slot_masks[slot] |= (labels == c_lbl)

    sprites = []
    for slot in range(cols):
        sp = np.zeros((rh, rw, 4), dtype=np.uint8)
        sp[slot_masks[slot]] = row_rgba[slot_masks[slot]]
        sprites.append(sp)
    return sprites


def slice_8f_walk_run_sheet(src_path: Path) -> tuple[list[Image.Image], list[Image.Image], int]:
    """
    Slices a 2x8 pose-guided Walk (Row 0) + Run (Row 1) sheet into 8+8 stabilized
    192x304 RGBA frames using connected-component isolation, preserving natural
    vertical gait bounce and airborne flight!
    """
    im_rgb = Image.open(src_path).convert("RGB")
    rgba = np.array(remove_background_rgba(im_rgb, tol=11.0, mask_watermark=True))
    H, W, _ = rgba.shape
    row_h = H // 2

    rows_out: list[list[Image.Image]] = [[], []]
    walk_heights: list[int] = []

    for r in range(2):
        row_slice = rgba[r * row_h : (r + 1) * row_h, :]
        slot_sprites = extract_row_sprites_cc(row_slice, COLS)

        contact_y1s = []
        cell_data = []
        for c in range(COLS):
            sp = slot_sprites[c]
            alpha = sp[:, :, 3] > 0
            ys, xs = np.where(alpha)
            if len(ys) > 0:
                y0, y1 = int(ys.min()), int(ys.max())
                x0, x1 = int(xs.min()), int(xs.max())
                t_cut = y0 + int((y1 - y0) * 0.50)
                t_xs = np.where(alpha[y0:t_cut, :])[1]
                cx = int(round(np.median(t_xs))) if len(t_xs) > 0 else (x0 + x1) // 2
                cell_data.append((sp, x0, y0, x1, y1, cx))
                if c in (0, 1, 4, 5):
                    contact_y1s.append(y1)
                if r == 0:
                    walk_heights.append(y1 - y0)
            else:
                cell_data.append(None)

        row_ground_src = int(round(np.median(contact_y1s))) if contact_y1s else (row_h - 32)
        y_shift = GROUND_ANCHOR_Y - row_ground_src

        for c in range(COLS):
            frame_im = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
            item = cell_data[c]
            if item is not None:
                sp, x0, y0, x1, y1, cx = item
                crop = Image.fromarray(sp[y0 : y1 + 1, x0 : x1 + 1], "RGBA")
                dest_x = (FRAME_W // 2) - (cx - x0)
                dest_y = y0 + y_shift
                dest_y = max(2, min(FRAME_H - crop.height - 2, dest_y))
                frame_im.paste(crop, (dest_x, dest_y), crop)
            rows_out[r].append(frame_im)

    median_walk_h = int(round(np.median(walk_heights))) if walk_heights else 250
    return rows_out[0], rows_out[1], median_walk_h


def build_character_direction(
    char_name: str,
    direction: str,
    walk_run_src: Path,
    idle_base_im: Image.Image,
) -> Path:
    facing_se = direction == "se"
    walk_frames, run_frames, target_h = slice_8f_walk_run_sheet(walk_run_src)
    idle_frames = generate_breathing_idle_frames(idle_base_im, target_height=target_h, facing_se=facing_se)

    out_frame_dir = SPRITES_DIR / char_name / direction
    out_frame_dir.mkdir(parents=True, exist_ok=True)
    # Remove any old 6-frame files before writing 8-frame sets
    for old in out_frame_dir.glob("*.png"):
        old.unlink()

    master = Image.new("RGBA", (FRAME_W * COLS, FRAME_H * ROWS), (0, 0, 0, 0))
    walk_run_sheet = Image.new("RGBA", (FRAME_W * COLS, FRAME_H * 2), (0, 0, 0, 0))

    for r, (rname, flist) in enumerate([("idle", idle_frames), ("walk", walk_frames), ("run", run_frames)]):
        for c, fim in enumerate(flist):
            fim.save(out_frame_dir / f"{rname}_{c}.png")
            master.paste(fim, (c * FRAME_W, r * FRAME_H), fim)
            if r >= 1:
                walk_run_sheet.paste(fim, (c * FRAME_W, (r - 1) * FRAME_H), fim)

    master_path = SPRITES_DIR / f"{char_name}_isometric_{direction}_full_sheet.png"
    master.save(master_path)
    master.save(BRAIN_DIR / f"{char_name}_isometric_{direction}_8f_master.png")

    wr_path = SPRITES_DIR / f"{char_name}_isometric_{direction}_8f_walk_run.png"
    walk_run_sheet.save(wr_path)

    # Copy original raw 2x8 sheet into originals/
    Image.open(walk_run_src).save(ORIG_DIR / walk_run_src.name, quality=96)
    print(f"Built {master_path.name} ({master.size[0]}x{master.size[1]}, 3x8 frames, target_h={target_h}px)")
    return master_path


def main() -> None:
    ORIG_DIR.mkdir(parents=True, exist_ok=True)

    # Extract clean single-frame lowered-arm idle bases for Male Lancer (SE left half, NW right half)
    male_idle_pair_path = BRAIN_DIR / "male_lancer_idle_arms_lowered_1795194835581.jpg"
    male_idle_raw = Image.open(male_idle_pair_path).convert("RGB")
    male_idle_raw.save(ORIG_DIR / male_idle_pair_path.name, quality=96)
    male_idle_rgba = remove_background_rgba(male_idle_raw, tol=11.0, mask_watermark=True)
    mid_x = male_idle_rgba.width // 2
    male_se_idle_base = male_idle_rgba.crop((0, 0, mid_x, male_idle_rgba.height))
    male_nw_idle_base = male_idle_rgba.crop((mid_x, 0, male_idle_rgba.width, male_idle_rgba.height))

    fem_se_idle_base = Image.open(SPRITES_DIR / "female_lancer_isometric_se_sheet.png").crop((0, 0, 224, 360))

    # For Female NW idle base: use clean native Frame 6 (upright staggered back stance) from the 8f NW sheet
    fem_nw_raw = Image.open(BRAIN_DIR / "female_lancer_iso_nw_8f_walk_run_1795185455551.jpg").convert("RGB")
    fem_nw_rgba = remove_background_rgba(fem_nw_raw, tol=11.0, mask_watermark=True)
    cw = fem_nw_rgba.width / 8.0
    fem_nw_idle_base = fem_nw_rgba.crop((int(round(6 * cw)), 0, int(round(7 * cw)), fem_nw_rgba.height // 2))

    jobs = [
        ("male_lancer", "se", BRAIN_DIR / "male_lancer_iso_se_8f_walk_run_1795185356063.jpg", male_se_idle_base),
        ("male_lancer", "nw", BRAIN_DIR / "male_lancer_iso_nw_8f_walk_run_1795185457075.jpg", male_nw_idle_base),
        ("female_lancer", "se", BRAIN_DIR / "female_lancer_iso_se_8f_walk_run_1795185363799.jpg", fem_se_idle_base),
        ("female_lancer", "nw", BRAIN_DIR / "female_lancer_iso_nw_8f_walk_run_1795185455551.jpg", fem_nw_idle_base),
    ]

    for cname, d, src, idle_base in jobs:
        build_character_direction(cname, d, src, idle_base)


if __name__ == "__main__":
    main()
