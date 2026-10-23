"""Requested side-hole diagnosis: inspect built render LODs, not source only."""
import json
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME')
R = P/'SourceAssets/BackpackHarnessRebuild20261020'
job = json.loads((R/'render_read_job.json').read_text())
out = R/job.get('root', 'SideRepair20261022')/job['phase']
out.mkdir(parents=True, exist_ok=True)
Q, G, B, L = u.GeometryScript_MeshQueries, u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights, u.GeometryScript_List
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)


def vec(v):
    return [v.x, v.y, v.z]


manifest = json.loads((R/'manifest.json').read_text())
settings = json.loads((P/'Content/ColdSteelData/player_body.json').read_text())['outfits']['ue_mountain_backpack']
receipt = {'active_config': settings, 'meshes': []}
for row in manifest['variants']:
    asset = u.load_asset(row['asset'])
    for lod in range(S.get_lod_count(asset)):
        dm, status = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(),
            u.GeometryScriptCopyMeshFromAssetOptions(),
            u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA, lod_index=lod))
        if status != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Cannot read render data: '+row['asset'])
        _, positions, _ = Q.get_all_vertex_positions(dm, False)
        _, faces, _ = Q.get_all_triangle_indices(dm, False)
        positions = L.convert_vector_list_to_array(positions)
        faces = L.convert_triangle_list_to_array(faces)
        source_bones = json.loads(Path(row['source']).read_text())['bones']
        data = {'source': row['asset'], 'lod': lod, 'lod_type': 'RenderData',
            'revision': u.EditorAssetLibrary.get_metadata_tag(asset, 'BackpackHarnessRevision'),
            'front_face_convention': u.EditorAssetLibrary.get_metadata_tag(asset, 'BackpackFrontFaceConvention'),
            'positions': [vec(v) for v in positions], 'triangles': [vec(t) for t in faces],
            'materials': [{'slot': str(m.material_slot_name), 'asset': m.material_interface.get_path_name()}
                          for m in asset.materials],
            'bones': source_bones,
            'normals': [], 'uv': [], 'triangle_materials': [],
            'weight_scope': 'GeometryScript render conversion does not export skin weights; use SourceModel for weights'}
        for ti in range(len(faces)):
            a, b, c, valid = Q.get_triangle_u_vs(dm, 0, ti)
            _, na, nb, nc, nvalid = Q.get_triangle_normals(dm, ti)
            if not valid or not nvalid:
                raise RuntimeError('Missing render attributes')
            data['uv'].append([[v.x, v.y] for v in (a, b, c)])
            data['normals'].append([vec(n) for n in (na, nb, nc)])
            data['triangle_materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm, ti)[0])
        path = out/(row['profile']+'_render_lod'+str(lod)+'.json')
        path.write_text(json.dumps(data, separators=(',', ':')))
        receipt['meshes'].append({'profile': row['profile'], 'lod': lod, 'triangles': len(faces),
            'revision': data['revision'], 'build_settings': str(S.get_lod_build_settings(asset, lod))})
        print('BAG_RENDER_READ', row['profile'], lod, len(faces), flush=True)
        del dm, data
        u.SystemLibrary.collect_garbage()
mat = u.load_asset(manifest['variants'][0]['asset']).materials[0].material_interface
receipt['material'] = {'path': mat.get_path_name(), 'two_sided': mat.get_editor_property('two_sided'),
                       'blend_mode': str(mat.get_editor_property('blend_mode')), 'inputs': {}}
for prop in ['MP_BASE_COLOR', 'MP_NORMAL', 'MP_OPACITY', 'MP_OPACITY_MASK', 'MP_WORLD_POSITION_OFFSET']:
    node = u.MaterialEditingLibrary.get_material_property_input_node(mat, getattr(u.MaterialProperty, prop))
    receipt['material']['inputs'][prop] = str(node)
(out/'receipt.json').write_text(json.dumps(receipt, indent=2))
print('BAG_RENDER_READ_COMPLETE', flush=True)
