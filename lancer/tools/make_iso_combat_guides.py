import math
from PIL import Image, ImageDraw

W, H = 1376, 768
COLS, ROWS = 8, 2
CELL_W = W // COLS  # 172
CELL_H = H // ROWS  # 384

BG = (36, 36, 38)
GROUND_COL = (68, 72, 86)
HEAD_COL = (228, 232, 240)
TORSO_COL = (182, 188, 200)
L_LIMB = (56, 189, 248)
L_DARK = (14, 116, 144)
R_LIMB = (251, 146, 60)
R_DARK = (194, 65, 12)
JOINT_COL = (248, 248, 252)
SWORD_COL = (230, 245, 255)
ARC_COL = (90, 235, 255)
BOW_COL = (250, 204, 21)
ARROW_COL = (125, 249, 255)


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


def draw_sword_cell(draw, cx, ground_y, phase, facing_se=True):
    """8-frame Sword Attack: 0 Ready | 1 Windup1 | 2 Peak Coil | 3 Lunge | 4 SLASH IMPACT | 5 Follow-through | 6 Recover1 | 7 Recover2"""
    dir_x = 1.0 if facing_se else -1.0
    iso_y = 0.28 if facing_se else -0.28

    # Isometric ground diamond
    tw, th = 64, 32
    draw.polygon([(cx, ground_y - th/2), (cx + tw/2, ground_y), (cx, ground_y + th/2), (cx - tw/2, ground_y)], outline=GROUND_COL, fill=(44, 46, 54))

    # Body lunges slightly back on windup (1,2) and explodes forward on strike (3,4,5)
    body_shift = [0, -8, -14, 12, 22, 18, 8, 2][phase] * dir_x
    pelvis_h   = [98, 92, 88, 86, 84, 90, 95, 98][phase]
    lean_x     = [4, -10, -16, 18, 24, 16, 8, 4][phase] * dir_x

    pelvis_x = cx + body_shift * 0.65
    pelvis_y = ground_y - pelvis_h
    sh_x = pelvis_x + lean_x
    sh_y = pelvis_y - 64
    head_x = sh_x + lean_x * 0.22
    head_y = sh_y - 24

    sep = 11 if facing_se else -11
    l_hip = (pelvis_x + sep, pelvis_y - 3)
    r_hip = (pelvis_x - sep, pelvis_y + 3)
    l_sh = (sh_x + sep + 2, sh_y - 3)
    r_sh = (sh_x - sep - 2, sh_y + 3)

    # Stance feet: front foot lunges forward on frames 3..5
    f_step = [18, 12, 8, 34, 42, 38, 26, 20][phase]
    b_step = [-18, -24, -28, -26, -30, -26, -22, -18][phase]
    l_foot = (cx + sep + f_step * dir_x, ground_y - 3 + f_step * iso_y)
    r_foot = (cx - sep + b_step * dir_x, ground_y + 3 + b_step * iso_y)

    l_knee = solve_leg(l_hip, l_foot, 54, 52, dir_x)
    r_knee = solve_leg(r_hip, r_foot, 54, 52, dir_x)

    # Sword hand (Right hand = near hand in SE, far hand in NW) & Off hand (Left hand)
    # Relative to shoulder (dx*dir_x, dy)
    sw_hand_rel = [
        (20, 26),    # 0 Ready
        (-22, 4),    # 1 Windup back
        (-30, -24),  # 2 Peak coil overhead/back
        (26, -14),   # 3 Slash starting high-front
        (50, 12),    # 4 IMPACT extended forward-down
        (36, 34),    # 5 Follow-through low-front
        (26, 30),    # 6 Recovering
        (22, 26),    # 7 Back to ready
    ][phase]

    # Sword tip direction angle (in degrees, 0=right, -90=up, +90=down, mirrored if NW)
    sw_angle_deg = [20, -145, -125, -45, 22, 62, 40, 24][phase]
    sw_len = 74

    # Off hand balances opposite
    off_hand_rel = [
        (16, 18),
        (24, 10),
        (28, 6),
        (-16, 18),
        (-26, 16),
        (-22, 22),
        (-6, 20),
        (10, 18),
    ][phase]

    def place_arm(sh, rel):
        hx = sh[0] + rel[0] * dir_x
        hy = sh[1] + rel[1]
        ex = (sh[0] + hx) * 0.5 - 6 * dir_x
        ey = (sh[1] + hy) * 0.5 + 10
        return (ex, ey), (hx, hy)

    r_el, r_hand = place_arm(r_sh, sw_hand_rel)
    l_el, l_hand = place_arm(l_sh, off_hand_rel)

    rad = math.radians(sw_angle_deg)
    tip = (r_hand[0] + math.cos(rad) * sw_len * dir_x, r_hand[1] + math.sin(rad) * sw_len)

    def draw_chain(p0, p1, p2, col, r_u, r_l, is_leg=False):
        draw_capsule(draw, p0, p1, r_u, col)
        draw_capsule(draw, p1, p2, r_l, col)
        draw.ellipse((p1[0]-3, p1[1]-3, p1[0]+3, p1[1]+3), fill=JOINT_COL)
        if is_leg:
            draw_capsule(draw, p2, (p2[0] + 12*dir_x, p2[1] + 3*iso_y), 6, col)

    def draw_sword():
        draw.line([r_hand, tip], fill=SWORD_COL, width=6)
        draw.line([r_hand, tip], fill=(120, 210, 255), width=2)
        # Crossguard
        gx, gy = r_hand
        draw.ellipse((gx-5, gy-5, gx+5, gy+5), fill=BOW_COL)
        # Slash arc smear on frames 3, 4, 5!
        if phase in (3, 4, 5):
            arc_pts = []
            start_a, end_a = (-100, -10) if phase == 3 else ((-75, 45) if phase == 4 else (10, 80))
            for a_deg in range(start_a, end_a + 1, 10):
                ar = math.radians(a_deg)
                ax = sh_x + (32 + math.cos(ar) * 62) * dir_x
                ay = sh_y + 10 + math.sin(ar) * 56
                arc_pts.append((ax, ay))
            if len(arc_pts) >= 2:
                draw.line(arc_pts, fill=ARC_COL, width=10 if phase == 4 else 5)

    if facing_se:
        draw_chain(l_sh, l_el, l_hand, L_DARK, 8, 6)
        draw_chain(l_hip, l_knee, l_foot, L_DARK, 11, 8, True)
        draw_capsule(draw, (sh_x, sh_y), (pelvis_x, pelvis_y), 19, TORSO_COL)
        draw.ellipse((head_x-16, head_y-18, head_x+16, head_y+18), fill=HEAD_COL, outline=(18,20,26), width=2)
        draw.line([(head_x+4, head_y-2), (head_x+14, head_y+1)], fill=(30,30,40), width=3)
        draw_chain(r_hip, r_knee, r_foot, R_LIMB, 11, 8, True)
        draw_sword()
        draw_chain(r_sh, r_el, r_hand, R_LIMB, 8, 6)
    else:
        draw_sword()
        draw_chain(r_sh, r_el, r_hand, R_DARK, 8, 6)
        draw_chain(r_hip, r_knee, r_foot, R_DARK, 11, 8, True)
        draw_capsule(draw, (sh_x, sh_y), (pelvis_x, pelvis_y), 19, TORSO_COL)
        draw.ellipse((sh_x-9, sh_y+12, sh_x+9, sh_y+30), outline=(90,220,220), width=3)
        draw.ellipse((head_x-16, head_y-18, head_x+16, head_y+18), fill=(195,200,212), outline=(18,20,26), width=2)
        draw_chain(l_hip, l_knee, l_foot, L_LIMB, 11, 8, True)
        draw_chain(l_sh, l_el, l_hand, L_LIMB, 8, 6)


def draw_bow_cell(draw, cx, ground_y, phase, facing_se=True):
    """8-frame Bow Attack: 0 Ready | 1 Raise & Nock | 2 Half Draw | 3 FULL DRAW | 4 RELEASE/LOOSE | 5 Recoil | 6 Lower | 7 Recover"""
    dir_x = 1.0 if facing_se else -1.0
    iso_y = 0.28 if facing_se else -0.28

    tw, th = 64, 32
    draw.polygon([(cx, ground_y - th/2), (cx + tw/2, ground_y), (cx, ground_y + th/2), (cx - tw/2, ground_y)], outline=GROUND_COL, fill=(44, 46, 54))

    # Archer settles into firm wide stance while drawing (2,3), subtle recoil on release (4,5)
    body_shift = [0, -2, -6, -8, -4, -3, -1, 0][phase] * dir_x
    pelvis_h   = [98, 95, 92, 91, 93, 95, 97, 98][phase]
    lean_x     = [2, 0, -4, -6, 2, 0, 1, 2][phase] * dir_x

    pelvis_x = cx + body_shift
    pelvis_y = ground_y - pelvis_h
    sh_x = pelvis_x + lean_x
    sh_y = pelvis_y - 65
    head_x = sh_x + 2 * dir_x
    head_y = sh_y - 24

    sep = 11 if facing_se else -11
    l_hip = (pelvis_x + sep, pelvis_y - 3)
    r_hip = (pelvis_x - sep, pelvis_y + 3)
    l_sh = (sh_x + sep + 2, sh_y - 3)
    r_sh = (sh_x - sep - 2, sh_y + 3)

    f_step = [18, 22, 24, 24, 24, 22, 20, 18][phase]
    b_step = [-18, -22, -24, -24, -24, -22, -20, -18][phase]
    l_foot = (cx + sep + f_step * dir_x, ground_y - 3 + f_step * iso_y)
    r_foot = (cx - sep + b_step * dir_x, ground_y + 3 + b_step * iso_y)

    l_knee = solve_leg(l_hip, l_foot, 54, 52, dir_x)
    r_knee = solve_leg(r_hip, r_foot, 54, 52, dir_x)

    # Bow hand = Left hand (extended forward toward target); String hand = Right hand (pulls back near cheek)
    bow_hand_rel = [
        (24, 22),   # 0 Ready low
        (40, 2),    # 1 Raised aiming
        (46, -2),   # 2 Half draw
        (48, -3),   # 3 FULL DRAW
        (46, -7),   # 4 RELEASE recoil slightly up
        (42, 0),    # 5 Follow-through
        (32, 14),   # 6 Lowering
        (24, 22),   # 7 Ready
    ][phase]

    str_hand_rel = [
        (10, 24),   # 0 Ready
        (28, 4),    # 1 Nocking at bow
        (8, -2),    # 2 Half draw
        (-12, -5),  # 3 FULL DRAW pulled to cheek/shoulder!
        (-24, -8),  # 4 RELEASE hand snaps back!
        (-18, 4),   # 5 Follow-through
        (0, 18),    # 6 Relaxing
        (10, 24),   # 7 Ready
    ][phase]

    def place_arm(sh, rel, bend_up=False):
        hx = sh[0] + rel[0] * dir_x
        hy = sh[1] + rel[1]
        ex = (sh[0] + hx) * 0.5 - (10 if bend_up else 4) * dir_x
        ey = (sh[1] + hy) * 0.5 + (-6 if bend_up else 8)
        return (ex, ey), (hx, hy)

    l_el, l_hand = place_arm(l_sh, bow_hand_rel, bend_up=False)
    r_el, r_hand = place_arm(r_sh, str_hand_rel, bend_up=(phase in (2, 3, 4)))

    def draw_chain(p0, p1, p2, col, r_u, r_l, is_leg=False):
        draw_capsule(draw, p0, p1, r_u, col)
        draw_capsule(draw, p1, p2, r_l, col)
        draw.ellipse((p1[0]-3, p1[1]-3, p1[0]+3, p1[1]+3), fill=JOINT_COL)
        if is_leg:
            draw_capsule(draw, p2, (p2[0] + 12*dir_x, p2[1] + 3*iso_y), 6, col)

    def draw_bow_and_arrow():
        bx, by = l_hand
        # Bow curves backward more at draw phases 2 & 3
        flex = [6, 8, 16, 22, 8, 6, 6, 6][phase]
        top_tip = (bx - flex * dir_x, by - 42)
        bot_tip = (bx - flex * dir_x, by + 42)
        # Recurve bow arc (5-point polyline)
        bow_pts = [
            top_tip,
            (bx + 6 * dir_x, by - 22),
            (bx + 10 * dir_x, by),
            (bx + 6 * dir_x, by + 22),
            bot_tip,
        ]
        draw.line(bow_pts, fill=BOW_COL, width=5)

        # Bowstring
        if phase in (1, 2, 3):
            draw.line([top_tip, r_hand, bot_tip], fill=(220, 230, 240), width=2)
            # Nocked glowing arrow pointing forward
            a_tip = (bx + (24 if phase == 3 else 20) * dir_x, by + (6 * iso_y))
            draw.line([r_hand, a_tip], fill=ARROW_COL, width=3)
            draw.ellipse((a_tip[0]-4, a_tip[1]-4, a_tip[0]+4, a_tip[1]+4), fill=(220, 255, 255))
        else:
            draw.line([top_tip, bot_tip], fill=(200, 210, 225), width=2)
            if phase == 4:
                # Released glowing energy arrow streaking forward!
                s0 = (bx + 12 * dir_x, by)
                s1 = (bx + 54 * dir_x, by + 10 * iso_y)
                draw.line([s0, s1], fill=ARROW_COL, width=4)
                draw.ellipse((s1[0]-4, s1[1]-4, s1[0]+4, s1[1]+4), fill=(255, 255, 255))

    if facing_se:
        draw_chain(l_sh, l_el, l_hand, L_DARK, 8, 6)
        draw_chain(l_hip, l_knee, l_foot, L_DARK, 11, 8, True)
        draw_capsule(draw, (sh_x, sh_y), (pelvis_x, pelvis_y), 19, TORSO_COL)
        draw.ellipse((head_x-16, head_y-18, head_x+16, head_y+18), fill=HEAD_COL, outline=(18,20,26), width=2)
        draw.line([(head_x+4, head_y-2), (head_x+14, head_y+1)], fill=(30,30,40), width=3)
        draw_chain(r_hip, r_knee, r_foot, R_LIMB, 11, 8, True)
        draw_bow_and_arrow()
        draw_chain(r_sh, r_el, r_hand, R_LIMB, 8, 6)
    else:
        draw_bow_and_arrow()
        draw_chain(r_sh, r_el, r_hand, R_DARK, 8, 6)
        draw_chain(r_hip, r_knee, r_foot, R_DARK, 11, 8, True)
        draw_capsule(draw, (sh_x, sh_y), (pelvis_x, pelvis_y), 19, TORSO_COL)
        draw.ellipse((sh_x-9, sh_y+12, sh_x+9, sh_y+30), outline=(90,220,220), width=3)
        draw.ellipse((head_x-16, head_y-18, head_x+16, head_y+18), fill=(195,200,212), outline=(18,20,26), width=2)
        draw_chain(l_hip, l_knee, l_foot, L_LIMB, 11, 8, True)
        draw_chain(l_sh, l_el, l_hand, L_LIMB, 8, 6)


def build_combat_guide(out_path, facing_se=True):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    for c in range(COLS):
        cx = c * CELL_W + CELL_W // 2
        draw_sword_cell(draw, cx, CELL_H - 48, c, facing_se=facing_se)
        draw_bow_cell(draw, cx, 2 * CELL_H - 48, c, facing_se=facing_se)
    img.save(out_path)
    print("Saved combat pose guide:", out_path)


build_combat_guide("/tmp/iso_combat_guide_se_2x8.png", facing_se=True)
build_combat_guide("/tmp/iso_combat_guide_nw_2x8.png", facing_se=False)
