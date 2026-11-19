"""Capture Jason inputs, then save an isolated derivative in the same asset batch."""
import hashlib
import json
import re
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
OUT = PROJECT / 'SourceAssets/JasonStrong20261117/R2_LongLegs'
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'textures').mkdir(exist_ok=True)
config_path = PROJECT / 'Content/ColdSteelData/player_body.json'
config = json.loads(config_path.read_text(encoding='utf-8-sig'))
outfit_config = json.loads((PROJECT/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
body_profile = outfit_config.get('profiles',{}).get(config['body_mesh'],{})
body_source = body_profile.get('native_bare_skin',config['body_mesh'])
G, Q, B, L = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries, u.GeometryScript_BoneWeights, u.GeometryScript_List
sources = {'body': body_source, 'head': config['heads']['jason']['mesh']}
receipt = {'catalog_sha256_at_capture': hashlib.sha256(config_path.read_bytes()).hexdigest(),
           'head_settings': config['heads']['jason'], 'assets': {},
           'configured_body':config['body_mesh'],'effective_native_body':body_source}
material_inputs = {}

def xyz(v):
    return [v.x, v.y, v.z]

for name, source in sources.items():
    asset = u.load_asset(source)
    dm, result = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if result != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read ' + source)
    _, plist, _ = Q.get_all_vertex_positions(dm, False)
    positions = L.convert_vector_list_to_array(plist)
    _, tlist, _ = Q.get_all_triangle_indices(dm, False)
    triangles = L.convert_triangle_list_to_array(tlist)
    _, bones = B.get_all_bones_info(dm)
    weights = []
    for vi in range(len(positions)):
        _, ws, valid = B.get_vertex_bone_weights(dm, vi)
        weights.append([[w.bone_index, w.weight] for w in ws if w.weight > 0])
    uv, mids = [], []
    for ti in range(len(triangles)):
        a, b, c, valid = Q.get_triangle_u_vs(dm, 0, ti)
        uv.append([[v.x, v.y] for v in (a, b, c)])
        mid, valid = u.GeometryScript_Materials.get_triangle_material_id(dm, ti)
        mids.append(mid)
    materials = []
    overrides = config['heads']['jason'].get('materials', {}) if name == 'head' else {}
    for slot in asset.materials:
        slot_name = str(slot.material_slot_name)
        mat = u.load_asset(overrides[slot_name]) if slot_name in overrides else slot.material_interface
        path = mat.get_path_name() if mat else ''
        materials.append({'slot': slot_name, 'asset': path})
        if not mat or path in material_inputs:
            continue
        textures = {}
        for key in u.MaterialEditingLibrary.get_texture_parameter_names(mat):
            tex = u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mat, key)
            if not tex:
                continue
            k = str(key)
            record = {'asset': tex.get_path_name()}
            relevant = any(s in k.lower() for s in ('basecolor', 'base color', 'diffuse', 'albedo', 'normal baked', 'srmf baked', 'iris', 'sclera'))
            excluded = any(s in k.lower() for s in ('animated', ' vt', 'original'))
            if relevant and not excluded and 'Placeholder' not in tex.get_path_name():
                file = OUT / 'textures' / (tex.get_name() + '.png')
                if not file.exists():
                    task = u.AssetExportTask()
                    task.object, task.filename = tex, str(file)
                    task.exporter = u.TextureExporterPNG()
                    task.automated, task.prompt, task.replace_identical = True, False, False
                    if not u.Exporter.run_asset_export_task(task):
                        raise RuntimeError('Texture export failed: ' + tex.get_path_name())
                record['file'] = str(file)
            textures[k] = record
        scalars={}
        for key in u.MaterialEditingLibrary.get_scalar_parameter_names(mat):
            if str(key) in ('Roughness Global Offset Post-Bake','Roughness Global Multiply Post-Bake'):
                scalars[str(key)]=u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mat,key)
        material_inputs[path] = {'textures': textures,'scalars':scalars}
    data = {'source': source, 'skeleton': asset.skeleton.get_path_name(),
        'positions': [xyz(p) for p in positions], 'triangles': [xyz(t) for t in triangles],
        'triangle_uvs': uv, 'triangle_materials': mids, 'weights': weights, 'materials': materials,
        'bones': [{'name': str(b.name), 'index': b.index, 'parent': b.parent_index,
            'position': xyz(b.world_transform.translation),
            'axes': [xyz(b.world_transform.transform_location(v) - b.world_transform.translation)
                for v in (u.Vector(1,0,0), u.Vector(0,1,0), u.Vector(0,0,1))]} for b in bones]}
    (OUT / (name + '_source.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    receipt['assets'][name] = {'source': source, 'skeleton': data['skeleton'],
        'vertices': len(positions), 'triangles': len(triangles), 'materials': materials, 'bones': len(bones)}
    print('JASON_STRONG_CAPTURED ' + name, flush=True)
(OUT / 'material_inputs.json').write_text(json.dumps(material_inputs, indent=2), encoding='utf-8')
(OUT / 'source_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('JASON_STRONG_SOURCE_READY ' + json.dumps(receipt['assets']), flush=True)

# Keep the shared asset window for the complete independent authoring batch.
import sys
import runpy
sys.path.insert(0,str(PROJECT/'Tools/JasonStrongVariant'))
from muscle_shape import neck_seam
body_data=json.loads((OUT/'body_source.json').read_text())
(OUT/'neck_seam.json').write_text(json.dumps(neck_seam(body_data),separators=(',',':')))
runpy.run_path(str(PROJECT/'Tools/JasonStrongVariant/save_variant.py'),run_name='__main__')
