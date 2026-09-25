"""按背包统一规则渲染模块化装备的竖直图标（上衣／手套）。

规则与 ColdSteelWeaponIcons 捕获通道同源：
  · 画幅按作者占格推导，320 px／格行，长宽比等于格子长宽比；
  · 主轴填满 91%，轮廓中心（不是偏移常量）落在画幅中心；
  · 透明底、只渲主体。
装备与武器相反：保持竖直（肩颈在上、袖口与下摆朝上展开），不做横置。
本体色与 Tools/ModularOutfit/import_equipment.py 建的 UE 材质取同一组线性值，
渲染后用不透明区均值自校准曝光，避免过曝把深棕冲成肤色、把近黑冲成灰。

Run: blender -b -t 4 --python-exit-code 1 --python Tools/ModularOutfit/render_equipment_icons.py
"""
import bpy, math, os
from pathlib import Path
from mathutils import Vector

ROOT = Path('D:/FPS3D/FPSGAME')
BLEND = ROOT/'SourceAssets/ModularOutfit20260924/ItemPresentation.blend'
ICON = ROOT/'Content/ColdSteelData/Icons/ModularOutfit20260924'
FILL = 0.91                 # 与 ColdSteelWeaponIcons / ColdSteelMaterialIcon 同一常数
PX_PER_ROW = 320
SUPERSAMPLE = 2             # 渲 2x 再按比例降采样，边缘不糊

# 定义 id、主体对象、本体色（线性，与 import_equipment.py 一致）、粗糙度、作者占格
ITEMS = [
    ('ue_field_sweater',          'SM_FieldSweater_Pickup', (.115, .135, .080), .91, (3, 3)),
    ('ue_field_sweater_charcoal', 'SM_FieldSweater_Pickup', (.045, .053, .065), .91, (3, 3)),
    ('ue_field_gloves',           'SM_FieldGloves_Pickup',  (.180, .085, .035), .72, (2, 2)),
    ('ue_field_gloves_black',     'SM_FieldGloves_Pickup',  (.026, .030, .034), .72, (2, 2)),
]

assert BLEND.exists(), f'missing {BLEND}'
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
ICON.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
subjects = {}
for _, obj_name, _, _, _ in ITEMS:
    if obj_name not in subjects:
        obj = bpy.data.objects.get(obj_name)
        assert obj and obj.type == 'MESH', f'missing mesh {obj_name}'
        subjects[obj_name] = obj

# —— 相机：正对主体平铺面的干净轴测视角 ——
# 展示网格在 author_item_presentation.py 里已被压平到 XY 面（衣物纵向＝+Y），
# 所以相机沿 -Z 俯视、上方向取 +Y，衣物与手指就正好竖直，不会再被 to_track_quat 带出滚转。
for o in list(bpy.data.objects):
    if o.type == 'CAMERA':
        bpy.data.objects.remove(o, do_unlink=True)
cam_data = bpy.data.cameras.new('IconCamera')
cam_data.type = 'ORTHO'
cam_data.clip_start = 0.01
cam = bpy.data.objects.new('IconCamera', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

# —— 灯光：压到不夹光的量级，剩下的偏差交给曝光自校准 ——
for o in list(bpy.data.objects):
    if o.type == 'LIGHT':
        bpy.data.objects.remove(o, do_unlink=True)
for name, pos, power, size in [('Key', (-1, -1, 2), 55, 2), ('Fill', (1, .2, 1.5), 30, 1.5), ('Rim', (0, 1, 1.2), 45, 1)]:
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.shape, data.size = power, 'DISK', size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = pos
    obj.rotation_euler = (-Vector(pos)).to_track_quat('-Z', 'Y').to_euler()

if not scene.world:
    scene.world = bpy.data.worlds.new('SoftStudio')
scene.world.use_nodes = True
tree = scene.world.node_tree
tree.nodes.clear()
bg = tree.nodes.new('ShaderNodeBackground')
out = tree.nodes.new('ShaderNodeOutputWorld')
tree.links.new(bg.outputs[0], out.inputs['Surface'])
bg.inputs['Color'].default_value = (.25, .28, .34, 1)
bg.inputs['Strength'].default_value = .12       # 原来 0.5 的环境光是主要冲淡来源之一

scene.view_settings.view_transform = 'Standard'  # AgX 会把深色提亮去饱和
try:
    scene.view_settings.look = 'None'
except Exception:
    pass
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
try:
    scene.cycles.device = 'CPU'                   # 与本机 UE 捕获抢 GPU 没意义
except Exception:
    pass
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'


def surface(color, rough):
    m = bpy.data.materials.new('IconSurface')
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    p = t.nodes.new('ShaderNodeBsdfPrincipled')
    o = t.nodes.new('ShaderNodeOutputMaterial')
    t.links.new(p.outputs['BSDF'], o.inputs['Surface'])
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Specular IOR Level'].default_value = .3
    noise = t.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 220
    bump = t.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .13
    bump.inputs['Distance'].default_value = .0003
    t.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    t.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    return m


def silhouette(obj):
    """主体在像平面上（俯视＝XY）的投影包围盒。"""
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    return min(xs), max(xs), min(ys), max(ys)


def measure(path):
    """不透明区的均值，一律换算回线性，才能和本体色直接比。
    读回的字节图默认按 sRGB 解码，这里显式改成 Non-Color 拿原始编码值，再自己反解，
    避免色彩管理把校准方向搞反。"""
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    px = list(img.pixels)
    ch = img.channels
    acc = [0.0, 0.0, 0.0]
    n = 0
    for i in range(0, len(px), ch * 7):          # 每 7 像素取一个，够稳
        if px[i + 3] > .15:
            acc[0] += px[i]; acc[1] += px[i + 1]; acc[2] += px[i + 2]; n += 1
    bpy.data.images.remove(img)
    if not n:
        return None
    def to_linear(e):
        return e / 12.92 if e <= .04045 else ((e + .055) / 1.055) ** 2.4
    return [to_linear(acc[k] / n) for k in range(3)], n


report = []
for definition, obj_name, color, rough, grid in ITEMS:
    obj = subjects[obj_name]
    canvas_w = max(256, round(PX_PER_ROW * grid[0] / max(1, grid[1])))
    canvas_h = PX_PER_ROW
    aspect = canvas_w / canvas_h

    for other in subjects.values():
        other.hide_render = other is not obj
    obj.data.materials.clear()
    obj.data.materials.append(surface(color, rough))

    x0, x1, y0, y1 = silhouette(obj)
    span_x, span_y = x1 - x0, y1 - y0
    # 主轴填满 91%，与捕获通道同一式子；竖直方向不旋转，衣物纵向保持朝上。
    ortho = max(span_x, span_y * aspect) / FILL
    cam_data.ortho_scale = ortho
    cam.location = ((x0 + x1) * .5, (y0 + y1) * .5, max(span_x, span_y) * 4 + 1)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    scene.render.resolution_x = canvas_w * SUPERSAMPLE
    scene.render.resolution_y = canvas_h * SUPERSAMPLE
    scene.render.resolution_percentage = 100 // SUPERSAMPLE

    target = sum(color) / 3.0
    scene.view_settings.exposure = 0.0
    actual, n = 0.0, 0
    out_path = ICON / f'{definition}.png'
    for attempt in range(3):                     # 渲→量→按 log2 修正曝光，最多两次修正
        scene.render.filepath = str(out_path)    # 直接写最终路径，最后一帧就是成品
        bpy.ops.render.render(write_still=True)
        got = measure(str(out_path))
        if not got:
            report.append(f'{definition}: 不透明区为空')
            break
        mean, n = got
        actual = sum(mean) / 3.0
        if attempt < 2 and actual > 1e-5:
            delta = math.log2(max(target / actual, 1e-3))
            if abs(delta) < 0.08:                # 已经够接近本体色
                break
            scene.view_settings.exposure += delta
            continue
        break
    report.append(f'{definition}: canvas={canvas_w}x{canvas_h} ortho={ortho:.4f} '
                  f'span=({span_x:.3f},{span_y:.3f}) target={target:.4f} '
                  f'rendered={actual:.4f} exposure={scene.view_settings.exposure:+.2f}EV px={n}')

print('EQUIPMENT_ICONS_DONE')
for line in report:
    print('  ' + line)
