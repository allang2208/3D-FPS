"""Export saved Kaitlin geometry as input to clothing and animation authoring.

Run in the isolated authoring project after assemble.py has saved its output.
This writes authoring inputs only; it does not publish the playable character.
"""
import json
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
assembly = json.loads((WORK / 'assembly_receipt.json').read_text(encoding='utf-8'))
if assembly['status'] != 'native_assembly_saved_in_authoring_host':
    raise RuntimeError('Finish the MetaHuman assembly before extracting its geometry.')
if (WORK / 'full_body_receipt.json').exists():
    complete_body = json.loads((WORK / 'full_body_receipt.json').read_text(encoding='utf-8'))
    assembly['skeletal_meshes'].append(complete_body['mesh'])
    assembly['saved_assets'].append(complete_body['mesh'])
destination = WORK / 'NativeGeometry'
destination.mkdir(exist_ok=True)
G, B, Q = u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights, u.GeometryScript_MeshQueries


def xyz(value):
    return [value.x, value.y, value.z]


components = []
subobjects = u.get_engine_subsystem(u.SubobjectDataSubsystem)
subobject_library = u.SubobjectDataBlueprintFunctionLibrary
for path in assembly['saved_assets']:
    data = u.EditorAssetLibrary.find_asset_data(path)
    if str(data.asset_class_path.asset_name) != 'Blueprint':
        continue
    blueprint = data.get_asset()
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(blueprint):
        component = subobject_library.get_object_for_blueprint(subobject_library.get_data(handle), blueprint)
        if isinstance(component, u.SkeletalMeshComponent):
            mesh = component.get_skeletal_mesh_asset()
            components.append({'blueprint': path, 'name': component.get_name(), 'type': 'SkeletalMeshComponent',
                               'mesh': mesh.get_path_name() if mesh else None,
                               'materials': [component.get_material(i).get_path_name()
                                             if component.get_material(i) else None
                                             for i in range(component.get_num_materials())]})
        elif isinstance(component, u.GroomComponent):
            groom = component.get_editor_property('groom_asset')
            binding = component.get_editor_property('binding_asset')
            components.append({'blueprint': path, 'name': component.get_name(), 'type': 'GroomComponent',
                               'asset': groom.get_path_name() if groom else None,
                               'binding': binding.get_path_name() if binding else None})
(WORK / 'native_components.json').write_text(json.dumps(components, indent=2), encoding='utf-8')
registry = u.AssetRegistryHelpers.get_asset_registry()
registry.scan_paths_synchronous(['/Game/Characters/KaitlinPlayer20261023/Native'], True)
dependency_options = u.AssetRegistryDependencyOptions(
    include_soft_package_references=True, include_hard_package_references=True,
    include_searchable_names=False, include_soft_management_references=False,
    include_hard_management_references=False)
external_dependencies = set()
for path in assembly['saved_assets']:
    for dependency in registry.get_dependencies(path.split('.', 1)[0], dependency_options) or []:
        dependency = str(dependency)
        if not dependency.startswith('/Game/Characters/KaitlinPlayer20261023/Native/'):
            external_dependencies.add(dependency)
(WORK / 'native_dependencies.json').write_text(json.dumps(sorted(external_dependencies), indent=2), encoding='utf-8')


receipt_path = WORK / 'native_geometry_receipt.json'
manifest = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}
for path in assembly['skeletal_meshes']:
    # This task's assembled source packages are immutable. Resume only missing
    # captures after adding the separate full-body source.
    if path in manifest and Path(manifest[path]['geometry']).exists():
        continue
    asset = u.load_asset(path)
    dm, outcome = G.copy_mesh_from_skeletal_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot extract authoring input: ' + path)
    _, bones = B.get_all_bones_info(dm)
    _, positions, _ = Q.get_all_vertex_positions(dm, False)
    _, triangles, _ = Q.get_all_triangle_indices(dm, False)
    positions = u.GeometryScript_List.convert_vector_list_to_array(positions)
    triangles = u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    weights = []
    for vertex in range(len(positions)):
        _, vertex_weights, valid = B.get_vertex_bone_weights(dm, vertex)
        if not valid:
            raise RuntimeError('Missing skin weights in ' + path)
        weights.append([[w.bone_index, w.weight] for w in vertex_weights if w.weight > 0])
    materials = [{'slot': str(slot.material_slot_name),
                  'asset': slot.material_interface.get_path_name() if slot.material_interface else ''}
                 for slot in asset.materials]
    triangle_materials = [u.GeometryScript_Materials.get_triangle_material_id(dm, index)[0]
                          for index in range(len(triangles))]
    data = {
        'source': path, 'skeleton': asset.skeleton.get_path_name(),
        'positions': [xyz(v) for v in positions], 'triangles': [xyz(v) for v in triangles],
        'weights': weights, 'materials': materials, 'triangle_materials': triangle_materials,
        'bones': [{'name': str(b.name), 'index': b.index, 'parent': b.parent_index,
                   'position': xyz(b.world_transform.translation),
                   'axes': [xyz(b.world_transform.transform_location(v) - b.world_transform.translation)
                            for v in (u.Vector(1, 0, 0), u.Vector(0, 1, 0), u.Vector(0, 0, 1))]}
                  for b in bones],
    }
    output = destination / (asset.get_name() + '.json')
    output.write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    manifest[path] = {'geometry': str(output), 'materials': materials,
                      'vertices': len(positions), 'triangles': len(triangles),
                      'bone_names': [str(b.name) for b in bones]}
    (WORK / 'native_geometry_receipt.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('KAITLIN_NATIVE_GEOMETRY_SAVED ' + path, flush=True)
    del dm, data, weights, positions, triangles, asset
    u.SystemLibrary.collect_garbage()
