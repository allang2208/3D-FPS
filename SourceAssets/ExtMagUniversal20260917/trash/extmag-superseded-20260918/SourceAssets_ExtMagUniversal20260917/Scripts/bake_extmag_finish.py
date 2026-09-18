"""Per-rifle coating bake for the extended magazines.

Follows the accepted route in SourceAssets/QBZ191MetalCoat20260913: keep UV0
and the imported split normals for the original structure normal/AO, add a
dedicated coating UV, and bake the *host rifle's* receiver coating into it
(BaseColor + ORM with occlusion in R, roughness in G, metallic in B).

The coating is sampled with a box projection at a recorded physical tile, the
same convention author_uv.py uses for the M4/AKM attachments, so the bake does
not depend on the magazine's own UV layout.

AKM: the mesh is additionally re-expressed in the rifle's own WPN_SOCKET_Magazine
frame. The AKM's accepted large drum is authored that way and mounted with an
identity seat, while the M4/QBZ rigs are handled in the weapon frame.

Run: blender -b -P bake_extmag_finish.py
"""
import bpy, json, math, os
import numpy as np
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FBXDIR = os.path.join(ROOT, "FBX")
TEXDIR = os.path.join(ROOT, "Textures")
SA = r"D:\FPS3D\FPSGAME\SourceAssets"

JOBS = {
    # mag fbx (weapon frame)                tile (m)      base                    rough                       metal
    "M4": dict(src="SM_ExtMag_M440_inframe.fbx", out="SM_ExtMag_M440_finish.fbx",
               tile=(0.12, 0.05),
               base=SA + r"\WeaponAttachmentFinish20260913\Textures\T_M4_Receiver_BaseColor.png",
               rough=SA + r"\WeaponAttachmentFinish20260913\Textures\T_M4_Receiver_Roughness.png",
               rough_invert=True, metal=None, metal_const=0.8),
    "QBZ": dict(src="SM_ExtMag_QBZ40_inframe.fbx", out="SM_ExtMag_QBZ40_finish.fbx",
                tile=(0.12, 0.05),
                base=SA + r"\QBZ191Hero20260913\Textures\T_QBZ_Hero_Body_BaseColor.png",
                rough=SA + r"\QBZ191Hero20260913\Textures\T_QBZ_Hero_Body_ORM.png",
                rough_channel="G", metal=None, metal_channel="B"),
    "AKM": dict(src="SM_ExtMag_AKM40_inframe.fbx", out="SM_ExtMag_AKM40_finish.fbx",
                tile=(0.12, 0.025),
                base=SA + r"\AKMArmSupport20260911\Metal\T_AKM_Mount_Base_color.png",
                rough=SA + r"\AKMArmSupport20260911\Metal\T_AKM_Mount_Roughness.png",
                metal=SA + r"\AKMArmSupport20260911\Metal\T_AKM_Mount_Metallic.png",
                metal_const=0.85),
}
AKM_SRC = os.path.join(SA, r"AKMSoviet20260911\SK_AKM_MannyNative.fbx")
SIZE = 2048


def import_fbx(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.context.scene.objects if o not in before]


def socket_frame(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = import_fbx(path)
    arm = next(o for o in objs if o.type == "ARMATURE")
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    return np.array(arm.matrix_world @ arm.data.bones["WPN_SOCKET_Magazine"].matrix_local)


def coating_material(name, cfg):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(emit.outputs[0], out.inputs["Surface"])
    obj = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(obj.outputs["Object"], mapping.inputs["Vector"])
    scale = (1.0 / cfg["tile"][0], 1.0 / cfg["tile"][1], 1.0 / min(cfg["tile"]))
    mapping.inputs["Scale"].default_value = scale

    def sampler(path, channel=None, srgb=True):
        img = bpy.data.images.load(path, check_existing=True)
        img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        node.projection = "BOX"
        node.projection_blend = 0.35
        nt.links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        if channel == "G":
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            nt.links.new(node.outputs["Color"], sep.inputs["Color"])
            return sep.outputs["Green"]
        if channel == "B":
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            nt.links.new(node.outputs["Color"], sep.inputs["Color"])
            return sep.outputs["Blue"]
        return node.outputs["Color"]

    base = sampler(cfg["base"])
    rough = sampler(cfg["rough"], channel=cfg.get("rough_channel"), srgb=False)
    if cfg.get("rough_invert"):
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(rough, inv.inputs[1])
        rough = inv.outputs[0]
    metal = sampler(cfg["metal"], channel=cfg.get("metal_channel"), srgb=False) if cfg.get("metal") else None
    return mat, base, rough, metal, emit


report = {}
akm_socket_to_world = socket_frame(AKM_SRC) if "AKM" in JOBS else None
for gun, cfg in JOBS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = [o for o in import_fbx(os.path.join(FBXDIR, cfg["src"])) if o.type == "MESH"]
    ob = objs[-1]
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    if gun == "AKM":
        Minv = np.linalg.inv(akm_socket_to_world)
        co = np.array([v.co[:] for v in ob.data.vertices], dtype=float)
        new = (Minv[:3, :3] @ co.T).T + Minv[:3, 3]
        for v, p in zip(ob.data.vertices, new):
            v.co = (float(p[0]), float(p[1]), float(p[2]))
        ob.data.update()

    # coating UV (index 1); UV0 and split normals untouched
    while len(ob.data.uv_layers) > 1:
        ob.data.uv_layers.remove(ob.data.uv_layers[-1])
    uv = ob.data.uv_layers.new(name="MagazineCoatUV")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.012,
                             area_weight=0.2, correct_aspect=True, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')

    mat, base, rough, metal, emit = coating_material("coat_" + gun, cfg)
    original = list(ob.data.materials)
    for i in range(len(ob.data.materials)):
        ob.data.materials[i] = mat

    nt = mat.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    target = nt.nodes.new("ShaderNodeTexImage")
    nt.nodes.active = target

    os.makedirs(TEXDIR, exist_ok=True)
    os.makedirs(os.path.join(TEXDIR, gun), exist_ok=True)
    maps = {}
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 8
    scene.render.bake.use_selected_to_active = False
    scene.render.bake.use_clear = True
    scene.render.bake.margin = 12
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        if any(d.use for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:
        print("CYCLES_CPU_FALLBACK", err, flush=True)

    for kind in ("BaseColor", "ORM"):
        img = bpy.data.images.new("T_ExtMag_%s_%s" % (gun, kind), width=SIZE, height=SIZE, alpha=False)
        img.colorspace_settings.name = "sRGB" if kind == "BaseColor" else "Non-Color"
        target.image = img
        if kind == "BaseColor":
            nt.links.new(base, emit.inputs["Color"])
        else:
            combine = nt.nodes.new("ShaderNodeCombineColor")
            nt.links.new(rough, combine.inputs["Green"])
            if metal is not None:
                nt.links.new(metal, combine.inputs["Blue"])
            else:
                combine.inputs["Blue"].default_value = cfg.get("metal_const", 0.8)
            combine.inputs["Red"].default_value = 1.0
            nt.links.new(combine.outputs[0], emit.inputs["Color"])
        bpy.ops.object.bake(type="EMIT")
        path = os.path.join(TEXDIR, gun, img.name + ".png")
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        maps[kind] = path
        print("EXTMAG_COATING_BAKED", gun, kind, flush=True)

    for i, m in enumerate(original):
        ob.data.materials[i] = m
    ob.data.uv_layers.active_index = 0
    ob.data.uv_layers[0].active_render = True
    out_path = os.path.join(FBXDIR, cfg["out"])
    bpy.ops.export_scene.fbx(filepath=out_path, use_selection=True,
                             object_types={'MESH'}, axis_forward='-Y', axis_up='Z',
                             bake_anim=False, mesh_smooth_type='FACE', use_tspace=True)
    report[gun] = {"fbx": os.path.basename(out_path), "textures": maps,
                   "coating_uv": 1, "uv_name": "MagazineCoatUV",
                   "physical_tile_m": list(cfg["tile"]),
                   "frame": "WPN_SOCKET_Magazine (socket)" if gun == "AKM" else "weapon frame",
                   "slots": [m.name if m else None for m in original]}

with open(os.path.join(ROOT, "Reference", "finish_bake.json"), "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1)
print("EXTMAG_FINISH_BAKE " + json.dumps(report))
