#!/usr/bin/env python3
"""
Builds the complete 5-row x 8-column Isometric Tactical RPG Master Sheets
(256x340 per cell -> 2048x1700 master sheet) for both Male and Female Lancers
in SE and NW directions:
  Row 0: 8-frame Breathing Idle
  Row 1: 8-frame Walk Cycle
  Row 2: 8-frame Run Cycle
  Row 3: 8-frame Sword Attack (Vharenn Slash)
  Row 4: 8-frame Bow Attack (Archeotek Recurve Shot)
"""

from __future__ import annotations
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image
import sys

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from build_8frame_lancer_sheets import remove_background_rgba

SPRITES_DIR = REPO / "sprites"
ORIG_DIR = REPO / "originals"
BRAIN_DIR = Path(
    "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/ff7f66f4-8693-48db-8219-5ca19e947042"
)

CELL_W = 256
CELL_H = 340
COLS = 8
ROWS = 5  # 0: idle, 1: walk, 2: run, 3: sword, 4: bow
GROUND_Y = 320  # consistent foot ground plane inside every 256x340 cell


import heapq


def strip_floor_diamonds(rgba: np.ndarray) -> np.ndarray:
    """Removes faint dark-grey isometric floor guide diamonds beneath boots while preserving dark boots."""
    out = rgba.copy()
    h, w, _ = out.shape
    # Floor diamonds only appear in the bottom 55px of each row and are flat low-saturation grey (40..66)
    rh = h // 2
    for r in range(2):
        y_start = r * rh + rh - 65
        y_end = (r + 1) * rh
        sub = out[y_start:y_end, :]
        rgb = sub[:, :, :3].astype(np.int16)
        alpha = sub[:, :, 3] > 0
        sat = rgb.max(axis=2) - rgb.min(axis=2)
        lum = rgb.mean(axis=2)
        # Floor diamond fill is flat mid-dark grey (~42..58) with very low local gradient
        gy = np.abs(np.diff(rgb, axis=0, prepend=rgb[:1, :])).max(axis=2)
        gx = np.abs(np.diff(rgb, axis=1, prepend=rgb[:, :1])).max(axis=2)
        grad = np.maximum(gx, gy)
        # Also remove the faint 1px diamond border (~60..76) touching flat diamond interior
        is_flat_tile = alpha & (sat <= 12) & (lum >= 38) & (lum <= 64) & (grad <= 10)
        # Connected components of flat tile pixels >= 25px -> clear + 1px border of low-sat grey <= 78
        sh, sw = is_flat_tile.shape
        vis = np.zeros((sh, sw), dtype=bool)
        clear_mask = np.zeros((sh, sw), dtype=bool)
        for y in range(sh):
            for x in range(sw):
                if is_flat_tile[y, x] and not vis[y, x]:
                    q = deque([(y, x)])
                    vis[y, x] = True
                    comp = []
                    while q:
                        cy, cx = q.popleft()
                        comp.append((cy, cx))
                        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < sh and 0 <= nx < sw and is_flat_tile[ny, nx] and not vis[ny, nx]:
                                vis[ny, nx] = True
                                q.append((ny, nx))
                    if len(comp) >= 24:
                        for cy, cx in comp:
                            clear_mask[cy, cx] = True
        # Expand 2px into adjacent low-saturation grey outline (lum 40..82, sat <= 14) so diamond edge vanishes too
        for _ in range(2):
            ext = clear_mask.copy()
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                shifted = np.roll(np.roll(clear_mask, dy, axis=0), dx, axis=1)
                ext |= shifted & alpha & (sat <= 15) & (lum >= 38) & (lum <= 84)
            clear_mask = ext
        sub[clear_mask] = 0
        out[y_start:y_end, :] = sub
    return out


def split_row_by_valleys(row_rgba: np.ndarray, cols: int = COLS) -> list[np.ndarray]:
    """
    2D Multi-Source Watershed Ownership segmentation:
    1. Identifies the 8 character bodies (excluding bright cyan slash/arrow VFX so bodies never merge).
    2. Runs a priority-queue 2D Dijkstra flood-fill from all 8 body seeds across all foreground pixels,
       giving forward-extending weapon/VFX pixels natural ownership by the character they attach to.
    3. Assigns any detached VFX/arrow component to the nearest character to its LEFT (forward attack dir).
    """
    rh, rw, _ = row_rgba.shape
    fg = row_rgba[:, :, 3] > 0
    r_c = row_rgba[:, :, 0].astype(np.int16)
    g_c = row_rgba[:, :, 1].astype(np.int16)
    b_c = row_rgba[:, :, 2].astype(np.int16)
    is_cyan_vfx = fg & (b_c > 145) & (g_c > 145) & (b_c - r_c > 20)
    # Dilate VFX mask by 3px so dark outlines around touching cyan slash arcs don't bridge two body seeds!
    vfx_dilated = is_cyan_vfx.copy()
    for _ in range(3):
        ext = vfx_dilated.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy or dx:
                    ext |= np.roll(np.roll(vfx_dilated, dy, axis=0), dx, axis=1)
        vfx_dilated = ext
    body_fg = fg & (~vfx_dilated)

    # 1. Find the 8 largest body components (sorted left to right)
    labels = np.zeros((rh, rw), dtype=np.int32)
    comps = []
    lbl = 0
    for y in range(rh):
        for x in range(rw):
            if body_fg[y, x] and labels[y, x] == 0:
                lbl += 1
                q = deque([(y, x)])
                labels[y, x] = lbl
                cnt = 0
                xsum = 0
                while q:
                    cy, cx = q.popleft()
                    cnt += 1
                    xsum += cx
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dy == 0 and dx == 0:
                                continue
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < rh and 0 <= nx < rw and body_fg[ny, nx] and labels[ny, nx] == 0:
                                labels[ny, nx] = lbl
                                q.append((ny, nx))
                comps.append((lbl, cnt, xsum / float(cnt)))

    main_comps = sorted(sorted(comps, key=lambda t: t[1], reverse=True)[:cols], key=lambda t: t[2])
    body_cxs = [m[2] for m in main_comps]

    owner = np.full((rh, rw), -1, dtype=np.int16)
    dist_map = np.full((rh, rw), 1e9, dtype=np.float64)
    pq: list[tuple[float, int, int, int]] = []

    for slot, (m_lbl, _, _) in enumerate(main_comps):
        ys, xs = np.where(labels == m_lbl)
        owner[ys, xs] = slot
        dist_map[ys, xs] = 0.0
        for y, x in zip(ys, xs):
            has_unowned = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < rh and 0 <= nx < rw and fg[ny, nx] and labels[ny, nx] != m_lbl:
                        has_unowned = True
                        break
                if has_unowned:
                    break
            if has_unowned:
                heapq.heappush(pq, (0.0, int(y), int(x), slot))

    # 2. Fast multi-source 2D Dijkstra across unseeded weapon & cyan VFX pixels
    while pq:
        d, y, x, slot = heapq.heappop(pq)
        if d > dist_map[y, x]:
            continue
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < rh and 0 <= nx < rw and fg[ny, nx] and dist_map[ny, nx] > 0.0:
                if abs(nx - body_cxs[slot]) > 145:
                    continue
                step = 1.414 if (dy != 0 and dx != 0) else 1.0
                if is_cyan_vfx[ny, nx]:
                    if dx > 0:
                        step *= 0.80
                    elif dx < 0:
                        step *= 1.35
                nd = d + step
                if nd < dist_map[ny, nx]:
                    dist_map[ny, nx] = nd
                    owner[ny, nx] = slot
                    heapq.heappush(pq, (nd, ny, nx, slot))

    # 3. Any remaining unowned foreground clusters (e.g., detached released arrow or flying slash spark):
    # Assign to nearest character body (favoring the character immediately to its LEFT for forward projectiles!)
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
                if len(pts) >= 6:
                    ccx = float(np.mean([p[1] for p in pts]))
                    # Prefer slot to the left (forward attack direction) if within 135px
                    best_slot = min(
                        range(cols),
                        key=lambda s: abs(ccx - body_cxs[s]) * (0.75 if ccx >= body_cxs[s] else 1.25),
                    )
                    if abs(ccx - body_cxs[best_slot]) < 140:
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


def anchor_combat_row(
    cells: list[np.ndarray],
    target_stand_h: int,
    flip_x: bool = False,
    fix_male_bow_f5: bool = False,
) -> list[Image.Image]:
    """
    Scales combat frames to match the exact standing height of Idle/Walk/Run,
    anchors feet consistently on GROUND_Y, and aligns torso center X on CELL_W // 2.
    """
    # Measure standing height from Frame 0 & Frame 7 (non-lunge ready stances)
    stand_hs = []
    for idx in (0, 7):
        ys, _ = np.where(cells[idx][:, :, 3] > 0)
        if len(ys):
            stand_hs.append(int(ys.max() - ys.min()))
    base_h = float(np.median(stand_hs)) if stand_hs else 225.0
    scale = max(1.0, min(1.16, target_stand_h / base_h))

    # Measure ground baseline of ready frames (0, 7) in source coordinates
    y1s = []
    for idx in (0, 1, 6, 7):
        ys, _ = np.where(cells[idx][:, :, 3] > 0)
        if len(ys):
            y1s.append(int(ys.max()))
    src_ground_y = float(np.median(y1s)) if y1s else 345.0

    # First pass: compute scaled frames anchored to GROUND_Y
    out_frames: list[Image.Image] = []
    torso_cxs = []
    for cell in cells:
        ys, xs = np.where(cell[:, :, 3] > 0)
        if len(ys) == 0:
            out_frames.append(Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0)))
            continue

        # Estimate torso center X from the LOWER-MIDDLE body (y between src_ground_y - 160 and src_ground_y - 30)
        # Excluding bright cyan slash arcs & arrows (which are saturated cyan) so VFX never shift torso X!
        r_c = cell[:, :, 0].astype(np.int16)
        g_c = cell[:, :, 1].astype(np.int16)
        b_c = cell[:, :, 2].astype(np.int16)
        is_vfx = (b_c > 170) & (g_c > 170) & (b_c - r_c > 35)
        body_mask = (cell[:, :, 3] > 0) & (~is_vfx)

        y_lo = max(0, int(src_ground_y - 185))
        y_hi = min(cell.shape[0], int(src_ground_y - 50))
        b_ys, b_xs = np.where(body_mask[y_lo:y_hi, :])
        body_cx = float(np.median(b_xs)) if len(b_xs) > 20 else float(np.median(xs))

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
        scaled = crop.resize((sw, sh), Image.Resampling.NEAREST)

        rel_cx_s = int(round(rel_cx * scale))
        dest_x = (CELL_W // 2) - rel_cx_s
        # Anchor using src_ground_y so lunges & overhead swings preserve natural vertical offset
        y_top_offset = int(round((y0 - src_ground_y) * scale))
        dest_y = GROUND_Y + y_top_offset
        dest_y = max(2, min(CELL_H - sh - 2, dest_y))
        dest_x = max(2, min(CELL_W - sw - 2, dest_x))

        frame = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
        frame.paste(scaled, (dest_x, dest_y), scaled)
        out_frames.append(frame)

    # Surgical head fix for Male SE Bow Frame 5 (where the model accidentally gave him a bob haircut)
    if fix_male_bow_f5 and len(out_frames) >= 6:
        f4 = np.array(out_frames[4])
        f5 = np.array(out_frames[5])
        # Locate top of head in f4 and f5
        y4 = int(np.where(f4[:, :, 3] > 0)[0].min())
        y5 = int(np.where(f5[:, :, 3] > 0)[0].min())
        # Head bounding box: top 64px around center x (CELL_W//2 - 36 .. CELL_W//2 + 28)
        hx0, hx1 = CELL_W // 2 - 36, CELL_W // 2 + 26
        head_h = 62
        head_patch = f4[y4 : y4 + head_h, hx0:hx1].copy()
        # Clear old hair/head in f5 in that band and replace with f4's swept-hair head
        f5[y5 : y5 + head_h, hx0:hx1] = 0
        f5[y5 : y5 + head_h, hx0:hx1] = head_patch
        out_frames[5] = Image.fromarray(f5, "RGBA")

    return out_frames


def embed_192x304_into_256x340(im: Image.Image) -> Image.Image:
    """Centers an existing 192x304 Idle/Walk/Run frame onto 256x340 at exact GROUND_Y."""
    out = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    dx = (CELL_W - im.width) // 2  # +32
    # Old ground anchor was y=286 inside 304 -> new GROUND_Y=320 -> dy = +34
    dy = GROUND_Y - 286
    out.paste(im, (dx, dy), im)
    return out


def build_character_5row(
    char_name: str,
    direction: str,
    combat_src: Path,
    target_stand_h: int,
    flip_combat: bool,
    fix_male_bow_f5: bool = False,
) -> Path:
    # Save original combat JPG into originals/
    raw_rgb = Image.open(combat_src).convert("RGB")
    raw_rgb.save(ORIG_DIR / combat_src.name, quality=96)

    # Remove dark background + faint floor diamond lines
    combat_rgba = np.array(remove_background_rgba(raw_rgb, tol=13.5, mask_watermark=True))
    combat_rgba = strip_floor_diamonds(combat_rgba)
    rh = combat_rgba.shape[0] // 2

    sword_cells = split_row_by_valleys(combat_rgba[0:rh, :], COLS)
    bow_cells = split_row_by_valleys(combat_rgba[rh : rh * 2, :], COLS)

    sword_frames = anchor_combat_row(sword_cells, target_stand_h, flip_x=flip_combat, fix_male_bow_f5=False)
    bow_frames = anchor_combat_row(bow_cells, target_stand_h, flip_x=flip_combat, fix_male_bow_f5=fix_male_bow_f5)

    # Save individual sword & bow frames + standalone 2x8 combat sheet
    frame_dir = SPRITES_DIR / char_name / direction
    frame_dir.mkdir(parents=True, exist_ok=True)

    combat_sheet = Image.new("RGBA", (CELL_W * COLS, CELL_H * 2), (0, 0, 0, 0))
    for c in range(COLS):
        sword_frames[c].save(frame_dir / f"sword_{c}.png")
        bow_frames[c].save(frame_dir / f"bow_{c}.png")
        combat_sheet.paste(sword_frames[c], (c * CELL_W, 0), sword_frames[c])
        combat_sheet.paste(bow_frames[c], (c * CELL_W, CELL_H), bow_frames[c])

    combat_sheet_path = SPRITES_DIR / f"{char_name}_isometric_{direction}_8f_sword_bow.png"
    combat_sheet.save(combat_sheet_path)
    combat_sheet.save(BRAIN_DIR / f"{char_name}_isometric_{direction}_8f_sword_bow.png")

    # Assemble complete 5-row x 8-column Master Sheet (Idle, Walk, Run, Sword, Bow)
    master = Image.new("RGBA", (CELL_W * COLS, CELL_H * ROWS), (0, 0, 0, 0))
    for r, rname in enumerate(["idle", "walk", "run"]):
        for c in range(COLS):
            f_old = Image.open(frame_dir / f"{rname}_{c}.png")
            f_pad = embed_192x304_into_256x340(f_old)
            master.paste(f_pad, (c * CELL_W, r * CELL_H), f_pad)

    for c in range(COLS):
        master.paste(sword_frames[c], (c * CELL_W, 3 * CELL_H), sword_frames[c])
        master.paste(bow_frames[c], (c * CELL_W, 4 * CELL_H), bow_frames[c])

    master_path = SPRITES_DIR / f"{char_name}_isometric_{direction}_5row_master.png"
    master.save(master_path)
    print(f"Built {master_path.name} ({master.size[0]}x{master.size[1]}) + {combat_sheet_path.name}")
    return master_path


def main() -> None:
    ORIG_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("male_lancer", "se", BRAIN_DIR / "male_lancer_iso_se_8f_sword_bow_1795198036056.jpg", 246, False, True),
        ("male_lancer", "nw", BRAIN_DIR / "male_lancer_iso_nw_8f_sword_bow_1795198159081.jpg", 240, True, False),
        ("female_lancer", "se", BRAIN_DIR / "female_lancer_iso_se_8f_sword_bow_1795198032252.jpg", 260, False, False),
        ("female_lancer", "nw", BRAIN_DIR / "female_lancer_iso_nw_8f_sword_bow_1795198170232.jpg", 248, True, False),
    ]
    for cname, d, src, th, flip_c, fix_m5 in jobs:
        build_character_5row(cname, d, src, th, flip_c, fix_m5)


if __name__ == "__main__":
    main()
