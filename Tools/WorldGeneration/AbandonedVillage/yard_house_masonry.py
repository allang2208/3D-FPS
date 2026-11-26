"""Bind the village relief materials to the native courtyard stones and mortar."""
import unreal as ue


RELIEF = '/Game/WorldGeneration/TemperateHills/VillageMasonry/Relief/'
STONE_SLOTS = ('MI_StoneWall_Pieces_00A', 'MI_Main_Mortar_00A')
TAG = 'VillageYard.HouseMasonry'
PREVIOUS = '/Game/WorldGeneration/TemperateHills/EcologyUpgrade/Receivers/VillageWalls/'


def house_materials():
    materials = {}
    for name in STONE_SLOTS:
        material = ue.load_asset(RELIEF + name)
        if not material:
            raise RuntimeError('Missing courtyard relief material ' + RELIEF + name)
        materials[name] = material
    return materials


def bind_yard_wall(component, materials):
    component.modify()
    matched = set()
    for index, slot in enumerate(component.static_mesh.static_materials):
        name = slot.material_interface.get_name() if slot.material_interface else ''
        if name in materials:
            matched.add(name)
            target = materials[name]
            if component.get_material(index) != target:
                component.set_material(index, target)
            if component.get_material(index) != target:
                raise RuntimeError(f'Could not assign {name} to {component.get_path_name()} slot {index}')
    # Mossy B, C and D pieces have stone and moss sections, without a mortar section.
    if 'MI_StoneWall_Pieces_00A' not in matched:
        raise RuntimeError('No native stone section on ' + component.static_mesh.get_path_name())
    if TAG not in map(str, component.component_tags):
        component.component_tags = list(component.component_tags) + [TAG]
    return matched


def update_existing_yards(actors):
    materials = house_materials()
    count = 0
    by_material = {name: 0 for name in materials}
    for actor in actors.get_all_level_actors():
        for comp in actor.get_components_by_class(ue.InstancedStaticMeshComponent):
            if not comp.static_mesh or not comp.static_mesh.get_name().startswith('SM_H_StoneWall_00A_Piece'):
                continue
            # Earlier village bakes used these per-component receivers exclusively on yard
            # boundaries. House rubble can share the static mesh, but has separate components.
            previous = any(m and m.get_path_name().startswith(PREVIOUS) for m in comp.get_materials())
            if previous or TAG in map(str, comp.component_tags):
                actor.modify()
                matched = bind_yard_wall(comp, materials)
                instances = comp.get_instance_count()
                count += instances
                for name in matched:
                    by_material[name] += instances
    ue.log(f'Village courtyard relief: {count} wall instances, material coverage {by_material}')
    return count
