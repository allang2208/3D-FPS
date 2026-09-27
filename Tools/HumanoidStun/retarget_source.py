"""Import Dizzy, reuse the prepared humanoid IK mappings and export fit inputs."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HumanoidStun20260926')
DEST='/Game/Monsters/HumanoidStun'
lib=u.EditorAssetLibrary;at=u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE is active; end play before retargeting. No import was started.')
source=u.load_asset('/Game/Monsters/FatZombieMeshy/Sources/SK_M2M_Source')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opts.skeleton=source.skeleton
opts.import_mesh=False;opts.import_animations=True;opts.import_materials=False;opts.import_textures=False
data=opts.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False)
data.set_editor_property('custom_sample_rate',60);data.set_editor_property('convert_scene_unit',True)
task=u.AssetImportTask();task.filename=str(ROOT/'A_M2M_Dizzy.fbx');task.destination_path=DEST+'/Sources'
task.destination_name='A_M2M_Dizzy';task.options=opts;task.automated=True;task.save=True;task.replace_existing=True
clip=u.load_asset(DEST+'/Sources/A_M2M_Dizzy')
if not clip:
    at.import_asset_tasks([task])
    clip=u.load_asset(DEST+'/Sources/A_M2M_Dizzy')
if not clip:raise RuntimeError('Dizzy source import failed')
targets=json.loads((ROOT.parent/'HumanoidKnockdown20260926/imported_animations.json').read_text())
report={}
for role,info in targets.items():
    mesh=u.load_asset(info['mesh'])
    rtg=u.load_asset('/Game/Monsters/HumanoidKnockdown/Rig/RTG_M2M_'+role)
    if not rtg or not mesh:raise RuntimeError('Missing prepared humanoid mapping '+role)
    args=u.IKRetargetBatchOperationInputs()
    args.assets_to_retarget=[lib.find_asset_data(clip.get_path_name())]
    args.source_mesh=source;args.target_mesh=mesh;args.ik_retarget_asset=rtg
    args.search='A_M2M_';args.replace='A_'+role+'_';args.target_path=DEST+'/'+role
    args.include_referenced_assets=False;args.overwrite_existing_files=True
    outputs=u.IKRetargetBatchOperation.run_batch_retarget(args)
    saved=[]
    for item in outputs:
        anim=item.get_asset()
        if not isinstance(anim,u.AnimSequence):continue
        anim.set_preview_skeletal_mesh(mesh);anim.set_editor_property('enable_root_motion',False)
        if not lib.save_loaded_asset(anim,False):raise RuntimeError('Save failed '+anim.get_name())
        export=u.AssetExportTask();export.object=anim;export.filename=str(ROOT/(anim.get_name()+'_raw.fbx'))
        export.automated=True;export.prompt=False;export.replace_identical=True;export.exporter=u.AnimSequenceExporterFBX()
        exp_opts=u.FbxExportOption();exp_opts.set_editor_property('export_preview_mesh',True);export.options=exp_opts
        if not u.Exporter.run_asset_export_task(export):raise RuntimeError('Export failed '+anim.get_name())
        saved.append({'asset':anim.get_path_name(),'seconds':anim.get_play_length()})
    if len(saved)!=1:raise RuntimeError('Dizzy retarget incomplete '+role)
    report[role]={'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'clips':saved}
    (ROOT/'imported_animations.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DIZZY_RETARGET_SAVED '+json.dumps(report))
