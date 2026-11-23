import math
from PIL import Image, ImageDraw

W, H = 1376, 768
COLS, ROWS = 8, 2
CELL_W = W // COLS  # 172
CELL_H = H // ROWS  # 384

BG = (36, 36, 38)
GROUND_COL = (68, 72, 86)
HEAD_COL = (232, 232, 224)
TORSO_COL = (205, 198, 182)
GOLD_COL = (240, 192, 72)
L_LIMB = (56, 189, 248)
L_DARK = (14, 116, 144)
R_LIMB = (251, 146, 60)
R_DARK = (194, 65, 12)
JOINT_COL = (248, 248, 252)
FIRE_COL = (255, 210, 75)
FIRE_BRIGHT = (255, 248, 195)


def draw_capsule(draw, p0, p1, radius, fill, outline=(18, 20, 26)):
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < 1e-3:
        draw.ellipse((x0 - radius, y0 - radius, x0 + radius, y0 + radius), fill=fill, outline=outline, width=2)
        return
    nx, ny = -dy / length * radius, dx / length * radius
    poly = [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]
    draw.polygon(poly, fill=fill)
    draw.ellipse((x0 - radius, y0 - radius, x0 + radius, y0 + radius), fill=fill)
    draw.ellipse((x1 - radius, y1 - radius, x1 + radius, y1 + radius), fill=fill)
    draw.line([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny)], fill=outline, width=2)
    draw.line([(x0 - nx, y0 - ny), (x1 - nx, y1 - ny)], fill=outline, width=2)


def solve_leg(hip, foot, thigh_len, shin_len, knee_forward_sign):
    hx, hy = hip
    fx, fy = foot
    dx, dy = fx - hx, fy - hy
    d = max(1.0, min(thigh_len + shin_len - 0.5, math.hypot(dx, dy)))
    cos_a = max(-1.0, min(1.0, (thigh_len**2 + d**2 - shin_len**2) / (2 * thigh_len * d)))
    angle_base = math.atan2(dy, dx)
    angle_off = math.acos(cos_a)
    theta = angle_base - knee_forward_sign * angle_off
    return (hx + math.cos(theta) * thigh_len, hy + math.sin(theta) * thigh_len)


def draw_archon_head_halo(draw, hx, hy, dir_x, facing_se, halo_glow=False):
    # Spiked Golden Solar Halo behind hood
    r_halo = 25 if halo_glow else 22
    draw.ellipse((hx - r_halo, hy - r_halo - 4, hx + r_halo, hy + r_halo - 4), outline=FIRE_BRIGHT if halo_glow else GOLD_COL, width=4 if halo_glow else 3)
    for deg in range(-150, 31, 30):
        rad = math.radians(deg)
        p0 = (hx + math.cos(rad) * r_halo, hy - 4 + math.sin(rad) * r_halo)
        p1 = (hx + math.cos(rad) * (r_halo + 9), hy - 4 + math.sin(rad) * (r_halo + 9))
        draw.line([p0, p1], fill=FIRE_BRIGHT if halo_glow else GOLD_COL, width=2)
    # Hooded pointed knight-helm
    draw.ellipse((hx - 15, hy - 17, hx + 15, hy + 17), fill=HEAD_COL, outline=(18, 20, 26), width=2)
    if facing_se:
        draw.line([(hx + 3*dir_x, hy - 2), (hx + 12*dir_x, hy + 1)], fill=(60, 215, 255), width=3)


def draw_walk_run_cell(draw, cx, ground_y, phase, is_run, facing_se=True):
    dir_x = 1.0 if facing_se else -1.0
    iso_y = 0.28 if facing_se else -0.28
    tw, th = 64, 32
    draw.polygon([(cx, ground_y - th/2), (cx + tw/2, ground_y), (cx, ground_y + th/2), (cx - tw/2, ground_y)], outline=GROUND_COL, fill=(44, 46, 54))

    thigh_len, shin_len = 54.0, 52.0
    if not is_run:
        pelvis_h = [96, 88, 101, 105, 96, 88, 101, 105][phase]
        l_x = [34, 12, -5, -22, -32, -26, 4, 26][phase]
        l_l = [0, 0, 0, 3, 6, 14, 18, 10][phase]
        r_x = [-32, -26, 4, 26, 34, 12, -5, -22][phase]
        r_l = [6, 14, 18, 10, 0, 0, 0, 3][phase]
        pelvis_x, sh_x, torso_len = cx - 2 * dir_x, cx + 4 * dir_x, 66
        l_arm_s = [-0.85, -0.45, 0.0, 0.45, 0.85, 0.45, 0.0, -0.45][phase]
        r_arm_s = [0.85, 0.45, 0.0, -0.45, -0.85, -0.45, 0.0, 0.45][phase]
    else:
        pelvis_h = [92, 82, 98, 114, 92, 82, 98, 114][phase]
        l_x = [36, 8, -32, -46, -34, -10, 26, 44][phase]
        l_l = [0, 0, 4, 28, 24, 30, 26, 20][phase]
        r_x = [-34, -10, 26, 44, 36, 8, -32, -46][phase]
        r_l = [24, 30, 26, 20, 0, 0, 4, 28][phase]
        pelvis_x, sh_x, torso_len = cx - 9 * dir_x, cx + 13 * dir_x, 62
        l_arm_s = [-1.05, -0.55, 0.25, 1.0, 1.05, 0.55, -0.25, -1.0][phase]
        r_arm_s = [1.05, 0.55, -0.25, -1.0, -1.05, -0.55, 0.25, 1.0][phase]

    pelvis_y = ground_y - pelvis_h
    sh_y = pelvis_y - torso_len
    head_x, head_y = sh_x + (5 if is_run else 1) * dir_x, sh_y - 25
    sep = 11 if facing_se else -11
    l_hip, r_hip = (pelvis_x + sep, pelvis_y - 3), (pelvis_x - sep, pelvis_y + 3)
    l_sh, r_sh = (sh_x + sep + 2, sh_y - 3), (sh_x - sep - 2, sh_y + 3)
    l_foot = (cx + sep + l_x * dir_x, ground_y - 3 + l_x * iso_y - l_l)
    r_foot = (cx - sep + r_x * dir_x, ground_y + 3 + r_x * iso_y - r_l)
    l_knee = solve_leg(l_hip, l_foot, thigh_len, shin_len, dir_x)
    r_knee = solve_leg(r_hip, r_foot, thigh_len, shin_len, dir_x)

    def make_arm(sh, swing):
        if not is_run:
            el = (sh[0] + swing * 20 * dir_x, sh[1] + 34 - abs(swing) * 4)
            hand = (el[0] + (swing * 18 + 8) * dir_x, el[1] + 28 - max(0, swing) * 10)
        else:
            el = (sh[0] + (swing * 26 - 6) * dir_x, sh[1] + 28 - abs(swing) * 8)
            hand = (el[0] + (swing * 16 + 22) * dir_x, el[1] + 4 - max(0, swing) * 18)
        return el, hand

    l_el, l_hand = make_arm(l_sh, l_arm_s)
    r_el, r_hand = make_arm(r_sh, r_arm_s)

    def draw_chain(p0, p1, p2, col, r_u, r_l, is_leg=False):
        draw_capsule(draw, p0, p1, r_u, col)
        draw_capsule(draw, p1, p2, r_l, col)
        draw.ellipse((p1[0]-3, p1[1]-3, p1[0]+3, p1[1]+3), fill=JOINT_COL)
        if is_leg:
            draw_capsule(draw, p2, (p2[0] + 12*dir_x, p2[1] + 3*iso_y), 6, col)

    if facing_se:
        draw_chain(l_sh, l_el, l_hand, L_DARK, 8, 6)
        draw_chain(l_hip, l_knee, l_foot, L_DARK, 11, 8, True)
        draw_capsule(draw, (sh_x, sh_y), (pelvis_x, pelvis_y), 19, TORSO_COL)
        draw_archon_head_halo(draw, head_x, head_y, dir_x, True)
        draw_chain(r_hip, r_knee, r_foot, R_LIMB, 11, 8, True)
        draw_chain(r_sh, r_el, r_hand, R_LIMB, 8, 6)
    else:
        draw_chain(r_sh, r_el, r_hand, R_DARK, 8, 6)
        draw_chain(r_hip, r_knee, r_foot, R_DARK, 11, 8, True)
        draw_capsule(draw, (sh_x, sh_y), (pelvis_x, pelvis_y), 19, TORSO_COL)
        draw_archon_head_halo(draw, head_x, head_y, dir_x, False)
        draw_chain(l_hip, l_knee, l_foot, L_LIMB, 11, 8, True)
        draw_chain(l_sh, l_el, l_hand, L_LIMB, 8, 6)


def draw_turibulo_cell(draw, cx, ground_y, phase, facing_se=True):
    """Row 0: 8-frame Turíbulo (Censer Flail) + Towering Solar Greatshield Attack."""
    dir_x = 1.0 if facing_se else -1.0
    iso_y = 0.28 if facing_se else -0.28
    tw, th = 64, 32
    draw.polygon([(cx, ground_y - th/2), (cx + tw/2, ground_y), (cx, ground_y + th/2), (cx - tw/2, ground_y)], outline=GROUND_COL, fill=(44, 46, 54))

    body_shift = [0, -8, -12, 10, 20, 14, 6, 0][phase] * dir_x
    pelvis_h   = [96, 92, 88, 86, 84, 90, 94, 96][phase]
    lean_x     = [3, -8, -14, 16, 22, 14, 6, 3][phase] * dir_x

    pelvis_x = cx + body_shift * 0.65
    pelvis_y = ground_y - pelvis_h
    sh_x = pelvis_x + lean_x
    sh_y = pelvis_y - 64
    head_x, head_y = sh_x + lean_x * 0.22, sh_y - 24

    sep = 11 if facing_se else -11
    l_hip, r_hip = (pelvis_x + sep, pelvis_y - 3), (pelvis_x - sep, pelvis_y + 3)
    l_sh, r_sh = (sh_x + sep + 2, sh_y - 3), (sh_x - sep - 2, sh_y + 3)

    f_step = [18, 12, 8, 32, 40, 34, 24, 18][phase]
    b_step = [-18, -22, -26, -24, -28, -24, -20, -18][phase]
    l_foot = (cx + sep + f_step * dir_x, ground_y - 3 + f_step * iso_y)
    r_foot = (cx - sep + b_step * dir_x, ground_y + 3 + b_step * iso_y)
    l_knee = solve_leg(l_hip, l_foot, 54, 52, dir_x)
    r_knee = solve_leg(r_hip, r_foot, 54, 52, dir_x)

    # Flail hand (Right) & Greatshield hand (Left)
    fl_rel = [(10, 26), (-20, 4), (-22, -26), (22, -16), (44, 10), (32, 30), (20, 28), (10, 26)][phase]
    shld_rel = [(26, 16), (32, 10), (36, 6), (20, 16), (14, 20), (18, 18), (24, 16), (26, 16)][phase]

    def place_arm(sh, rel):
        hx = sh[0] + rel[0] * dir_x
        hy = sh[1] + rel[1]
        return ((sh[0] + hx) * 0.5 - 6 * dir_x, (sh[1] + hy) * 0.5 + 10), (hx, hy)

    r_el, r_hand = place_arm(r_sh, fl_rel)
    l_el, l_hand = place_arm(l_sh, shld_rel)

    # Flail handle + swinging chain + spiked blazing censer ball
    h_deg = [130, -145, -105, -45, 18, 65, 95, 130][phase]
    b_off = [(-18, 48), (-42, 10), (-34, -44), (10, -52), (56, 8), (38, 46), (10, 50), (-18, 48)][phase]
    hr = math.radians(h_deg)
    h_tip = (r_hand[0] + math.cos(hr) * 26 * dir_x, r_hand[1] + math.sin(hr) * 26)
    ball = (h_tip[0] + b_off[0] * dir_x, h_tip[1] + b_off[1])

    def draw_chain_limb(p0, p1, p2, col, r_u, r_l, is_leg=False):
        draw_capsule(draw, p0, p1, r_u, col)
        draw_capsule(draw, p1, p2, r_l, col)
        draw.ellipse((p1[0]-3, p1[1]-3, p1[0]+3, p1[1]+3), fill=JOINT_COL)
        if is_leg:
            draw_capsule(draw, p2, (p2[0] + 12*dir_x, p2[1] + 3*iso_y), 6, col)

    def draw_shield():
        sx, sy = l_hand
        pts = [(sx - 10*dir_x, sy - 50), (sx + 16*dir_x, sy - 36), (sx + 18*dir_x, sy + 42), (sx + 2*dir_x, sy + 58), (sx - 12*dir_x, sy + 36)]
        draw.polygon(pts, fill=TORSO_COL, outline=GOLD_COL)
        draw.ellipse((sx - 4, sy - 10, sx + 10, sy + 4), fill=FIRE_COL, outline=GOLD_COL, width=2)

    def draw_turibulo():
        draw.line([r_hand, h_tip], fill=GOLD_COL, width=5)
        draw.line([h_tip, ball], fill=(195, 180, 140), width=2)
        draw.ellipse((ball[0]-11, ball[1]-11, ball[0]+11, ball[1]+11), fill=FIRE_COL, outline=GOLD_COL, width=2)
        if phase in (3, 4, 5):
            arc_pts = []
            sa, ea = (-110, -15) if phase == 3 else ((-80, 48) if phase == 4 else (12, 82))
            for a in range(sa, ea + 1, 10):
                ar = math.radians(a)
                arc_pts.append((sh_x + (30 + math.cos(ar)*66)*dir_x, sh_y + 10 + math.sin(ar)*58))
            draw.line(arc_pts, fill=FIRE_COL, width=11 if phase == 4 else 5)

    if facing_se:
        draw_chain_limb(l_sh, l_el, l_hand, L_DARK, 8, 6)
        draw_shield()
        draw_chain_limb(l_hip, l_knee, l_foot, L_DARK, 11, 8, True)
        draw_capsule(draw, (sh_x, sh_y), (pelvis_x, pelvis_y), 19, TORSO_COL)
        draw_archon_head_halo(draw, head_x, head_y, dir_x, True, halo_glow=(phase in (3, 4)))
        draw_chain_limb(r_hip, r_knee, r_foot, R_LIMB, 11, 8, True)
        draw_turibulo()
        draw_chain_limb(r_sh, r_el, r_hand, R_LIMB, 8, 6)
    else:
        draw_turibulo()
        draw_chain_limb(r_sh, r_el, r_hand, R_DARK, 8, 6)
        draw_chain_limb(r_hip, r_knee, r_foot, R_DARK, 11, 8, True)
        draw_capsule(draw, (sh_x, sh_y), (pelvis_x, pelvis_y), 19, TORSO_COL)
        draw_archon_head_halo(draw, head_x, head_y, dir_x, False, halo_glow=(phase in (3, 4)))
        draw_chain_limb(l_hip, l_knee, l_foot, L_LIMB, 11, 8, True)
        draw_chain_limb(l_sh, l_el, l_hand, L_LIMB, 8, 6)
        draw_shield()


def draw_miracle_cell(draw, cx, ground_y, phase, facing_se=True):
    """Row 1: 8-frame First Light Miracle Cast (0 Ready -> 1-2 Kneel/Gather -> 3-4 Levitate & Channel Radiant Solar Burst -> 5-6 Project Golden Wave -> 7 Recover)."""
    dir_x = 1.0 if facing_se else -1.0
    iso_y = 0.28 if facing_se else -0.28
    tw, th = 64, 32
    draw.polygon([(cx, ground_y - th/2), (cx + tw/2, ground_y), (cx, ground_y + th/2), (cx - tw/2, ground_y)], outline=GROUND_COL, fill=(44, 46, 54))

    # Subtle solemn prayer gathering (1,2) -> radiant elevation/thrust (3,4,5) -> settle (6,7)
    pelvis_h = [98, 92, 90, 102, 108, 104, 100, 98][phase]
    lean_x   = [2, -4, -6, 0, 8, 12, 6, 2][phase] * dir_x

    pelvis_x = cx
    pelvis_y = ground_y - pelvis_h
    sh_x = pelvis_x + lean_x
    sh_y = pelvis_y - 66
    head_x, head_y = sh_x + lean_x * 0.15, sh_y - 25

    sep = 11 if facing_se else -11
    l_hip, r_hip = (pelvis_x + sep, pelvis_y - 3), (pelvis_x - sep, pelvis_y + 3)
    l_sh, r_sh = (sh_x + sep + 2, sh_y - 3), (sh_x - sep - 2, sh_y + 3)

    l_foot = (cx + sep + 14 * dir_x, ground_y - 3 + 14 * iso_y)
    r_foot = (cx - sep - 14 * dir_x, ground_y + 3 - 14 * iso_y)
    l_knee = solve_leg(l_hip, l_foot, 54, 52, dir_x)
    r_knee = solve_leg(r_hip, r_foot, 54, 52, dir_x)

    # Hands gather at sternum Eclipse Sun (1,2) -> rise wide to heavens (3,4) -> project forward burst (5) -> lower (6,7)
    r_rel = [(8, 28), (12, 12), (10, 4), (-14, -22), (18, -32), (42, -6), (26, 16), (8, 28)][phase]
    l_rel = [(18, 26), (18, 10), (16, 2), (24, -24), (36, -28), (48, -2), (30, 14), (18, 26)][phase]

    def place_arm(sh, rel):
        hx = sh[0] + rel[0] * dir_x
        hy = sh[1] + rel[1]
        return ((sh[0] + hx) * 0.5 - 4 * dir_x, (sh[1] + hy) * 0.5 + 8), (hx, hy)

    r_el, r_hand = place_arm(r_sh, r_rel)
    l_el, l_hand = place_arm(l_sh, l_rel)

    # Glowing golden Solar Rune circle on ground & radiant energy burst during phases 2..6
    if phase in (2, 3, 4, 5):
        rr = [0, 0, 26, 38, 48, 36, 0, 0][phase]
        draw.ellipse((cx - rr, ground_y - rr * 0.5, cx + rr, ground_y + rr * 0.5), outline=FIRE_COL, width=3)
    if phase in (3, 4, 5):
        # Radiant golden miracle burst in front/above hands
        bx = head_x + (18 if phase == 3 else (36 if phase == 4 else 52)) * dir_x
        by = head_y + (-20 if phase == 3 else (-8 if phase == 4 else 12))
        br = 18 if phase == 3 else (28 if phase == 4 else 22)
        draw.ellipse((bx - br, by - br, bx + br, by + br), fill=FIRE_BRIGHT, outline=FIRE_COL, width=4)

    def draw_chain_limb(p0, p1, p2, col, r_u, r_l, is_leg=False):
        draw_capsule(draw, p0, p1, r_u, col)
        draw_capsule(draw, p1, p2, r_l, col)
        draw.ellipse((p1[0]-3, p1[1]-3, p1[0]+3, p1[1]+3), fill=JOINT_COL)
        if is_leg:
            draw_capsule(draw, p2, (p2[0] + 12*dir_x, p2[1] + 3*iso_y), 6, col)

    if facing_se:
        draw_chain_limb(l_sh, l_el, l_hand, L_DARK, 8, 6)
        draw_chain_limb(l_hip, l_knee, l_foot, L_DARK, 11, 8, True)
        draw_capsule(draw, (sh_x, sh_y), (pelvis_x, pelvis_y), 19, TORSO_COL)
        draw_archon_head_halo(draw, head_x, head_y, dir_x, True, halo_glow=(phase in (2, 3, 4, 5)))
        draw_chain_limb(r_hip, r_knee, r_foot, R_LIMB, 11, 8, True)
        draw_chain_limb(r_sh, r_el, r_hand, R_LIMB, 8, 6)
    else:
        draw_chain_limb(r_sh, r_el, r_hand, R_DARK, 8, 6)
        draw_chain_limb(r_hip, r_knee, r_foot, R_DARK, 11, 8, True)
        draw_capsule(draw, (sh_x, sh_y), (pelvis_x, pelvis_y), 19, TORSO_COL)
        draw_archon_head_halo(draw, head_x, head_y, dir_x, False, halo_glow=(phase in (2, 3, 4, 5)))
        draw_chain_limb(l_hip, l_knee, l_foot, L_LIMB, 11, 8, True)
        draw_chain_limb(l_sh, l_el, l_hand, L_LIMB, 8, 6)


def build_all():
    for suffix, f_se in [("se", True), ("nw", False)]:
        im_wr = Image.new("RGB", (W, H), BG)
        d_wr = ImageDraw.Draw(im_wr)
        for c in range(COLS):
            cx = c * CELL_W + CELL_W // 2
            draw_walk_run_cell(d_wr, cx, CELL_H - 48, c, False, f_se)
            draw_walk_run_cell(d_wr, cx, 2 * CELL_H - 48, c, True, f_se)
        im_wr.save(f"/tmp/archon_guide_{suffix}_walk_run.png")

        im_cb = Image.new("RGB", (W, H), BG)
        d_cb = ImageDraw.Draw(im_cb)
        for c in range(COLS):
            cx = c * CELL_W + CELL_W // 2
            draw_turibulo_cell(d_cb, cx, CELL_H - 48, c, f_se)
            draw_miracle_cell(d_cb, cx, 2 * CELL_H - 48, c, f_se)
        im_cb.save(f"/tmp/archon_guide_{suffix}_combat.png")
    print("Generated all 4 Archon isometric pose guides!")


build_all()
