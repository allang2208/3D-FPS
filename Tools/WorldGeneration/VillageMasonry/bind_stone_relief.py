"""Bind the village relief surfaces without re-authoring a mesh or its collision."""
import gc
import hashlib
import json
import os
from pathlib import Path

import unreal as ue


ROOT = '/Game/WorldGeneration/TemperateHills/VillageMasonry'
ORIGINAL = '/Game/UnrealNormandy/MaterialInstances'
RELIEF = ROOT + '/Relief'
NAMES = ('MI_Main_StoneWall_00A', 'MI_Main_StoneWall_00B_Gray',
         'MI_StoneWall_Pieces_00A', 'MI_Main_Mortar_00A')


def package(asset):
    return asset.get_path_name().split('.')[0] if asset else None


def physical_state(mesh):
    body = mesh.get_editor_property('body_setup')
    box = mesh.get_bounding_box()
    compound = body.get_editor_property('agg_geom')
    return {
        'bounds_cm': [[p.x, p.y, p.z] for p in (box.min, box.max)],
        'lods': [[mesh.get_num_vertices(i), mesh.get_num_triangles(i)]
                 for i in range(mesh.get_num_lods())],
        'nanite': mesh.get_editor_property('nanite_settings').enabled,
        'collision_geometry_sha256': hashlib.sha256(compound.export_text().encode()).hexdigest(),
        'collision_trace': str(body.get_editor_property('collision_trace_flag')),
        'complex_collision_mesh': package(mesh.get_editor_property('complex_collision_mesh')),
    }


def bind(path, materials):
    mesh = ue.load_asset(path)
    if not isinstance(mesh, ue.StaticMesh):
        raise RuntimeError('Missing displaced mesh ' + path)
    before = physical_state(mesh)
    slots = [slot.copy() for slot in mesh.static_materials]
    bindings = []
    changed = False
    for slot in slots:
        existing = package(slot.material_interface)
        if existing is None:
            raise RuntimeError('Unresolved source material on '+path+' / '+str(slot.material_slot_name))
        target = materials.get(existing)
        if target and existing != package(target):
            slot.material_interface = target
            changed = True
        bindings.append({'slot': str(slot.material_slot_name), 'before': existing,
                         'after': package(slot.material_interface), 'masonry': target is not None})
    if not any(row['masonry'] for row in bindings):
        raise RuntimeError('No Normandy masonry slots on ' + path)
    if changed:
        mesh.modify()
        # The Blueprint setter updates the material table and its registry cache.
        # Keep the original slot names, UV density info, sections and source models.
        mesh.static_materials = slots
        if not ue.EditorAssetLibrary.save_loaded_asset(mesh, False):
            raise RuntimeError('Could not save ' + path)
    if [package(slot.material_interface) for slot in mesh.static_materials] != [b['after'] for b in bindings]:
        raise RuntimeError('Material table differs after binding ' + path)
    if before != physical_state(mesh):
        raise RuntimeError('Mesh geometry or collision changed while binding ' + path)
    return {'mesh': path, 'changed': changed, 'physical_state': before, 'bindings': bindings}


def main():
    work = Path(os.environ['STONE_RELIEF_BIND_WORK'])
    meshes = json.loads((work/'inputs.json').read_text(encoding='utf-8-sig'))
    materials = {}
    for name in NAMES:
        target = ue.load_asset(RELIEF+'/'+name)
        if not isinstance(target, ue.MaterialInterface):
            raise RuntimeError('Missing relief material '+name)
        materials[ORIGINAL+'/'+name] = target
        materials[package(target)] = target
    result = []
    for name in meshes:
        result.append(bind(ROOT+'/ReliefMeshes/'+name, materials))
        ue.log('VILLAGE_RELIEF_BOUND '+name)
        gc.collect()
        ue.SystemLibrary.collect_garbage()
    (work/'bindings.json').write_text(json.dumps(result, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
