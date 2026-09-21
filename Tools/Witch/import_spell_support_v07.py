"""Import only the two revised witch spells; retain all existing body assets."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchMeshy20260919')
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():
    raise RuntimeError('Editor does not host D:/FPS3D/FPSGAME; no witch assets imported')
AUTHOR=ROOT/'Authoring/SpellSupportV07'
DEST='/Game/Monsters/WitchMeshy/SpellSupportV07'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
manifest=json.loads((AUTHOR/'motion_manifest.json').read_text(encoding='utf-8'))
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE is running; revised witch spells have not been imported')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if any(p.get_path_name().startswith(DEST) for p in dirty):
    raise RuntimeError('SpellSupportV07 has unsaved edits; retained without reimport')
body=u.load_asset('/Game/Monsters/WitchMeshy/OriginalRobeV05/SK_Witch_Meshy')
if any(p.get_path_name()==body.skeleton.get_path_name().split('.')[0] for p in dirty):
    raise RuntimeError('Witch skeleton has unsaved edits; retained without importing curves')
report={'runtime_tested':False,'body_changed':False,'assets':[],'release_seconds':{}}
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for role,data in manifest['clips'].items():
    name='A_Witch_'+role
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opts.skeleton=body.skeleton;opts.import_mesh=False;opts.import_animations=True
    opts.import_materials=False;opts.import_textures=False
    imp=opts.anim_sequence_import_data
    for prop,value in [('convert_scene',True),('convert_scene_unit',True),('import_uniform_scale',1.0),
                       ('force_front_x_axis',False),('use_default_sample_rate',False),('custom_sample_rate',60),
                       ('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)]:
        imp.set_editor_property(prop,value)
    existing=u.load_asset(DEST+'/'+name)
    if existing:
        stored=existing.get_editor_property('asset_import_data')
        for prop,value in [('convert_scene',True),('convert_scene_unit',True),('import_uniform_scale',1.0),('force_front_x_axis',False)]:
            stored.set_editor_property(prop,value)
    task=u.AssetImportTask();task.filename=data['file'];task.destination_path=DEST;task.destination_name=name
    task.factory=u.FbxFactory();task.options=opts;task.automated=True;task.save=False
    task.replace_existing=True;task.replace_existing_settings=True
    AT.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('No clip imported for '+role)
    clip=u.load_asset(DEST+'/'+name)
    clip.set_editor_property('loop',False);clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',True);clip.set_preview_skeletal_mesh(body)
    for curve,values in data['curves'].items():
        if u.AnimationLibrary.does_curve_exist(clip,curve,u.RawCurveTrackTypes.RCT_FLOAT):
            u.AnimationLibrary.remove_curve(clip,curve)
        u.AnimationLibrary.add_curve(clip,curve)
        u.AnimationLibrary.add_float_curve_keys(clip,curve,[i/60 for i in range(len(values))],values)
    LIB.set_metadata_tag(clip,'Source','Clean cloud V02 upper action; independently planted soles and hip weight transfer V07')
    LIB.set_metadata_tag(clip,'ReleaseSeconds',str(data['release']))
    LIB.set_metadata_tag(clip,'Status','Authoring/import only; user gameplay review pending')
    if not LIB.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+name)
    report['assets'].append(clip.get_path_name());report['release_seconds'][role]=data['release']
    print('SAVED '+clip.get_path_name(),flush=True)
# Curves can dirty the shared skeleton; save only this known import-owned change.
if not LIB.save_loaded_asset(body.skeleton,False):raise RuntimeError('Could not save imported curve names')
cdo=u.get_default_object(u.WitchMonster)
cdo.set_editor_property('cast_clip',u.load_asset(DEST+'/A_Witch_CastPoison'))
cdo.set_editor_property('throw_clip',u.load_asset(DEST+'/A_Witch_ThrowPoisonBottle'))
cdo.set_editor_property('attack_clip',u.load_asset(DEST+'/A_Witch_CastPoison'))
report['status']='Saved and connected to native F6 Witch; user test pending'
(AUTHOR/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
