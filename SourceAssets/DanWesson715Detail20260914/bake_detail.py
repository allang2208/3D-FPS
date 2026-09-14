"""Bake the existing 715 surface, preserving runtime geometry and every action."""
import ast
import json
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

O = Path(__file__).parent; S = O.parent; T = O/'Textures'; T.mkdir(exist_ok=True)
sys.path.insert(0, str(O))
from surface_material import author_material, FINISH, PART_ROUGHNESS
bpy.context.preferences.filepaths.save_version = 0
SOURCE = S/'DanWesson715Mirror20260914/DanWesson715_Mirror_Editable.blend'
try: bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error): raise
s = bpy.context.scene; rig = bpy.data.objects['SK_DW715_Manny']
inverse_bind = rig.data.bones['WPN_root'].matrix_local.inverted()
prior = json.loads((S/'DanWesson715Mirror20260914/textures.json').read_text())
visibility = {ob:(ob.hide_render, ob.hide_get()) for ob in s.objects}
collection_visibility = {col:col.hide_render for col in bpy.data.collections}
for col in bpy.data.collections: col.hide_render = False
for ob in s.objects:
    if ob.type == 'MESH': ob.hide_render = True

def activate(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects: ob.hide_set(False); ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[-1]

tree = ast.parse((S/'M1911Hero20260913/build.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'emit'], type_ignores=[]), 'existing_emit_routing', 'exec'))

def source_object(name):
    if name in ('DW715_Frame','DW715_BarrelShroud','DW715_FrameLatch','DW715_RearLatch'): return 'DW_BaseModel'
    for prefix in ('DW_Trigger','DW_Hummer','DW_MagazineAssembly'):
        if name.startswith('DW715_'+prefix): return prefix
    return None

normal_sources = {}
def restore_author_normals(high, original_name):
    """Carry the supplied corner normals into the high author's source basis.

    No runtime low mesh is changed. Coplanar dissolve in the old author pipeline
    can merge faces; matching positions and SourceUV keeps source seams distinct.
    """
    if original_name not in normal_sources:
        ob = bpy.data.objects[original_name]
        transform = inverse_bind @ ob.matrix_world
        normal_matrix = transform.to_3x3().inverted().transposed()
        coords = [transform @ v.co for v in ob.data.vertices]
        kd = KDTree(len(coords))
        for i, co in enumerate(coords): kd.insert(co, i)
        kd.balance()
        corners = [[] for _ in coords]
        uv = ob.data.uv_layers.active
        for poly in ob.data.polygons:
            face = (normal_matrix @ poly.normal).normalized()
            for li in poly.loop_indices:
                loop = ob.data.loops[li]
                corners[loop.vertex_index].append((uv.data[li].uv.copy(), (normal_matrix @ ob.data.corner_normals[li].vector).normalized(), face))
        normal_sources[original_name] = kd, corners
    kd, corners = normal_sources[original_name]
    uv = high.data.uv_layers['SourceUV']
    normals = [item.vector.copy() for item in high.data.corner_normals]
    restored = 0
    for poly in high.data.polygons:
        for li in poly.loop_indices:
            point = high.data.vertices[high.data.loops[li].vertex_index].co
            candidates = kd.find_range(point, .000002)
            matches = [entry for _, vi, _ in candidates for entry in corners[vi]]
            if not matches: continue
            item = min(matches, key=lambda x:(x[0]-uv.data[li].uv).length_squared*1000 + (1-x[2].dot(poly.normal))*.001)
            normals[li] = item[1]; restored += 1
    high.data.normals_split_custom_set(normals)
    for mod in list(high.modifiers):
        if mod.type == 'WEIGHTED_NORMAL': high.modifiers.remove(mod)
    return dict(source=original_name, restored_corners=restored, corners=len(normals))

s.render.engine = 'CYCLES'; s.cycles.samples = 16; s.cycles.use_denoising = False
s.render.bake.margin = 16; s.render.bake.use_selected_to_active = True; s.render.bake.use_clear = False
s.render.bake.cage_extrusion = .00065; s.render.bake.max_ray_distance = .002
s.render.bake.normal_space = 'TANGENT'
s.render.bake.normal_r, s.render.bake.normal_g, s.render.bake.normal_b = 'POS_X', 'POS_Y', 'POS_Z'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
for device in prefs.devices: device.use = device.type == 'OPTIX'
s.cycles.device = 'GPU' if any(d.use for d in prefs.devices) else 'CPU'

def bake_mesh(objects, label, high):
    for ob in objects: ob.hide_set(False)
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    copies = []
    for index, ob in enumerate(objects):
        mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg) if high else ob.data.copy()
        if not high: mesh.transform(inverse_bind)
        # Equal translations isolate each pair; identity rotation retains all
        # source/target tangent bases and does not change texture coordinates.
        mesh.transform(Matrix.Translation(Vector((index*.5, 0, 0))))
        copy = bpy.data.objects.new(label+'_part', mesh); s.collection.objects.link(copy); copies.append(copy)
    activate(copies); bpy.ops.object.join(); result = bpy.context.object; result.name = label
    return result

manifest = {}; production = dict(source=str(SOURCE), reference='QBZ191Hero20260913', geometry='Runtime mesh unchanged; material-only copy', author_normals={}, parts={}, testing='Not run')
for group, info in prior.items():
    lows = [bpy.data.objects[name] for name in info['objects']]
    highs = [bpy.data.objects[name+'_HIGH'] for name in info['objects']]
    for low, high in zip(lows, highs):
        original_name = source_object(low.name)
        if original_name:
            production['author_normals'][low.name] = restore_author_normals(high, original_name)
        for i, old in enumerate(high.data.materials):
            if 'DarkInterior' in old.name: continue
            mat = author_material(group, low.name, original_name is not None)
            high.data.materials[i] = mat
            production['parts'][low.name] = dict(roughness=mat['roughness_center'], structural=bool(mat['structure_strength']))
    bl = bake_mesh(lows, 'TEMP_DETAIL_LOW', False); bh = bake_mesh(highs, 'TEMP_DETAIL_HIGH', True)
    for high in highs: high.hide_set(True)
    bl.data.uv_layers.active = bl.data.uv_layers['HeroUV']; bl.data.uv_layers.active.active_render = True
    target = bpy.data.materials.new('BAKE_DETAIL_TARGET_'+group); target.use_nodes = True
    bl.data.materials.clear(); bl.data.materials.append(target)
    for poly in bl.data.polygons: poly.material_index = 0
    maps = {}
    for kind in ('BaseColor', 'ORM', 'Normal'):
        name = 'T_DW715_Detail_'+group+'_'+('NormalGL' if kind == 'Normal' else kind)
        im = bpy.data.images.new(name, width=4096, height=4096, alpha=False)
        im.colorspace_settings.name = 'sRGB' if kind == 'BaseColor' else 'Non-Color'
        im.generated_color = (.5,.5,1,1) if kind == 'Normal' else (1,FINISH[group]['rough'],1,1) if kind == 'ORM' else (*FINISH[group]['base'],1)
        nodes = target.node_tree.nodes; tex = nodes.get('BAKE_TARGET') or nodes.new('ShaderNodeTexImage')
        tex.name = 'BAKE_TARGET'; tex.image = im; nodes.active = tex
        emit(bh, kind); bl.hide_render = False; bh.hide_render = False; activate([bh,bl])
        bpy.ops.object.bake(type='NORMAL' if kind == 'Normal' else 'EMIT')
        bl.hide_render = True; bh.hide_render = True
        im.filepath_raw = str(T/(name+'.png')); im.file_format = 'PNG'; im.save(); maps[kind] = im
        print('DW715_DETAIL_BAKED', group, kind, flush=True)
    emit(bh, 'Normal'); bpy.data.objects.remove(bl, do_unlink=True); bpy.data.objects.remove(bh, do_unlink=True)
    # Keep the existing material-slot names for optional future exports.
    existing = bpy.data.materials.get(info['slot'])
    if existing: existing.name = info['slot']+'_MirrorPrevious'
    mat = bpy.data.materials.new(info['slot']); mat.use_nodes = True
    n,l = mat.node_tree.nodes,mat.node_tree.links; bs = next(x for x in n if x.type == 'BSDF_PRINCIPLED')
    uv = n.new('ShaderNodeUVMap'); uv.uv_map = 'HeroUV'
    for kind, im in maps.items():
        tex = n.new('ShaderNodeTexImage'); tex.image = im; l.new(uv.outputs[0],tex.inputs['Vector'])
        if kind == 'BaseColor': l.new(tex.outputs[0],bs.inputs['Base Color'])
        elif kind == 'Normal':
            normal = n.new('ShaderNodeNormalMap'); normal.uv_map = 'HeroUV'; l.new(tex.outputs[0],normal.inputs['Color']); l.new(normal.outputs[0],bs.inputs['Normal'])
        else:
            split = n.new('ShaderNodeSeparateColor'); l.new(tex.outputs[0],split.inputs[0]); l.new(split.outputs[1],bs.inputs['Roughness']); l.new(split.outputs[2],bs.inputs['Metallic'])
    for low in lows: low.data.materials[0] = mat
    manifest[group] = dict(size=4096, slot=info['slot'], material='M_DW715_Detail_'+group, textures={k:im.filepath_raw for k,im in maps.items()}, objects=info['objects'])
    (O/'textures.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

for ob,(render,hidden) in visibility.items(): ob.hide_render = render; ob.hide_set(hidden)
for col,hidden in collection_visibility.items(): col.hide_render = hidden
(O/'production.json').write_text(json.dumps(production,indent=2),encoding='utf-8')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_Detail_Editable.blend'))
print('DW715_DETAIL_SOURCE_COMPLETE', flush=True)
