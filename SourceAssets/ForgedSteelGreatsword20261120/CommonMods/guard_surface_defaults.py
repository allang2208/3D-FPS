"""Keep the fitted mesh defaults on the same materials as the equipped guard."""
import unreal as u


def bind_saved_guards(mesh_paths, material_paths):
    surfaces = {slot: u.load_asset(path) for slot, path in material_paths.items()}
    if not all(surfaces.values()):
        raise RuntimeError('Could not load the guard materials: ' + str(material_paths))
    for path in mesh_paths:
        mesh = u.load_asset(path)
        slots = [str(slot.material_slot_name) for slot in mesh.static_materials]
        if set(slots) != set(surfaces):
            raise RuntimeError(f'{path} has unexpected slots {slots}')
        if all(mesh.get_material(i) == surfaces[slot] for i, slot in enumerate(slots)):
            continue
        mesh.modify()
        for index, slot in enumerate(slots):
            mesh.set_material(index, surfaces[slot])
        if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):
            raise RuntimeError('Could not save ' + path)
