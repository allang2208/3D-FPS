"""Import only Running, RunFast and Stagger; preserve mesh, physics and other clips."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).parent; DEST='/Game/Monsters/Mutant3Meshy'
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
mesh=u.load_asset(DEST+'/SK_Mutant3_Meshy'); contract=json.loads((ROOT/'animation_contract.json').read_text())
lib=u.EditorAssetLibrary; outputs={}
for role,item in contract['clips'].items():
    name='A_Mutant3_'+role; o=u.FbxImportUI(); o.automated_import_should_detect_type=False
    o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION; o.import_mesh=False; o.import_animations=True; o.skeleton=mesh.skeleton
    o.import_materials=False; o.import_textures=False; o.import_as_skeletal=True
    data=o.anim_sequence_import_data; data.set_editor_property('use_default_sample_rate',False); data.set_editor_property('custom_sample_rate',120)
    data.set_editor_property('convert_scene_unit',True); data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    task=u.AssetImportTask(); task.filename=str(ROOT/'final'/(name+'.fbx')); task.destination_name=name; task.destination_path=DEST+'/Animations'
    task.options=o; task.automated=True; task.save=True; task.replace_existing=True
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]); clip=u.load_asset(task.destination_path+'/'+name)
    if not clip: raise RuntimeError('Failed to import replacement '+name)
    clip.set_preview_skeletal_mesh(mesh); clip.set_editor_property('loop',item['loop']); clip.set_editor_property('enable_root_motion',False); clip.set_editor_property('force_root_lock',True)
    lib.set_metadata_tag(clip,'Source','Mesh2Motion CC0: '+item['source'])
    lib.set_metadata_tag(clip,'Revision','2026-09-15 revision2: natural jogging / standing chest recoil')
    lib.set_metadata_tag(clip,'Status','Replacement imported; user gameplay testing pending'); lib.save_loaded_asset(clip,False)
    outputs[role]={'asset':clip.get_path_name(),**item}
(ROOT/'import_delivery.json').write_text(json.dumps(outputs,indent=2),encoding='utf-8')
u.log('MUTANT3_REPLACEMENTS_IMPORTED '+json.dumps(outputs))
