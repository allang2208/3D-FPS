"""Import the four body-fit animations onto the original target skeleton."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).parent
DEST='/Game/Monsters/Mutant3Meshy'
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
tools=u.AssetToolsHelpers.get_asset_tools();lib=u.EditorAssetLibrary
mesh=u.load_asset(DEST+'/SK_Mutant3_Meshy')
contract=json.loads((ROOT/'animation_contract.json').read_text())
outputs={}
for role in contract['clips']:
    name='A_Mutant3_'+role
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh=False;options.import_animations=True;options.skeleton=mesh.skeleton
    options.import_materials=False;options.import_textures=False
    options.import_as_skeletal=True
    options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    data=options.anim_sequence_import_data
    data.set_editor_property('use_default_sample_rate',False)
    data.set_editor_property('custom_sample_rate',120)
    data.set_editor_property('convert_scene_unit',True)
    data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    task=u.AssetImportTask();task.filename=str(ROOT/'final'/(name+'.fbx'))
    task.destination_name=name;task.destination_path=DEST+'/Animations';task.options=options
    task.automated=True;task.save=True;task.replace_existing=True
    tools.import_asset_tasks([task])
    clip=u.load_asset(DEST+'/Animations/'+name)
    if clip is None:raise RuntimeError('Animation import failed: '+name+' '+str(task.imported_object_paths))
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('loop',contract['clips'][role]['loop'])
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',True)
    lib.set_metadata_tag(clip,'Source',contract['clips'][role]['origin']+': '+contract['clips'][role]['source'])
    lib.set_metadata_tag(clip,'Authoring','Native UE IK retarget; original Meshy skin; body-fit bake')
    lib.set_metadata_tag(clip,'Status','Authored candidate; user visual and gameplay testing pending')
    lib.save_loaded_asset(clip,False)
    outputs[role]={'asset':clip.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),**contract['clips'][role]}
lib.set_metadata_tag(mesh,'Source','User-provided Meshy_AI_The_Forsaken_Brute_biped.zip')
lib.set_metadata_tag(mesh,'Status','Original skin retained; automatic physics bodies; user testing pending')
lib.save_loaded_asset(mesh,False)
(ROOT/'ue_delivery.json').write_text(json.dumps({'mesh':mesh.get_path_name(),
    'skeleton':mesh.skeleton.get_path_name(),'clips':outputs,
    'content_folder':DEST,'stage_project':str(ROOT/'UEAuthoring/Mutant3Authoring.uproject'),
    'state':'Imported asset package. No runtime, render, or gameplay testing performed.'},indent=2),encoding='utf-8')
u.log('MUTANT3_FINAL_IMPORT_COMPLETE '+json.dumps(outputs))

