#!/usr/bin/env python3
"""
Builds 8-frame Weapon-Ready Standing Idle animations (native SE & NW, 256x340 cells)
for ALL Soverai classes & weapon loadouts:
  - Male Lancer:   Sword Idle, Bow Idle
  - Female Lancer: Sword Idle, Bow Idle
  - Bastion:       Sword + Shield Idle, Two-Handed Glaive Idle
  - Archon (Gold): Turibulo (Flaming Censer Flail) + Solar Greatshield Idle

Exports into each class's dedicated repository:
  - Separate 2x8 sheets (SE top, NW bottom)
  - Separate 1x8 horizontal strips
  - Individual 256x340 transparent PNG frames
  - Individual transparent animated GIFs
  - Side-by-side Unarmed vs. Weapon-Ready Idle comparison showcase GIFs
"""

from __future__ import annotations
import math
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

BRAIN_DIR = Path(
    "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/ff7f66f4-8693-48db-8219-5ca19e947042"
)
BASE = Path("/home/antigravity/caio-bress")
LANCER_REPO = BASE / "soverai-lancer-sprites"
BASTION_REPO = BASE / "soverai-bastion-sprites"
ARCHON_REPO = BASE / "soverai-archon-sprites"

CELL_W = 256
CELL_H = 340
COLS = 8


def smooth_step(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / max(1e-5, edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def remove_background_rgba(
    img_rgb: Image.Image, tol: float = 12.0, mask_watermark: bool = True, clean_warm_glow: bool = False
) -> Image.Image:
    """Removes flat dark charcoal backdrop while preserving crisp dark outlines, thin cyan bowstrings, and flames."""
    arr = np.array(img_rgb, dtype=np.float32)
    h, w, _ = arr.shape
    border = np.concatenate([arr[0, :], arr[-1, :], arr[:, 0], arr[:, -1]])
    bg = np.median(border, axis=0)

    if mask_watermark and w >= 1200 and h >= 700:
        arr[h - 46 :, w - 46 :] = bg

    dist = np.sqrt(np.sum((arr - bg) ** 2, axis=2))
    grad_y = np.abs(np.diff(arr, axis=0, prepend=arr[:1, :])).max(axis=2)
    grad_x = np.abs(np.diff(arr, axis=1, prepend=arr[:, :1])).max(axis=2)
    grad = np.maximum(grad_x, grad_y)

    visited = np.zeros((h, w), dtype=bool)
    is_bg = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    seeds = [(y, x) for x in range(w) for y in (0, h - 1, h // 2)]
    seeds += [(y, x) for y in range(h) for x in (0, w - 1)]

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

    # Enclosed flat holes (like between legs, inside bow arc, between flail chain & body)
    flat_cand = (dist < 7.5) & (grad < 5.0) & (~is_bg)
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
                if len(comp) >= 12:
                    vals = np.array([arr[cy, cx] for cy, cx in comp])
                    if np.max(np.std(vals, axis=0)) < 2.3:
                        for cy, cx in comp:
                            is_bg[cy, cx] = True

    if clean_warm_glow:
        r_f, g_f, b_f = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        lum_f = (r_f + g_f + b_f) / 3.0
        warm_dark_glow = (
            (~is_bg)
            & (lum_f > 35.5)
            & (lum_f < 116.0)
            & (r_f < 152.0)
            & (r_f >= b_f)
            & (r_f >= g_f - 3.0)
            & (grad < 28.0)
        )
        gq: deque[tuple[int, int]] = deque()
        bg_dil = is_bg.copy()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            bg_dil |= np.roll(np.roll(is_bg, dy, axis=0), dx, axis=1)
        for sy, sx in np.argwhere(warm_dark_glow & bg_dil):
            is_bg[sy, sx] = True
            gq.append((int(sy), int(sx)))
        while gq:
            cy, cx = gq.popleft()
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and warm_dark_glow[ny, nx] and not is_bg[ny, nx]:
                    is_bg[ny, nx] = True
                    gq.append((ny, nx))

    # Drop tiny isolated noise specs (< 6px, keeping small sparks/fire embers on archon if >= 6px)
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
                if len(comp) < 6:
                    for cy, cx in comp:
                        is_bg[cy, cx] = True

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(arr, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.where(is_bg, 0, 255)
    return Image.fromarray(rgba, "RGBA")


def split_pair_halves(pair_rgba: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Splits a side-by-side SE (left) and NW (right) pair cleanly at the widest empty vertical valley."""
    arr = np.array(pair_rgba)
    h, w, _ = arr.shape
    col_sum = (arr[:, :, 3] > 0).sum(axis=0)
    mid_lo, mid_hi = int(w * 0.38), int(w * 0.62)
    split_x = mid_lo + int(np.argmin(col_sum[mid_lo:mid_hi]))
    return pair_rgba.crop((0, 0, split_x, h)), pair_rgba.crop((split_x, 0, w, h))


def place_weapon_pose_on_canvas(
    half_rgba: Image.Image, target_body_h: int, ground_y: int
) -> tuple[np.ndarray, int, int, int]:
    """
    Scales an armed standing pose to match the exact unarmed body height & foot baseline,
    while safely keeping extended weapons (swords, glaives, bows, flails) inside 256x340.
    Returns (canvas_rgba_arr, y_min_body, y_max_body, torso_cx).
    """
    arr0 = np.array(half_rgba)
    ys0, xs0 = np.where(arr0[:, :, 3] > 0)
    x0, x1 = int(xs0.min()), int(xs0.max())
    y0, y1 = int(ys0.min()), int(ys0.max())
    crop = half_rgba.crop((x0, y0, x1 + 1, y1 + 1))
    c_arr = np.array(crop)
    ch, cw, _ = c_arr.shape
    alpha = c_arr[:, :, 3] > 0

    # Find torso core column (upper-mid band 15%..55% where head/torso dominates over outstretched weapons)
    band = alpha[int(ch * 0.12) : int(ch * 0.52), :]
    col_counts = band.sum(axis=0)
    # Smooth over 31px window to locate the main body mass center X (not a thin sword/glaive tip)
    kernel = np.ones(min(61, max(9, cw // 5)))
    smoothed = np.convolve(col_counts.astype(np.float32), kernel, mode="same")
    body_cx_crop = int(np.argmax(smoothed))

    # Measure true head-to-boot height inside central torso/leg corridor around body_cx_crop
    corridor_half = max(35, int(cw * 0.24))
    cx_lo = max(0, body_cx_crop - corridor_half)
    cx_hi = min(cw, body_cx_crop + corridor_half)
    b_ys, _ = np.where(alpha[:, cx_lo:cx_hi])
    body_y0 = int(b_ys.min()) if len(b_ys) else 0
    body_y1 = int(b_ys.max()) if len(b_ys) else (ch - 1)
    body_h_src = max(1, body_y1 - body_y0 + 1)

    scale = target_body_h / float(body_h_src)
    sw = max(1, int(round(cw * scale)))
    sh = max(1, int(round(ch * scale)))

    # Ensure extended weapons (like Bastion's Glaive or Lancer's Saber) fit cleanly inside 256x340
    if sw > CELL_W - 6 or sh > CELL_H - 12:
        fit = min((CELL_W - 6) / float(cw), (CELL_H - 12) / float(ch))
        if fit < scale:
            scale = fit
            sw = max(1, int(round(cw * scale)))
            sh = max(1, int(round(ch * scale)))

    scaled = crop.resize((sw, sh), Image.Resampling.NEAREST)
    dest_x = (CELL_W // 2) - int(round(body_cx_crop * scale))
    dest_y = ground_y - int(round((body_y1 + 1) * scale))

    # Clamp gently so no weapon tip is ever clipped at canvas border
    dest_x = max(3, min(CELL_W - sw - 3, dest_x))
    dest_y = max(4, min(CELL_H - sh - 3, dest_y))

    canvas = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    canvas.paste(scaled, (dest_x, dest_y), scaled)
    src = np.array(canvas)

    y_min_body = max(0, dest_y + int(round(body_y0 * scale)))
    y_max_body = min(CELL_H - 1, dest_y + int(round(body_y1 * scale)))
    torso_cx = max(20, min(CELL_W - 20, dest_x + int(round(body_cx_crop * scale))))
    return src, y_min_body, y_max_body, torso_cx


def generate_weapon_idle_frames(
    half_rgba: Image.Image,
    target_body_h: int,
    ground_y: int,
    class_mode: str,
    facing_se: bool,
) -> list[Image.Image]:
    """
    Generates an 8-frame living Weapon-Ready Standing Idle cycle:
      - Feet locked cleanly at ground_y
      - Class-authentic breathing chest/shoulder heave
      - Subtle 1-frame lagged poise sway on held weapons (swords, bows, shields, glaives, flails)
      - Class-specific living VFX:
          * archon:  floating spiked Solar Halo + flickering sacred flames on Turibulo censer + gold/cyan glow
          * bastion: heavy hydraulic breathing + cyan visor/shield-reactor/thruster pulse + cape billow
          * lancer:  athletic breathing + subtle sash sway + turquoise canister & cyan bowstring shimmer
    """
    src, y_min, y_max, cx = place_weapon_pose_on_canvas(half_rgba, target_body_h, ground_y)
    char_h = max(1, y_max - y_min)

    frames: list[Image.Image] = []
    for i in range(COLS):
        theta = (2.0 * math.pi * i) / COLS
        b = 0.5 - 0.5 * math.cos(theta)
        theta_lag = (2.0 * math.pi * ((i - 1.15) % COLS)) / COLS
        b_lag = 0.5 - 0.5 * math.cos(theta_lag)
        sway = math.sin(theta - 0.85)
        flame_phase = 2.0 * theta  # 2 flame flicker cycles per 8-frame breathing loop

        out = np.zeros_like(src)
        for y_out in range(CELL_H):
            u = (y_out - y_min) / float(char_h)
            if u < -0.18 or u > 1.12:
                continue

            leg_ramp = 1.0 - smooth_step(0.50, 0.83, u)
            chest_peak = 1.0 - smooth_step(0.36, 0.72, u)
            chest_bell = smooth_step(0.18, 0.34, u) * (1.0 - smooth_step(0.42, 0.62, u))

            if class_mode == "archon":
                halo_band = 1.0 - smooth_step(0.12, 0.22, u)
                dy_body = 6.2 * b * chest_peak + 1.6 * b * leg_ramp
                dy_halo = 5.0 * b + 3.0 * b_lag
                dy_base = dy_body * (1.0 - halo_band) + dy_halo * halo_band
                expand_scale = 1.0 + 0.058 * b * chest_bell
                cloak_band = smooth_step(0.45, 0.58, u) * (1.0 - smooth_step(0.86, 0.96, u))
            elif class_mode == "bastion":
                dy_base = 5.8 * b * chest_peak + 1.4 * b * leg_ramp
                expand_scale = 1.0 + 0.052 * b * chest_bell
                cloak_band = smooth_step(0.50, 0.64, u) * (1.0 - smooth_step(0.86, 0.96, u))
            else:  # lancer
                dy_base = 4.8 * b * chest_peak + 1.2 * b * leg_ramp
                expand_scale = 1.0 + 0.048 * b * chest_bell
                cloak_band = smooth_step(0.52, 0.64, u) * (1.0 - smooth_step(0.84, 0.94, u))

            for x_out in range(CELL_W):
                rel_x = x_out - cx
                abs_x = abs(rel_x)

                # Held weapon / outer arm poise band (moves smoothly with lagged breathing heave)
                weapon_zone = smooth_step(24.0, 42.0, abs_x) * (1.0 - smooth_step(0.82, 0.98, u))
                if class_mode == "bastion":
                    # Heavy armored arms & weapons have deliberate hydraulic poise
                    local_dy = dy_base + 1.8 * b_lag * weapon_zone
                elif class_mode == "archon":
                    # Hanging censer flail & greatshield ride subtly with the Archon's breath
                    local_dy = dy_base + 2.2 * b_lag * weapon_zone
                else:
                    local_dy = dy_base + 1.6 * b_lag * weapon_zone

                # Keep torso expansion strictly on the central body so rigid swords/bows/shields don't stretch
                torso_exp_w = 1.0 - smooth_step(22.0, 40.0, abs_x)
                eff_expand = 1.0 + (expand_scale - 1.0) * torso_exp_w
                sx_rel = rel_x / eff_expand

                # Subtle hanging cloak/sash drift or gentle weapon tip sway
                if cloak_band > 0.0 and 14 < abs_x < 44:
                    sx_rel -= sway * 2.0 * cloak_band * (1.0 if facing_se else -1.0)
                elif weapon_zone > 0.25 and abs_x > 46:
                    # Very subtle 1px breathing tip drift on extended weapons (flail / glaive / sword / bow)
                    sx_rel -= sway * 1.1 * weapon_zone

                # For Archon's flaming Turibulo censer (outer flail side), animate rising flame flicker!
                flail_side = (rel_x < -38) if facing_se else (rel_x > 38)
                is_flame_zone = (class_mode == "archon") and flail_side and (0.30 < u < 0.78)
                if is_flame_zone:
                    # Peek whether source pixel is bright golden-white fire before warping flame tips
                    py_test = int(round(y_out + local_dy))
                    px_test = int(round(cx + sx_rel))
                    if 0 <= py_test < CELL_H and 0 <= px_test < CELL_W:
                        tp = src[py_test, px_test]
                        if tp[3] > 0 and int(tp[0]) > 210 and int(tp[1]) > 140 and (int(tp[0]) - int(tp[2]) > 55):
                            curl = math.sin(flame_phase + y_out * 0.22) * 1.6
                            rise = (0.5 + 0.5 * math.cos(flame_phase + x_out * 0.16)) * 1.8
                            sx_rel += curl
                            local_dy += rise

                sx = int(round(cx + sx_rel))
                sy = int(round(y_out + local_dy))
                if 0 <= sy < CELL_H and 0 <= sx < CELL_W:
                    px = src[sy, sx]
                    if px[3] > 0:
                        r_v, g_v, b_v, a_v = int(px[0]), int(px[1]), int(px[2]), int(px[3])
                        # Living emissive glow shimmer
                        is_cyan = (b_v > 125 and b_v - r_v > 24) or (g_v > 145 and b_v > 145 and r_v < 115)
                        if is_cyan and b > 0.04:
                            boost = int(round(28 * b))
                            r_v = min(255, r_v + boost // 2)
                            g_v = min(255, g_v + boost)
                            b_v = min(255, b_v + boost)
                        elif class_mode == "archon":
                            is_halo = (u < 0.24) and (r_v > 165 and g_v > 125 and r_v - b_v > 42)
                            is_fire = flail_side and (r_v > 210 and g_v > 140 and r_v - b_v > 55)
                            is_sun_core = (not flail_side) and (r_v > 200 and g_v > 160 and r_v - b_v > 50)
                            if is_fire:
                                pulse = 0.5 + 0.5 * math.sin(flame_phase)
                                boost = int(round(26 * pulse))
                                r_v = min(255, r_v + boost)
                                g_v = min(255, g_v + int(boost * 0.9))
                                b_v = min(255, b_v + boost // 2)
                            elif (is_halo or is_sun_core) and b > 0.04:
                                boost = int(round(24 * b))
                                r_v = min(255, r_v + boost)
                                g_v = min(255, g_v + int(boost * 0.85))
                                b_v = min(255, b_v + boost // 2)
                        out[y_out, x_out] = (r_v, g_v, b_v, a_v)

        frames.append(Image.fromarray(out, "RGBA"))
    return frames


def rgba_frames_to_transparent_gif(frames_rgba: list[Image.Image], out_path: Path, duration_ms: int) -> None:
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
        q_arr = np.array(f.convert("RGB").quantize(palette=pal_ref, dither=Image.Dither.NONE), dtype=np.uint8)
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


def draw_iso_stage(w: int, h: int, centers: list[tuple[int, int]], labels: list[str], title: str) -> Image.Image:
    bg = Image.new("RGBA", (w, h), (22, 25, 34, 255))
    draw = ImageDraw.Draw(bg)
    draw.text((22, 16), title, fill=(238, 224, 186, 255))
    tw, th = 160, 80
    for (cx, cy), label in zip(centers, labels):
        top, right, bottom, left = (cx, cy - th // 2), (cx + tw // 2, cy), (cx, cy + th // 2), (cx - tw // 2, cy)
        depth = 12
        draw.polygon([left, bottom, (bottom[0], bottom[1] + depth), (left[0], left[1] + depth)], fill=(30, 34, 46, 255), outline=(58, 66, 86, 255))
        draw.polygon([right, bottom, (bottom[0], bottom[1] + depth), (right[0], right[1] + depth)], fill=(24, 28, 38, 255), outline=(58, 66, 86, 255))
        draw.polygon([top, right, bottom, left], fill=(44, 49, 64, 255), outline=(88, 102, 130, 255))
        itw, ith = tw - 26, th - 13
        draw.polygon([(cx, cy - ith // 2), (cx + itw // 2, cy), (cx, cy + ith // 2), (cx - itw // 2, cy)], outline=(66, 76, 98, 255))
        bbox = draw.textbbox((0, 0), label)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw // 2, cy + th // 2 + 18), label, fill=(214, 218, 228, 255))
    return bg


def export_weapon_idle(
    repo: Path,
    char_dir: str,
    prefix: str,
    weapon_key: str,
    src_jpg: Path,
    target_h_se: int,
    target_h_nw: int,
    ground_y: int,
    class_mode: str,
    clean_warm_glow: bool = False,
) -> tuple[list[Image.Image], list[Image.Image]]:
    """Builds and exports 2x8 sheet, 1x8 strips, 16 PNGs, and 2 transparent GIFs for one weapon idle."""
    orig_dir = repo / "originals"
    sprites_dir = repo / "sprites"
    gifs_dir = repo / "gifs"
    orig_dir.mkdir(parents=True, exist_ok=True)
    sprites_dir.mkdir(parents=True, exist_ok=True)
    gifs_dir.mkdir(parents=True, exist_ok=True)

    Image.open(src_jpg).save(orig_dir / src_jpg.name, quality=96)
    pair_rgba = remove_background_rgba(
        Image.open(src_jpg).convert("RGB"), tol=12.0, clean_warm_glow=clean_warm_glow
    )
    se_half, nw_half = split_pair_halves(pair_rgba)

    se_frames = generate_weapon_idle_frames(se_half, target_h_se, ground_y, class_mode, facing_se=True)
    nw_frames = generate_weapon_idle_frames(nw_half, target_h_nw, ground_y, class_mode, facing_se=False)

    sheet_2x8 = Image.new("RGBA", (CELL_W * COLS, CELL_H * 2), (0, 0, 0, 0))
    for r, (d, flist) in enumerate([("se", se_frames), ("nw", nw_frames)]):
        fdir = sprites_dir / char_dir / d
        fdir.mkdir(parents=True, exist_ok=True)
        strip = Image.new("RGBA", (CELL_W * COLS, CELL_H), (0, 0, 0, 0))
        for c, fim in enumerate(flist):
            fim.save(fdir / f"idle_{weapon_key}_{c}.png")
            strip.paste(fim, (c * CELL_W, 0), fim)
            sheet_2x8.paste(fim, (c * CELL_W, r * CELL_H), fim)
        strip.save(sprites_dir / f"{prefix}_{d}_idle_{weapon_key}_strip.png")
        rgba_frames_to_transparent_gif(flist, gifs_dir / f"{prefix}_{d}_idle_{weapon_key}.gif", 140)

    sheet_name = f"{prefix}_idle_{weapon_key}_sheet.png"
    sheet_2x8.save(sprites_dir / sheet_name)
    sheet_2x8.save(BRAIN_DIR / sheet_name)
    print(f"Exported {sheet_name} ({prefix} {weapon_key} idle: SE & NW 8f)")
    return se_frames, nw_frames


def build_comparison_showcase_gif(
    out_paths: list[Path],
    title: str,
    columns: list[tuple[str, list[Image.Image], list[Image.Image]]],
) -> None:
    """
    Creates an animated comparison GIF showing all idle stances (Unarmed + Weapon-Ready)
    side-by-side, cycling cleanly between Front-Diagonal (SE) and Rear-Diagonal (NW).
    """
    n = len(columns)
    col_step = 230
    w = max(560, 120 * 2 + (n - 1) * col_step)
    h = 400
    x_start = (w - (n - 1) * col_step) // 2
    centers = [(x_start + i * col_step, 316) for i in range(n)]
    labels = [lbl for lbl, _, _ in columns]

    frames: list[Image.Image] = []
    for dir_label, dir_idx in [("FRONT-DIAG (SE)", 1), ("REAR-DIAG (NW)", 2)]:
        stage = draw_iso_stage(w, h, centers, labels, f"{title} - {dir_label}")
        for _loop in range(2):
            for c in range(COLS):
                fr = stage.copy()
                fd = ImageDraw.Draw(fr)
                for idx, (cx, cy) in enumerate(centers):
                    cell = columns[idx][dir_idx][c]
                    fd.ellipse((cx - 38, cy - 16, cx + 38, cy + 20), fill=(10, 12, 18, 165))
                    fr.alpha_composite(cell, dest=(cx - CELL_W // 2, cy - CELL_H + 22))
                frames.append(fr.convert("RGB").quantize(colors=192, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE))

    for p in out_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(p, save_all=True, append_images=frames[1:], loop=0, duration=140, optimize=True)
    print(f"Saved comparison GIF -> {out_paths[0].name}")


def load_row0(master_path: Path) -> list[Image.Image]:
    im = Image.open(master_path).convert("RGBA")
    return [im.crop((c * CELL_W, 0, (c + 1) * CELL_W, CELL_H)) for c in range(COLS)]


def main() -> None:
    # 1. MALE LANCER (Sword Idle & Bow Idle)
    ml_sw_se, ml_sw_nw = export_weapon_idle(
        LANCER_REPO, "male_lancer", "male_lancer", "sword",
        BRAIN_DIR / "male_lancer_sword_idle_pair_1795406558901.jpg",
        target_h_se=246, target_h_nw=242, ground_y=320, class_mode="lancer",
    )
    ml_bw_se, ml_bw_nw = export_weapon_idle(
        LANCER_REPO, "male_lancer", "male_lancer", "bow",
        BRAIN_DIR / "male_lancer_bow_idle_pair_1795406629657.jpg",
        target_h_se=246, target_h_nw=242, ground_y=320, class_mode="lancer",
    )
    ml_u_se = load_row0(LANCER_REPO / "sprites" / "male_lancer_isometric_se_5row_master.png")
    ml_u_nw = load_row0(LANCER_REPO / "sprites" / "male_lancer_isometric_nw_5row_master.png")
    build_comparison_showcase_gif(
        [LANCER_REPO / "gifs" / "male_lancer_idles_showcase.gif", BRAIN_DIR / "male_lancer_idles_showcase.gif"],
        "Male Lancer - Unarmed vs. Weapon-Ready Idles",
        [("UNARMED IDLE", ml_u_se, ml_u_nw), ("SWORD IDLE", ml_sw_se, ml_sw_nw), ("BOW IDLE", ml_bw_se, ml_bw_nw)],
    )

    # 2. FEMALE LANCER (Sword Idle & Bow Idle)
    fl_sw_se, fl_sw_nw = export_weapon_idle(
        LANCER_REPO, "female_lancer", "female_lancer", "sword",
        BRAIN_DIR / "female_lancer_sword_idle_pair_1795406702851.jpg",
        target_h_se=258, target_h_nw=248, ground_y=320, class_mode="lancer",
    )
    fl_bw_se, fl_bw_nw = export_weapon_idle(
        LANCER_REPO, "female_lancer", "female_lancer", "bow",
        BRAIN_DIR / "female_lancer_bow_idle_pair_1795406700624.jpg",
        target_h_se=258, target_h_nw=248, ground_y=320, class_mode="lancer",
    )
    fl_u_se = load_row0(LANCER_REPO / "sprites" / "female_lancer_isometric_se_5row_master.png")
    fl_u_nw = load_row0(LANCER_REPO / "sprites" / "female_lancer_isometric_nw_5row_master.png")
    build_comparison_showcase_gif(
        [LANCER_REPO / "gifs" / "female_lancer_idles_showcase.gif", BRAIN_DIR / "female_lancer_idles_showcase.gif"],
        "Female Lancer - Unarmed vs. Weapon-Ready Idles",
        [("UNARMED IDLE", fl_u_se, fl_u_nw), ("SWORD IDLE", fl_sw_se, fl_sw_nw), ("BOW IDLE", fl_bw_se, fl_bw_nw)],
    )

    # 3. BASTION (Sword + Shield Idle & Two-Handed Glaive Idle)
    ba_ss_se, ba_ss_nw = export_weapon_idle(
        BASTION_REPO, "bastion", "bastion", "sword_shield",
        BRAIN_DIR / "bastion_sword_shield_idle_pair_1795406491389.jpg",
        target_h_se=248, target_h_nw=248, ground_y=318, class_mode="bastion",
    )
    ba_gl_se, ba_gl_nw = export_weapon_idle(
        BASTION_REPO, "bastion", "bastion", "glaive",
        BRAIN_DIR / "bastion_glaive_idle_pair_1795406490775.jpg",
        target_h_se=248, target_h_nw=248, ground_y=318, class_mode="bastion",
    )
    ba_u_se = load_row0(BASTION_REPO / "sprites" / "bastion_isometric_se_5row_master.png")
    ba_u_nw = load_row0(BASTION_REPO / "sprites" / "bastion_isometric_nw_5row_master.png")
    build_comparison_showcase_gif(
        [BASTION_REPO / "gifs" / "bastion_idles_showcase.gif", BRAIN_DIR / "bastion_idles_showcase.gif"],
        "Bastion (Siege Armor) - Unarmed vs. Weapon-Ready Idles",
        [("UNARMED IDLE", ba_u_se, ba_u_nw), ("SWORD + SHIELD IDLE", ba_ss_se, ba_ss_nw), ("GLAIVE IDLE", ba_gl_se, ba_gl_nw)],
    )

    # 4. ARCHON - FIRST LIGHT (Turibulo + Solar Greatshield Idle)
    ar_ts_se, ar_ts_nw = export_weapon_idle(
        ARCHON_REPO, "archon", "archon", "turibulo_shield",
        BRAIN_DIR / "archon_turibulo_shield_idle_pair_1795406558400.jpg",
        target_h_se=253, target_h_nw=253, ground_y=318, class_mode="archon",
        clean_warm_glow=True,
    )
    ar_u_se = load_row0(ARCHON_REPO / "sprites" / "archon_isometric_se_5row_master.png")
    ar_u_nw = load_row0(ARCHON_REPO / "sprites" / "archon_isometric_nw_5row_master.png")
    build_comparison_showcase_gif(
        [ARCHON_REPO / "gifs" / "archon_idles_showcase.gif", BRAIN_DIR / "archon_idles_showcase.gif"],
        "Archon (First Light) - Unarmed vs. Turibulo + Shield Idle",
        [("UNARMED CELESTIAL IDLE", ar_u_se, ar_u_nw), ("TURIBULO + SHIELD IDLE", ar_ts_se, ar_ts_nw)],
    )

    print("ALL 7 WEAPON-READY STANDING IDLE SETS BUILT SUCCESSFULLY!")


if __name__ == "__main__":
    main()
