import unreal,json
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4InfimaRigRepair20260909')
DEST='/Game/Weapons/M4InfimaRigV4'

def imp(filename,options):
    task=unreal.AssetImportTask();task.filename=str(OUT/filename);task.destination_path=DEST
    task.automated=True;task.replace_existing=True;task.save=True;task.options=options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    assert task.imported_object_paths,filename

o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
o.import_as_skeletal=True;o.import_mesh=True;o.import_animations=False;o.import_materials=False;o.import_textures=False;o.create_physics_asset=False
imp('SK_M4_Infima.fbx',o)
mesh=unreal.load_asset(DEST+'/SK_M4_Infima');assert isinstance(mesh,unreal.SkeletalMesh)
old=unreal.load_asset('/Game/Weapons/M4InfimaV3/SK_M4_Infima');assert old
old_materials={str(s.material_slot_name):s.material_interface for s in old.materials}
slots=mesh.materials
for index,slot in enumerate(slots):
    key=str(slot.material_slot_name);assert key in old_materials,key
    slot.material_interface=old_materials[key]
    slots[index]=slot
mesh.set_editor_property('materials',slots)
skeleton=mesh.skeleton
unreal.AnimationLibrary.set_skeleton_preview_mesh(skeleton,mesh)
unreal.EditorAssetLibrary.save_loaded_asset(mesh)
unreal.EditorAssetLibrary.save_loaded_asset(skeleton)
# The imported armature carries the existing 100x metre-to-centimetre root scale.
# General-purpose compression tolerances were visible as centimetre-scale motion errors.
settings_path=DEST+'/BC_M4Viewmodel'
settings=unreal.load_asset(settings_path) if unreal.EditorAssetLibrary.does_asset_exist(settings_path) else unreal.EditorAssetLibrary.duplicate_asset('/ACLPlugin/ACLAnimBoneCompressionSettings',settings_path)
assert settings
settings.set_editor_property('error_threshold',0.0001)
settings.set_editor_property('force_below_threshold',True)
for codec in settings.get_editor_property('codecs'):
    codec.set_editor_property('ErrorThreshold',0.0001)
    codec.set_editor_property('OptimizationTargets',[mesh])
    codec.set_editor_property('KeyframeStrippingProportion',unreal.PerPlatformFloat(0.0))
    codec.set_editor_property('KeyframeStrippingThreshold',unreal.PerPlatformFloat(0.0))
unreal.EditorAssetLibrary.save_loaded_asset(settings,only_if_is_dirty=False)
report={}
for clip in json.loads((OUT/'export_report.json').read_text())['clips']:
    o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION
    o.import_mesh=False;o.import_as_skeletal=False;o.import_animations=True;o.skeleton=skeleton;o.import_materials=False;o.import_textures=False
    o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    o.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
    name='A_AKM_'+clip['clip'];imp(name+'.fbx',o)
    a=unreal.load_asset(DEST+'/'+name);assert a
    a.set_editor_property('bone_compression_settings',settings)
    unreal.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
    length=a.get_play_length();keys=a.get_editor_property('number_of_sampled_keys')
    assert abs(length-clip['duration'])<.001,(name,length)
    assert keys==clip['frames'],(name,keys,clip['frames'])
    report[name]={'duration':length,'keys':keys}
(OUT/'ue_import_report.json').write_text(json.dumps({'destination':DEST,'clips':report,'materials_reused_from':'M4InfimaV3'},indent=2))
unreal.log('M4_RIG_REPAIR_IMPORT_PASS')
