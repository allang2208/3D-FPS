"""Per-rifle extended-magazine images.

attachment-icons.md: a shared image may not stand in for a different
silhouette, so the option needs its own image per rifle. Modes:

  -- icon     the deployable option icon (Reference/icon_<weapon>.png), on the
              accepted neutral polymer studio of render_icon_qbz40.py.
  -- coating  material evidence (Reference/material_preview_<weapon>_coating.png):
              the same mesh with that rifle's baked per-rifle coating
              (Textures/<gun>/, made by bake_extmag_finish.py) under the accepted
              attachment-icon studio (AttachmentIconAudit20260914).

Presentation: ortho side view, muzzle (+Y) to the left, transparent
background, single piece.
"""
import bpy
import math
import os
import sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FBXDIR = os.path.join(ROOT, "FBX")
TEXDIR = os.path.join(ROOT, "Textures")
OUTDIR = os.path.join(ROOT, "Reference")
SA = r"D:\FPS3D\FPSGAME\SourceAssets"
AKM_RIFLE = os.path.join(SA, r"AKMSoviet20260911\SK_AKM_MannyNative.fbx")

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = ARGV[0] if ARGV else "icon"

JOBS = {
    "ue_m4a1": dict(gun="M4", fbx="SM_ExtMag_M440_finish.fbx", socket_frame=False),
    "ue_akm": dict(gun="AKM", fbx="SM_ExtMag_AKM40_finish.fbx", socket_frame=True),
    "ue_qbz191": dict(gun="QBZ", fbx="SM_ExtMag_QBZ40_finish.fbx", socket_frame=False),
}


def import_fbx(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.context.scene.objects if o not in before]


def socket_matrix(path):
    """World rest matrix of WPN_SOCKET_Magazine, the frame the AKM bake wrote."""
    objs = import_fbx(path)
    arm = next(o for o in objs if o.type == "ARMATURE")
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    matrix = arm.matrix_world @ arm.data.bones["WPN_SOCKET_Magazine"].matrix_local
    for obj in objs:
        bpy.data.objects.remove(obj, do_unlink=True)
    return matrix


def new_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, nt, bsdf


def image_node(nt, path, srgb, uv_out):
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    node = nt.nodes.new("ShaderNodeTexImage")
    node.image = img
    nt.links.new(uv_out, node.inputs["Vector"])
    return node


def channel(nt, node, name):
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(node.outputs["Color"], sep.inputs["Color"])
    return sep.outputs[name]


def build_polymer_material(mesh, gun):
    """The presentation the accepted ext_mag icon used (render_icon_qbz40.py)."""
    mat, nt, bsdf = new_material("icon_polymer_" + gun)
    bsdf.inputs["Base Color"].default_value = (0.045, 0.046, 0.052, 1)
    bsdf.inputs["Roughness"].default_value = 0.52
    bsdf.inputs["Metallic"].default_value = 0.0
    mesh.data.materials.clear()
    mesh.data.materials.append(mat)


def build_coating_material(mesh, gun, uv0_name, coat_name, structure_normal):
    """install_extmag_finish.py's construction: host-rifle coating on the
    coating UV, original structure normal on UV0."""
    mat, nt, bsdf = new_material("icon_finish_" + gun)
    uv0 = nt.nodes.new("ShaderNodeUVMap")
    uv0.uv_map = uv0_name
    coat = nt.nodes.new("ShaderNodeUVMap")
    coat.uv_map = coat_name
    base = image_node(nt, os.path.join(TEXDIR, gun, "T_ExtMag_%s_BaseColor.png" % gun), True, coat.outputs["UV"])
    orm = image_node(nt, os.path.join(TEXDIR, gun, "T_ExtMag_%s_ORM.png" % gun), False, coat.outputs["UV"])
    nt.links.new(base.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(channel(nt, orm, "Green"), bsdf.inputs["Roughness"])
    nt.links.new(channel(nt, orm, "Blue"), bsdf.inputs["Metallic"])
    if os.path.exists(structure_normal):
        nrm = image_node(nt, structure_normal, False, uv0.outputs["UV"])
        bump = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(nrm.outputs["Color"], bump.inputs["Color"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mesh.data.materials.clear()
    mesh.data.materials.append(mat)


def frame_from_geometry(mesh):
    """World bounds straight from the vertices.

    ob.dimensions / ob.bound_box keep the pre-edit values until a depsgraph
    update, which is what put the re-expressed AKM mesh outside its own frame.
    """
    return [mesh.matrix_world @ vert.co for vert in mesh.data.vertices]


for key, cfg in JOBS.items():
    gun = cfg["gun"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = [o for o in import_fbx(os.path.join(FBXDIR, cfg["fbx"])) if o.type == "MESH"]
    ob = objs[-1]
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    if cfg["socket_frame"]:
        # The AKM mesh is authored in WPN_SOCKET_Magazine; put it back into the
        # rifle frame so all three images share one presentation.
        matrix = socket_matrix(AKM_RIFLE)
        for vert in ob.data.vertices:
            vert.co = matrix @ vert.co
        ob.data.update()
        bpy.context.view_layer.update()

    uv0_name = ob.data.uv_layers[0].name
    coat_name = next((layer.name for layer in ob.data.uv_layers if "Coat" in layer.name), None)

    if MODE == "coating":
        if coat_name is None:
            raise RuntimeError("coating UV missing on " + cfg["fbx"])
        build_coating_material(ob, gun, uv0_name, coat_name,
                               os.path.join(FBXDIR, "SM_ExtMag_%s_inframe.fbm" % (
                                   "M440" if gun == "M4" else ("QBZ40" if gun == "QBZ" else "AKM40")),
                                   "Magazine_Material.001_Normal.png" if gun == "QBZ"
                                   else "Magazine Light_Normal.png"))
    else:
        build_polymer_material(ob, gun)

    scene = bpy.context.scene
    points = frame_from_geometry(ob)
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    size = hi - lo
    center = (lo + hi) * 0.5
    print("EXTMAG_ICON_DIMS %s %s lo=%s hi=%s" % (
        key, tuple(round(v, 4) for v in size),
        tuple(round(v, 4) for v in lo), tuple(round(v, 4) for v in hi)), flush=True)

    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = 1024
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.use_compositing = False
    scene.render.use_sequencer = False

    d = Vector((1, 0, 0))  # camera on -X looking +X: +Y (mag front) appears LEFT
    z = -d
    x = Vector((0, 0, 1)).cross(z).normalized()
    y = z.cross(x)
    cam_d = bpy.data.cameras.new("c")
    cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new("c", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam

    if MODE == "coating":
        cam_d.ortho_scale = 2.36
        ob.matrix_world = (Matrix.Scale(2.0 / max(size.x, size.z), 4)
                           @ Matrix.Translation(-center) @ ob.matrix_world)
        cam.matrix_world = (Matrix.Translation(-d * 5)
                            @ Matrix((x, y, z)).transposed().to_4x4())
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 48
        scene.cycles.use_denoising = True
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            prefs.compute_device_type = 'OPTIX'
            prefs.get_devices()
            for device in prefs.devices:
                device.use = device.type == 'OPTIX'
            if any(dev.use for dev in prefs.devices):
                scene.cycles.device = 'GPU'
        except Exception as err:
            print("CYCLES_CPU_FALLBACK", str(err), flush=True)
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.exposure = 0.35
        scene.world = bpy.data.worlds.new('ExtMagCoatingStudio')
        scene.world.use_nodes = True
        bg = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
        bg.inputs[0].default_value = (.36, .36, .36, 1)
        bg.inputs[1].default_value = .55
        for loc, energy, lsize in (((-1.5, -3, 3), 700, 4), ((2, 1.5, 2.5), 950, 3),
                                   ((-3, -1, -.5), 180, 2), ((0, -4, .2), 110, 3)):
            bpy.ops.object.light_add(type='AREA', location=loc)
            light = bpy.context.object
            light.data.energy = energy
            light.data.shape = 'DISK'
            light.data.size = lsize
            light.rotation_euler = (-light.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = os.path.join(OUTDIR, "material_preview_%s_coating.png" % key)
    else:
        cam_d.ortho_scale = max(size.y, size.z) / 0.80
        cam.matrix_world = (Matrix.Translation(center - d * 2)
                            @ Matrix((x, y, z)).transposed().to_4x4())
        key_light = bpy.data.lights.new("key", 'AREA')
        key_light.energy = 60
        key_light.size = 1.2
        ko = bpy.data.objects.new("key", key_light)
        scene.collection.objects.link(ko)
        ko.location = (-0.6, -0.5, 0.5)
        ko.rotation_euler = (math.radians(55), 0, math.radians(50))
        fill = bpy.data.lights.new("fill", 'AREA')
        fill.energy = 25
        fill.size = 1.5
        fo = bpy.data.objects.new("fill", fill)
        scene.collection.objects.link(fo)
        fo.location = center + Vector((0.5, 0.6, -0.2))
        fo.rotation_euler = (math.radians(100), 0, math.radians(-130))
        scene.render.engine = 'BLENDER_EEVEE'
        scene.render.filepath = os.path.join(OUTDIR, "icon_%s.png" % key)

    bpy.ops.render.render(write_still=True)
    print("EXTMAG_ICON_RENDERED %s %s" % (MODE, key), flush=True)

print("EXTMAG_ICON_RENDER_DONE " + MODE)
