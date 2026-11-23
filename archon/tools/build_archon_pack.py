#!/usr/bin/env python3
"""
Builds the complete 5-row x 8-column Isometric Tactical RPG Sprite Pack & Animated
GIFs for the ARCHON (The Old Faith — Path of the First Light: Ivory, Gold & Navy)
across native SE and NW views:
  Row 0: 8-frame Breathing + Floating Solar Halo Idle (Unarmed)
  Row 1: 8-frame Regal Walk Cycle (Unarmed)
  Row 2: 8-frame Celestial Run / Sprint Cycle (Unarmed)
  Row 3: 8-frame Turíbulo (Censer Flail) + Solar Greatshield Attack
  Row 4: 8-frame First Light Miracle Cast (Solar Judgement)
"""

from __future__ import annotations
import heapq
import math
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent
SPRITES_DIR = REPO / "sprites"
GIFS_DIR = REPO / "gifs"
ORIG_DIR = REPO / "originals"
BRAIN_DIR = Path(
    "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/ff7f66f4-8693-48db-8219-5ca19e947042"
)

CELL_W = 256
CELL_H = 340
COLS = 8
ROWS = 5
GROUND_Y = 318
TARGET_H = 252


def smooth_step(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / max(1e-5, edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def remove_background_rgba(
    img_rgb: Image.Image,
    tol: float = 12.0,
    mask_watermark: bool = True,
    clean_warm_glow: bool = False,
) -> Image.Image:
    """Removes flat dark charcoal background (and optional outer dark-amber glow halos) while preserving dark outlines and bright fire."""
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

    flat_cand = (dist < 7.0) & (grad < 4.5) & (~is_bg)
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

    if clean_warm_glow:
        # Dissolve outer dark brownish-amber bloom around glowing golden sunbursts/orbs on dark charcoal backdrop.
        # Strictly flood-filled from existing background so it stops cleanly at crisp dark outlines (lum <= 35)
        # and at bright golden-yellow pixel-art fire/rays (lum >= 122 or R >= 158).
        r_f = arr[:, :, 0]
        g_f = arr[:, :, 1]
        b_f = arr[:, :, 2]
        lum_f = (r_f + g_f + b_f) / 3.0
        warm_dark_glow = (
            (~is_bg)
            & (lum_f > 35.5)
            & (lum_f < 126.0)
            & (r_f < 162.0)
            & (r_f >= b_f - 1.0)
            & (r_f >= g_f - 3.0)
            & (grad < 30.0)
        )
        gq: deque[tuple[int, int]] = deque()
        # Seed from warm_dark_glow pixels directly bordering is_bg
        bg_dil = is_bg.copy()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            bg_dil |= np.roll(np.roll(is_bg, dy, axis=0), dx, axis=1)
        g_seeds = np.argwhere(warm_dark_glow & bg_dil)
        for sy, sx in g_seeds:
            is_bg[sy, sx] = True
            gq.append((int(sy), int(sx)))
        while gq:
            cy, cx = gq.popleft()
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and warm_dark_glow[ny, nx] and not is_bg[ny, nx]:
                    is_bg[ny, nx] = True
                    gq.append((ny, nx))
        # One-pass fringe trim for any 1-2px residual muddy brown halo touching background
        for _ in range(2):
            bg_n = is_bg.copy()
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                bg_n |= np.roll(np.roll(is_bg, dy, axis=0), dx, axis=1)
            fringe = (~is_bg) & bg_n & (lum_f > 36.0) & (lum_f < 118.0) & (r_f < 155.0) & (r_f >= b_f + 3.0)
            is_bg |= fringe

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
                if len(comp) < 8:
                    for cy, cx in comp:
                        is_bg[cy, cx] = True

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(arr, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.where(is_bg, 0, 255)
    return Image.fromarray(rgba, "RGBA")


def strip_floor_diamonds(rgba: np.ndarray, num_rows: int = 2, remove_thin_lines: bool = False) -> np.ndarray:
    """Removes faint dark-grey isometric floor guide diamonds while preserving golden solar rune circles."""
    out = rgba.copy()
    h, w, _ = out.shape
    rh = h // num_rows
    for r in range(num_rows):
        y_start = r * rh + rh - 78
        y_end = (r + 1) * rh
        sub = out[y_start:y_end, :]
        rgb = sub[:, :, :3].astype(np.int16)
        alpha = sub[:, :, 3] > 0
        sat = rgb.max(axis=2) - rgb.min(axis=2)
        lum = rgb.mean(axis=2)
        gy = np.abs(np.diff(rgb, axis=0, prepend=rgb[:1, :])).max(axis=2)
        gx = np.abs(np.diff(rgb, axis=1, prepend=rgb[:, :1])).max(axis=2)
        grad = np.maximum(gx, gy)
        # Strict low-saturation dark grey only (leaves golden solar rune rings 100% untouched!)
        is_flat = alpha & (sat <= 12) & (lum >= 38) & (lum <= 72) & (grad <= 14)
        sh, sw = is_flat.shape
        vis = np.zeros((sh, sw), dtype=bool)
        clear_mask = np.zeros((sh, sw), dtype=bool)
        for y in range(sh):
            for x in range(sw):
                if is_flat[y, x] and not vis[y, x]:
                    q = deque([(y, x)])
                    vis[y, x] = True
                    comp = []
                    while q:
                        cy, cx = q.popleft()
                        comp.append((cy, cx))
                        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < sh and 0 <= nx < sw and is_flat[ny, nx] and not vis[ny, nx]:
                                vis[ny, nx] = True
                                q.append((ny, nx))
                    if len(comp) >= 16:
                        for cy, cx in comp:
                            clear_mask[cy, cx] = True
        for _ in range(3):
            ext = clear_mask.copy()
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                shifted = np.roll(np.roll(clear_mask, dy, axis=0), dx, axis=1)
                ext |= shifted & alpha & (sat <= 16) & (lum >= 38) & (lum <= 94)
            clear_mask = ext

        if remove_thin_lines:
            # For Walk/Run sheets (no golden rune rings), erase remaining thin 1-2px grey diamond outline strokes
            thin_band = np.zeros((sh, sw), dtype=bool)
            thin_band[max(0, sh - 54) :, :] = True
            grey_cand = alpha & (~clear_mask) & thin_band & (sat <= 19) & (lum >= 38) & (lum <= 108)
            # Identify thin pixels (3x3 neighborhood has <= 6 opaque pixels, i.e., thin guide stroke not solid boot)
            opaq_cnt = np.zeros((sh, sw), dtype=np.int16)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    opaq_cnt += np.roll(np.roll(alpha.astype(np.int16), dy, axis=0), dx, axis=1)
            thin_grey = grey_cand & (opaq_cnt <= 6)
            # Also remove small isolated low-sat grey fragments floating under feet
            t_vis = np.zeros((sh, sw), dtype=bool)
            for y in range(max(0, sh - 54), sh):
                for x in range(sw):
                    if grey_cand[y, x] and not t_vis[y, x]:
                        q = deque([(y, x)])
                        t_vis[y, x] = True
                        comp = []
                        while q:
                            cy, cx = q.popleft()
                            comp.append((cy, cx))
                            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                ny, nx = cy + dy, cx + dx
                                if 0 <= ny < sh and 0 <= nx < sw and grey_cand[ny, nx] and not t_vis[ny, nx]:
                                    t_vis[ny, nx] = True
                                    q.append((ny, nx))
                        thin_ratio = sum(1 for cy, cx in comp if thin_grey[cy, cx]) / max(1, len(comp))
                        if thin_ratio >= 0.55:
                            for cy, cx in comp:
                                clear_mask[cy, cx] = True

        sub[clear_mask] = 0
        out[y_start:y_end, :] = sub
    return out


def segment_row_watershed(
    row_rgba: np.ndarray,
    cols: int = COLS,
    has_gold_vfx: bool = False,
    attack_left: bool = False,
    custom_seed_boxes: list[tuple[int, int]] | None = None,
) -> list[np.ndarray]:
    """Column-Anchored 2D Multi-Source Watershed Ownership (float64 Dijkstra) for golden-fire Archon sheets."""
    rh, rw, _ = row_rgba.shape
    fg = row_rgba[:, :, 3] > 0
    r_c = row_rgba[:, :, 0].astype(np.int16)
    g_c = row_rgba[:, :, 1].astype(np.int16)
    b_c = row_rgba[:, :, 2].astype(np.int16)

    if has_gold_vfx:
        # Radiant golden-white fire / solar burst VFX (very bright warm yellow/white)
        is_vfx = fg & (r_c > 215) & (g_c > 170) & ((r_c - b_c > 50) | ((r_c > 240) & (g_c > 230) & (b_c > 165)))
        vfx_dilated = is_vfx.copy()
        for _ in range(2):
            ext = vfx_dilated.copy()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy or dx:
                        ext |= np.roll(np.roll(vfx_dilated, dy, axis=0), dx, axis=1)
            vfx_dilated = ext
    else:
        is_vfx = np.zeros((rh, rw), dtype=bool)
        vfx_dilated = is_vfx

    col_w = rw / float(cols)
    owner = np.full((rh, rw), -1, dtype=np.int16)
    dist_map = np.full((rh, rw), 1e9, dtype=np.float64)
    pq: list[tuple[float, int, int, int]] = []
    body_cxs: list[float] = []

    y_lo, y_hi = int(rh * 0.25), int(rh * 0.90)
    for slot in range(cols):
        if custom_seed_boxes is not None:
            sx0, sx1 = custom_seed_boxes[slot]
            sx0, sx1 = max(0, sx0), min(rw, sx1)
            cx0, cx1 = sx0, sx1
        else:
            cx0 = int(round(slot * col_w))
            cx1 = int(round((slot + 1) * col_w))
            margin = int(round((cx1 - cx0) * 0.14))
            sx0 = max(0, cx0 + margin)
            sx1 = min(rw, cx1 - margin)

        core = fg[y_lo:y_hi, sx0:sx1] & (~vfx_dilated[y_lo:y_hi, sx0:sx1])
        ch_b, cw_b = core.shape
        vis = np.zeros((ch_b, cw_b), dtype=bool)
        best_pts: list[tuple[int, int]] = []
        for yy in range(ch_b):
            for xx in range(cw_b):
                if core[yy, xx] and not vis[yy, xx]:
                    q = deque([(yy, xx)])
                    vis[yy, xx] = True
                    pts = []
                    while q:
                        cy, cx = q.popleft()
                        pts.append((cy + y_lo, cx + sx0))
                        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < ch_b and 0 <= nx < cw_b and core[ny, nx] and not vis[ny, nx]:
                                vis[ny, nx] = True
                                q.append((ny, nx))
                    if len(pts) > len(best_pts):
                        best_pts = pts

        if best_pts:
            body_cxs.append(float(np.mean([p[1] for p in best_pts])))
            for py, px in best_pts:
                owner[py, px] = slot
                dist_map[py, px] = 0.0
            for py, px in best_pts:
                for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ny, nx = py + dy, px + dx
                    if 0 <= ny < rh and 0 <= nx < rw and fg[ny, nx] and owner[ny, nx] == -1:
                        heapq.heappush(pq, (0.0, py, px, slot))
                        break
        else:
            body_cxs.append((cx0 + cx1) * 0.5)

    fwd_sign = -1 if attack_left else 1
    while pq:
        d, y, x, slot = heapq.heappop(pq)
        if d > dist_map[y, x]:
            continue
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < rh and 0 <= nx < rw and fg[ny, nx] and dist_map[ny, nx] > 0.0:
                rel_fwd = (nx - body_cxs[slot]) * fwd_sign
                if abs(rel_fwd) > 175:
                    continue
                step = 1.414 if (dy != 0 and dx != 0) else 1.0
                if vfx_dilated[ny, nx]:
                    # Let golden sunbursts expand symmetrically above head (y < rh*0.40),
                    # and bias forward along weapon arcs in the strike zone
                    if ny > rh * 0.35 and rel_fwd < -35:
                        step *= 2.4
                    elif dx * fwd_sign > 0:
                        step *= 0.65
                nd = d + step
                if nd < dist_map[ny, nx]:
                    dist_map[ny, nx] = nd
                    owner[ny, nx] = slot
                    heapq.heappush(pq, (nd, ny, nx, slot))

    unowned = fg & (owner == -1)
    u_vis = np.zeros((rh, rw), dtype=bool)
    for y in range(rh):
        for x in range(rw):
            if unowned[y, x] and not u_vis[y, x]:
                q = deque([(y, x)])
                u_vis[y, x] = True
                pts = []
                while q:
                    cy, cx = q.popleft()
                    pts.append((cy, cx))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < rh and 0 <= nx < rw and unowned[ny, nx] and not u_vis[ny, nx]:
                                u_vis[ny, nx] = True
                                q.append((ny, nx))
                if len(pts) >= 5:
                    ccx = float(np.mean([p[1] for p in pts]))
                    best_slot = min(range(cols), key=lambda s: abs(ccx - body_cxs[s]))
                    if abs(ccx - body_cxs[best_slot]) < 165:
                        for cy, cx in pts:
                            owner[cy, cx] = best_slot

    cells: list[np.ndarray] = []
    for slot in range(cols):
        ys, xs = np.where(owner == slot)
        if len(xs) == 0:
            cells.append(np.zeros((rh, 172, 4), dtype=np.uint8))
            continue
        x0 = max(0, int(xs.min()) - 2)
        x1 = min(rw, int(xs.max()) + 3)
        sub = np.zeros((rh, x1 - x0, 4), dtype=np.uint8)
        mask_sub = owner[:, x0:x1] == slot
        sub[mask_sub] = row_rgba[:, x0:x1][mask_sub]
        cells.append(sub)
    return cells


def generate_celestial_idle_frames(
    base_rgba: Image.Image, target_height: int, facing_se: bool = True
) -> list[Image.Image]:
    """
    8-frame Archon Breathing + Levitating Solar Halo Idle:
    feet stay locked to GROUND_Y while torso expands & rises smoothly on inhale,
    the spiked gold Solar Halo floats subtly with 1-frame lag, tattered ivory/navy
    cloak ribbons sway gently, and cyan optics + back thruster + gold halo glow!
    """
    arr0 = np.array(base_rgba)
    ys0, xs0 = np.where(arr0[:, :, 3] > 0)
    crop = base_rgba.crop((int(xs0.min()), int(ys0.min()), int(xs0.max()) + 1, int(ys0.max()) + 1))

    scale = target_height / float(crop.height)
    new_w = max(1, int(round(crop.width * scale)))
    new_h = max(1, int(round(crop.height * scale)))
    scaled = crop.resize((new_w, new_h), Image.Resampling.NEAREST)

    base_canvas = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    s_arr = np.array(scaled)
    s_alpha = s_arr[:, :, 3] > 0
    t_xs = np.where(s_alpha[: int(new_h * 0.55), :])[1]
    cx_crop = int(round(np.median(t_xs))) if len(t_xs) > 0 else new_w // 2
    px0 = (CELL_W // 2) - cx_crop
    py0 = GROUND_Y - new_h
    base_canvas.paste(scaled, (px0, py0), scaled)

    src = np.array(base_canvas)
    ys, xs = np.where(src[:, :, 3] > 0)
    y_min, y_max = int(ys.min()), int(ys.max())
    char_h = max(1, y_max - y_min)
    cx = CELL_W // 2

    frames: list[Image.Image] = []
    for i in range(COLS):
        theta = (2.0 * math.pi * i) / COLS
        b = 0.5 - 0.5 * math.cos(theta)
        theta_lag = (2.0 * math.pi * ((i - 1.1) % COLS)) / COLS
        b_lag = 0.5 - 0.5 * math.cos(theta_lag)
        ribbon_sway = math.sin(theta - 0.8)

        out = np.zeros_like(src)
        for y_out in range(CELL_H):
            u = (y_out - y_min) / float(char_h)
            if u < -0.15 or u > 1.05:
                continue

            # Feet locked (u >= 0.80); ribcage rises -7px; Solar Halo (u < 0.14) levitates extra smoothly with lag!
            leg_ramp = 1.0 - smooth_step(0.48, 0.82, u)
            chest_peak = 1.0 - smooth_step(0.36, 0.72, u)
            halo_band = 1.0 - smooth_step(0.12, 0.22, u)

            dy_body = 6.5 * b * chest_peak + 1.8 * b * leg_ramp
            dy_halo = 5.2 * b + 3.2 * b_lag
            dy = dy_body * (1.0 - halo_band) + dy_halo * halo_band

            chest_bell = smooth_step(0.20, 0.34, u) * (1.0 - smooth_step(0.42, 0.60, u))
            expand_scale = 1.0 + 0.068 * b * chest_bell
            cloak_band = smooth_step(0.44, 0.56, u) * (1.0 - smooth_step(0.86, 0.96, u))

            for x_out in range(CELL_W):
                rel_x = x_out - cx
                pauldron_mask = smooth_step(18.0, 30.0, abs(rel_x)) * smooth_step(0.20, 0.32, u) * (1.0 - smooth_step(0.50, 0.62, u))
                local_dy = dy + 1.8 * b_lag * pauldron_mask

                sx_rel = rel_x / expand_scale
                if cloak_band > 0.0 and abs(rel_x) > 16:
                    sx_rel -= ribbon_sway * 3.0 * cloak_band * (1.0 if facing_se else -1.0)

                sx = int(round(cx + sx_rel))
                sy = int(round(y_out + local_dy))
                if 0 <= sy < CELL_H and 0 <= sx < CELL_W:
                    px = src[sy, sx]
                    if px[3] > 0:
                        r_v, g_v, b_v, a_v = int(px[0]), int(px[1]), int(px[2]), int(px[3])
                        # Subtle holy shimmer on cyan optics/thruster and golden halo spikes on inhale
                        is_cyan = (b_v > 125 and b_v - r_v > 25) or (g_v > 140 and b_v > 145 and r_v < 110)
                        is_halo_gold = (u < 0.24) and (r_v > 170 and g_v > 130 and r_v - b_v > 45)
                        if is_cyan and b > 0.05:
                            boost = int(round(30 * b))
                            r_v = min(255, r_v + boost // 2)
                            g_v = min(255, g_v + boost)
                            b_v = min(255, b_v + boost)
                        elif is_halo_gold and b > 0.05:
                            boost = int(round(24 * b))
                            r_v = min(255, r_v + boost)
                            g_v = min(255, g_v + int(boost * 0.85))
                            b_v = min(255, b_v + boost // 2)
                        out[y_out, x_out] = (r_v, g_v, b_v, a_v)

        frames.append(Image.fromarray(out, "RGBA"))
    return frames


def anchor_row_frames(
    cells: list[np.ndarray],
    target_stand_h: int = TARGET_H,
    anchor_indices: tuple[int, ...] = (0, 1, 4, 5),
    flip_x: bool = False,
    per_frame_normalize_idx: int | None = None,
) -> list[Image.Image]:
    """Anchors cells consistently to GROUND_Y and torso center X = CELL_W // 2."""
    stand_hs = []
    y1s = []
    for idx in anchor_indices:
        if idx < len(cells):
            ys, _ = np.where(cells[idx][:, :, 3] > 0)
            if len(ys):
                stand_hs.append(int(ys.max() - ys.min()))
                y1s.append(int(ys.max()))
    med_h = float(np.median(stand_hs)) if stand_hs else 250.0
    base_scale = max(0.84, min(1.18, target_stand_h / med_h))
    src_ground = float(np.median(y1s)) if y1s else 345.0

    frames: list[Image.Image] = []
    for c_idx, cell in enumerate(cells):
        ys, xs = np.where(cell[:, :, 3] > 0)
        if len(ys) == 0:
            frames.append(Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0)))
            continue

        # Normalize an individual taller frame (like Frame 0 of SE Turíbulo) to exact TARGET_H
        scale = base_scale
        use_ground = src_ground
        if per_frame_normalize_idx is not None and c_idx == per_frame_normalize_idx:
            fh_this = float(ys.max() - ys.min())
            if fh_this > med_h * 1.07:
                scale = target_stand_h / fh_this
                use_ground = float(ys.max())

        r_c = cell[:, :, 0].astype(np.int16)
        g_c = cell[:, :, 1].astype(np.int16)
        b_c = cell[:, :, 2].astype(np.int16)
        is_vfx = (r_c > 225) & (g_c > 185) & (r_c - b_c > 55)
        body_mask = (cell[:, :, 3] > 0) & (~is_vfx)

        y_lo = max(0, int(use_ground - 205))
        y_hi = min(cell.shape[0], int(use_ground - 40))
        _, b_xs = np.where(body_mask[y_lo:y_hi, :])
        body_cx = float(np.median(b_xs)) if len(b_xs) > 30 else float(np.median(xs))

        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        crop = Image.fromarray(cell[y0 : y1 + 1, x0 : x1 + 1], "RGBA")
        if flip_x:
            crop = crop.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            rel_cx = (x1 - x0) - (body_cx - x0)
        else:
            rel_cx = body_cx - x0

        sw = max(1, int(round(crop.width * scale)))
        sh = max(1, int(round(crop.height * scale)))
        if sh > CELL_H - 6 or sw > CELL_W - 6:
            fit_scale = min(scale, (CELL_H - 6) / float(crop.height), (CELL_W - 6) / float(crop.width))
            sw = max(1, int(round(crop.width * fit_scale)))
            sh = max(1, int(round(crop.height * fit_scale)))
            eff_scale = fit_scale
        else:
            eff_scale = scale
        scaled = crop.resize((sw, sh), Image.Resampling.NEAREST)

        dest_x = (CELL_W // 2) - int(round(rel_cx * eff_scale))
        dest_y = GROUND_Y + int(round((y0 - use_ground) * eff_scale))
        dest_y = max(2, min(CELL_H - sh - 2, dest_y))
        dest_x = max(2, min(CELL_W - sw - 2, dest_x))

        frame = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
        frame.paste(scaled, (dest_x, dest_y), scaled)
        frames.append(frame)

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


def draw_iso_stage(w: int, h: int, centers: list[tuple[int, int]], labels: list[str]) -> Image.Image:
    bg = Image.new("RGBA", (w, h), (22, 25, 34, 255))
    draw = ImageDraw.Draw(bg)
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
        draw.text((cx - lw // 2, cy + th // 2 + 18), label, fill=(218, 206, 178, 255))
    return bg


def build_showcase_gifs(se_master: Image.Image, nw_master: Image.Image) -> None:
    GIFS_DIR.mkdir(parents=True, exist_ok=True)
    for d, sheet in [("se", se_master), ("nw", nw_master)]:
        w, h = 720, 395
        centers = [(130, 314), (360, 314), (590, 314)]
        labels = [f"IDLE ({d.upper()})", f"WALK ({d.upper()})", f"RUN ({d.upper()})"]
        stage = draw_iso_stage(w, h, centers, labels)
        ImageDraw.Draw(stage).text((22, 16), f"Archon (First Light) - Movement Cycles ({d.upper()})", fill=(244, 224, 172, 255))
        frames = []
        for c in range(COLS):
            fr = stage.copy()
            fd = ImageDraw.Draw(fr)
            for r, (cx, cy) in enumerate(centers):
                cell = sheet.crop((c * CELL_W, r * CELL_H, (c + 1) * CELL_W, (r + 1) * CELL_H))
                is_air = (r == 2 and c in (3, 7))
                rx, ry = (28, 13) if is_air else (38, 18)
                fd.ellipse((cx - rx, cy - ry + 2, cx + rx, cy + ry + 2), fill=(10, 12, 18, 120 if is_air else 165))
                fr.alpha_composite(cell, dest=(cx - CELL_W // 2, cy - CELL_H + 22))
            frames.append(fr.convert("RGB").quantize(colors=192, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE))
        out_p = GIFS_DIR / f"archon_{d}_movement_showcase.gif"
        frames[0].save(out_p, save_all=True, append_images=frames[1:], loop=0, duration=100, optimize=True)
        (BRAIN_DIR / out_p.name).write_bytes(out_p.read_bytes())

    for d, sheet in [("se", se_master), ("nw", nw_master)]:
        w, h = 600, 395
        centers = [(160, 314), (440, 314)]
        labels = [f"TURIBULO + SHIELD ({d.upper()})", f"MIRACLE CAST ({d.upper()})"]
        stage = draw_iso_stage(w, h, centers, labels)
        ImageDraw.Draw(stage).text((22, 16), f"Archon (First Light) - Combat & Miracles ({d.upper()})", fill=(244, 224, 172, 255))
        frames = []
        for c in range(COLS):
            fr = stage.copy()
            fd = ImageDraw.Draw(fr)
            for row_idx, (cx, cy) in zip([3, 4], centers):
                cell = sheet.crop((c * CELL_W, row_idx * CELL_H, (c + 1) * CELL_W, (row_idx + 1) * CELL_H))
                fd.ellipse((cx - 38, cy - 16, cx + 38, cy + 20), fill=(10, 12, 18, 165))
                fr.alpha_composite(cell, dest=(cx - CELL_W // 2, cy - CELL_H + 22))
            frames.append(fr.convert("RGB").quantize(colors=192, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE))
        out_p = GIFS_DIR / f"archon_{d}_combat_showcase.gif"
        frames[0].save(out_p, save_all=True, append_images=frames[1:], loop=0, duration=100, optimize=True)
        (BRAIN_DIR / out_p.name).write_bytes(out_p.read_bytes())

    w, h = 560, 395
    centers = [(155, 314), (405, 314)]
    base_stage = draw_iso_stage(w, h, centers, ["FRONT-DIAG (SE)", "REAR-DIAG (NW)"])
    seq = [
        (0, "CELESTIAL IDLE (8F)", 2, 135),
        (1, "REGAL WALK (8F)", 2, 100),
        (2, "CELESTIAL RUN (8F)", 2, 85),
        (3, "TURIBULO + SHIELD (8F)", 2, 96),
        (4, "FIRST LIGHT MIRACLE (8F)", 2, 110),
    ]
    frames, durs = [], []
    for row_idx, badge, loops, dur in seq:
        for _ in range(loops):
            for c in range(COLS):
                fr = base_stage.copy()
                fd = ImageDraw.Draw(fr)
                fd.rounded_rectangle((18, 14, 285, 38), radius=6, fill=(32, 36, 48, 255), outline=(240, 192, 72, 255))
                fd.text((28, 21), f"{badge}  [{c+1}/8]", fill=(250, 238, 200, 255))
                for sheet, (cx, cy) in zip([se_master, nw_master], centers):
                    cell = sheet.crop((c * CELL_W, row_idx * CELL_H, (c + 1) * CELL_W, (row_idx + 1) * CELL_H))
                    fd.ellipse((cx - 38, cy - 16, cx + 38, cy + 20), fill=(10, 12, 18, 165))
                    fr.alpha_composite(cell, dest=(cx - CELL_W // 2, cy - CELL_H + 22))
                frames.append(fr.convert("RGB").quantize(colors=192, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE))
                durs.append(dur)
    all_p = GIFS_DIR / "archon_all_animations_showcase.gif"
    frames[0].save(all_p, save_all=True, append_images=frames[1:], loop=0, duration=durs, optimize=True)
    (BRAIN_DIR / all_p.name).write_bytes(all_p.read_bytes())
    print("Exported all Archon showcase GIFs!")


def main() -> None:
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    GIFS_DIR.mkdir(parents=True, exist_ok=True)
    ORIG_DIR.mkdir(parents=True, exist_ok=True)

    pair_src = BRAIN_DIR / "archon_v2_isometric_unarmed_pair_1795226646019.jpg"
    showcase_src = BRAIN_DIR / "archon_v2_isometric_combat_showcase_1795226658270.jpg"
    se_wr_src = BRAIN_DIR / "archon_iso_se_8f_walk_run_1795228679291.jpg"
    nw_wr_src = BRAIN_DIR / "archon_iso_nw_8f_walk_run_1795228678558.jpg"
    se_cb_src = BRAIN_DIR / "archon_iso_se_8f_combat_1795228851708.jpg"
    nw_cb_src = BRAIN_DIR / "archon_iso_nw_8f_combat_1795228852878.jpg"

    for p in [pair_src, showcase_src, se_wr_src, nw_wr_src, se_cb_src, nw_cb_src]:
        Image.open(p).save(ORIG_DIR / p.name, quality=96)

    # 1. Walk & Run (SE & NW) - aggressive floor diamond stroke cleanup (no golden rune rings on walk/run)
    se_wr_rgba = strip_floor_diamonds(
        np.array(remove_background_rgba(Image.open(se_wr_src).convert("RGB"), tol=12.5)), 2, remove_thin_lines=True
    )
    nw_wr_rgba = strip_floor_diamonds(
        np.array(remove_background_rgba(Image.open(nw_wr_src).convert("RGB"), tol=12.5)), 2, remove_thin_lines=True
    )
    rh = se_wr_rgba.shape[0] // 2

    se_walk_frames = anchor_row_frames(segment_row_watershed(se_wr_rgba[0:rh, :], COLS, False), TARGET_H)
    se_run_frames = anchor_row_frames(segment_row_watershed(se_wr_rgba[rh : rh * 2, :], COLS, False), TARGET_H)
    nw_walk_frames = anchor_row_frames(segment_row_watershed(nw_wr_rgba[0:rh, :], COLS, False), TARGET_H)
    nw_run_frames = anchor_row_frames(segment_row_watershed(nw_wr_rgba[rh : rh * 2, :], COLS, False), TARGET_H)
    print("Archon Walk & Run sliced & normalized!")

    # 2. Celestial Breathing + Floating Halo Idle (SE & NW)
    pair_rgba = remove_background_rgba(Image.open(pair_src).convert("RGB"), tol=12.0)
    mid_x = pair_rgba.width // 2
    se_idle_frames = generate_celestial_idle_frames(pair_rgba.crop((0, 0, mid_x, pair_rgba.height)), TARGET_H, True)
    nw_idle_frames = generate_celestial_idle_frames(pair_rgba.crop((mid_x, 0, pair_rgba.width, pair_rgba.height)), TARGET_H, False)
    print("Archon 8-frame Celestial Breathing Idle built!")

    # 3. SE Combat (Row 0: 7 non-uniform Turíbulo + Shield figures -> padded cleanly to 8f; Row 1: 8-frame Miracle Cast)
    se_cb_rgba = strip_floor_diamonds(
        np.array(remove_background_rgba(Image.open(se_cb_src).convert("RGB"), tol=12.5, clean_warm_glow=True)), 2
    )
    se_tur_boxes = [
        (100, 260),
        (365, 475),
        (560, 655),
        (750, 845),
        (925, 1015),
        (1085, 1185),
        (1235, 1345),
    ]
    se_tur_cells_7 = segment_row_watershed(
        se_cb_rgba[0:rh, :], cols=7, has_gold_vfx=True, attack_left=False, custom_seed_boxes=se_tur_boxes
    )
    se_tur_7 = anchor_row_frames(se_tur_cells_7, TARGET_H, anchor_indices=(1, 5, 6), per_frame_normalize_idx=0)
    # 8th frame smoothly returns to ready guard (Frame 6 settled back toward Frame 0)
    se_tur_frames = [se_tur_7[0], se_tur_7[1], se_tur_7[2], se_tur_7[3], se_tur_7[4], se_tur_7[5], se_tur_7[6], se_tur_7[6]]

    se_mir_frames = anchor_row_frames(
        segment_row_watershed(se_cb_rgba[rh : rh * 2, :], cols=8, has_gold_vfx=True, attack_left=False),
        TARGET_H,
        anchor_indices=(0, 1, 6, 7),
    )
    print("Archon SE Turíbulo & Miracle Cast sliced!")

    # 4. NW Combat (Row 0: 8f Turíbulo + Shield facing NW; Row 1: 8f Miracle Cast flipped so golden wave fires NW!)
    nw_cb_rgba = strip_floor_diamonds(
        np.array(remove_background_rgba(Image.open(nw_cb_src).convert("RGB"), tol=12.5, clean_warm_glow=True)), 2
    )
    nw_tur_frames = anchor_row_frames(
        segment_row_watershed(nw_cb_rgba[0:rh, :], cols=8, has_gold_vfx=True, attack_left=True),
        TARGET_H,
        anchor_indices=(0, 1, 6, 7),
    )
    nw_mir_frames = anchor_row_frames(
        segment_row_watershed(nw_cb_rgba[rh : rh * 2, :], cols=8, has_gold_vfx=True, attack_left=False),
        TARGET_H,
        anchor_indices=(0, 1, 6, 7),
        flip_x=True,
    )
    print("Archon NW Turíbulo & Miracle Cast sliced!")

    # 5. Export Master 5x8 sheets, Separate 2x8 sheets, 1x8 strips, 80 PNGs, and 15 animated GIFs
    anim_names = ["idle", "walk", "run", "turibulo_shield", "miracle_cast"]
    durations = {"idle": 140, "walk": 100, "run": 85, "turibulo_shield": 95, "miracle_cast": 110}
    se_rows = [se_idle_frames, se_walk_frames, se_run_frames, se_tur_frames, se_mir_frames]
    nw_rows = [nw_idle_frames, nw_walk_frames, nw_run_frames, nw_tur_frames, nw_mir_frames]

    se_master = Image.new("RGBA", (CELL_W * COLS, CELL_H * ROWS), (0, 0, 0, 0))
    nw_master = Image.new("RGBA", (CELL_W * COLS, CELL_H * ROWS), (0, 0, 0, 0))

    for d, rows_list, master_im in [("se", se_rows, se_master), ("nw", nw_rows, nw_master)]:
        fdir = SPRITES_DIR / "archon" / d
        fdir.mkdir(parents=True, exist_ok=True)
        for r, (aname, flist) in enumerate(zip(anim_names, rows_list)):
            strip = Image.new("RGBA", (CELL_W * COLS, CELL_H), (0, 0, 0, 0))
            for c, fim in enumerate(flist):
                fim.save(fdir / f"{aname}_{c}.png")
                strip.paste(fim, (c * CELL_W, 0), fim)
                master_im.paste(fim, (c * CELL_W, r * CELL_H), fim)
            strip.save(SPRITES_DIR / f"archon_{d}_{aname}_strip.png")
            rgba_frames_to_transparent_gif(flist, GIFS_DIR / f"archon_{d}_{aname}.gif", durations[aname])

    se_master.save(SPRITES_DIR / "archon_isometric_se_5row_master.png")
    nw_master.save(SPRITES_DIR / "archon_isometric_nw_5row_master.png")
    se_master.save(BRAIN_DIR / "archon_isometric_se_5row_master.png")
    nw_master.save(BRAIN_DIR / "archon_isometric_nw_5row_master.png")

    for r, aname in enumerate(anim_names):
        sh = Image.new("RGBA", (CELL_W * COLS, CELL_H * 2), (0, 0, 0, 0))
        sh.paste(se_master.crop((0, r * CELL_H, CELL_W * COLS, (r + 1) * CELL_H)), (0, 0))
        sh.paste(nw_master.crop((0, r * CELL_H, CELL_W * COLS, (r + 1) * CELL_H)), (0, CELL_H))
        sh.save(SPRITES_DIR / f"archon_{aname}_sheet.png")
        sh.save(BRAIN_DIR / f"archon_{aname}_sheet.png")

    build_showcase_gifs(se_master, nw_master)
    print("ALL Archon (First Light) sprites, separate sheets, strips & GIFs exported cleanly!")


if __name__ == "__main__":
    main()
