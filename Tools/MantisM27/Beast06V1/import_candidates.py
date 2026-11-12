"""Save fitted review candidates without changing M27's active Blueprint."""
from pathlib import Path
import json
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1')
SOURCE=ROOT/'Delivery'; DEST='/Game/Monsters/MantisM27/Beast06V1/Animations'
manifest=json.loads((SOURCE/'motion_manifest.json').read_text())
L=u.EditorAssetLibrary; mesh=u.load_asset('/Game/Monsters/MantisM27/BindingV2/SK_MantisM27_BindingV2')
report={'revision':'Beast06V1','clips':{},'raw_reopened':{},'animation_assets_saved':False,
        'blueprint_connected':False,'runtime_tested':False,'native_code_changed':False}
def receipt(): (ROOT/'ue_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
try:
    # The retarget commandlet saved all inputs, then hit an engine compression
    # assertion during shutdown. Reopen the saved raw inputs in this process.
    raw=json.loads((ROOT/'native_poses.json').read_text())
    for role,info in raw['clips'].items():
        clip=u.load_asset(info['raw_asset'])
        if not isinstance(clip,u.AnimSequence): raise RuntimeError('Raw asset did not reopen '+role)
        report['raw_reopened'][role]={'asset':clip.get_path_name(),'seconds':clip.get_play_length()}
    receipt()
    for role,info in manifest['clips'].items():
        name=Path(info['file']).stem; options=u.FbxImportUI()
        options.automated_import_should_detect_type=False; options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh=False; options.import_as_skeletal=options.import_animations=True
        options.import_materials=options.import_textures=False; options.skeleton=mesh.skeleton
        for prop,value in {'convert_scene':True,'convert_scene_unit':True,'import_uniform_scale':1.,
                          'use_default_sample_rate':False,'custom_sample_rate':60,
                          'animation_length':u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,
                          'preserve_local_transform':True}.items():
            options.anim_sequence_import_data.set_editor_property(prop,value)
        task=u.AssetImportTask(); task.filename=str(SOURCE/info['file']); task.destination_path=DEST; task.destination_name=name
        task.automated=task.replace_existing=task.replace_existing_settings=True; task.save=False
        task.options=options; task.factory=u.FbxFactory(); u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        clip=u.load_asset(DEST+'/'+name)
        if not clip or not task.imported_object_paths: raise RuntimeError('Import failed '+role)
        clip.set_preview_skeletal_mesh(mesh); clip.set_editor_property('enable_root_motion',False); clip.set_editor_property('force_root_lock',False)
        L.set_metadata_tag(clip,'SourceAnimation',info['source'])
        L.set_metadata_tag(clip,'M27.Authoring','Beast06V1 review candidate; native retarget and anatomical fitting; not connected to runtime')
        if not L.save_loaded_asset(clip,False): raise RuntimeError('Save failed '+role)
        report['clips'][role]={'asset':clip.get_path_name(),'seconds':clip.get_play_length(),
                              'skeleton':clip.get_editor_property('skeleton').get_path_name()}
        receipt(); print('M27_BEAST06_CANDIDATE_SAVED '+role,flush=True)
    report['animation_assets_saved']=True; receipt()
    main='/Game/Monsters/MantisM27/BP_MantisM27'
    review='/Game/Monsters/MantisM27/Beast06V1/BP_MantisM27_Beast06ReviewV1'
    bp=u.load_asset(review) or L.duplicate_asset(main,review)
    if not bp: raise RuntimeError('Could not create separate review Blueprint')
    defaults=u.get_default_object(bp.generated_class())
    for prop,role in {'attack_clip':'LeftSlash','left_slash_clip':'LeftSlash','right_slash_clip':'RightSlash','idle_clip':'Idle'}.items():
        defaults.set_editor_property(prop,u.load_asset(report['clips'][role]['asset']))
    combat_class=u.load_class(None,'/Script/FPSGAME.MonsterCombatComponent')
    combat=defaults.get_component_by_class(combat_class)
    if not combat: raise RuntimeError('Review Blueprint has no combat component')
    combat.set_editor_property('hit_clip',u.load_asset(report['clips']['HitF']['asset']))
    L.set_metadata_tag(bp,'M27.Review','Beast06V1 fitted candidates; four direction routing remains planned; primary runtime Blueprint unchanged')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    if not L.save_loaded_asset(bp,False): raise RuntimeError('Could not save review Blueprint')
    report['review_blueprint']={'asset':review,'saved':True,'connected_clips':['LeftSlash','RightSlash','Idle','HitF'],
                               'direction_routing_implemented':False,'primary_blueprint_changed':False}
    receipt()
    print('M27_BEAST06_CANDIDATES_COMPLETE',flush=True)
except Exception as error:
    report['error']=str(error); receipt(); raise
