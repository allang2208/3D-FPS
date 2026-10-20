"""Commandlet (UE closed): install the M4 bare-skin V9 sample on the live viewmodel.

1. textures, scatter profile, M_M4SkinV9 + MI_M4SkinV9 under /Game/Characters/ModularOutfit20260924/BareSkinV9M4/
2. SK_M4_FoldingSights_HK416 skin: V9 rest positions, normals, new UV0, wrist/elbow-join weight denoise
3. 14 JC_ corrective morphs (driven at runtime by UFPSArmJointCorrectiveComponent)
4. skin slots 6/7 -> MI_M4SkinV9; weapon parts, skeleton, other UV channels and LOD count untouched
The asset must still match the V8 read-back hash; the original package is copied to Before/ first.
"""
import json, hashlib, shutil
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME'); R = P / 'SourceAssets/BareSkinV9M4_20261017'
DEST = '/Game/Characters/ModularOutfit20260924/BareSkinV9M4'
E = u.EditorAssetLibrary; L = u.MaterialEditingLibrary; A = u.AssetToolsHelpers.get_asset_tools()
G = u.GeometryScript_AssetUtils; Q = u.GeometryScript_MeshQueries; Ed = u.GeometryScript_MeshEdits; Bw = u.GeometryScript_BoneWeights
receipt = dict(saved=[], runtime_tested=False, visual_acceptance='pending user test')


def disk(path): return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha(f):
    h = hashlib.sha256()
    with open(f, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def save(asset):
    if not E.save_loaded_asset(asset, False): raise RuntimeError('Cannot save ' + asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())


pay = json.loads((R / 'Work/install_payload.json').read_text())
MESH = pay['mesh']
if sha(disk(MESH)) != pay['asset_sha256']: raise RuntimeError('Viewmodel changed since the V8 read-back; nothing written')
backup = R / 'Before' / disk(MESH).relative_to(P); backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists(): shutil.copy2(disk(MESH), backup)

# ---------------------------------------------------------------- textures
def texture(name, srgb, compression):
    task = u.AssetImportTask(); task.filename = str(R / 'Textures' / (name + '.png')); task.destination_path = DEST + '/Textures'
    task.destination_name = name; task.automated = True; task.replace_existing = True; task.save = False; task.factory = u.TextureFactory()
    A.import_asset_tasks([task]); tex = u.load_asset(DEST + '/Textures/' + name)
    if not tex: raise RuntimeError('Texture import failed ' + name)
    tex.set_editor_property('srgb', srgb); tex.set_editor_property('compression_settings', compression)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_CHARACTER)
    if compression == u.TextureCompressionSettings.TC_NORMALMAP: tex.set_editor_property('flip_green_channel', False)
    save(tex); return tex


colour = texture('T_M4SkinV9_Colour', True, u.TextureCompressionSettings.TC_DEFAULT)
normal = texture('T_M4SkinV9_Normal', False, u.TextureCompressionSettings.TC_NORMALMAP)
masks = texture('T_M4SkinV9_Masks', False, u.TextureCompressionSettings.TC_MASKS)

# ---------------------------------------------------------------- scatter profile + material
profile = u.load_asset(DEST + '/SSP_M4SkinV9')
if not profile:
    profile = A.duplicate_asset('SSP_M4SkinV9', DEST, u.load_asset('/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4SurfaceV5/SSP_M4UnifiedSkin'))
st = profile.get_editor_property('settings'); st.set_editor_property('mean_free_path_distance', .25)
profile.set_editor_property('settings', st); save(profile)
mat = u.load_asset(DEST + '/M_M4SkinV9') or A.create_asset('M_M4SkinV9', DEST, u.Material, u.MaterialFactoryNew())
L.delete_all_material_expressions(mat)


def node(cls, **props):
    n = L.create_material_expression(mat, cls)
    for k, v in props.items(): n.set_editor_property(k, v)
    return n


def scalar(name, value): return node(u.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)


def sample(name, tex, kind): return node(u.MaterialExpressionTextureSampleParameter2D, parameter_name=name, texture=tex, sampler_type=kind)


code = (R / 'skin_v9.hlsl').read_text()
inputs = {'Colour': (sample('SkinColour', colour, u.MaterialSamplerType.SAMPLERTYPE_COLOR), 'RGB'),
          'NormalSample': (sample('SkinNormal', normal, u.MaterialSamplerType.SAMPLERTYPE_NORMAL), 'RGB'),
          'Masks': (sample('SkinMasks', masks, u.MaterialSamplerType.SAMPLERTYPE_MASKS), 'RGBA'),
          'Tint': (node(u.MaterialExpressionVectorParameter, parameter_name='SkinTint', default_value=u.LinearColor(1, 1, 1, 1)), 'RGB'),
          'NormalStrength': (scalar('NormalStrength', 1.0), ''), 'RoughnessScale': (scalar('RoughnessScale', 1.0), ''),
          'RoughnessOffset': (scalar('RoughnessOffset', 0.0), ''), 'SkinSpecular': (scalar('SkinSpecular', .35), ''),
          'CavitySpecular': (scalar('CavitySpecular', .7), ''), 'AOStrength': (scalar('AOStrength', .6), ''),
          'ScatterStrength': (scalar('ScatterStrength', .7), '')}
custom = node(u.MaterialExpressionCustom, code=code, output_type=u.CustomMaterialOutputType.CMOT_FLOAT3, description='M4 bare skin V9')
pins = []
for name in inputs:
    pin = u.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
custom.set_editor_property('inputs', pins)
outs = []
for name, kind in (('OutColour', u.CustomMaterialOutputType.CMOT_FLOAT3), ('OutRoughness', u.CustomMaterialOutputType.CMOT_FLOAT1),
                   ('OutSpecular', u.CustomMaterialOutputType.CMOT_FLOAT1), ('OutAO', u.CustomMaterialOutputType.CMOT_FLOAT1),
                   ('OutScatter', u.CustomMaterialOutputType.CMOT_FLOAT1)):
    o = u.CustomOutput(); o.set_editor_property('output_name', name); o.set_editor_property('output_type', kind); outs.append(o)
custom.set_editor_property('additional_outputs', outs)
for name, (expr, pin) in inputs.items():
    if not L.connect_material_expressions(expr, pin, custom, name): raise RuntimeError('Cannot connect ' + name)
for pin, prop in (('', u.MaterialProperty.MP_NORMAL), ('OutColour', u.MaterialProperty.MP_BASE_COLOR), ('OutRoughness', u.MaterialProperty.MP_ROUGHNESS),
                  ('OutSpecular', u.MaterialProperty.MP_SPECULAR), ('OutAO', u.MaterialProperty.MP_AMBIENT_OCCLUSION), ('OutScatter', u.MaterialProperty.MP_OPACITY)):
    if not L.connect_material_property(custom, pin, prop): raise RuntimeError('Cannot connect output ' + pin)
if not L.connect_material_property(node(u.MaterialExpressionConstant, r=0), '', u.MaterialProperty.MP_METALLIC): raise RuntimeError('metallic')
mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_SUBSURFACE_PROFILE)
mat.set_editor_property('subsurface_profile', profile)
L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH); L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_MORPH_TARGETS)
L.layout_material_expressions(mat)
errors = L.recompile_material(mat)
if errors: raise RuntimeError('Skin material compile failed: ' + str(errors))
save(mat)
mi = u.load_asset(DEST + '/MI_M4SkinV9') or A.create_asset('MI_M4SkinV9', DEST, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
L.set_material_instance_parent(mi, mat); L.update_material_instance(mi); save(mi)

# ---------------------------------------------------------------- mesh: positions, normals, UV0, weights
mesh = u.load_asset(MESH)
slots = [s.copy() for s in mesh.materials]
dm, status = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Read failed')
_, ps, _ = Q.get_all_vertex_positions(dm, False); ps = list(u.GeometryScript_List.convert_vector_list_to_array(ps))
vids = pay['vertex_ids']; worst = 0.0
for vid, old in zip(vids, pay['old_positions']):
    q = ps[vid]; worst = max(worst, abs(q.x - old[0]), abs(q.y - old[1]), abs(q.z - old[2]))
if worst > 1e-3: raise RuntimeError('Live skin vertices differ from the snapshot (%.4f cm)' % worst)
for vid, p in zip(vids, pay['positions']): ps[vid] = u.Vector(*p)
Ed.set_all_mesh_vertex_positions(dm, u.GeometryScript_List.convert_array_to_vector_list(ps))
for vid, n in zip(vids, pay['vertex_normals']):
    _, ok = u.GeometryScript_Normals.update_vertex_normal(dm, vid, True, u.Vector(*n), False, u.Vector(1, 0, 0), u.Vector(0, 1, 0), False, True)
    if not ok: raise RuntimeError('normal %d' % vid)
for tid, uv in zip(pay['triangle_ids'], pay['uv0']):
    x = u.GeometryScriptUVTriangle(uv0=u.Vector2D(*uv[0]), uv1=u.Vector2D(*uv[1]), uv2=u.Vector2D(*uv[2]))
    _, ok = u.GeometryScript_UVs.set_mesh_triangle_u_vs(dm, 0, tid, x, True)
    if not ok: raise RuntimeError('uv %d' % tid)
_, bones = Bw.get_all_bones_info(dm); bone_ids = {str(b.name): b.index for b in bones}
for vid, row in pay['weights'].items():
    Bw.set_vertex_bone_weights(dm, int(vid), [u.GeometryScriptBoneWeight(bone_index=bone_ids[b], weight=w) for b, w in row.items()])
options = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False, enable_recompute_tangents=True, replace_materials=True,
    new_materials=[s.material_interface for s in slots], new_material_slot_names=[s.get_editor_property('imported_material_slot_name') for s in slots],
    bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_, status = G.copy_mesh_to_skeletal_mesh(dm, mesh, options, u.GeometryScriptMeshWriteLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Mesh write failed')

# ---------------------------------------------------------------- corrective morphs
written = {}
names_in_order = list(pay['morphs'])
for name, rows in pay['morphs'].items():
    # one mesh rebuild at the end: only the last write runs PostEditChange
    morph_opts = u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=True, emit_transaction=False,
        defer_mesh_post_edit_change=name != names_in_order[-1], copy_normals=True)
    md, status = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Morph base read failed')
    for vid, x, y, z, nx, ny, nz in rows:
        Ed.set_vertex_position(md, int(vid), u.Vector(x, y, z), True)
        u.GeometryScript_Normals.update_vertex_normal(md, int(vid), True, u.Vector(nx, ny, nz), False, u.Vector(1, 0, 0), u.Vector(0, 1, 0), False, True)
    _, outcome = G.copy_morph_target_to_skeletal_mesh(md, mesh, name, morph_opts, u.GeometryScriptMeshWriteLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Morph write failed ' + name)
    written[name] = len(rows)
for i, s in enumerate(slots):
    if i in pay['skin_slots']: s.set_editor_property('material_interface', mi)
mesh.set_editor_property('materials', slots)
E.set_metadata_tag(mesh, 'BareSkinV9', '20261017 M4 sample: rest anatomy, ring/elbow-join cleanup, V9 UV0 + baked skin, JC_ correctives')
save(mesh)

# ---------------------------------------------------------------- read back
names = [m.get_name() for m in (mesh.get_editor_property('morph_targets') or [])]
rb, _ = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
_, qs, _ = Q.get_all_vertex_positions(rb, False); qs = u.GeometryScript_List.convert_vector_list_to_array(qs)
err = max(max(abs(qs[v].x - p[0]), abs(qs[v].y - p[1]), abs(qs[v].z - p[2])) for v, p in zip(vids, pay['positions']))
receipt.update(mesh=MESH, morphs=written, morph_targets_on_asset=names, position_readback_max_cm=err,
               slots=[(str(s.material_slot_name), s.material_interface.get_path_name() if s.material_interface else '') for s in mesh.materials],
               lods=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(mesh), mesh_sha256=sha(disk(MESH)))
(R / 'install_receipt.json').write_text(json.dumps(receipt, indent=1))
print('M4V9_INSTALL_COMPLETE', json.dumps(dict(morphs=len(names), err=err)), flush=True)
