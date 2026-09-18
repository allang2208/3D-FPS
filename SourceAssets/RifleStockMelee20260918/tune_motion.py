"""动作表数值校核：把枪根刚体搬运换算成「枪托/枪口在画面里的位置」。

用途：改 author_quickcombat.py 的 MOTION 之前先在这里看屏幕坐标，
不用每次都开 Blender 渲染。相机按视模视点（骨架头骨原点，18 mm≈90° 水平 FOV）。

坐标（armature 空间，米）：+Y 前 / +X 右 / +Z 上。
旋转与作者源一致：R = Rx(pitch)·Rz(yaw)·Ry(roll)，delta = T(pivot+off)·R·T(-pivot)。
"""
import math

# 取自 M4_Hand_MAT_Editable.blend 的 M4_idle（inspect_grip.py 读数）
PIVOT = (0.0992, 0.0361, -0.1463)     # 右腕
BUTT = (0.058, -0.116, -0.098)        # 枪托底
MUZZLE = (0.051, 0.594, -0.026)       # 枪口
LEFT_HAND = (0.012, 0.2886, -0.1043)  # 左手（护木）——横向横扫时的支点候选
CAMERA = (0.0, -0.02, 0.0)
HALF_H = 45.0                          # 水平半 FOV（18 mm / 36 mm 传感器）
HALF_V = math.degrees(math.atan(10.125 / 18.0))


def rot(pitch, yaw, roll):
    p, y, r = (math.radians(a) for a in (pitch, yaw, roll))
    def rx(v):
        x, yy, z = v
        return (x, yy * math.cos(p) - z * math.sin(p), yy * math.sin(p) + z * math.cos(p))
    def rz(v):
        x, yy, z = v
        return (x * math.cos(y) - yy * math.sin(y), x * math.sin(y) + yy * math.cos(y), z)
    def ry(v):
        x, yy, z = v
        return (x * math.cos(r) + z * math.sin(r), yy, -x * math.sin(r) + z * math.cos(r))
    return lambda v: rx(rz(ry(v)))


def screen(point):
    x, y, z = (point[i] - CAMERA[i] for i in range(3))
    azimuth = math.degrees(math.atan2(x, y))
    elevation = math.degrees(math.atan2(z, math.hypot(x, y)))
    u = 0.5 + 0.5 * math.tan(math.radians(azimuth)) / math.tan(math.radians(HALF_H))
    v = 0.5 - 0.5 * math.tan(math.radians(elevation)) / math.tan(math.radians(HALF_V))
    inside = '屏内' if (0.0 <= u <= 1.0 and 0.0 <= v <= 1.0) else '出画'
    return u, v, inside, math.hypot(x, y, z)


def evaluate(table, pivot=PIVOT):
    print(' 支点=%s' % (pivot,))
    print(' t      butt(u,v) 出/入 | muzzle(u,v) | butt距离 muzzle距离')
    for i, t in enumerate(table['times']):
        pitch, yaw, roll = table['pitch'][i], table['yaw'][i], table['roll'][i]
        off = table['offset'][i]
        apply = rot(pitch, yaw, roll)
        def move(p):
            rotated = apply(tuple(p[k] - pivot[k] for k in range(3)))
            return tuple(rotated[k] + pivot[k] + off[k] for k in range(3))
        bu, bv, bin_, bd = screen(move(BUTT))
        mu, mv, min_, md = screen(move(MUZZLE))
        print(' %.2f   (%.2f,%.2f) %s | (%.2f,%.2f) %s | %.2f m  %.2f m'
              % (t, bu, bv, bin_, mu, mv, min_, bd, md))


# C 版：横向横扫（用户 2026-09-18 指正「是横向枪托攻击」）。
# 支点在右腕，俯仰基本不动、偏航做大：整枪在水平面内横扫，
# 枪口自画面左侧扫到右侧，枪托（贴镜头、本来就在画面外下方）反向扫过。
MOTION_C = {
    'times': [0.00, 0.058, 0.200, 0.260, 0.348, 0.383, 0.511, 0.72],
    'pitch': [0.0, 2.0, 5.0, 5.0, -3.0, -4.0, -3.0, 0.0],
    # 蓄势把枪口甩到画面左侧（yaw 正 = 枪口向左），接触时正好扫过画面中心，跟随继续向右。
    'yaw': [0.0, 24.0, 46.0, 46.0, -12.0, -22.0, -36.0, 0.0],
    'roll': [0.0, 4.0, 10.0, 11.0, -8.0, -10.0, -8.0, 0.0],
    'offset': [(0.0, 0.0, 0.0), (0.01, 0.05, 0.01), (0.02, 0.12, 0.02), (0.02, 0.12, 0.02),
               (0.00, 0.18, 0.00), (-0.01, 0.19, 0.00), (-0.02, 0.20, 0.00), (0.0, 0.0, 0.0)],
}


MOTION_B = {
    'times': [0.00, 0.05, 0.16, 0.21, 0.30, 0.33, 0.44, 0.62],
    'pitch': [0.0, -6.0, -70.0, -74.0, -78.0, -78.0, -70.0, 0.0],
    'yaw': [0.0, 2.0, 6.0, 2.0, -18.0, -24.0, -30.0, 0.0],
    'roll': [0.0, 2.0, 8.0, 4.0, -18.0, -22.0, -26.0, 0.0],
    'offset': [(0.0, 0.0, 0.0), (0.02, 0.20, 0.00), (0.06, 0.34, 0.02), (0.06, 0.35, 0.02),
               (0.02, 0.36, 0.02), (0.01, 0.37, 0.02), (0.00, 0.38, 0.02), (0.0, 0.0, 0.0)],
}

def solve(u_target, v_target, pitch_range, yaw_range, roll_range, fwd_range, right_range, up_range,
          want_muzzle_offscreen=True, min_dist=0.30):
    """按目标屏幕位置反解 (pitch, yaw, roll, offset)，并打印最优解。"""
    best = None
    step_rot, step_pos = 4.0, 0.02
    for pitch in frange(*pitch_range, step_rot):
        for yaw in frange(*yaw_range, step_rot):
            for roll in frange(*roll_range, step_rot):
                apply = rot(pitch, yaw, roll)
                base_butt = apply(tuple(BUTT[k] - PIVOT[k] for k in range(3)))
                base_muzzle = apply(tuple(MUZZLE[k] - PIVOT[k] for k in range(3)))
                for right in frange(*right_range, step_pos):
                    for fwd in frange(*fwd_range, step_pos):
                        for up in frange(*up_range, step_pos):
                            off = (right, fwd, up)
                            butt = tuple(base_butt[k] + PIVOT[k] + off[k] for k in range(3))
                            muzzle = tuple(base_muzzle[k] + PIVOT[k] + off[k] for k in range(3))
                            bu, bv, bin_, bd = screen(butt)
                            mu, mv, min_, md = screen(muzzle)
                            score = abs(bu - u_target) + abs(bv - v_target)
                            if bd < min_dist:
                                score += (min_dist - bd) * 20.0
                            if bd > 0.9:
                                score += (bd - 0.9) * 6.0
                            if want_muzzle_offscreen and min_ == '屏内':
                                score += 0.6
                            if not want_muzzle_offscreen and min_ == '出画':
                                score += 0.3
                            score += 0.35 * (abs(right) + abs(fwd) + abs(up))
                            if best is None or score < best[0]:
                                best = (score, pitch, yaw, roll, off, (bu, bv, bin_, bd), (mu, mv, min_, md))
    _, pitch, yaw, roll, off, bs, ms = best
    print('target(%.2f,%.2f) -> pitch=%.0f yaw=%.0f roll=%.0f off=(%.2f,%.2f,%.2f)'
          % (u_target, v_target, pitch, yaw, roll, off[0], off[1], off[2]))
    print('    butt=(%.2f,%.2f) %s %.2f m | muzzle=(%.2f,%.2f) %s %.2f m'
          % (bs[0], bs[1], bs[2], bs[3], ms[0], ms[1], ms[2], ms[3]))
    return pitch, yaw, roll, off


def frange(start, stop, step):
    values, value, count = [], start, 0
    while value <= stop + 1e-9 and count < 200:
        values.append(round(value, 4))
        value = start + (count + 1) * step
        count += 1
    return values


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'solve':
        # 参考视频里的枪托屏幕轨迹（30 fps 原生帧读数）
        solve(0.42, 0.85, (-50, -10), (-30, 20), (-40, 20), (-0.06, 0.20), (-0.04, 0.10), (-0.06, 0.04))
        solve(0.58, 0.60, (-80, -30), (-30, 20), (-40, 20), (0.06, 0.24), (-0.06, 0.08), (-0.02, 0.08))
        solve(0.42, 0.52, (-80, -20), (-40, 10), (-70, -10), (0.10, 0.28), (-0.10, 0.06), (-0.04, 0.06))
        solve(0.34, 0.60, (-80, -10), (-50, 10), (-100, -30), (0.12, 0.30), (-0.12, 0.04), (-0.06, 0.06))
    elif len(sys.argv) > 1 and sys.argv[1] == 'C':
        evaluate(MOTION_C)                 # 与作者源一致：支点 = 右腕
    else:
        evaluate(MOTION_B)
