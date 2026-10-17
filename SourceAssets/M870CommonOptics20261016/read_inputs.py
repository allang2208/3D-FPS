"""Read existing optic interfaces for M870 adapter authoring; no asset writes."""
import unreal as u
import json
from pathlib import Path

O = Path(__file__).parent
I = O / 'Input'
I.mkdir(exist_ok=True)
G, Q, L = u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries, u.GeometryScript_List
ME = u.MaterialEditingLibrary
paths = {k: '/Game/Weapons/Super90/Optics20261007/Meshes/SM_Super90_' + k
         for k in ('holographic', 'eoth_holographic', 'panoramic_red_dot', 'prism_scope_2x', 'lpvo_1_6x', 'lpvo_ring')}
paths.update(thermal_scope='/Game/Weapons/ThermalScope20261006/Runtime/SM_Thermal_Common',
             thermal_selector='/Game/Weapons/ThermalScope20261006/Runtime/SM_ThermalSelector_Common')
R = {'assets': {}, 'materials': {}}
for key, path in paths.items():
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError('Missing ' + path)
    dm, status = G.copy_mesh_from_static_mesh(mesh, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),
        u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Read failed ' + key)
    _, v, _ = Q.get_all_vertex_positions(dm, False)
    vertices = [[p.x, p.y, p.z] for p in L.convert_vector_list_to_array(v)]
    sockets = {str(s.socket_name): {'location': [s.relative_location.x, s.relative_location.y, s.relative_location.z]}
               for s in u.ObjectIterator(u.StaticMeshSocket) if s.get_outer() == mesh and mesh.find_socket(s.socket_name) == s}
    slots = []
    for slot in mesh.static_materials:
        mat = slot.material_interface
        name = mat.get_path_name() if mat else None
        slots.append({'name': str(slot.material_slot_name), 'material': name})
        if mat and name not in R['materials']:
            base = mat.get_base_material()
            scalar_names = [str(n) for n in ME.get_scalar_parameter_names(base)]
            vector_names = [str(n) for n in ME.get_vector_parameter_names(base)]
            R['materials'][name] = {'class': mat.get_class().get_name(), 'base': base.get_path_name(),
                'scalar_names': scalar_names, 'vector_names': vector_names}
    (I / (key + '.json')).write_text(json.dumps({'vertices_cm': vertices}), encoding='utf-8')
    task = u.AssetExportTask()
    task.object, task.filename = mesh, str(I / (key + '.fbx'))
    task.automated, task.prompt, task.replace_identical = True, False, True
    task.options = u.FbxExportOption()
    task.options.level_of_detail = False
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('Export failed ' + key)
    R['assets'][key] = {'path': path, 'slots': slots, 'sockets': sockets, 'fbx': task.filename}
(O / 'inputs.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('M870_OPTIC_AUTHORING_INPUTS', len(paths), flush=True)
