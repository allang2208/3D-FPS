"""Torch v8 (runs INSIDE the running editor):

  python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/build_bronze_torch_v8_20260918.py

用户反馈（v7 之后）：
  1. 去除金属圆环            -> 删掉全部 torus：柱箍 collar、杆顶 joint_ring、杯口 cup_lip。
  2. 跟附着物连接的杆子使用直线，不添加任何形状装饰
                             -> 横臂回到**一根等截面直杆**（x16..50），删掉根部靴座、收细端头、
                                两块菱形板、中央凸台和 8 枚铆钉，也删掉夹箍套筒；直杆直接插进立杆。
  3. 跟罗马柱衔接的位置降低一些 -> 网格的局部原点仍是"柱轴心 + 横臂平面"（约定不变），
                                降低由关卡 actor 高度给出：210 -> 190（见 place_*_v7 脚本 TORCH_Z）。

保留：立杆的车削剖面（水滴尾椎 + 四道珠结，v5 用户要求的主体细节）和杯体（v7 的 96 段杯脚/束颈/
鼓腹/卷唇/内腔）。如果那几道珠结也算"圆环"，说一声再去掉。
材质沿用 v7 的光滑青铜 M_Bronze，本脚本不动材质。

契约：局部原点 = 柱轴心、托臂沿 +X、横臂平面 local z=0、杯唇 local z≈42.6、尾椎 local z≈-44。
"""

import time

import unreal

SV = unreal.ModelingService
D = "/Game/Props/RomanColumn20260915"
TORCH = D + "/SM_BronzeTorch"
BRONZE = D + "/M_Bronze"
LOG = []


def log(m):
    print("[tv8] " + m)


def do(label, result):
    ok = getattr(result, "success", None)
    LOG.append((label, ok))
    log("%-14s %s" % (label, ok))
    return result


def tf(x=0.0, y=0.0, z=0.0, pitch=0.0, yaw=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, pitch, yaw).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def wait(path, timeout=25.0):
    end = time.time() + timeout
    while time.time() < end:
        a = unreal.EditorAssetLibrary.load_asset(path)
        if a:
            return a
        time.sleep(0.3)
    return None


t = SV.create_mesh().handle

# 一根等截面直杆：根部嵌入柱身 5 cm（柱面 r≈21，杆从 x16 起），端头到立杆轴心 x50。
do("arm", SV.append_box(t, tf(33.0, 0.0, 0.0), 34.0, 2.2, 2.2, 0, 0, 0, "Center", 0))

# 车削立杆：水滴尾椎 -> 四道珠结 -> 顶部喇叭座（v7 未改动）
stem = [(0.00, -44.0), (1.10, -43.4), (2.30, -41.6), (3.60, -38.2), (4.30, -34.0),
        (4.20, -30.0), (3.50, -26.2), (2.40, -23.4), (1.90, -21.0), (2.60, -19.6),
        (1.90, -18.2), (1.75, -16.4), (1.60, -14.0), (2.70, -12.4), (1.75, -10.6),
        (1.60, -8.0), (1.55, -5.6), (2.60, -4.2), (1.70, -2.6), (1.60, -0.5),
        (1.70, 1.2), (2.90, 2.6), (1.90, 4.0), (1.85, 6.0), (2.10, 8.0),
        (3.60, 10.4), (5.60, 12.0), (0.00, 12.0)]
do("stem", SV.append_revolve_polygon(t, tf(50, 0, 0), stem, 0.0, 64, 360.0, 0))

# 杯体：杯脚 -> 束颈 -> 外鼓腹 -> 卷唇 -> 内腔（v7 未改动，但去掉了杯唇珠环）
cup = [(0.00, 11.6), (6.40, 11.6), (6.60, 12.6), (5.20, 14.2), (4.90, 15.6), (6.20, 17.6),
       (8.40, 20.4), (10.60, 24.0), (12.80, 28.4), (14.60, 33.2), (15.60, 36.8),
       (16.10, 39.6), (16.50, 41.4), (16.30, 42.4), (15.30, 42.6), (14.60, 41.4),
       (13.60, 38.0), (11.40, 33.0), (8.60, 27.0), (5.60, 21.0), (3.00, 16.4),
       (1.40, 14.2), (0.00, 13.6)]
do("cup", SV.append_revolve_polygon(t, tf(50, 0, 0), cup, 0.0, 96, 360.0, 0))

info = SV.get_mesh_info(t)
log("v8: tris=%s comps=%s open=%s closed=%s" % (
    info.triangle_count, info.connected_components, info.open_border_edges, info.is_closed))
log("bbox x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f" % (
    info.bounds_min.x, info.bounds_max.x, info.bounds_min.y, info.bounds_max.y,
    info.bounds_min.z, info.bounds_max.z))
ok_geom = info.is_closed and info.open_border_edges == 0 and info.connected_components == 3
# 无箍环后 x 最小 = 直杆根部 16（不再是柱箍的 -24.2），最大 = 杯口 66.5；z 仍是尾椎 -44 / 卷唇 42.6。
ok_bounds = (abs(info.bounds_min.x - 16.0) < 0.6 and abs(info.bounds_max.x - 66.5) < 0.6
             and abs(info.bounds_min.z + 44.0) < 0.6 and abs(info.bounds_max.z - 42.6) < 0.6
             and abs(info.bounds_min.y + 16.5) < 0.6 and abs(info.bounds_max.y - 16.5) < 0.6)

do("uv", SV.auto_uv(t, "XAtlas", 0))
do("save", SV.save_mesh_to_static_mesh(t, TORCH, True, True, False, True))
SV.release_mesh(t)
if wait(TORCH):
    do("collision", SV.generate_collision(TORCH, "ConvexHulls", 4, 25, True))
    do("material", SV.set_asset_materials(TORCH, BRONZE, True))

log("geometry_ok=%s bounds_ok=%s steps=%d failed=%s" % (
    ok_geom, ok_bounds, len(LOG), [e[0] for e in LOG if e[1] is False]))
log("RESULT: " + ("PASS" if ok_geom and ok_bounds and not [e for e in LOG if e[1] is False] else "CHECK"))
