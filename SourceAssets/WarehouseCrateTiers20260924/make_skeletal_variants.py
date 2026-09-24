"""Create the five skeletal crate variants by duplicating the source chest SK and swapping slot materials.

    & 'E:\\Program Files (x86)\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe' <uproject> -run=pythonscript -script="<abs path>" -unattended -nop4 -nosplash

True animation reuse, verified live: the source SkeletalMesh /Game/ColdSteelUI/Warehouse20260909/RitualV8/
warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigid shares warehouse_chest_rigid_Skeleton (5 bones =
the GLB node hierarchy, skins=0) with the existing Open (0.9s) / Close (0.7s) AnimSequences, and its 11
imported slot names match the derive TIERS mapping keys exactly. A duplicate + per-slot material_interface
swap therefore inherits geometry, rig, LODs and the physics asset untouched -- AColdSteelWarehouseChest
(USkeletalMeshComponent, ChestAsset+OpenClip/CloseClip) plays the existing clips on these meshes unchanged.
Only NEW assets are written; the source is read-only, so this is safe even while an editor process is up.
"""
import json
import unreal as u

SRC = '/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigid'
DST = '/Game/Props/WarehouseCrateTiers20260924/Skeletal'
MAT = '/Game/Props/WarehouseCrateTiers20260924/Materials/M_'
TIERS = {
    'T1_Wood': {'White_Marble_PBR': 'Crate_Wood', 'Brass_Frame': 'Crate_WoodDark', 'Brass_Strap': 'Crate_WoodDark',
        'Brass_Hardware': 'Crate_IronDark', 'Gold_PBR': 'Crate_WoodDark', 'Sapphire_PBR': 'Crate_WoodDark',
        'Navy_Velvet': 'Crate_WoodDark', 'Interior_Magic_Blue': 'Crate_WoodDark',
        'Ritual_Champagne': 'Crate_WoodDark', 'Ritual_Gunmetal': 'Crate_Wood', 'Ritual_Engraving': 'Crate_IronDark'},
    'T2_StoneWood': {'White_Marble_PBR': 'Crate_Wood', 'Brass_Frame': 'Crate_Stone', 'Brass_Strap': 'Crate_Stone',
        'Brass_Hardware': 'Crate_Iron', 'Gold_PBR': 'Crate_Stone', 'Sapphire_PBR': 'Crate_IronDark',
        'Navy_Velvet': 'Crate_WoodDark', 'Interior_Magic_Blue': 'Crate_WoodDark',
        'Ritual_Champagne': 'Crate_Stone', 'Ritual_Gunmetal': 'Crate_Stone', 'Ritual_Engraving': 'Crate_IronDark'},
    'T3_Iron': {'White_Marble_PBR': 'Crate_Iron', 'Brass_Frame': 'Crate_Iron', 'Brass_Strap': 'Crate_Iron',
        'Brass_Hardware': 'Crate_IronDark', 'Gold_PBR': 'Crate_IronDark', 'Sapphire_PBR': 'Crate_IronDark',
        'Navy_Velvet': 'Crate_IronDark', 'Interior_Magic_Blue': 'Crate_IronDark',
        'Ritual_Champagne': 'Crate_Iron', 'Ritual_Gunmetal': 'Crate_IronDark', 'Ritual_Engraving': 'Crate_IronDark'},
    'T4_IronGold': {'White_Marble_PBR': 'Crate_Iron', 'Brass_Frame': 'Crate_Gold', 'Brass_Strap': 'Crate_Gold',
        'Brass_Hardware': 'Crate_Gold', 'Gold_PBR': 'Crate_Gold', 'Sapphire_PBR': 'Crate_IronDark',
        'Navy_Velvet': 'Crate_IronDark', 'Interior_Magic_Blue': 'Crate_IronDark',
        'Ritual_Champagne': 'Crate_Gold', 'Ritual_Gunmetal': 'Crate_IronDark', 'Ritual_Engraving': 'Crate_Gold'},
    'T5_SilverGem': {'White_Marble_PBR': 'Crate_Silver', 'Brass_Frame': 'Crate_Gold', 'Brass_Strap': 'Crate_Gold',
        'Brass_Hardware': 'Crate_Gold', 'Gold_PBR': 'Crate_Gold', 'Sapphire_PBR': 'Crate_Gem',
        'Navy_Velvet': 'Crate_IronDark', 'Interior_Magic_Blue': 'Crate_IronDark',
        'Ritual_Champagne': 'Crate_Gold', 'Ritual_Gunmetal': 'Crate_Silver', 'Ritual_Engraving': 'Crate_Gold'},
}
E = u.EditorAssetLibrary
src = u.load_asset(SRC)
assert src is not None, 'source chest SK missing'
src_skel = src.get_editor_property('skeleton')
receipt = {'source': SRC, 'skeleton': src_skel.get_path_name(), 'variants': {}, 'runtime_tested': False}

# material cache; assert loadable up front so a missing crate material fails before duplicates
mats = {}
for mapping in TIERS.values():
    for target in mapping.values():
        if target not in mats:
            mats[target] = u.load_asset(MAT + target)
            if mats[target] is None:
                raise RuntimeError('crate material missing: ' + target)

for tier, mapping in TIERS.items():
    name = 'SK_WarehouseCrate_' + tier
    path = DST + '/' + name
    if E.does_asset_exist(path):
        mesh = u.load_asset(path)
        print('REUSE', path, flush=True)
    else:
        if not E.does_directory_exist(DST):
            E.make_directory(DST)
        mesh = E.duplicate_asset(SRC, path)
        if mesh is None:
            raise RuntimeError('duplicate failed ' + path)
    slots = mesh.get_editor_property('materials')
    if len(slots) != 11:
        raise RuntimeError('%s slot count %d != 11' % (name, len(slots)))
    seen = {}
    # struct-array trap: the for-loop element and slots[i] read are VALUE COPIES -- mutate a
    # local, write it back into the array by index, then set the whole array on the mesh.
    for i, slot in enumerate(slots):
        slot_name = str(slot.get_editor_property('material_slot_name'))
        if slot_name not in mapping:
            raise RuntimeError('unknown slot %s on %s' % (slot_name, name))
        slot.set_editor_property('material_interface', mats[mapping[slot_name]])
        slots[i] = slot
        seen[slot_name] = mapping[slot_name]
    if set(seen) != set(mapping):
        raise RuntimeError('slot set mismatch on ' + name)
    mesh.set_editor_property('materials', slots)
    for slot in mesh.get_editor_property('materials'):  # in-session read-back gate before save
        mi = slot.get_editor_property('material_interface')
        want = mapping[str(slot.get_editor_property('material_slot_name'))]
        if mi is None or str(mi.get_name()) != 'M_' + want:
            raise RuntimeError('material write did not stick on %s slot %s (got %s, want %s)'
                               % (name, slot.get_editor_property('material_slot_name'),
                                  mi.get_name() if mi else None, want))
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(path)], False):
        raise RuntimeError('save failed ' + path)
    receipt['variants'][name] = {'slots': seen,
                                 'skeleton_shared': mesh.get_editor_property('skeleton').get_path_name() == src_skel.get_path_name()}
    print('VARIANT', name, json.dumps(seen), flush=True)

open('D:/FPS3D/FPSGAME/SourceAssets/WarehouseCrateTiers20260924/skeletal_receipt.json', 'w', encoding='utf-8').write(
    json.dumps(receipt, ensure_ascii=False, indent=2))
print('SK_VARIANTS_DONE', len(receipt['variants']), flush=True)
