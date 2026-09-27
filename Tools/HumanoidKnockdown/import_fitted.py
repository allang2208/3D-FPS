"""Save the three fitted recovery clips for each current humanoid skeleton."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HumanoidKnockdown20260926')
DEST='/Game/Monsters/HumanoidKnockdown'
meta=json.loads((ROOT/'imported_animations.json').read_text())
clips=json.loads((ROOT/'fitted/authored_clips.json').read_text())
lib=u.EditorAssetLibrary;at=u.AssetToolsHelpers.get_asset_tools()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
delivery={}
for role,items in clips.items():
    mesh=u.load_asset(meta[role]['mesh'])
    saved=[]
    for name,info in items.items():
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        options.import_as_skeletal=True;options.import_mesh=False;options.import_animations=True
        options.import_materials=False;options.import_textures=False;options.skeleton=mesh.skeleton
        data=options.anim_sequence_import_data
        data.set_editor_property('use_default_sample_rate',False)
        data.set_editor_property('custom_sample_rate',60)
        data.set_editor_property('convert_scene_unit',True)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        task=u.AssetImportTask();task.filename=info['file'];task.destination_name=name
        task.destination_path=DEST+'/'+role;task.options=options
        task.automated=True;task.save=True;task.replace_existing=True
        at.import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('Import produced no asset: '+name)
        clip=u.load_asset(DEST+'/'+role+'/'+name)
        clip.set_preview_skeletal_mesh(mesh)
        clip.set_editor_property('loop',False)
        clip.set_editor_property('enable_root_motion',False)
        clip.set_editor_property('force_root_lock',True)
        lib.set_metadata_tag(clip,'Source','Mesh2Motion CC0: Hit_Knockback / LayToIdle; fitted to existing target skin')
        lib.set_metadata_tag(clip,'Authoring','Original bone lengths; grounded skin; fat-body hand clearance; prone roll prefix')
        lib.set_metadata_tag(clip,'Status','Saved asset; user visual/gameplay testing pending')
        if not lib.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+name)
        saved.append({'asset':clip.get_path_name(),'seconds':clip.get_play_length(),'file':info['file']})
    delivery[role]={'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'clips':saved}
    (ROOT/'fitted_delivery.json').write_text(json.dumps(delivery,indent=2),encoding='utf-8')
print('FITTED_RECOVERY_SAVED '+json.dumps(delivery))
