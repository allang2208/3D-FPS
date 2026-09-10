"""Create the final skeletal-rendering assets without editing the source packages.

Run again with -AKMRuntimeReadback for a separate, read-only saved-asset check.
"""
import json
from pathlib import Path
import unreal

OUT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKMReplacement')
SOURCE='/Game/Weapons/AKMReplacement'
DEST=SOURCE+'/Rendering'
GAME_MESH=DEST+'/SK_AKM_Replacement_Game'
READBACK_ONLY='-AKMRuntimeReadback' in unreal.SystemLibrary.get_command_line()
usage=unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH
source_mesh=unreal.load_asset(SOURCE+'/SK_AKM_Replacement')
assert isinstance(source_mesh,unreal.SkeletalMesh),'Missing source skeletal mesh'
source_skeleton=source_mesh.get_editor_property('skeleton')
source_slots=source_mesh.get_editor_property('materials')
assert len(source_slots)==7,len(source_slots)
expected_materials=[]
for slot in source_slots:
    original=slot.get_editor_property('material_interface')
    assert isinstance(original,unreal.Material),original
    assert original.get_path_name().startswith(SOURCE+'/')
    expected_materials.append(DEST+'/'+original.get_name()+'_Skinned')

if not READBACK_ONLY:
    unreal.EditorAssetLibrary.make_directory(DEST)
    runtime_materials=[]
    for slot,destination in zip(source_slots,expected_materials):
        original=slot.get_editor_property('material_interface')
        mat=unreal.load_asset(destination)
        if not mat:mat=unreal.EditorAssetLibrary.duplicate_asset(original.get_path_name(),destination)
        assert isinstance(mat,unreal.Material),destination
        assert mat.get_path_name().startswith(DEST+'/'),mat.get_path_name()
        unreal.MaterialEditingLibrary.set_material_usage(mat,usage)
        unreal.MaterialEditingLibrary.recompile_material(mat)
        assert unreal.MaterialEditingLibrary.has_material_usage(mat,usage),destination
        assert unreal.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False),destination
        runtime_materials.append(mat)
    runtime_mesh=unreal.load_asset(GAME_MESH)
    if not runtime_mesh:runtime_mesh=unreal.EditorAssetLibrary.duplicate_asset(source_mesh.get_path_name(),GAME_MESH)
    assert isinstance(runtime_mesh,unreal.SkeletalMesh),GAME_MESH
    assert runtime_mesh.get_path_name().startswith(DEST+'/'),runtime_mesh.get_path_name()
    slots=runtime_mesh.get_editor_property('materials')
    assert len(slots)==7,len(slots)
    for index,(slot,mat)in enumerate(zip(slots,runtime_materials)):
        slot.set_editor_property('material_interface',mat);slots[index]=slot
    runtime_mesh.set_editor_property('materials',slots)
    assert unreal.EditorAssetLibrary.save_loaded_asset(runtime_mesh,only_if_is_dirty=False),GAME_MESH

runtime_mesh=unreal.load_asset(GAME_MESH)
assert isinstance(runtime_mesh,unreal.SkeletalMesh),GAME_MESH
runtime_skeleton=runtime_mesh.get_editor_property('skeleton')
assert runtime_skeleton==source_skeleton,('Skeleton changed',runtime_skeleton,source_skeleton)
slots=runtime_mesh.get_editor_property('materials')
assert len(slots)==7,len(slots)
materials=[]
for index,(slot,expected)in enumerate(zip(slots,expected_materials)):
    mat=slot.get_editor_property('material_interface')
    assert mat.get_path_name().split('.')[0]==expected,(index,mat.get_path_name(),expected)
    enabled=unreal.MaterialEditingLibrary.has_material_usage(mat,usage)
    assert enabled,('Missing skeletal usage',mat.get_path_name())
    materials.append({'slot':index,'material':mat.get_path_name(),'skeletal_mesh_usage':enabled})
clips=[]
for clip in ['idle','aim','fire','aim_fire','reload','reload_empty','draw','holster','inspect','equip']:
    anim=unreal.load_asset(SOURCE+'/A_AKM_'+clip)
    assert anim and anim.get_editor_property('skeleton')==runtime_skeleton,clip
    clips.append(anim.get_path_name())
report={'passed':True,'mode':'independent saved asset readback'if READBACK_ONLY else 'create and save',
        'mesh':runtime_mesh.get_path_name(),'skeleton':runtime_skeleton.get_path_name(),
        'same_source_skeleton':True,'materials':materials,'compatible_animation_clips':clips,
        'source_assets_modified':False,'destination':DEST}
filename='akm_runtime_materials_readback.json'if READBACK_ONLY else 'akm_runtime_materials_build.json'
(OUT/filename).write_text(json.dumps(report,indent=2),encoding='utf-8')
marker='AKM_RUNTIME_MATERIALS_READBACK_OK'if READBACK_ONLY else 'AKM_RUNTIME_MATERIALS_BUILD_OK'
unreal.log(marker+' '+json.dumps({'mesh':report['mesh'],'materials':len(materials),'all_usage_enabled':all(m['skeletal_mesh_usage']for m in materials),'same_skeleton':True,'clips':len(clips)}))
