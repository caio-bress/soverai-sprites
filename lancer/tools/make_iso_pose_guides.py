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
# Left side = Cyan/Blue, Right side = Warm Orange/Coral
L_LIMB = (56, 189, 248)
L_DARK = (14, 116, 144)
R_LIMB = (251, 146, 60)
R_DARK = (194, 65, 12)
JOINT_COL = (248, 248, 252)


def draw_capsule(draw: ImageDraw.ImageDraw, p0, p1, radius, fill, outline=(18, 20, 26)):
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


def draw_mannequin_cell(draw, cx, ground_y, phase_idx, is_run, facing_se=True):
    dir_x = 1.0 if facing_se else -1.0
    iso_y_slope = 0.28 if facing_se else -0.28

    # Isometric ground diamond
    tw, th = 64, 32
    diamond = [
        (cx, ground_y - th / 2),
        (cx + tw / 2, ground_y),
        (cx, ground_y + th / 2),
        (cx - tw / 2, ground_y),
    ]
    draw.polygon(diamond, outline=GROUND_COL, fill=(44, 46, 54))

    thigh_len, shin_len = 54.0, 52.0  # total 106px

    if not is_run:
        # 8-FRAME WALK CYCLE (Richard Williams standard):
        # 0: L-Contact | 1: L-Down | 2: L-Passing | 3: L-Up | 4: R-Contact | 5: R-Down | 6: R-Passing | 7: R-Up
        pelvis_h = [96, 88, 101, 105, 96, 88, 101, 105][phase_idx]
        l_x = [34,  12, -5, -22, -32, -26,  4,  26][phase_idx]
        l_l = [0,   0,  0,   3,    6,  14, 18,  10][phase_idx]
        r_x = [-32, -26,  4,  26, 34,  12, -5, -22][phase_idx]
        r_l = [6,   14, 18,  10,  0,   0,  0,   3][phase_idx]

        pelvis_x = cx - 2 * dir_x
        shoulder_x = cx + 4 * dir_x
        torso_len = 66
        # Arms swing opposite to legs
        l_arm_s = [-0.85, -0.45, 0.0, 0.45, 0.85, 0.45, 0.0, -0.45][phase_idx]
        r_arm_s = [0.85, 0.45, 0.0, -0.45, -0.85, -0.45, 0.0, 0.45][phase_idx]
    else:
        # 8-FRAME RUN CYCLE:
        # 0: L-Contact | 1: L-Squash | 2: L-Drive | 3: Flight A | 4: R-Contact | 5: R-Squash | 6: R-Drive | 7: Flight B
        pelvis_h = [92, 82, 98, 114, 92, 82, 98, 114][phase_idx]
        l_x = [36,  8, -32, -46, -34, -10, 26,  44][phase_idx]
        l_l = [0,   0,   4,  28,  24,  30, 26,  20][phase_idx]
        r_x = [-34, -10, 26, 44,  36,   8, -32, -46][phase_idx]
        r_l = [24,  30, 26, 20,   0,   0,   4,  28][phase_idx]

        pelvis_x = cx - 9 * dir_x
        shoulder_x = cx + 13 * dir_x
        torso_len = 62
        l_arm_s = [-1.05, -0.55, 0.25, 1.0, 1.05, 0.55, -0.25, -1.0][phase_idx]
        r_arm_s = [1.05, 0.55, -0.25, -1.0, -1.05, -0.55, 0.25, 1.0][phase_idx]

    pelvis_y = ground_y - pelvis_h
    shoulder_y = pelvis_y - torso_len
    head_x = shoulder_x + (5 if is_run else 1) * dir_x
    head_y = shoulder_y - 25

    sep = 10 if facing_se else -10
    l_hip = (pelvis_x + sep, pelvis_y - 3)
    r_hip = (pelvis_x - sep, pelvis_y + 3)
    l_sh = (shoulder_x + sep + 2, shoulder_y - 3)
    r_sh = (shoulder_x - sep - 2, shoulder_y + 3)

    l_foot = (cx + sep + l_x * dir_x, ground_y - 3 + l_x * iso_y_slope - l_l)
    r_foot = (cx - sep + r_x * dir_x, ground_y + 3 + r_x * iso_y_slope - r_l)

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

    if facing_se:
        far_arm = (l_sh, l_el, l_hand, L_DARK)
        far_leg = (l_hip, l_knee, l_foot, L_DARK)
        near_leg = (r_hip, r_knee, r_foot, R_LIMB)
        near_arm = (r_sh, r_el, r_hand, R_LIMB)
    else:
        far_arm = (r_sh, r_el, r_hand, R_DARK)
        far_leg = (r_hip, r_knee, r_foot, R_DARK)
        near_leg = (l_hip, l_knee, l_foot, L_LIMB)
        near_arm = (l_sh, l_el, l_hand, L_LIMB)

    def draw_chain(p0, p1, p2, col, r_up, r_low, is_leg=False):
        draw_capsule(draw, p0, p1, r_up, col)
        draw_capsule(draw, p1, p2, r_low, col)
        draw.ellipse((p1[0]-3, p1[1]-3, p1[0]+3, p1[1]+3), fill=JOINT_COL)
        if is_leg:
            toe = (p2[0] + 12 * dir_x, p2[1] + 3 * iso_y_slope)
            draw_capsule(draw, p2, toe, 6, col)

    draw_chain(*far_arm[:3], far_arm[3], 8, 6, is_leg=False)
    draw_chain(*far_leg[:3], far_leg[3], 11, 8, is_leg=True)

    draw_capsule(draw, (shoulder_x, shoulder_y), (pelvis_x, pelvis_y), 19, TORSO_COL)
    if facing_se:
        draw.ellipse((head_x - 16, head_y - 18, head_x + 16, head_y + 18), fill=HEAD_COL, outline=(18, 20, 26), width=2)
        draw.line([(head_x + 4, head_y - 2), (head_x + 14, head_y + 1)], fill=(30, 30, 40), width=3)
    else:
        draw.ellipse((shoulder_x - 9, shoulder_y + 12, shoulder_x + 9, shoulder_y + 30), outline=(90, 220, 220), width=3)
        draw.ellipse((head_x - 16, head_y - 18, head_x + 16, head_y + 18), fill=(195, 200, 212), outline=(18, 20, 26), width=2)

    draw_chain(*near_leg[:3], near_leg[3], 11, 8, is_leg=True)
    draw_chain(*near_arm[:3], near_arm[3], 8, 6, is_leg=False)


def build_guide(out_path, facing_se=True):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    for r, is_run in enumerate([False, True]):
        ground_y = r * CELL_H + CELL_H - 48
        for c in range(COLS):
            cx = c * CELL_W + CELL_W // 2
            draw_mannequin_cell(draw, cx, ground_y, c, is_run=is_run, facing_se=facing_se)
    img.save(out_path)
    print("Saved refined pose guide:", out_path)


build_guide("/tmp/iso_pose_guide_se_2x8.png", facing_se=True)
build_guide("/tmp/iso_pose_guide_nw_2x8.png", facing_se=False)
