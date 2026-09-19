import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).parent; DEST='/Game/Monsters/Mutant3Meshy'
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
at=u.AssetToolsHelpers.get_asset_tools(); lib=u.EditorAssetLibrary
source=u.load_asset(DEST+'/Sources/SK_M2M_Source'); target=u.load_asset(DEST+'/SK_Mutant3_Meshy')
rtg=u.load_asset(DEST+'/Rig/RTG_M2M_Mutant3')
clips=[]
for role in ['Jog','HitChest','ZombiePosture']:
    o=u.FbxImportUI(); o.automated_import_should_detect_type=False; o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    o.skeleton=source.skeleton; o.import_mesh=False; o.import_animations=True; o.import_materials=False; o.import_textures=False
    o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    o.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    o.anim_sequence_import_data.set_editor_property('convert_scene_unit',True)
    task=u.AssetImportTask(); task.filename=str(ROOT/f'prepared/A_M2M_{role}.fbx'); task.destination_name='A_M2M_'+role
    task.destination_path=DEST+'/Sources/Revision2'; task.options=o; task.automated=True; task.save=True; task.replace_existing=True
    at.import_asset_tasks([task]); clip=u.load_asset(task.destination_path+'/'+task.destination_name)
    if not clip: raise RuntimeError('Donor import failed: '+role)
    clips.append(clip)
params=u.IKRetargetBatchOperationInputs(); params.assets_to_retarget=[lib.find_asset_data(a.get_path_name()) for a in clips]
params.source_mesh=source; params.target_mesh=target; params.ik_retarget_asset=rtg
params.search='A_M2M_'; params.replace='A_Mutant3_R2_'; params.target_path=DEST+'/RetargetedRaw/Revision2'
params.include_referenced_assets=False; params.overwrite_existing_files=True
outputs=u.IKRetargetBatchOperation.run_batch_retarget(params); (ROOT/'native_retarget').mkdir(exist_ok=True)
report={}
for data in outputs:
    a=data.get_asset()
    if not isinstance(a,u.AnimSequence): continue
    a.set_preview_skeletal_mesh(target); a.set_editor_property('enable_root_motion',False); lib.save_loaded_asset(a,False)
    task=u.AssetExportTask(); task.object=a; task.filename=str(ROOT/'native_retarget'/(a.get_name()+'.fbx'))
    task.automated=True; task.prompt=False; task.replace_identical=True; task.exporter=u.AnimSequenceExporterFBX()
    options=u.FbxExportOption(); options.set_editor_property('export_preview_mesh',False); task.options=options
    if not u.Exporter.run_asset_export_task(task): raise RuntimeError('Donor export failed: '+a.get_name())
    report[a.get_name()]={'seconds':a.get_play_length(),'asset':a.get_path_name()}
(ROOT/'native_retarget.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('MUTANT3_REVISION2_RETARGETED '+json.dumps(report))
