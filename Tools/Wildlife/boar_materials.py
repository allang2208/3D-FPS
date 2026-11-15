"""Use the boar mesh's own coat; keep the pack variant for a stock-mesh rebuild."""
import unreal as u


def apply(blueprint):
    component = u.get_default_object(blueprint.generated_class()).get_editor_property('mesh')
    mesh = component.get_editor_property('skeletal_mesh_asset')
    slots = mesh.get_editor_property('materials')
    inherited_coat = mesh.get_name() == 'SK_WL_Boar'
    changes = []
    for index, slot in enumerate(slots):
        base = slot.material_interface
        if base is None:
            continue
        if inherited_coat:
            if base.get_name() in ('M_BoarCoat','M_BoarHair') and component.get_material(index) != base:
                changes.append((index,None))
        else:
            name = base.get_name().removesuffix('Dirty')
            if name not in ('M_Pig','M_PigHair'):
                continue
            mat = u.load_asset('/Game/AnimalVarietyPack/Pig/Materials/'+name+'Dirty')
            if not mat:
                raise RuntimeError('Missing pack material '+name)
            if component.get_material(index) != mat:
                changes.append((index,mat))
    if changes:
        blueprint.modify()
        component.modify()
        for index, mat in changes:
            component.set_material(index,mat)
        if not u.EditorAssetLibrary.save_loaded_asset(blueprint,False):
            raise RuntimeError('Could not save '+blueprint.get_path_name())


if __name__ == '__main__':
    path = '/Game/Monsters/Wildlife/Pig/BP_WL_Pig'
    if any(pkg.get_name() == path for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('The boar blueprint has unsaved changes')
    apply(u.load_asset(path))
