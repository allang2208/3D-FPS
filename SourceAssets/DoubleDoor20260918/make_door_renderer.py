"""把窗的离线渲染脚本改造成双开门的（一次性转换脚本，不参与构建）。

只改尺寸常量、OBJ 名、相机与输出文件名；置换表里每条都断言命中，避免静默漏改。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "Window20260918", "render_window_materials.py")
DST = os.path.join(HERE, "render_door_materials.py")

PAIRS = [
    ('''"""离线渲染 40×40 双开窗的几种材质外观（numpy z-buffer + Lambert，不需要引擎／RHI）。''',
     '''"""离线渲染 2×2 m 双开门的几种材质外观（numpy z-buffer + Lambert，不需要引擎／RHI）。'''),
    ('''读 build_window_meshes_20260918.py 导出的三角汤 OBJ，按与 C++ 同一套铰链数学摆出关／开两种
状态，再分别按木材／石头／大理石上色。相机、光照与体素墙（2×2 洞）都写死在脚本里，方便对照。

运行：python SourceAssets/Window20260918/render_window_materials.py''',
     '''读 build_double_door_meshes_20260918.py 导出的三角汤 OBJ，按与 C++ 同一套铰链数学摆出关／开两种
状态，再分别按木材／石头／大理石上色。相机、光照与体素墙（10×10 落地门洞）都写死在脚本里。
本文件与窗的渲染脚本同源（窗见 SourceAssets/Window20260918/render_window_materials.py），
差别只在尺寸常量、洞口位置与相机。

运行：python SourceAssets/DoubleDoor20260918/render_door_materials.py'''),
    ('''# 窗的装配尺寸（cm），必须与 ColdSteelWindow.cpp / build_window_meshes 保持一致。
FRAME_W, FRAME_H, FRAME_DEPTH = 100.0, 100.0, 20.0
MEMBER = 6.0
LEAF_HALF_W = 43.5 / 2.0
LEAF_HALF_T = 2.0                 # 名义板厚的一半（窗扇包围盒的 X 含把手凸出，铰链按名义板厚算）''',
     '''# 门的装配尺寸（cm），必须与 ColdSteelDoubleDoor.cpp / build_double_door_meshes 保持一致。
FRAME_W, FRAME_H, FRAME_DEPTH = 200.0, 200.0, 20.0
MEMBER = 8.0
LEAF_HALF_W = 91.5 / 2.0
LEAF_HALF_T = 2.5                 # 名义板厚的一半（门扇包围盒的 X 含把手凸出，铰链按名义板厚算）'''),
    ('''def wall(hole_y=(-50.0, 50.0), hole_z=(60.0, 160.0)):
    """一层 20 cm 体素墙（正对着窗开一个 5×5 洞），给窗一个尺度参照。''',
     '''def wall(hole_y=(-100.0, 100.0), hole_z=(0.0, 200.0)):
    """一层 20 cm 体素墙（正对着门开一个 10×10、落地的洞），给门一个尺度参照。'''),
    ("    for iy in range(-2, 8):", "    for iy in range(-2, 12):"),
    ("        for iz in range(-3, 7):", "        for iz in range(0, 13):"),
    ('frame = load_obj("window_frame_100.obj")', 'frame = load_obj("door_frame_200.obj")'),
    ('leaf = load_obj("window_leaf_100.obj")', 'leaf = load_obj("door_leaf_200.obj")'),
    ('CLOSED = assemble(frame, leaf, 0.0, 1.0, lift=60.0, report="关·")',
     'CLOSED = assemble(frame, leaf, 0.0, 1.0, lift=0.0, report="关·")'),
    ('OPEN = assemble(frame, leaf, OPEN_ANGLE, 1.0, lift=60.0, report="开外")',
     'OPEN = assemble(frame, leaf, OPEN_ANGLE, 1.0, lift=0.0, report="开外")'),
    ('OPEN_IN = assemble(frame, leaf, OPEN_ANGLE, -1.0, lift=60.0, report="开内")',
     'OPEN_IN = assemble(frame, leaf, OPEN_ANGLE, -1.0, lift=0.0, report="开内")'),
    ('print("  窗 bbox %.0f x %.0f x %.0f，z %.0f..%.0f（含抬到洞里 +60）" % (',
     'print("  门 bbox %.0f x %.0f x %.0f，z %.0f..%.0f（门洞落地）" % ('),
    ('print("== 三种材质：关窗（3/4 视角，含 5×5 洞的体素墙）==")',
     'print("== 三种材质：关门（3/4 视角，含 10×10 落地门洞的体素墙）==")'),
    ("FRONT_CAM = (430.0, -330.0, 300.0)", "FRONT_CAM = (560.0, -430.0, 320.0)"),
    ("FRONT_TARGET = (0.0, 0.0, 120.0)", "FRONT_TARGET = (0.0, 0.0, 110.0)"),
    ("render(CLOSED, COLORS[group], group, FRONT_CAM, FRONT_TARGET, 860, 760, 32.0, wall_tris=WALL)",
     "render(CLOSED, COLORS[group], group, FRONT_CAM, FRONT_TARGET, 880, 800, 34.0, wall_tris=WALL)"),
    ('name = "window_%s_closed.png" % group', 'name = "door_%s_closed.png" % group'),
    ('print("== 正视图：只看窗（石材，去掉墙，便于读窗框与两扇的比例）==")',
     'print("== 正视图：只看门（石材，去掉墙，便于读门框与两扇的比例）==")'),
    ('''save("window_stone_isolated.png", render(CLOSED, COLORS["stone"], "stone", (540.0, 0.0, 120.0),
                                         (0.0, 0.0, 120.0), 820, 820, 24.0))''',
     '''save("door_stone_isolated.png", render(CLOSED, COLORS["stone"], "stone", (820.0, 0.0, 105.0),
                                       (0.0, 0.0, 105.0), 820, 900, 22.0))'''),
    ('''save("window_stone_front.png", render(CLOSED, COLORS["stone"], "stone", (640.0, 0.0, 120.0),
                                      (0.0, 0.0, 120.0), 820, 820, 26.0, wall_tris=WALL))''',
     '''save("door_stone_front.png", render(CLOSED, COLORS["stone"], "stone", (980.0, 0.0, 130.0),
                                    (0.0, 0.0, 130.0), 820, 900, 26.0, wall_tris=WALL))'''),
    ('print("== 内侧视角（大理石，从 −X 看向室内那一面）==")',
     'print("== 内侧视角（大理石，从 −X 看向室内那一面）==")'),
    ('''save("window_marble_inside.png", render(CLOSED, COLORS["marble"], "marble", (-560.0, -300.0, 330.0),
                                        (0.0, 0.0, 120.0), 860, 760, 30.0, wall_tris=WALL))''',
     '''save("door_marble_inside.png", render(CLOSED, COLORS["marble"], "marble", (-820.0, -430.0, 350.0),
                                      (0.0, 0.0, 120.0), 880, 800, 32.0, wall_tris=WALL))'''),
    ('print("== 开窗状态：只看窗（大理石，向外开；读两扇的摆向与铰链位置）==")',
     'print("== 开门状态：只看门（大理石，向外开；读两扇的摆向与铰链位置）==")'),
    ('''save("window_marble_open_isolated.png", render(OPEN, COLORS["marble"], "marble", (450.0, -350.0, 300.0),
                                               (0.0, 0.0, 120.0), 860, 760, 34.0))''',
     '''save("door_marble_open_isolated.png", render(OPEN, COLORS["marble"], "marble", (660.0, -520.0, 350.0),
                                             (0.0, 0.0, 115.0), 880, 800, 34.0))'''),
    ('print("== 开窗状态：含墙（大理石，向外开）==")', 'print("== 开门状态：含墙（大理石，向外开）==")'),
    ('''save("window_marble_open.png", render(OPEN, COLORS["marble"], "marble", (540.0, -390.0, 330.0),
                                      (0.0, 0.0, 120.0), 860, 760, 32.0, wall_tris=WALL))''',
     '''save("door_marble_open.png", render(OPEN, COLORS["marble"], "marble", (760.0, -560.0, 380.0),
                                    (0.0, 0.0, 115.0), 880, 800, 34.0, wall_tris=WALL))'''),
    ('print("== 开窗状态：含墙（木材，向内开，玩家在室外侧的对照）==")',
     'print("== 开门状态：含墙（木材，向内开，玩家在室外侧的对照）==")'),
    ('''save("window_wood_open_inward.png", render(OPEN_IN, COLORS["wood"], "wood", (540.0, -390.0, 330.0),
                                           (0.0, 0.0, 120.0), 860, 760, 32.0, wall_tris=WALL))''',
     '''save("door_wood_open_inward.png", render(OPEN_IN, COLORS["wood"], "wood", (760.0, -560.0, 380.0),
                                         (0.0, 0.0, 115.0), 880, 800, 34.0, wall_tris=WALL))'''),
    ('print("== 开窗状态：俯视角（木材，向外开；看清两扇各自绕外侧铰链转出去）==")',
     'print("== 开门状态：俯视角（木材，向外开；看清两扇各自绕外侧铰链转出去）==")'),
    ('''save("window_wood_open_top.png", render(OPEN, COLORS["wood"], "wood", (230.0, -560.0, 700.0),
                                        (0.0, 0.0, 115.0), 860, 760, 34.0, wall_tris=WALL))''',
     '''save("door_wood_open_top.png", render(OPEN, COLORS["wood"], "wood", (320.0, -760.0, 980.0),
                                      (0.0, 0.0, 120.0), 880, 800, 34.0, wall_tris=WALL))'''),
    ('print("== 中缝特写（大理石，只看把手与两扇交界）==")',
     'print("== 中缝特写（大理石，只看把手与两扇交界）==")'),
    ('''save("window_marble_handle_detail.png", render(CLOSED, COLORS["marble"], "marble", (170.0, -55.0, 128.0),
                                               (0.0, 0.0, 118.0), 900, 760, 22.0))''',
     '''save("door_marble_handle_detail.png", render(CLOSED, COLORS["marble"], "marble", (300.0, -110.0, 230.0),
                                             (0.0, 0.0, 215.0), 900, 760, 22.0))'''),
    ('sheet = Image.new("RGB", (860, 760 * 3 + 24), (28, 30, 33))',
     'sheet = Image.new("RGB", (880, 800 * 3 + 24), (28, 30, 33))'),
    ('    sheet.paste(Image.fromarray(shots[group]), (0, index * (760 + 8)))',
     '    sheet.paste(Image.fromarray(shots[group]), (0, index * (800 + 8)))'),
    ('sheet.save(os.path.join(DIR, "window_material_sheet.png"))',
     'sheet.save(os.path.join(DIR, "door_material_sheet.png"))'),
    ('print("    wrote window_material_sheet.png")', 'print("    wrote door_material_sheet.png")'),
]

text = open(SRC, encoding="utf-8").read()
missing = []
for old, new in PAIRS:
    if old not in text:
        missing.append(old.splitlines()[0][:70])
    text = text.replace(old, new)
if missing:
    print("MISSING (未命中，需要人工确认):")
    for m in missing:
        print("   ", m)
    sys.exit(1)
open(DST, "w", encoding="utf-8").write(text)
print("wrote %s (%d bytes), %d replacements" % (DST, len(text), len(PAIRS)))
