"""Apply the village wall permutations to a staged copy of the saved village packages."""
import json
import os
import sys
from pathlib import Path

import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wall_material_sampling import add_zero_normal_switch, share_relief_height, enable_flat, FLAT, FLAT_RELIEF

ROOT = '/Game/WorldGeneration/TemperateHills/'
RELIEF = ROOT+'VillageMasonry/Relief/'
VARIANTS = ROOT+'VillageMasonry/WallVariants/'
LEVEL = ROOT+'AbandonedVillage/L_AbandonedVillage'
FUNCTION = '/Game/UnrealNormandy/MaterialFunctions/MF_GlobalNormal'
# Specialize only the wall permutations for which the SM6 compile removes a sample.
# Mortar's layer blend compiles with two extra estimated samples on this path.
FLAT_SOURCES = {'/Game/UnrealNormandy/MaterialInstances/'+n for n in
                (*FLAT_RELIEF, 'MI_StoneWall_Pieces_00B_Gray', 'MI_BrickWall_Chunks_00A')}
FLAT_SOURCES.add(ROOT+'EcologyUpgrade/Receivers/MI_bd09fc1a8433')
SHOPS = ('Village_02_Tavern','Village_05_Windmill','Village_06_Bakery','Village_09_Gunshop',
         'Village_Blacksmith','Village_Carpenter','Village_Herbalist')
WALL_MESH = ('wall','envelope','masonry','facade','infill','openingbay','chapelyard','shell')
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary


def package(obj):
    return obj.get_path_name().split('.')[0]


def main(out):
    saved = []
    changes = []
    variants = {}
    def save(obj):
        if not E.save_loaded_asset(obj, False):
            raise RuntimeError('Could not save '+package(obj))
        saved.append(package(obj))
    fn = u.load_asset(FUNCTION)
    if add_zero_normal_switch(fn):
        save(fn)
    else:
        saved.append(FUNCTION)
    for layer in ('00','01'):
        projection = u.load_asset(RELIEF+'MF_ReliefProjection'+layer)
        texture_set = u.load_asset(RELIEF+'MF_VillageTextureSet'+layer)
        share_relief_height(projection,texture_set)
        save(projection)
        save(texture_set)
    for name in FLAT_RELIEF:
        inst=u.load_asset(RELIEF+name)
        enable_flat(inst)
        save(inst)

    E.make_directory(VARIANTS.rstrip('/'))
    world=u.EditorLoadingAndSavingUtils.load_map(LEVEL)
    if not world:
        raise RuntimeError('Could not open '+LEVEL)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    for actor in actors.get_all_level_actors():
        label=actor.get_actor_label()
        for part in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=part.static_mesh
            if not mesh: continue
            yard='VillageYard.HouseMasonry' in map(str,part.component_tags)
            shop=label.startswith(SHOPS) and any(token in mesh.get_name().lower() for token in WALL_MESH)
            if not (yard or shop): continue
            for slot,source in enumerate(part.get_materials()):
                if not isinstance(source,u.MaterialInstanceConstant): continue
                src=package(source)
                if src not in FLAT_SOURCES: continue
                names={str(n) for n in L.get_scalar_parameter_names(source)}
                switches={str(n) for n in L.get_static_switch_parameter_names(source)}
                if 'NormalGlobal_Intensity' not in names or FLAT not in switches: continue
                if L.get_material_instance_scalar_parameter_value(source,'NormalGlobal_Intensity') != 0.0: continue
                if src not in variants:
                    name=source.get_name()+'_VillageWall'
                    dest=VARIANTS+name
                    if E.does_asset_exist(dest):
                        child=u.load_asset(dest)
                        if child.parent != source: raise RuntimeError('Variant parent collision at '+dest)
                    else:
                        child=u.AssetToolsHelpers.get_asset_tools().create_asset(
                            name,VARIANTS.rstrip('/'),u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
                        L.set_material_instance_parent(child,source)
                    enable_flat(child)
                    save(child)
                    variants[src]=child
                actor.modify()
                part.modify()
                part.set_material(slot,variants[src])
                changes.append(dict(actor=label,mesh=package(mesh),component=part.get_name(),slot=slot,
                                    source=src,variant=package(variants[src])))
    if changes:
        if not u.EditorLoadingAndSavingUtils.save_map(world,LEVEL):
            raise RuntimeError('Village overrides did not save')
        saved.append(LEVEL)
    (out/'authored.json').write_text(json.dumps(dict(saved=saved,bindings=changes,
        variants={p:package(v) for p,v in variants.items()}),indent=2,ensure_ascii=False),encoding='utf8')


if __name__ == '__main__':
    main(Path(os.environ['VILLAGE_WALL_MATERIAL_RUN']))

