import math
from PIL import Image, ImageDraw

W, H = 1376, 768
COLS, ROWS = 8, 2
CELL_W = W // COLS  # 172
CELL_H = H // ROWS  # 384

BG = (36, 36, 38)
GROUND_COL = (68, 72, 86)
CARAPACE_COL = (150, 158, 172)
BRASS_COL = (205, 168, 86)
POD_RED = (210, 62, 62)
VISOR_BLUE = (72, 185, 255)
L_LIMB = (56, 189, 248)
L_DARK = (14, 116, 144)
R_LIMB = (251, 146, 60)
R_DARK = (194, 65, 12)
JOINT_COL = (248, 248, 252)
WEAPON_COL = (232, 242, 252)
SHIELD_COL = (188, 152, 74)
ARC_COL = (95, 230, 255)


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


def draw_bastion_torso(draw, sh_x, sh_y, pelvis_x, pelvis_y, dir_x, facing_se):
    """Draws Bastion's signature hulking domed Siege Armor carapace + twin missile pods."""
    # Twin missile pods on top back
    pod_off = -12 * dir_x if facing_se else 10 * dir_x
    draw.rectangle((sh_x + pod_off - 24, sh_y - 38, sh_x + pod_off - 2, sh_y - 18), fill=BRASS_COL, outline=(18,20,26), width=2)
    draw.rectangle((sh_x + pod_off + 4, sh_y - 38, sh_x + pod_off + 26, sh_y - 18), fill=BRASS_COL, outline=(18,20,26), width=2)
    draw.ellipse((sh_x + pod_off - 19, sh_y - 34, sh_x + pod_off - 7, sh_y - 22), fill=POD_RED)
    draw.ellipse((sh_x + pod_off + 9, sh_y - 34, sh_x + pod_off + 21, sh_y - 22), fill=POD_RED)

    # Wide hunched carapace torso
    draw_capsule(draw, (sh_x, sh_y), (pelvis_x, pelvis_y), 29, CARAPACE_COL)
    # Recessed domed head hump inside shoulders
    hx = sh_x + 4 * dir_x
    hy = sh_y - 14
    draw.ellipse((hx - 20, hy - 18, hx + 20, hy + 16), fill=CARAPACE_COL, outline=(18,20,26), width=2)
    if facing_se:
        # Brass collar & glowing blue visor
        draw.ellipse((hx + 2 * dir_x - 10, hy - 2, hx + 2 * dir_x + 12, hy + 12), fill=VISOR_BLUE, outline=BRASS_COL, width=3)
    else:
        # Rear armor pack / reactor vents
        draw.rectangle((sh_x - 14, sh_y + 2, sh_x + 14, sh_y + 34), fill=BRASS_COL, outline=(18,20,26), width=2)
        draw.ellipse((sh_x - 6, sh_y + 12, sh_x + 6, sh_y + 24), fill=VISOR_BLUE)


def draw_walk_run_cell(draw, cx, ground_y, phase, is_run, facing_se=True):
    dir_x = 1.0 if facing_se else -1.0
    iso_y = 0.28 if facing_se else -0.28

    tw, th = 72, 36
    draw.polygon([(cx, ground_y - th/2), (cx + tw/2, ground_y), (cx, ground_y + th/2), (cx - tw/2, ground_y)], outline=GROUND_COL, fill=(44, 46, 54))

    thigh_len, shin_len = 52.0, 48.0  # stout, heavy juggernaut legs (100px)

    if not is_run:
        # HEAVY 8-FRAME STOMPING WALK
        pelvis_h = [90, 82, 94, 98, 90, 82, 94, 98][phase]
        l_x = [30,  10, -4, -20, -28, -22,  4,  22][phase]
        l_l = [0,   0,  0,   3,    6,  12, 16,   8][phase]
        r_x = [-28, -22,  4,  22, 30,  10, -4, -20][phase]
        r_l = [6,   12, 16,   8,  0,   0,  0,   3][phase]
        pelvis_x = cx - 2 * dir_x
        sh_x = cx + 6 * dir_x
        torso_len = 66
        l_arm_s = [-0.75, -0.4, 0.0, 0.4, 0.75, 0.4, 0.0, -0.4][phase]
        r_arm_s = [0.75, 0.4, 0.0, -0.4, -0.75, -0.4, 0.0, 0.4][phase]
    else:
        # HEAVY 8-FRAME JUGGERNAUT CHARGE / RUN
        pelvis_h = [86, 76, 92, 106, 86, 76, 92, 106][phase]
        l_x = [34,  6, -30, -40, -30, -8, 24,  38][phase]
        l_l = [0,   0,   4,  22,  20, 26, 22,  16][phase]
        r_x = [-30, -8, 24,  38,  34,  6, -30, -40][phase]
        r_l = [20,  26, 22,  16,   0,  0,   4,  22][phase]
        pelvis_x = cx - 10 * dir_x
        sh_x = cx + 16 * dir_x
        torso_len = 62
        l_arm_s = [-0.95, -0.5, 0.2, 0.9, 0.95, 0.5, -0.2, -0.9][phase]
        r_arm_s = [0.95, 0.5, -0.2, -0.9, -0.95, -0.5, 0.2, 0.9][phase]

    pelvis_y = ground_y - pelvis_h
    sh_y = pelvis_y - torso_len
    sep = 16 if facing_se else -16
    l_hip = (pelvis_x + sep, pelvis_y - 3)
    r_hip = (pelvis_x - sep, pelvis_y + 3)
    l_sh = (sh_x + sep + 6, sh_y - 2)
    r_sh = (sh_x - sep - 6, sh_y + 2)

    l_foot = (cx + sep + l_x * dir_x, ground_y - 3 + l_x * iso_y - l_l)
    r_foot = (cx - sep + r_x * dir_x, ground_y + 3 + r_x * iso_y - r_l)
    l_knee = solve_leg(l_hip, l_foot, thigh_len, shin_len, dir_x)
    r_knee = solve_leg(r_hip, r_foot, thigh_len, shin_len, dir_x)

    def make_arm(sh, swing):
        if not is_run:
            el = (sh[0] + swing * 18 * dir_x, sh[1] + 34 - abs(swing) * 4)
            hand = (el[0] + (swing * 16 + 8) * dir_x, el[1] + 28 - max(0, swing) * 8)
        else:
            el = (sh[0] + (swing * 24 - 6) * dir_x, sh[1] + 28 - abs(swing) * 8)
            hand = (el[0] + (swing * 16 + 20) * dir_x, el[1] + 6 - max(0, swing) * 16)
        return el, hand

    l_el, l_hand = make_arm(l_sh, l_arm_s)
    r_el, r_hand = make_arm(r_sh, r_arm_s)

    def draw_chain(p0, p1, p2, col, r_u, r_l, is_leg=False):
        draw_capsule(draw, p0, p1, r_u, col)
        draw_capsule(draw, p1, p2, r_l, col)
        draw.ellipse((p1[0]-3, p1[1]-3, p1[0]+3, p1[1]+3), fill=JOINT_COL)
        if is_leg:
            draw_capsule(draw, p2, (p2[0] + 12*dir_x, p2[1] + 3*iso_y), 7, col)

    if facing_se:
        draw_chain(l_sh, l_el, l_hand, L_DARK, 11, 8)
        draw_chain(l_hip, l_knee, l_foot, L_DARK, 15, 10, True)
        draw_bastion_torso(draw, sh_x, sh_y, pelvis_x, pelvis_y, dir_x, True)
        draw_chain(r_hip, r_knee, r_foot, R_LIMB, 15, 10, True)
        draw_chain(r_sh, r_el, r_hand, R_LIMB, 11, 8)
        # Heavy shoulder pauldrons
        draw.ellipse((r_sh[0]-18, r_sh[1]-16, r_sh[0]+18, r_sh[1]+16), fill=BRASS_COL, outline=(18,20,26), width=2)
    else:
        draw_chain(r_sh, r_el, r_hand, R_DARK, 11, 8)
        draw_chain(r_hip, r_knee, r_foot, R_DARK, 15, 10, True)
        draw_bastion_torso(draw, sh_x, sh_y, pelvis_x, pelvis_y, dir_x, False)
        draw_chain(l_hip, l_knee, l_foot, L_LIMB, 15, 10, True)
        draw_chain(l_sh, l_el, l_hand, L_LIMB, 11, 8)
        draw.ellipse((l_sh[0]-20, l_sh[1]-18, l_sh[0]+20, l_sh[1]+18), fill=CARAPACE_COL, outline=(18,20,26), width=2)


def draw_sword_shield_cell(draw, cx, ground_y, phase, facing_se=True):
    """Row 0: 8-frame Heavy Sword + Siege Tower Shield Attack."""
    dir_x = 1.0 if facing_se else -1.0
    iso_y = 0.28 if facing_se else -0.28
    tw, th = 72, 36
    draw.polygon([(cx, ground_y - th/2), (cx + tw/2, ground_y), (cx, ground_y + th/2), (cx - tw/2, ground_y)], outline=GROUND_COL, fill=(44, 46, 54))

    body_shift = [0, -6, -12, 10, 20, 16, 6, 0][phase] * dir_x
    pelvis_h   = [92, 88, 84, 82, 80, 86, 90, 92][phase]
    lean_x     = [4, -8, -14, 16, 22, 14, 6, 4][phase] * dir_x

    pelvis_x = cx + body_shift * 0.65
    pelvis_y = ground_y - pelvis_h
    sh_x = pelvis_x + lean_x
    sh_y = pelvis_y - 64

    sep = 16 if facing_se else -16
    l_hip = (pelvis_x + sep, pelvis_y - 3)
    r_hip = (pelvis_x - sep, pelvis_y + 3)
    l_sh = (sh_x + sep + 5, sh_y - 2)
    r_sh = (sh_x - sep - 5, sh_y + 2)

    f_step = [18, 14, 10, 32, 38, 34, 24, 18][phase]
    b_step = [-18, -22, -26, -24, -28, -24, -20, -18][phase]
    l_foot = (cx + sep + f_step * dir_x, ground_y - 3 + f_step * iso_y)
    r_foot = (cx - sep + b_step * dir_x, ground_y + 3 + b_step * iso_y)
    l_knee = solve_leg(l_hip, l_foot, 52, 48, dir_x)
    r_knee = solve_leg(r_hip, r_foot, 52, 48, dir_x)

    # Right hand = Heavy Broadsword, Left hand = Heavy Siege Tower Shield
    sw_rel = [(18, 28), (-24, 6), (-32, -24), (24, -18), (48, 12), (36, 34), (24, 30), (18, 28)][phase]
    sw_deg = [15, -140, -120, -45, 22, 62, 38, 18][phase]
    shld_rel = [(26, 16), (32, 8), (36, 4), (22, 16), (14, 20), (18, 18), (24, 16), (26, 16)][phase]

    def place_arm(sh, rel):
        hx = sh[0] + rel[0] * dir_x
        hy = sh[1] + rel[1]
        return ((sh[0] + hx) * 0.5 - 6 * dir_x, (sh[1] + hy) * 0.5 + 10), (hx, hy)

    r_el, r_hand = place_arm(r_sh, sw_rel)
    l_el, l_hand = place_arm(l_sh, shld_rel)

    rad = math.radians(sw_deg)
    tip = (r_hand[0] + math.cos(rad) * 76 * dir_x, r_hand[1] + math.sin(rad) * 76)

    def draw_chain(p0, p1, p2, col, r_u, r_l, is_leg=False):
        draw_capsule(draw, p0, p1, r_u, col)
        draw_capsule(draw, p1, p2, r_l, col)
        draw.ellipse((p1[0]-3, p1[1]-3, p1[0]+3, p1[1]+3), fill=JOINT_COL)
        if is_leg:
            draw_capsule(draw, p2, (p2[0] + 12*dir_x, p2[1] + 3*iso_y), 7, col)

    def draw_shield():
        sx, sy = l_hand
        # Tall armored siege shield
        pts = [
            (sx - 10*dir_x, sy - 42),
            (sx + 16*dir_x, sy - 34),
            (sx + 18*dir_x, sy + 36),
            (sx + 2*dir_x, sy + 48),
            (sx - 12*dir_x, sy + 34),
        ]
        draw.polygon(pts, fill=SHIELD_COL, outline=(18, 20, 26))

    def draw_sword():
        draw.line([r_hand, tip], fill=WEAPON_COL, width=9)
        draw.ellipse((r_hand[0]-6, r_hand[1]-6, r_hand[0]+6, r_hand[1]+6), fill=BRASS_COL)
        if phase in (3, 4, 5):
            arc_pts = []
            sa, ea = (-100, -10) if phase == 3 else ((-75, 45) if phase == 4 else (10, 80))
            for a in range(sa, ea + 1, 10):
                ar = math.radians(a)
                arc_pts.append((sh_x + (30 + math.cos(ar)*64)*dir_x, sh_y + 10 + math.sin(ar)*58))
            draw.line(arc_pts, fill=ARC_COL, width=11 if phase == 4 else 5)

    if facing_se:
        draw_chain(l_sh, l_el, l_hand, L_DARK, 11, 8)
        draw_shield()
        draw_chain(l_hip, l_knee, l_foot, L_DARK, 15, 10, True)
        draw_bastion_torso(draw, sh_x, sh_y, pelvis_x, pelvis_y, dir_x, True)
        draw_chain(r_hip, r_knee, r_foot, R_LIMB, 15, 10, True)
        draw_sword()
        draw_chain(r_sh, r_el, r_hand, R_LIMB, 11, 8)
    else:
        draw_sword()
        draw_chain(r_sh, r_el, r_hand, R_DARK, 11, 8)
        draw_chain(r_hip, r_knee, r_foot, R_DARK, 15, 10, True)
        draw_bastion_torso(draw, sh_x, sh_y, pelvis_x, pelvis_y, dir_x, False)
        draw_chain(l_hip, l_knee, l_foot, L_LIMB, 15, 10, True)
        draw_chain(l_sh, l_el, l_hand, L_LIMB, 11, 8)
        draw_shield()


def draw_glaive_cell(draw, cx, ground_y, phase, facing_se=True):
    """Row 1: 8-frame Two-Handed Glaive Sweeping Cleave Attack."""
    dir_x = 1.0 if facing_se else -1.0
    iso_y = 0.28 if facing_se else -0.28
    tw, th = 72, 36
    draw.polygon([(cx, ground_y - th/2), (cx + tw/2, ground_y), (cx, ground_y + th/2), (cx - tw/2, ground_y)], outline=GROUND_COL, fill=(44, 46, 54))

    body_shift = [0, -8, -14, 12, 22, 18, 8, 0][phase] * dir_x
    pelvis_h   = [92, 86, 82, 80, 78, 84, 90, 92][phase]
    lean_x     = [4, -10, -16, 18, 24, 16, 6, 4][phase] * dir_x

    pelvis_x = cx + body_shift * 0.65
    pelvis_y = ground_y - pelvis_h
    sh_x = pelvis_x + lean_x
    sh_y = pelvis_y - 64

    sep = 16 if facing_se else -16
    l_hip = (pelvis_x + sep, pelvis_y - 3)
    r_hip = (pelvis_x - sep, pelvis_y + 3)
    l_sh = (sh_x + sep + 5, sh_y - 2)
    r_sh = (sh_x - sep - 5, sh_y + 2)

    f_step = [18, 12, 8, 34, 42, 38, 24, 18][phase]
    b_step = [-18, -24, -28, -26, -30, -26, -20, -18][phase]
    l_foot = (cx + sep + f_step * dir_x, ground_y - 3 + f_step * iso_y)
    r_foot = (cx - sep + b_step * dir_x, ground_y + 3 + b_step * iso_y)
    l_knee = solve_leg(l_hip, l_foot, 52, 48, dir_x)
    r_knee = solve_leg(r_hip, r_foot, 52, 48, dir_x)

    # Two-handed grip on long glaive shaft: front hand (left) and rear hand (right) move together
    # Dramatic overhead-back windup (F1, F2) -> explosive downward-forward sweeping cleave (F3, F4, F5) -> guard (F6, F7)
    r_rel = [(8, 28), (4, 8), (-2, -26), (12, -22), (24, 10), (16, 28), (12, 28), (8, 28)][phase]
    l_rel = [(22, 10), (-14, -14), (-26, -34), (34, -18), (48, 24), (38, 42), (30, 24), (22, 10)][phase]

    def place_arm(sh, rel):
        hx = sh[0] + rel[0] * dir_x
        hy = sh[1] + rel[1]
        return ((sh[0] + hx) * 0.5 - 6 * dir_x, (sh[1] + hy) * 0.5 + 10), (hx, hy)

    r_el, r_hand = place_arm(r_sh, r_rel)
    l_el, l_hand = place_arm(l_sh, l_rel)

    # Glaive axis runs from rear hand through front hand to big cleaver blade tip
    dx_g = l_hand[0] - r_hand[0]
    dy_g = l_hand[1] - r_hand[1]
    glen = max(1.0, math.hypot(dx_g, dy_g))
    ux, uy = dx_g / glen, dy_g / glen
    butt = (r_hand[0] - ux * 46, r_hand[1] - uy * 46)
    blade_base = (l_hand[0] + ux * 28, l_hand[1] + uy * 28)
    blade_tip = (l_hand[0] + ux * 74, l_hand[1] + uy * 74)

    def draw_chain(p0, p1, p2, col, r_u, r_l, is_leg=False):
        draw_capsule(draw, p0, p1, r_u, col)
        draw_capsule(draw, p1, p2, r_l, col)
        draw.ellipse((p1[0]-3, p1[1]-3, p1[0]+3, p1[1]+3), fill=JOINT_COL)
        if is_leg:
            draw_capsule(draw, p2, (p2[0] + 12*dir_x, p2[1] + 3*iso_y), 7, col)

    def draw_glaive():
        draw.line([butt, blade_base], fill=(138, 92, 58), width=5)
        draw.line([blade_base, blade_tip], fill=WEAPON_COL, width=11)
        if phase in (3, 4, 5):
            arc_pts = []
            sa, ea = (-110, -15) if phase == 3 else ((-80, 50) if phase == 4 else (15, 85))
            for a in range(sa, ea + 1, 10):
                ar = math.radians(a)
                arc_pts.append((sh_x + (32 + math.cos(ar)*72)*dir_x, sh_y + 12 + math.sin(ar)*64))
            draw.line(arc_pts, fill=ARC_COL, width=12 if phase == 4 else 6)

    if facing_se:
        draw_chain(l_sh, l_el, l_hand, L_DARK, 11, 8)
        draw_chain(l_hip, l_knee, l_foot, L_DARK, 15, 10, True)
        draw_bastion_torso(draw, sh_x, sh_y, pelvis_x, pelvis_y, dir_x, True)
        draw_chain(r_hip, r_knee, r_foot, R_LIMB, 15, 10, True)
        draw_glaive()
        draw_chain(r_sh, r_el, r_hand, R_LIMB, 11, 8)
    else:
        draw_glaive()
        draw_chain(r_sh, r_el, r_hand, R_DARK, 11, 8)
        draw_chain(r_hip, r_knee, r_foot, R_DARK, 15, 10, True)
        draw_bastion_torso(draw, sh_x, sh_y, pelvis_x, pelvis_y, dir_x, False)
        draw_chain(l_hip, l_knee, l_foot, L_LIMB, 15, 10, True)
        draw_chain(l_sh, l_el, l_hand, L_LIMB, 11, 8)


def build_all():
    for suffix, f_se in [("se", True), ("nw", False)]:
        im_wr = Image.new("RGB", (W, H), BG)
        d_wr = ImageDraw.Draw(im_wr)
        for c in range(COLS):
            cx = c * CELL_W + CELL_W // 2
            draw_walk_run_cell(d_wr, cx, CELL_H - 48, c, False, f_se)
            draw_walk_run_cell(d_wr, cx, 2 * CELL_H - 48, c, True, f_se)
        im_wr.save(f"/tmp/bastion_guide_{suffix}_walk_run.png")

        im_cb = Image.new("RGB", (W, H), BG)
        d_cb = ImageDraw.Draw(im_cb)
        for c in range(COLS):
            cx = c * CELL_W + CELL_W // 2
            draw_sword_shield_cell(d_cb, cx, CELL_H - 48, c, f_se)
            draw_glaive_cell(d_cb, cx, 2 * CELL_H - 48, c, f_se)
        im_cb.save(f"/tmp/bastion_guide_{suffix}_combat.png")
    print("Generated all 4 Bastion heavyweight isometric pose guides!")


build_all()
