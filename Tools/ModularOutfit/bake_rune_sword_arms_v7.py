import json
import shutil
import time
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
SOURCE = '/Game/Weapons/AzureRunesword20260913/Modules20260919/SK_RuneSword_Arms.SK_RuneSword_Arms'
BARE = '/Game/Characters/ModularOutfit20260924/BarePalmV7/RuneSword/SK_RuneSword_BareArmsV7.SK_RuneSword_BareArmsV7'
SKIN = '/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials/MI_BareNative_Default.MI_BareNative_Default'
ARM_IDS = (1, 2)
BACKUP = PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7/NativeDefaults/Packages/RuneSwordArms.uasset'
E = u.EditorAssetLibrary
G = u.GeometryScript_AssetUtils
M = u.GeometryScript_Materials
Ed = u.GeometryScript_MeshEdits
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
SAVE = u.EditorLoadingAndSavingUtils

def play_world():
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if not world:
        return None
    name = world.get_name()
    if 'UEDPIE' in name or name.startswith('UEDPIE') or 'PIE_' in name:
        return world
    return None

world = play_world()
if world:
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    for _ in range(80):
        time.sleep(0.25)
        if not play_world():
            break
    else:
        raise RuntimeError('Finish play before baking rune sword arms')

def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing '+path)
    return asset

def save(asset):
    asset.modify()
    pkg = asset.get_outer()
    for _ in range(12):
        if SAVE.save_packages([pkg], False) or E.save_loaded_asset(asset, False):
            return
        time.sleep(0.25)
    raise RuntimeError('Cannot save '+asset.get_path_name())

def dynamic(asset):
    dm, out = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if out != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read '+asset.get_path_name())
    return dm

source = load(SOURCE)
bare = load(BARE)
skin = load(SKIN)
slots = [s.copy() for s in source.materials]
if len(slots) < 3:
    raise RuntimeError('Unexpected rune sword arms slot count '+str(len(slots)))
disk = PROJECT/'Content/Weapons/AzureRunesword20260913/Modules20260919/SK_RuneSword_Arms.uasset'
BACKUP.parent.mkdir(parents=True, exist_ok=True)
if disk.exists() and not BACKUP.exists():
    shutil.copy2(disk, BACKUP)
before = [(str(s.material_slot_name), s.material_interface.get_path_name() if s.material_interface else None) for s in slots]
dm = dynamic(source)
for material in ARM_IDS:
    M.delete_triangles_by_material_id(dm, material, True)
bare_dm = dynamic(bare)
for i in range(3):
    M.remap_material_i_ds(bare_dm, i, 1000+i)
for i, material in enumerate((ARM_IDS[0], ARM_IDS[1], ARM_IDS[1])):
    M.remap_material_i_ds(bare_dm, 1000+i, material)
Ed.append_mesh(dm, bare_dm, u.Transform(), True)
mats = [s.material_interface for s in slots]
for material in ARM_IDS:
    mats[material] = skin
options = u.GeometryScriptCopyMeshToAssetOptions(
    replace_materials=True, new_materials=mats,
    new_material_slot_names=[s.material_slot_name for s in slots],
    enable_recompute_normals=False, enable_recompute_tangents=True,
    bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_, out = G.copy_mesh_to_skeletal_mesh(dm, source, options, u.GeometryScriptMeshWriteLOD())
if out != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Cannot author rune sword arms')
lod_count = S.get_lod_count(source)
if lod_count > 1:
    S.regenerate_lod(source, lod_count, True, False)
E.set_metadata_tag(source, 'BareArmsDefault', 'V7; modular arms mesh used by long grip')
save(source)
after = []
for i, slot in enumerate(source.materials):
    mat = slot.material_interface
    after.append((i, str(slot.material_slot_name), mat.get_path_name() if mat else None))
receipt = {
    'source': SOURCE, 'bare': BARE, 'backup': str(BACKUP),
    'before': before, 'after': after,
    'hide_source_materials': list(ARM_IDS), 'runtime_tested': False,
}
(PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7/NativeDefaults/RuneSwordArms.json').write_text(
    json.dumps(receipt, indent=2) + chr(10), encoding='utf-8')
print('RUNE_SWORD_ARMS_BAKED', json.dumps({'after': after}), flush=True)
