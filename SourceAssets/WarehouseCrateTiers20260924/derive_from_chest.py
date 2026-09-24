"""Derive the five tier crates FROM the real warehouse chest geometry (RitualV8 GLB).

The from-scratch procedural crates were rejected as below bar ("模型不达标"), so the tier
set keeps the chest's own silhouette and detail and differs only by material zoning:
  T1 木箱 / T2 石饰木箱 / T3 铁箱 / T4 金纹铁箱 / T5 宝石银箱（金花纹＋蓝宝石原样保留）

Pipeline (background Blender run):
  import GLB -> apply armature at REST (verified closed pose) -> join body+lid+latch
  -> scale x100 to cm units (front -Y, ground pivot) -> angle-based smoothing groups
  -> planar UV in metres -> per tier: duplicate, remap slots to Crate_* names, triangulate, export FBX.
Slot roles came from chest_source_report.json (frame rails, arch straps, rear hinges +Y,
latch -Y, medallion gems, front champagne/gunmetal/engraving ornaments).
"""
import bpy, json, math
from mathutils import Vector
from pathlib import Path

HERE = Path(__file__).parent
GLB = HERE.parent / 'ChestRitual20260909' / 'warehouse_chest_ritual_v8.glb'
AUTHORED = HERE / 'Authored'
AUTHORED.mkdir(exist_ok=True)
SLOT_BASE = {  # crate slot -> viewport tint only; UE binds by NAME
    'Crate_Wood': (0.45, 0.28, 0.14), 'Crate_WoodDark': (0.25, 0.15, 0.08),
    'Crate_Stone': (0.55, 0.55, 0.54), 'Crate_Iron': (0.48, 0.49, 0.51),
    'Crate_IronDark': (0.20, 0.21, 0.23), 'Crate_Gold': (0.85, 0.60, 0.20),
    'Crate_Silver': (0.75, 0.78, 0.82), 'Crate_Gem': (0.02, 0.10, 0.55),
}
SLOT_ORDER = ['Crate_Wood', 'Crate_WoodDark', 'Crate_Stone', 'Crate_Iron', 'Crate_IronDark',
              'Crate_Gold', 'Crate_Silver', 'Crate_Gem']
TIERS = {
    'T1_Wood': {
        'White_Marble_PBR': 'Crate_Wood', 'Brass_Frame': 'Crate_WoodDark', 'Brass_Strap': 'Crate_WoodDark',
        'Brass_Hardware': 'Crate_IronDark', 'Gold_PBR': 'Crate_WoodDark', 'Sapphire_PBR': 'Crate_WoodDark',
        'Navy_Velvet': 'Crate_WoodDark', 'Interior_Magic_Blue': 'Crate_WoodDark',
        'Ritual_Champagne': 'Crate_WoodDark', 'Ritual_Gunmetal': 'Crate_Wood', 'Ritual_Engraving': 'Crate_IronDark'},
    'T2_StoneWood': {
        'White_Marble_PBR': 'Crate_Wood', 'Brass_Frame': 'Crate_Stone', 'Brass_Strap': 'Crate_Stone',
        'Brass_Hardware': 'Crate_Iron', 'Gold_PBR': 'Crate_Stone', 'Sapphire_PBR': 'Crate_IronDark',
        'Navy_Velvet': 'Crate_WoodDark', 'Interior_Magic_Blue': 'Crate_WoodDark',
        'Ritual_Champagne': 'Crate_Stone', 'Ritual_Gunmetal': 'Crate_Stone', 'Ritual_Engraving': 'Crate_IronDark'},
    'T3_Iron': {
        'White_Marble_PBR': 'Crate_Iron', 'Brass_Frame': 'Crate_Iron', 'Brass_Strap': 'Crate_Iron',
        'Brass_Hardware': 'Crate_IronDark', 'Gold_PBR': 'Crate_IronDark', 'Sapphire_PBR': 'Crate_IronDark',
        'Navy_Velvet': 'Crate_IronDark', 'Interior_Magic_Blue': 'Crate_IronDark',
        'Ritual_Champagne': 'Crate_Iron', 'Ritual_Gunmetal': 'Crate_IronDark', 'Ritual_Engraving': 'Crate_IronDark'},
    'T4_IronGold': {
        'White_Marble_PBR': 'Crate_Iron', 'Brass_Frame': 'Crate_Gold', 'Brass_Strap': 'Crate_Gold',
        'Brass_Hardware': 'Crate_Gold', 'Gold_PBR': 'Crate_Gold', 'Sapphire_PBR': 'Crate_IronDark',
        'Navy_Velvet': 'Crate_IronDark', 'Interior_Magic_Blue': 'Crate_IronDark',
        'Ritual_Champagne': 'Crate_Gold', 'Ritual_Gunmetal': 'Crate_IronDark', 'Ritual_Engraving': 'Crate_Gold'},
    'T5_SilverGem': {
        'White_Marble_PBR': 'Crate_Silver', 'Brass_Frame': 'Crate_Gold', 'Brass_Strap': 'Crate_Gold',
        'Brass_Hardware': 'Crate_Gold', 'Gold_PBR': 'Crate_Gold', 'Sapphire_PBR': 'Crate_Gem',
        'Navy_Velvet': 'Crate_IronDark', 'Interior_Magic_Blue': 'Crate_IronDark',
        'Ritual_Champagne': 'Crate_Gold', 'Ritual_Gunmetal': 'Crate_Silver', 'Ritual_Engraving': 'Crate_Gold'},
}

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 0.01
bpy.ops.import_scene.gltf(filepath=str(GLB))

# --- collapse to one static closed mesh -----------------------------------
mesh_objs = [o for o in scene.objects if o.type == 'MESH']
armatures = [o for o in scene.objects if o.type == 'ARMATURE']
assert len(mesh_objs) == 3, 'expected body+lid+latch, got %s' % [o.name for o in mesh_objs]
# local mesh data sits in DCC units; the parented world transform carries the
# metres scale. Derive the exact local->cm factor per object BEFORE touching parents.
factors = {}
for obj in mesh_objs:
    local = [max(c[i] for c in obj.bound_box) - min(c[i] for c in obj.bound_box) for i in range(3)]
    f = [obj.dimensions[i] * 100.0 / max(local[i], 1e-9) for i in range(3)]
    if not all(abs(f[i] - f[0]) < 1e-3 for i in range(3)):
        raise RuntimeError('%s non-uniform local->cm scale %s' % (obj.name, f))
    factors[obj.name] = f[0]
print('LOCAL_TO_CM factors: %s' % {k: round(v, 4) for k, v in factors.items()}, flush=True)
for obj in mesh_objs:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    if obj.data.shape_keys:
        obj.shape_key_clear()  # modifier_apply refuses shape keys; static closed copy needs none
    for mod in list(obj.modifiers):
        if mod.type == 'ARMATURE':
            bpy.ops.object.modifier_apply(modifier=mod.name)  # rest pose = closed
for arm in armatures:
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs:
        obj.select_set(True); bpy.context.view_layer.objects.active = obj
        bpy.ops.object.parent_clear(type='CLEAR')  # drop parent WITHOUT baking its transform
    bpy.data.objects.remove(arm, do_unlink=True)
for act in list(bpy.data.actions):
    if act.users == 0:
        bpy.data.actions.remove(act)

# --- join in world space FIRST (hierarchy intact, assembly exact) -----------
bpy.ops.object.select_all(action='DESELECT')
for obj in mesh_objs: obj.select_set(True)
bpy.context.view_layer.objects.active = mesh_objs[0]
bpy.ops.object.join()
chest = bpy.context.object
chest.name = 'WarehouseChest_Closed'
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# Normalise empirically: the GLB's world X extent measured 1.512 m (chest_source_report);
# whatever unit chain the importer+skinning left, scale so the join's X equals 151.2 cm.
f = 151.2 / max(chest.dimensions)
chest.scale = (f, f, f)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
dims0 = [round(v, 2) for v in chest.dimensions]
print('ASSEMBLED_CHEST dims_cm=%s (normaliser %.4f applied to %s)' % (
      dims0, f, 'join-unit'), flush=True)
assert abs(chest.dimensions.x - 151.2) < 0.5, 'chest X not 151 cm: %s' % dims0
zs = [v.co.z for v in chest.data.vertices]
bpy.context.scene.cursor.location = (0.0, 0.0, min(zs))
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

# drop skinning/colour artifacts, keep one UV (planar replaces it)
for uv in list(chest.data.uv_layers): chest.data.uv_layers.remove(uv)
for vc in list(chest.data.vertex_colors): chest.data.vertex_colors.remove(vc)
# clear the gltf's custom split normals so the angle-based smoothing groups below are
# what the FACE export carries into UE
bpy.ops.object.select_all(action='DESELECT')
chest.select_set(True); bpy.context.view_layer.objects.active = chest
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
try:
    cleared = str(bpy.ops.mesh.customdata_custom_splitnormals_clear())
except Exception as exc:  # operator absent/no data: report honestly, keep imported normals
    cleared = 'skipped: %s' % exc
bpy.ops.object.mode_set(mode='OBJECT')

# ground pivot at footprint centre
zs = [v.co.z for v in chest.data.vertices]
bpy.context.scene.cursor.location = (0.0, 0.0, min(zs))
bpy.ops.object.select_all(action='DESELECT')
chest.select_set(True); bpy.context.view_layer.objects.active = chest
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

# smoothing groups by edge angle (classic face-smooth flags; FBX FACE export).
# Built from polygon edge_keys: MeshEdge.link_polygons does not exist in Blender 5.1.
me = chest.data
for poly in me.polygons: poly.use_smooth = True
me.update()
THRESH = math.radians(40.0)
edge_polys = {}
for pi, poly in enumerate(me.polygons):
    for ek in poly.edge_keys:
        edge_polys.setdefault((min(ek), max(ek)), []).append(pi)
sharp_edges = 0
for ek, polys in edge_polys.items():
    if len(polys) == 2 and me.polygons[polys[0]].normal.angle(me.polygons[polys[1]].normal) > THRESH:
        me.polygons[polys[0]].use_smooth = False
        me.polygons[polys[1]].use_smooth = False
        sharp_edges += 1
print('SMOOTHING face angle>40deg sharp edges: %d of %d' % (sharp_edges, len(edge_polys)), flush=True)

def planar_uv(mesh_obj):
    uv = mesh_obj.data.uv_layers.new(name='UV0_Physical')
    m = mesh_obj.data
    for face in m.polygons:
        axis = max(range(3), key=lambda i: abs(face.normal[i]))
        for index in face.loop_indices:
            p = m.vertices[m.loops[index].vertex_index].co / 100.0
            uv.data[index].uv = (p.y, p.z) if axis == 0 else (p.x, p.z) if axis == 1 else (p.x, p.y)

planar_uv(chest)

# --- per-tier material zoning + export -------------------------------------
mats = {}
for name, tint in SLOT_BASE.items():
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf: bsdf.inputs['Base Color'].default_value = (*tint, 1.0)
    mats[name] = mat

source_slots = [m.name.split('.')[0] if m else None for m in chest.data.materials]
receipt = {'source_glb': GLB.name, 'source_slots': [m.name for m in chest.data.materials],
           'closed_rest_pose': True, 'split_normals_clear': cleared, 'unit': 'cm', 'front': '-Y',
           'tiers': {}}

for tier, mapping in TIERS.items():
    unknown = [s for s in mapping if s not in source_slots]
    if unknown:
        raise RuntimeError('Tier %s references slots missing from the GLB: %s' % (tier, unknown))
    dup = chest.copy(); dup.data = chest.data.copy(); dup.name = 'SM_WarehouseCrate_' + tier
    scene.collection.objects.link(dup)
    orig = [poly.material_index for poly in dup.data.polygons]  # BEFORE clear() clamps
    base = [source_slots[i] for i in orig]
    order = sorted({mapping[b] for b in base}, key=SLOT_ORDER.index)
    dup.data.materials.clear()
    for s in order: dup.data.materials.append(mats[s])
    for poly, b in zip(dup.data.polygons, base):
        poly.material_index = order.index(mapping[b])
    tri = dup.modifiers.new('ExportTriangles', 'TRIANGULATE')
    bpy.ops.object.select_all(action='DESELECT')
    dup.select_set(True); bpy.context.view_layer.objects.active = dup
    bpy.ops.object.modifier_apply(modifier=tri.name)
    dims = dup.dimensions
    out = AUTHORED / ('SM_WarehouseCrate_%s.fbx' % tier)
    bpy.ops.object.select_all(action='DESELECT')
    dup.select_set(True); bpy.context.view_layer.objects.active = dup
    bpy.ops.export_scene.fbx(filepath=str(out), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='-Y', axis_up='Z', object_types={'MESH'}, mesh_smooth_type='FACE',
                             bake_anim=False, path_mode='COPY', embed_textures=False)
    receipt['tiers'][tier] = {'fbx': out.name, 'tris': len(dup.data.polygons),
                              'size_cm': [round(dims[i], 1) for i in range(3)], 'slots': order}
    print('DERIVED %s tris=%d size=%s slots=%s' % (tier, len(dup.data.polygons),
          [round(v, 1) for v in dims], order), flush=True)
    mesh_data = dup.data  # grab the block pointer BEFORE removing the object
    bpy.data.objects.remove(dup, do_unlink=True)
    bpy.data.meshes.remove(mesh_data)

bpy.ops.wm.save_as_mainfile(filepath=str(AUTHORED / 'WarehouseChestDerived.blend'))
(HERE / 'derive_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
print('DERIVE_DONE ' + json.dumps({t: v['tris'] for t, v in receipt['tiers'].items()}), flush=True)
