"""Replace miner locomotion/attack clips while reusing the enlarged mesh."""
import unreal,json
from pathlib import Path

ROOT=Path(unreal.Paths.project_dir())/'SourceAssets/InfectedMiner20260913/NaturalWrist/Delivery'
DEST='/Game/Monsters/InfectedMiner/NaturalWrist20260913'
lib=unreal.EditorAssetLibrary
mesh=unreal.load_asset('/Game/Monsters/InfectedMiner/DragGround20260913/SK_InfectedMiner_DragGround')
report=json.loads((ROOT/'rebuild.json').read_text())
clips={}
for state in ['Idle','Walk','Attack']:
    options=unreal.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION
    options.skeleton=mesh.skeleton;options.import_mesh=False;options.import_animations=True
    options.import_materials=False;options.import_textures=False
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
    name='A_Miner_NaturalWrist_'+state
    task=unreal.AssetImportTask();task.filename=str(ROOT/f'A_Miner_{state}.fbx')
    task.destination_path=DEST;task.destination_name=name;task.options=options
    task.automated=True;task.replace_existing=True;task.save=True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    clip=unreal.load_asset(DEST+'/'+name)
    if not clip:raise RuntimeError('Import failed: '+name)
    unreal.AnimationLibrary.remove_all_animation_notify_tracks(clip)
    clip.set_preview_skeletal_mesh(mesh);lib.save_loaded_asset(clip,False)
    clips[state]=clip;report['clips'][state]['path']=clip.get_path_name()
bp=unreal.load_asset('/Game/Monsters/InfectedMiner/BP_InfectedMiner')
cdo=unreal.get_default_object(bp.generated_class())
for state,clip in clips.items():cdo.set_editor_property(state.lower()+'_clip',clip)
lib.save_loaded_asset(bp,False)
report['delivery_mesh']=mesh.get_path_name();report['blueprint']=bp.get_path_name()
report['geometry_bind_skin_materials_changed']=False
(ROOT/'rebuild.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('MINER_NATURAL_WRIST_IMPORTED '+json.dumps({state:clip.get_path_name() for state,clip in clips.items()}))
