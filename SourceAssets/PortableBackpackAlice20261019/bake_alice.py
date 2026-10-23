import bpy
import bmesh
import json
import math
import os

SRC = os.environ.get("ALICE_BAKE_SRC", r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019\AliceBackpack_uv.blend")
OUT_DIR = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
TEX_DIR = os.path.join(OUT_DIR, "Textures")
os.makedirs(TEX_DIR, exist_ok=True)

RES = json.loads(os.environ.get("ALICE_BAKE_RES", '{"Canvas": 2048, "Webbing": 2048, "Leather": 1024, "Metal": 1024}'))
SAMPLES = {"BaseColor": 1, "Normal": 1, "Roughness": 1, "AO": 8}

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
obj = next(o for o in scene.objects if o.type == "MESH")

# Remove faces whose UV triangle is degenerate; smart-project can leave a few.
bm = bmesh.new()
bm.from_mesh(obj.data)
uv_layer = bm.loops.layers.uv.active
bad = []
for f in bm.faces:
    p = [(l[uv_layer].uv.x, l[uv_layer].uv.y) for l in f.loops]
    a = 0.0
    for i in range(len(p)):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % len(p)]
        a += x1 * y2 - x2 * y1
    if abs(a) < 1e-10:
        bad.append(f)
if bad:
    bmesh.ops.delete(bm, geom=bad, context="FACES")
bm.to_mesh(obj.data)
bm.free()
obj.data.update()
print("ALICE_BAKE removed_degenerate=%d remaining_faces=%d" % (len(bad), len(obj.data.polygons)))


INPUT_ALIASES = {
    "scale": "Scale",
    "detail": "Detail",
    "roughness": "Roughness",
    "distortion": "Distortion",
    "detail_scale": "Detail Scale",
    "detail_roughness": "Detail Roughness",
    "strength": "Strength",
    "distance": "Distance",
}


def add(nt, typ, loc=(0, 0), **props):
    n = nt.nodes.new(typ)
    n.location = loc
    for k, v in props.items():
        if hasattr(n, k):
            setattr(n, k, v)
            continue
        inp = INPUT_ALIASES.get(k, k)
        if inp in n.inputs:
            n.inputs[inp].default_value = v
            continue
        raise AttributeError("%s has no property/input %s" % (typ, k))
    return n


def link(nt, a, out, b, inp):
    nt.links.new(a.outputs[out], b.inputs[inp])


def ramp(nt, stops, loc=(0, 0)):
    n = add(nt, "ShaderNodeValToRGB", loc)
    cr = n.color_ramp
    while len(cr.elements) > 1:
        cr.elements.remove(cr.elements[-1])
    cr.elements[0].position = stops[0][0]
    cr.elements[0].color = stops[0][1]
    for pos, col in stops[1:]:
        e = cr.elements.new(pos)
        e.color = col
    return n


def math_node(nt, op, a=None, b=None, loc=(0, 0)):
    n = add(nt, "ShaderNodeMath", loc, operation=op)
    if a is not None:
        n.inputs[0].default_value = a
    if b is not None:
        n.inputs[1].default_value = b
    return n


def base_principled(mat):
    nt = mat.node_tree
    nt.nodes.clear()
    out = add(nt, "ShaderNodeOutputMaterial", (700, 0))
    bsdf = add(nt, "ShaderNodeBsdfPrincipled", (400, 0))
    link(nt, bsdf, "BSDF", out, "Surface")
    tc = add(nt, "ShaderNodeTexCoord", (-1100, 0))
    mp = add(nt, "ShaderNodeMapping", (-900, 0))
    link(nt, tc, "Object", mp, "Vector")
    return nt, out, bsdf, mp


def finish_bump(nt, bsdf, height_socket, strength, distance, loc):
    bump = add(nt, "ShaderNodeBump", loc, strength=strength, distance=distance)
    link(nt, height_socket, bump, "Height") if False else None
    return bump


def hook_bump(nt, bsdf, height_out, strength, distance, loc):
    bump = add(nt, "ShaderNodeBump", loc, strength=strength, distance=distance)
    nt.links.new(height_out, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return bump


def ao_and_edge(nt, loc=(-700, -500)):
    ao = add(nt, "ShaderNodeAmbientOcclusion", loc, samples=1, distance=0.08, only_local=True)
    ao.inputs["Distance"].default_value = 0.08
    geo = add(nt, "ShaderNodeNewGeometry", (loc[0], loc[1] - 260))
    edge = ramp(nt, [(0.48, (0, 0, 0, 1)), (0.62, (1, 1, 1, 1))], (loc[0] + 220, loc[1] - 260))
    nt.links.new(geo.outputs["Pointiness"], edge.inputs["Fac"])
    return ao, edge


def build_canvas(mat):
    nt, out, bsdf, mp = base_principled(mat)
    mp.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    noise = add(nt, "ShaderNodeTexNoise", (-700, 320), scale=7.0, detail=6.0, roughness=0.68)
    link(nt, mp, "Vector", noise, "Vector")
    col = ramp(nt, [
        (0.18, (0.055, 0.062, 0.038, 1)),
        (0.48, (0.115, 0.125, 0.078, 1)),
        (0.72, (0.165, 0.172, 0.110, 1)),
        (0.92, (0.225, 0.225, 0.155, 1)),
    ], (-480, 520))
    link(nt, noise, "Fac", col, "Fac")

    wave = add(nt, "ShaderNodeTexWave", (-700, 120), scale=220.0, distortion=1.8, detail=2.0, detail_scale=2.0, detail_roughness=0.6)
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    link(nt, mp, "Vector", wave, "Vector")
    weave = ramp(nt, [(0.30, (0.0, 0.0, 0.0, 1)), (0.70, (0.18, 0.18, 0.18, 1))], (-480, 280))
    link(nt, wave, "Fac", weave, "Fac")
    mix1 = add(nt, "ShaderNodeMixRGB", (-220, 460), blend_type="MULTIPLY")
    mix1.inputs["Fac"].default_value = 0.42
    link(nt, col, "Color", mix1, "Color1")
    link(nt, weave, "Color", mix1, "Color2")

    vor = add(nt, "ShaderNodeTexVoronoi", (-700, -120), scale=26.0)
    vor.feature = "F1"
    link(nt, mp, "Vector", vor, "Vector")
    mottle = ramp(nt, [(0.05, (0.78, 0.78, 0.78, 1)), (0.55, (1.0, 1.0, 1.0, 1))], (-470, -80))
    link(nt, vor, "Distance", mottle, "Fac")
    mix2 = add(nt, "ShaderNodeMixRGB", (30, 430), blend_type="MULTIPLY")
    mix2.inputs["Fac"].default_value = 0.22
    link(nt, mix1, "Color", mix2, "Color1")
    link(nt, mottle, "Color", mix2, "Color2")

    ao, edge = ao_and_edge(nt)
    mixao = add(nt, "ShaderNodeMixRGB", (250, 330), blend_type="MULTIPLY")
    mixao.inputs["Fac"].default_value = 0.5
    link(nt, mix2, "Color", mixao, "Color1")
    link(nt, ao, "Color", mixao, "Color2")
    edge_col = add(nt, "ShaderNodeRGB", (460, 100))
    edge_col.outputs[0].default_value = (0.30, 0.29, 0.20, 1)
    mixedge = add(nt, "ShaderNodeMixRGB", (480, 260), blend_type="MIX")
    mixedge.inputs["Fac"].default_value = 0.18
    link(nt, mixao, "Color", mixedge, "Color1")
    link(nt, edge_col, "Color", mixedge, "Color2")
    nt.links.new(mixedge.outputs["Color"], bsdf.inputs["Base Color"])

    # Roughness: 0.78-0.92, rougher in cavities, slightly polished on edges.
    rn = add(nt, "ShaderNodeTexNoise", (-500, -360), scale=90.0, detail=4.0, roughness=0.7)
    link(nt, mp, "Vector", rn, "Vector")
    rr = add(nt, "ShaderNodeMapRange", (-260, -340))
    rr.inputs["From Min"].default_value = 0.0
    rr.inputs["From Max"].default_value = 1.0
    rr.inputs["To Min"].default_value = 0.78
    rr.inputs["To Max"].default_value = 0.92
    link(nt, rn, "Fac", rr, "Value")
    inv_ao = math_node(nt, "SUBTRACT", 1.0, 0.0, (-250, -520))
    nt.links.new(ao.outputs["AO"], inv_ao.inputs[1])
    rough_ao = math_node(nt, "MULTIPLY", 0.0, 0.10, (-50, -500))
    nt.links.new(inv_ao.outputs[0], rough_ao.inputs[0])
    add1 = math_node(nt, "ADD", 0.0, 0.0, (150, -440))
    nt.links.new(rr.outputs["Result"], add1.inputs[0])
    nt.links.new(rough_ao.outputs[0], add1.inputs[1])
    edge_r = math_node(nt, "MULTIPLY", 0.0, 0.055, (150, -620))
    nt.links.new(edge.outputs["Color"], edge_r.inputs[0])
    sub = math_node(nt, "SUBTRACT", 0.0, 0.0, (340, -440))
    nt.links.new(add1.outputs[0], sub.inputs[0])
    nt.links.new(edge_r.outputs[0], sub.inputs[1])
    nt.links.new(sub.outputs[0], bsdf.inputs["Roughness"])

    # Bump: woven ribs + coarse wrinkle field, no flat white noise.
    wn = add(nt, "ShaderNodeTexNoise", (-650, -900), scale=14.0, detail=5.0, roughness=0.7)
    link(nt, mp, "Vector", wn, "Vector")
    wv = add(nt, "ShaderNodeTexWave", (-650, -1120), scale=360.0, distortion=2.2, detail=2.0)
    wv.wave_type = "BANDS"
    wv.bands_direction = "Y"
    link(nt, mp, "Vector", wv, "Vector")
    a = math_node(nt, "MULTIPLY", 0.0, 0.65, (-400, -900))
    nt.links.new(wv.outputs["Fac"], a.inputs[0])
    b = math_node(nt, "MULTIPLY", 0.0, 0.35, (-400, -1050))
    nt.links.new(wn.outputs["Fac"], b.inputs[0])
    c = math_node(nt, "ADD", 0.0, 0.0, (-180, -970))
    nt.links.new(a.outputs[0], c.inputs[0])
    nt.links.new(b.outputs[0], c.inputs[1])
    hook_bump(nt, bsdf, c.outputs[0], 0.38, 0.0016, (80, -900))
    bsdf.inputs["Metallic"].default_value = 0.0
    mat.diffuse_color = (0.16, 0.17, 0.10, 1)


def build_webbing(mat):
    nt, out, bsdf, mp = base_principled(mat)
    mp.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    noise = add(nt, "ShaderNodeTexNoise", (-700, 330), scale=45.0, detail=5.0, roughness=0.7)
    link(nt, mp, "Vector", noise, "Vector")
    col = ramp(nt, [
        (0.20, (0.060, 0.065, 0.036, 1)),
        (0.55, (0.120, 0.128, 0.075, 1)),
        (0.85, (0.190, 0.195, 0.125, 1)),
    ], (-470, 520))
    link(nt, noise, "Fac", col, "Fac")
    wave = add(nt, "ShaderNodeTexWave", (-700, 120), scale=330.0, distortion=0.8, detail=1.0)
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    link(nt, mp, "Vector", wave, "Vector")
    weave = ramp(nt, [(0.28, (0.0, 0.0, 0.0, 1)), (0.72, (0.20, 0.20, 0.20, 1))], (-470, 280))
    link(nt, wave, "Fac", weave, "Fac")
    mix = add(nt, "ShaderNodeMixRGB", (-180, 440), blend_type="MULTIPLY")
    mix.inputs["Fac"].default_value = 0.5
    link(nt, col, "Color", mix, "Color1")
    link(nt, weave, "Color", mix, "Color2")
    ao, edge = ao_and_edge(nt)
    mixao = add(nt, "ShaderNodeMixRGB", (60, 320), blend_type="MULTIPLY")
    mixao.inputs["Fac"].default_value = 0.38
    link(nt, mix, "Color", mixao, "Color1")
    link(nt, ao, "Color", mixao, "Color2")
    edge_col = add(nt, "ShaderNodeRGB", (250, 80))
    edge_col.outputs[0].default_value = (0.29, 0.28, 0.19, 1)
    mixedge = add(nt, "ShaderNodeMixRGB", (270, 270), blend_type="MIX")
    mixedge.inputs["Fac"].default_value = 0.22
    link(nt, mixao, "Color", mixedge, "Color1")
    link(nt, edge_col, "Color", mixedge, "Color2")
    nt.links.new(mixedge.outputs["Color"], bsdf.inputs["Base Color"])

    rn = add(nt, "ShaderNodeTexNoise", (-500, -350), scale=120.0, detail=4.0)
    link(nt, mp, "Vector", rn, "Vector")
    rr = add(nt, "ShaderNodeMapRange", (-260, -330))
    rr.inputs["To Min"].default_value = 0.70
    rr.inputs["To Max"].default_value = 0.84
    link(nt, rn, "Fac", rr, "Value")
    inv_ao = math_node(nt, "SUBTRACT", 1.0, 0.0, (-250, -520))
    nt.links.new(ao.outputs["AO"], inv_ao.inputs[1])
    rough_ao = math_node(nt, "MULTIPLY", 0.0, 0.10, (-50, -500))
    nt.links.new(inv_ao.outputs[0], rough_ao.inputs[0])
    add1 = math_node(nt, "ADD", 0.0, 0.0, (150, -440))
    nt.links.new(rr.outputs["Result"], add1.inputs[0])
    nt.links.new(rough_ao.outputs[0], add1.inputs[1])
    edge_r = math_node(nt, "MULTIPLY", 0.0, 0.08, (150, -620))
    nt.links.new(edge.outputs["Color"], edge_r.inputs[0])
    sub = math_node(nt, "SUBTRACT", 0.0, 0.0, (340, -440))
    nt.links.new(add1.outputs[0], sub.inputs[0])
    nt.links.new(edge_r.outputs[0], sub.inputs[1])
    nt.links.new(sub.outputs[0], bsdf.inputs["Roughness"])

    wn = add(nt, "ShaderNodeTexNoise", (-650, -900), scale=80.0, detail=4.0)
    link(nt, mp, "Vector", wn, "Vector")
    a = math_node(nt, "MULTIPLY", 0.0, 0.60, (-400, -900))
    nt.links.new(wave.outputs["Fac"], a.inputs[0])
    b = math_node(nt, "MULTIPLY", 0.0, 0.40, (-400, -1050))
    nt.links.new(wn.outputs["Fac"], b.inputs[0])
    c = math_node(nt, "ADD", 0.0, 0.0, (-180, -970))
    nt.links.new(a.outputs[0], c.inputs[0])
    nt.links.new(b.outputs[0], c.inputs[1])
    hook_bump(nt, bsdf, c.outputs[0], 0.55, 0.0015, (80, -900))
    bsdf.inputs["Metallic"].default_value = 0.0
    mat.diffuse_color = (0.14, 0.15, 0.08, 1)


def build_leather(mat):
    nt, out, bsdf, mp = base_principled(mat)
    mp.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    noise = add(nt, "ShaderNodeTexNoise", (-700, 330), scale=28.0, detail=6.0, roughness=0.7)
    link(nt, mp, "Vector", noise, "Vector")
    col = ramp(nt, [
        (0.15, (0.045, 0.026, 0.016, 1)),
        (0.55, (0.095, 0.055, 0.030, 1)),
        (0.88, (0.160, 0.095, 0.050, 1)),
    ], (-470, 520))
    link(nt, noise, "Fac", col, "Fac")
    vor = add(nt, "ShaderNodeTexVoronoi", (-700, 110), scale=70.0)
    link(nt, mp, "Vector", vor, "Vector")
    grain = ramp(nt, [(0.02, (0.15, 0.15, 0.15, 1)), (0.30, (0.42, 0.42, 0.42, 1)), (0.65, (1, 1, 1, 1))], (-470, 250))
    link(nt, vor, "Distance", grain, "Fac")
    mix = add(nt, "ShaderNodeMixRGB", (-180, 430), blend_type="MULTIPLY")
    mix.inputs["Fac"].default_value = 0.34
    link(nt, col, "Color", mix, "Color1")
    link(nt, grain, "Color", mix, "Color2")
    ao, edge = ao_and_edge(nt)
    mixao = add(nt, "ShaderNodeMixRGB", (60, 300), blend_type="MULTIPLY")
    mixao.inputs["Fac"].default_value = 0.45
    link(nt, mix, "Color", mixao, "Color1")
    link(nt, ao, "Color", mixao, "Color2")
    edge_col = add(nt, "ShaderNodeRGB", (250, 70))
    edge_col.outputs[0].default_value = (0.22, 0.135, 0.075, 1)
    mixedge = add(nt, "ShaderNodeMixRGB", (270, 250), blend_type="MIX")
    mixedge.inputs["Fac"].default_value = 0.30
    link(nt, mixao, "Color", mixedge, "Color1")
    link(nt, edge_col, "Color", mixedge, "Color2")
    nt.links.new(mixedge.outputs["Color"], bsdf.inputs["Base Color"])

    rn = add(nt, "ShaderNodeTexNoise", (-500, -350), scale=55.0, detail=5.0)
    link(nt, mp, "Vector", rn, "Vector")
    rr = add(nt, "ShaderNodeMapRange", (-260, -330))
    rr.inputs["To Min"].default_value = 0.46
    rr.inputs["To Max"].default_value = 0.64
    link(nt, rn, "Fac", rr, "Value")
    inv_ao = math_node(nt, "SUBTRACT", 1.0, 0.0, (-250, -520))
    nt.links.new(ao.outputs["AO"], inv_ao.inputs[1])
    rough_ao = math_node(nt, "MULTIPLY", 0.0, 0.08, (-50, -500))
    nt.links.new(inv_ao.outputs[0], rough_ao.inputs[0])
    add1 = math_node(nt, "ADD", 0.0, 0.0, (150, -440))
    nt.links.new(rr.outputs["Result"], add1.inputs[0])
    nt.links.new(rough_ao.outputs[0], add1.inputs[1])
    edge_r = math_node(nt, "MULTIPLY", 0.0, 0.12, (150, -620))
    nt.links.new(edge.outputs["Color"], edge_r.inputs[0])
    add2 = math_node(nt, "ADD", 0.0, 0.0, (340, -440))
    nt.links.new(add1.outputs[0], add2.inputs[0])
    nt.links.new(edge_r.outputs[0], add2.inputs[1])
    nt.links.new(add2.outputs[0], bsdf.inputs["Roughness"])

    a = math_node(nt, "MULTIPLY", 0.0, 0.7, (-400, -900))
    nt.links.new(vor.outputs["Distance"], a.inputs[0])
    b = math_node(nt, "MULTIPLY", 0.0, 0.3, (-400, -1050))
    nt.links.new(noise.outputs["Fac"], b.inputs[0])
    c = math_node(nt, "ADD", 0.0, 0.0, (-180, -970))
    nt.links.new(a.outputs[0], c.inputs[0])
    nt.links.new(b.outputs[0], c.inputs[1])
    hook_bump(nt, bsdf, c.outputs[0], 0.60, 0.0018, (80, -900))
    bsdf.inputs["Metallic"].default_value = 0.0
    mat.diffuse_color = (0.10, 0.06, 0.035, 1)


def build_metal(mat):
    nt, out, bsdf, mp = base_principled(mat)
    mp.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    noise = add(nt, "ShaderNodeTexNoise", (-700, 330), scale=70.0, detail=5.0, roughness=0.7)
    link(nt, mp, "Vector", noise, "Vector")
    col = ramp(nt, [
        (0.15, (0.020, 0.024, 0.028, 1)),
        (0.55, (0.060, 0.068, 0.075, 1)),
        (0.88, (0.135, 0.145, 0.155, 1)),
    ], (-470, 520))
    link(nt, noise, "Fac", col, "Fac")
    ao, edge = ao_and_edge(nt)
    mixao = add(nt, "ShaderNodeMixRGB", (60, 300), blend_type="MULTIPLY")
    mixao.inputs["Fac"].default_value = 0.6
    link(nt, col, "Color", mixao, "Color1")
    link(nt, ao, "Color", mixao, "Color2")
    edge_col = add(nt, "ShaderNodeRGB", (250, 70))
    edge_col.outputs[0].default_value = (0.30, 0.31, 0.33, 1)
    mixedge = add(nt, "ShaderNodeMixRGB", (270, 250), blend_type="MIX")
    mixedge.inputs["Fac"].default_value = 0.35
    link(nt, mixao, "Color", mixedge, "Color1")
    link(nt, edge_col, "Color", mixedge, "Color2")
    nt.links.new(mixedge.outputs["Color"], bsdf.inputs["Base Color"])

    scratch = add(nt, "ShaderNodeTexNoise", (-650, -300), scale=520.0, detail=4.0, roughness=0.8)
    link(nt, mp, "Vector", scratch, "Vector")
    sr = add(nt, "ShaderNodeValToRGB", (-400, -300))
    sr.color_ramp.elements[0].position = 0.30
    sr.color_ramp.elements[0].color = (0.15, 0.15, 0.15, 1)
    sr.color_ramp.elements[1].position = 0.72
    sr.color_ramp.elements[1].color = (0.55, 0.55, 0.55, 1)
    link(nt, scratch, "Fac", sr, "Fac")
    base_r = add(nt, "ShaderNodeMapRange", (-170, -300))
    base_r.inputs["To Min"].default_value = 0.28
    base_r.inputs["To Max"].default_value = 0.52
    link(nt, sr, "Color", base_r, "Value")
    # Edge polishing reduces roughness; cavities hold dirt and roughness.
    edge_r = math_node(nt, "MULTIPLY", 0.0, 0.18, (60, -250))
    nt.links.new(edge.outputs["Color"], edge_r.inputs[0])
    inv_ao = math_node(nt, "SUBTRACT", 1.0, 0.0, (60, -430))
    nt.links.new(ao.outputs["AO"], inv_ao.inputs[1])
    ao_r = math_node(nt, "MULTIPLY", 0.0, 0.12, (250, -430))
    nt.links.new(inv_ao.outputs[0], ao_r.inputs[0])
    a = math_node(nt, "ADD", 0.0, 0.0, (250, -300))
    nt.links.new(base_r.outputs["Result"], a.inputs[0])
    nt.links.new(ao_r.outputs[0], a.inputs[1])
    b = math_node(nt, "SUBTRACT", 0.0, 0.0, (430, -300))
    nt.links.new(a.outputs[0], b.inputs[0])
    nt.links.new(edge_r.outputs[0], b.inputs[1])
    nt.links.new(b.outputs[0], bsdf.inputs["Roughness"])

    wv = add(nt, "ShaderNodeTexWave", (-650, -850), scale=450.0, distortion=3.0, detail=2.0)
    wv.wave_type = "BANDS"
    wv.bands_direction = "X"
    link(nt, mp, "Vector", wv, "Vector")
    hook_bump(nt, bsdf, wv.outputs["Fac"], 0.18, 0.0008, (80, -800))
    bsdf.inputs["Metallic"].default_value = 1.0
    mat.diffuse_color = (0.07, 0.075, 0.08, 1)


BUILDERS = {
    "M_Alice_Canvas": build_canvas,
    "M_Alice_Webbing": build_webbing,
    "M_Alice_Leather": build_leather,
    "M_Alice_Metal": build_metal,
}
for name, fn in BUILDERS.items():
    mat = bpy.data.materials.get(name)
    assert mat, name
    fn(mat)
    print("ALICE_BAKE shader " + name)

if os.environ.get("ALICE_SKIP_BAKE") == "1":
    print("ALICE_BAKE shader-only validation passed")
    raise SystemExit(0)

# Render/bake setup.
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.render.bake.margin = 16
scene.render.bake.use_clear = True
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
if not scene.world:
    scene.world = bpy.data.worlds.new("AliceBakeWorld")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.8, 0.8, 0.8, 1)
    bg.inputs[1].default_value = 1.0

# Bake one isolated object per material, all sharing the same atlas.
base_obj = obj
base_obj.hide_render = True
base_obj.hide_set(True)
bake_objects = []
for mi, name in enumerate(["Canvas", "Webbing", "Leather", "Metal"]):
    dup = base_obj.copy()
    dup.data = base_obj.data.copy()
    bpy.context.collection.objects.link(dup)
    dup.name = "Bake_" + name
    bm = bmesh.new()
    bm.from_mesh(dup.data)
    bm.faces.ensure_lookup_table()
    bad = [f for f in bm.faces if f.material_index != mi]
    bmesh.ops.delete(bm, geom=bad, context="FACES")
    bm.to_mesh(dup.data)
    bm.free()
    dup.data.materials.clear()
    dup.data.materials.append(bpy.data.materials["M_Alice_" + name])
    for p in dup.data.polygons:
        p.material_index = 0
    dup.hide_render = False
    dup.hide_set(False)
    bake_objects.append((name, dup))
    print("ALICE_BAKE object %s faces=%d" % (name, len(dup.data.polygons)))

for name, dup in bake_objects:
    mat = bpy.data.materials["M_Alice_" + name]
    nt = mat.node_tree
    res = RES[name]
    pass_images = {}
    for kind, cs in [("BaseColor", "sRGB"), ("Normal", "Non-Color"), ("Roughness", "Non-Color"), ("AO", "Non-Color")]:
        img = bpy.data.images.new("T_Alice_%s_%s" % (name, kind), width=res, height=res, alpha=False, float_buffer=False)
        img.colorspace_settings.name = cs
        img.generated_color = (0, 0, 0, 1)
        pass_images[kind] = img
    tex_node = nt.nodes.new("ShaderNodeTexImage")
    tex_node.name = "BakeTarget"
    tex_node.location = (900, -200)
    nt.nodes.active = tex_node
    for n in nt.nodes:
        n.select = False
    tex_node.select = True
    bpy.ops.object.select_all(action="DESELECT")
    dup.select_set(True)
    bpy.context.view_layer.objects.active = dup

    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for kind in ["BaseColor", "Normal", "Roughness", "AO"]:
        img = pass_images[kind]
        tex_node.image = img
        scene.cycles.samples = SAMPLES[kind]
        scene.cycles.use_denoising = False
        print("ALICE_BAKE start %s %s %d" % (name, kind, res))
        if kind == "BaseColor":
            scene.render.bake.use_pass_direct = False
            scene.render.bake.use_pass_indirect = False
            scene.render.bake.use_pass_color = True
            # Diffuse color is black on metals; temporarily disable metallic
            # so the albedo pass carries the steel colour into BaseColor.
            metallic = bsdf.inputs["Metallic"].default_value
            bsdf.inputs["Metallic"].default_value = 0.0
            bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=16, use_clear=True)
            bsdf.inputs["Metallic"].default_value = metallic
        elif kind == "Normal":
            bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", margin=16, use_clear=True)
        elif kind == "Roughness":
            bpy.ops.object.bake(type="ROUGHNESS", margin=16, use_clear=True)
        else:
            bpy.ops.object.bake(type="AO", margin=16, use_clear=True)
        path = os.path.join(TEX_DIR, "T_Alice_%s_%s.png" % (name, kind))
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        print("ALICE_BAKE saved " + path)

# Restore original object for export.
base_obj.hide_render = False
base_obj.hide_set(False)
for _, dup in bake_objects:
    bpy.data.objects.remove(dup, do_unlink=True)
bpy.ops.object.select_all(action="DESELECT")
base_obj.select_set(True)
bpy.context.view_layer.objects.active = base_obj
OUT_BLEND = os.environ.get("ALICE_BAKE_OUT_BLEND", os.path.join(OUT_DIR, "AliceBackpack_baked.blend"))
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
bpy.ops.wm.obj_export(
    filepath=os.environ.get("ALICE_BAKE_OUT_OBJ", os.path.join(OUT_DIR, "AliceBackpack_baked.obj")),
    export_selected_objects=True,
    apply_modifiers=True,
    export_uv=True,
    export_normals=True,
    export_materials=True,
    path_mode="AUTO",
)

receipt = {
    "removed_degenerate_faces": len(bad) if False else None,
    "textures": {},
    "faces": len(base_obj.data.polygons),
    "uv_layers": [layer.name for layer in base_obj.data.uv_layers],
}
for name in ["Canvas", "Webbing", "Leather", "Metal"]:
    receipt["textures"][name] = {
        "resolution": RES[name],
        "files": ["T_Alice_%s_%s.png" % (name, k) for k in ["BaseColor", "Normal", "Roughness", "AO"]],
    }
RECEIPT = os.environ.get("ALICE_BAKE_RECEIPT", os.path.join(OUT_DIR, "bake_receipt.json"))
with open(RECEIPT, "w", encoding="utf-8") as f:
    json.dump(receipt, f, ensure_ascii=False, indent=2)
print("ALICE_BAKE_DONE " + json.dumps(receipt, ensure_ascii=False, default=str))
