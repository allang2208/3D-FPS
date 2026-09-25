import json
from pathlib import Path
import unreal as u
AUTHOR = Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260925/FieldGlovesLeatherV1')
G = u.GeometryScript_AssetUtils
Q = u.GeometryScript_MeshQueries
L = u.MaterialEditingLibrary
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
report = {'meshes': {}, 'materials': {}}
for name, path in json.loads((Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1/published.json')).read_text())['profiles'].items():
    mesh = u.load_asset(path)
    dm, status = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    verts = tris = 0
    if status == u.GeometryScriptOutcomePins.SUCCESS:
        _, pos, _ = Q.get_all_vertex_positions(dm, False)
        verts = len(u.GeometryScript_List.convert_vector_list_to_array(pos))
        _, faces, _ = Q.get_all_triangle_indices(dm, False)
        tris = len(u.GeometryScript_List.convert_triangle_list_to_array(faces))
    report['meshes'][name] = {'verts': verts, 'tris': tris, 'lods': S.get_lod_count(mesh), 'api_verts': S.get_num_verts(mesh, 0)}
for path in ('/Game/Characters/ModularOutfit20260924/Materials/M_FieldGloves_Brown','/Game/Characters/ModularOutfit20260924/Materials/M_FieldGloves_Black'):
    mat = u.load_asset(path)
    params = {}
    textures = {}
    names = []
    for expr in L.get_material_expressions(mat):
        names.append(expr.get_class().get_name())
        if isinstance(expr, u.MaterialExpressionScalarParameter):
            params[str(expr.get_editor_property('parameter_name'))] = float(expr.get_editor_property('default_value'))
        elif isinstance(expr, (u.MaterialExpressionTextureSampleParameter2D, u.MaterialExpressionTextureObjectParameter)):
            tex = expr.get_editor_property('texture')
            textures[str(expr.get_editor_property('parameter_name'))] = tex.get_path_name() if tex else None
    report['materials'][path.split('/')[-1]] = {
        'params': params, 'textures': textures,
        'has_preskinned': any('PreSkinned' in n for n in names),
        'has_height': 'LeatherHeight' in textures or 'LeatherHeightCm' in params,
    }
(AUTHOR/'verify-v3.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print('FIELD_GLOVES_CUFF_VERIFY', json.dumps({'mesh_ok': all(v['verts']>5000 for v in report['meshes'].values()), 'count': len(report['meshes']), 'm4': report['meshes'].get('M4'), 'brown': report['materials'].get('M_FieldGloves_Brown',{}).get('params')}), flush=True)
