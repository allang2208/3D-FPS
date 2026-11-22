"""Shop-specific stone and lime joints on the repaired exterior."""
import unreal as ue


FINISHES = '/Game/WorldGeneration/TemperateHills/VillageBakery/Surfaces'
RELIEF = '/Game/WorldGeneration/TemperateHills/VillageMasonry/Relief/'
NORMANDY = '/Game/UnrealNormandy/MaterialInstances/'
SLOTS = {
    'AbandonedHouseStone': 'MI_BakeryWall_Fieldstone',
    'NativeMortar': 'MI_BakeryWall_LimeJoints',
}


def author_finish(name, parent_name, reference_name, tint_weights, relief_cm, normals):
    editor = ue.EditorAssetLibrary
    lib = ue.MaterialEditingLibrary
    parent = ue.load_asset(RELIEF+parent_name)
    reference = ue.load_asset(NORMANDY+reference_name)
    if not parent or not reference:
        raise RuntimeError('Missing village masonry reference for '+name)
    path = FINISHES+'/'+name
    instance = editor.load_asset(path) if editor.does_asset_exist(path) else (
        ue.AssetToolsHelpers.get_asset_tools().create_asset(name, FINISHES, ue.MaterialInstanceConstant,
                                                             ue.MaterialInstanceConstantFactoryNew()))
    if not instance:
        raise RuntimeError('Could not author '+path)
    instance.modify()
    lib.set_material_instance_parent(instance,parent)
    for index,layer in enumerate(('00','01')):
        field = 'TS'+layer+'_BaseColor_Tint'
        warm = lib.get_material_instance_vector_parameter_value(parent,field)
        cool = lib.get_material_instance_vector_parameter_value(reference,field)
        weight = tint_weights[index]
        color = ue.LinearColor(*[getattr(warm,k)*(1-weight)+getattr(cool,k)*weight for k in ('r','g','b','a')])
        lib.set_material_instance_vector_parameter_value(instance,field,color)
        lib.set_material_instance_scalar_parameter_value(instance,'VillageReliefCm'+layer,relief_cm[index])
        lib.set_material_instance_scalar_parameter_value(instance,'TS'+layer+'_NormalIntensity',normals[index])
    lib.update_material_instance(instance)
    if not editor.save_loaded_asset(instance,False):
        raise RuntimeError('Could not save '+path)


def author_wall_finishes():
    # The window surrounds of the neighbouring Normandy houses supply the grey stone.
    # Keep warmth in the fieldstones and let the fine joints recede between their edges.
    ue.EditorAssetLibrary.make_directory(FINISHES)
    author_finish(SLOTS['AbandonedHouseStone'], 'MI_Main_StoneWall_00A','MI_Main_StoneWall_00B_Gray',
                  (.42,.54),(.77,.67),(1.12,1.98))
    author_finish(SLOTS['NativeMortar'], 'MI_Main_Mortar_00A','MI_Main_Mortar_00B',
                  (.38,.0),(.20,.27),(1.10,1.0))


def bind_wall_finishes(component):
    bound = {}
    for slot,name in SLOTS.items():
        index = component.get_material_index(slot)
        material = ue.load_asset(FINISHES+'/'+name)
        if index < 0 or not material:
            raise RuntimeError('Missing bakery wall slot or finish: '+slot+' / '+name)
        component.set_material(index,material)
        bound[slot] = material.get_path_name()
    return bound
