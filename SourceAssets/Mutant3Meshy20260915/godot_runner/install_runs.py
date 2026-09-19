"""Install only the two authored run clips into FPSGAME; retain replaced packages."""
import unreal as u, json, shutil
from pathlib import Path
ROOT=Path(__file__).parent; DEST='/Game/Monsters/Mutant3Meshy'
project=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if project != ROOT.parents[2].resolve():
    raise RuntimeError('Install only in FPSGAME.uproject')
updated=json.loads((ROOT/'animation_contract.json').read_text())
backup=ROOT/'previous_packages'; backup.mkdir(exist_ok=True)
records=[]
for role in ['Running','RunFast']:
    for suffix in ['.uasset','.uexp','.ubulk']:
        file=project/'Content/Monsters/Mutant3Meshy/Animations'/('A_Mutant3_'+role+suffix)
        if file.is_file():
            dest=backup/file.name
            if not dest.exists(): shutil.copy2(file,dest)
            records.append({'original':str(file),'backup':str(dest)})
(ROOT/'previous_packages.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
mesh=u.load_asset(DEST+'/SK_Mutant3_Meshy'); lib=u.EditorAssetLibrary; outputs={}
for role in ['Running','RunFast']:
    item=updated['clips'][role]; name='A_Mutant3_'+role
    o=u.FbxImportUI(); o.automated_import_should_detect_type=False
    o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION; o.import_mesh=False; o.import_animations=True
    o.skeleton=mesh.skeleton; o.import_materials=False; o.import_textures=False; o.import_as_skeletal=True
    data=o.anim_sequence_import_data; data.set_editor_property('use_default_sample_rate',False)
    data.set_editor_property('custom_sample_rate',120); data.set_editor_property('convert_scene_unit',True)
    data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    task=u.AssetImportTask(); task.filename=str(ROOT/'final'/(name+'.fbx'))
    task.destination_name=name; task.destination_path=DEST+'/Animations'; task.options=o
    task.automated=True; task.save=True; task.replace_existing=True
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    path=task.destination_path+'/'+name
    if not task.imported_object_paths: raise RuntimeError('No imported asset returned for '+name)
    clip=u.load_asset(path)
    if not clip: raise RuntimeError('Could not load imported animation '+path)
    clip.set_preview_skeletal_mesh(mesh); clip.set_editor_property('loop',True)
    clip.set_editor_property('enable_root_motion',False); clip.set_editor_property('force_root_lock',True)
    lib.set_metadata_tag(clip,'Source','Denys Almaral running_58f; CC BY 4.0; legacy Godot runner Walk alias')
    lib.set_metadata_tag(clip,'SourceURL','https://denysalmaral.com/post/free-zombie-animations-for-your-games/')
    lib.set_metadata_tag(clip,'Revision','2026-09-15 Godot runner retarget; only locomotion replaced')
    lib.set_metadata_tag(clip,'Status','Imported; user gameplay testing pending')
    lib.save_loaded_asset(clip,False)
    outputs[role]={'asset':clip.get_path_name(),**item}
(ROOT/'import_delivery.json').write_text(json.dumps(outputs,indent=2),encoding='utf-8')
contract_path=ROOT.parent/'animation_contract.json'; contract=json.loads(contract_path.read_text())
contract['clips'].update(updated['clips']); contract['active_revision']='godot_runner'
contract['state']='Godot running_58f retarget installed in Running/RunFast; revision2 Hit_Chest retained; gameplay not tested'
contract_path.write_text(json.dumps(contract,indent=2),encoding='utf-8')
updated['state']=contract['state']
(ROOT/'animation_contract.json').write_text(json.dumps(updated,indent=2),encoding='utf-8')
delivery_path=ROOT.parent/'ue_delivery.json'; delivery=json.loads(delivery_path.read_text())
for role,item in updated['clips'].items(): delivery['clips'][role].update(item)
delivery['active_revision']='godot_runner'; delivery['state']=contract['state']
delivery_path.write_text(json.dumps(delivery,indent=2),encoding='utf-8')
(ROOT/'installed.json').write_text(json.dumps({'project':str(project),'assets':outputs,'runtime_tested':False,
    'changes':'Only Running and RunFast replaced. Mesh, skin, Hit_Chest and gameplay code retained.'},indent=2),encoding='utf-8')
u.log('GODOT_RUNNER_INSTALLED '+json.dumps(outputs))
