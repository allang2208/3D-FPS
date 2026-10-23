import bpy
import math
import os

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
TEX = os.path.join(ROOT, "Textures")
OUT = os.environ.get('ALICE_ICON_OUT',os.path.join(ROOT, "Preview", "icon_render.png"))
MATS = ["Canvas", "Webbing", "Leather", "Metal"]

current=r'D:\FPS3D\FPSGAME\SourceAssets\BackpacksReview20261021\AliceBackpack_side_openings.blend'
bpy.ops.wm.open_mainfile(filepath=os.environ.get('ALICE_ICON_SRC',current if os.path.exists(current) else os.path.join(ROOT, "AliceBackpack_uv_bevel.blend")))
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.name == "SM_AliceBackpack")
for o in list(bpy.context.scene.objects):
    if o.type not in {"MESH", "CAMERA", "LIGHT"}:
        bpy.data.objects.remove(o, do_unlink=True)

for i, mat_name in enumerate(MATS):
    mat = bpy.data.materials.new("Icon_" + mat_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    bc = nt.nodes.new("ShaderNodeTexImage")
    bc.image = bpy.data.images.load(os.path.join(TEX, "T_Alice_%s_BaseColor.png" % mat_name))
    bc.image.colorspace_settings.name = "sRGB"
    ao = nt.nodes.new("ShaderNodeTexImage")
    ao.image = bpy.data.images.load(os.path.join(TEX, "T_Alice_%s_AO.png" % mat_name))
    ao.image.colorspace_settings.name = "Non-Color"
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 0.45
    nt.links.new(bc.outputs["Color"], mix.inputs["Color1"])
    nt.links.new(ao.outputs["Color"], mix.inputs["Color2"])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])

    ntex = nt.nodes.new("ShaderNodeTexImage")
    ntex.image = bpy.data.images.load(os.path.join(TEX, "T_Alice_%s_Normal_GL.png" % mat_name))
    ntex.image.colorspace_settings.name = "Non-Color"
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 1.0
    nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])

    tiling = {"Canvas": 5.0, "Webbing": 7.0, "Leather": 5.0, "Metal": 4.0}[mat_name]
    uv = nt.nodes.new("ShaderNodeTexCoord")
    scale = nt.nodes.new("ShaderNodeVectorMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = (tiling, tiling, 1.0)
    nt.links.new(uv.outputs["UV"], scale.inputs[0])
    dtex = nt.nodes.new("ShaderNodeTexImage")
    dtex.image = bpy.data.images.load(os.path.join(TEX, "detail_v2", "detail_%s_Normal_GL.png" % mat_name))
    dtex.image.colorspace_settings.name = "Non-Color"
    dmap = nt.nodes.new("ShaderNodeNormalMap")
    dmap.inputs["Strength"].default_value = 0.7
    nt.links.new(scale.outputs["Vector"], dtex.inputs["Vector"])
    nt.links.new(dtex.outputs["Color"], dmap.inputs["Color"])
    dweight = nt.nodes.new("ShaderNodeVectorMath")
    dweight.operation = "MULTIPLY"
    dweight.inputs[1].default_value = (0.38, 0.38, 0.38)
    nt.links.new(dmap.outputs["Normal"], dweight.inputs[0])
    add = nt.nodes.new("ShaderNodeVectorMath")
    add.operation = "ADD"
    nt.links.new(nmap.outputs["Normal"], add.inputs[0])
    nt.links.new(dweight.outputs["Vector"], add.inputs[1])
    normalize = nt.nodes.new("ShaderNodeVectorMath")
    normalize.operation = "NORMALIZE"
    nt.links.new(add.outputs["Vector"], normalize.inputs[0])
    nt.links.new(normalize.outputs["Vector"], bsdf.inputs["Normal"])

    orm = nt.nodes.new("ShaderNodeTexImage")
    orm.image = bpy.data.images.load(os.path.join(TEX, "T_Alice_%s_ORM.png" % mat_name))
    orm.image.colorspace_settings.name = "Non-Color"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    sep.mode = "RGB"
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    drough = nt.nodes.new("ShaderNodeTexImage")
    drough.image = bpy.data.images.load(os.path.join(TEX, "detail_v2", "detail_%s_Roughness.png" % mat_name))
    drough.image.colorspace_settings.name = "Non-Color"
    nt.links.new(scale.outputs["Vector"], drough.inputs["Vector"])
    rmix = nt.nodes.new("ShaderNodeMixRGB")
    rmix.blend_type = "MIX"
    rmix.inputs["Fac"].default_value = 0.24
    nt.links.new(sep.outputs["Green"], rmix.inputs["Color1"])
    nt.links.new(drough.outputs["Color"], rmix.inputs["Color2"])
    nt.links.new(rmix.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    obj.data.materials[i] = mat

lo = [min(v.co[i] for v in obj.data.vertices) for i in range(3)]
hi = [max(v.co[i] for v in obj.data.vertices) for i in range(3)]
centre = [(lo[i] + hi[i]) * 0.5 for i in range(3)]
size = max(hi[i] - lo[i] for i in range(3))
print("ICON bounds", lo, hi, "size", size)

bpy.ops.object.empty_add(type="PLAIN_AXES", location=tuple(centre))
target = bpy.context.object
bpy.ops.object.camera_add(location=(centre[0] + size * 0.55, centre[1] - size * 2.4, centre[2] + size * 0.18))
cam = bpy.context.object
cam.data.type = "ORTHO"
cam.data.ortho_scale = size * 1.22
cam.data.dof.use_dof = False
con = cam.constraints.new(type="TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
bpy.context.scene.camera = cam


def area(name, loc, energy, size_l, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size_l
    light.data.color = color
    c = light.constraints.new(type="TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return light

area("IconKey", (centre[0] - size * 1.7, centre[1] - size * 2.0, centre[2] + size * 2.2), 45, size * 0.55, (1.0, 0.92, 0.82))
area("IconFill", (centre[0] + size * 2.0, centre[1] - size * 1.2, centre[2] + size * 0.5), 16, size * 0.70, (0.72, 0.82, 1.0))
area("IconRim", (centre[0] + size * 0.6, centre[1] + size * 2.2, centre[2] + size * 1.5), 34, size * 0.55, (1.0, 0.86, 0.70))

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = True
if scene.world is None:
    scene.world = bpy.data.worlds.new("IconWorld")
scene.world.use_nodes = True
bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.012, 0.014, 0.018, 1)
bg.inputs["Strength"].default_value = 0.28
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.05
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("ICON rendered", OUT)
