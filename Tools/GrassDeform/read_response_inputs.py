"""Read existing grass inputs for a reported failure; no play-state or asset edits."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u

out = Path(u.Paths.project_saved_dir()) / 'GrassResponseInputs20260927' / datetime.now().strftime('%H%M%S')
out.mkdir(parents=True, exist_ok=True)
L = u.MaterialEditingLibrary
r = {'meshes': {}, 'textures': {}, 'graphs': {}, 'worlds': []}
es = u.get_editor_subsystem(u.UnrealEditorSubsystem)
for world in (es.get_editor_world(), es.get_game_world()):
    if world:
        r['worlds'].append(world.get_path_name())
mpc = u.load_asset('/Game/PN_GrassLibrary/Materials/PN_WindParameters')
world = es.get_game_world()
if world:
    r['mpc'] = {name: u.MaterialLibrary.get_scalar_parameter_value(world, mpc, name)
                for name in ['bEnabled', 'ReadIsB', 'WorldTime', 'GrassHoldSeconds', 'GrassRecoverSeconds', 'GrassBendAngle']}
    r['body'] = str(u.MaterialLibrary.get_vector_parameter_value(world, mpc, 'GrassBodyContact'))
r['settings'] = str(u.get_default_object(u.load_class(None, '/Script/FPSGAME.GrassDeformSettings')).get_editor_property('HoldSeconds'))
for suffix in ('03_08', '05_03'):
    mesh = u.load_asset('/Game/WorldGeneration/TemperateHills/Grass/SM_Meadow_grass_' + suffix + '_mesh')
    mats = []
    for slot in mesh.static_materials:
        mat = slot.material_interface
        parent = mat.get_editor_property('parent')
        mats.append({'path': mat.get_path_name(), 'parent': parent.get_path_name(),
                     'offset_limit': L.get_material_instance_scalar_parameter_value(mat, 'GrassDeformMaxOffset'),
                     'version': u.EditorAssetLibrary.get_metadata_tag(parent, 'GrassDeformVersion')})
        for name in ('Position and Index Texture', 'X-Vector And X-Extent Texture'):
            tex = L.get_material_instance_texture_parameter_value(mat, name)
            task = u.AssetExportTask()
            task.object = tex
            task.filename = str(out / (tex.get_name() + ('.exr' if name.startswith('Position') else '.tga')))
            task.automated = True
            task.prompt = False
            task.replace_identical = False
            ok = u.Exporter.run_asset_export_task(task)
            r['textures'][name + suffix] = {'path': tex.get_path_name(), 'exported': ok, 'file': task.filename,
                'srgb': tex.get_editor_property('srgb'), 'filter': str(tex.get_editor_property('filter'))}
    dyn = u.DynamicMesh()
    lod = u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA, lod_index=0)
    u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dyn, u.GeometryScriptCopyMeshFromAssetOptions(), lod)
    Q = u.GeometryScript_MeshQueries
    triangles = []
    for ti in range(dyn.get_triangle_count()):
        a,b,c,valid = Q.get_triangle_u_vs(dyn, 1, ti)
        valid, *positions = Q.get_triangle_positions(dyn, ti)
        triangles.append({'uv': [a.x,a.y], 'positions': [[x.x,x.y,x.z] for x in positions]})
    r['meshes'][suffix] = {'bounds': str(mesh.get_bounds()), 'materials': mats, 'triangles': triangles}
for path in ('/Game/WorldGeneration/GrassDeform/MF_GrassDeform', '/Engine/Functions/Engine_MaterialFunctions02/WorldPositionOffset/ObjectScale'):
    fn = u.load_asset(path)
    r['graphs'][path] = []
    for node in L.get_material_function_expressions(fn):
        row = {'name':node.get_name(),'type':node.get_class().get_name()}
        for prop in ('desc','code','type','default_value','output_name','transform_source_type','transform_type'):
            try: row[prop] = str(node.get_editor_property(prop))
            except Exception: pass
        row['inputs'] = [n.get_name() if n else None for n in L.get_inputs_for_material_function_expression(fn,node)]
        r['graphs'][path].append(row)
(out / 'inputs.json').write_text(json.dumps(r,indent=2), encoding='utf-8')
print('GRASS_INPUTS ' + json.dumps({'out': str(out), 'worlds':r['worlds'], 'mpc':r.get('mpc'), 'body':r.get('body'),
    'settings':r['settings'], 'materials': {k:v['materials'] for k,v in r['meshes'].items()}, 'textures':r['textures']}))
