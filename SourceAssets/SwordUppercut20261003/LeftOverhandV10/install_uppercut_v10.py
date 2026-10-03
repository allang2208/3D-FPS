"""Save the user's forward lever rising cut V10; never run play."""
import json
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
PROJECT = P.parents[2]
DEST = '/Game/Weapons/SwordUppercut20261003'
REVISION = 'LeftOverhandUppercutV10'
L = u.EditorAssetLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE must end before any uppercut asset is edited or saved')
inputs = json.loads((P/'inputs.json').read_text('utf-8'))
mesh = u.load_asset(inputs['mesh'])
receipt = dict(revision=REVISION, animations={}, runtime_tested=False,
               rendered=False, paid_motion_used=False,
               reference='User clarified left thumb/index toward right hand; corrected overhand hilt side and wrist/forearm support; V9 right and timing retained')
if (P/'install_receipt.json').exists():
    receipt = json.loads((P/'install_receipt.json').read_text('utf-8'))

targets = globals().get('INSTALL_TARGETS',[('Standard',False), ('LongGrip',False), ('Standard',True)])
packages = {DEST+'/'+v+'/A_Sword_UppercutV1_'+v+('_PreviewLoop' if p else '') for v,p in targets}
dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if packages & dirty:
    raise RuntimeError('Preserving unsaved animation edits: '+str(sorted(packages & dirty)))

for variant,preview in targets:
    source = P/variant/'editable_keys.json'
    patch = json.loads(source.read_text('utf-8'))
    name = 'A_Sword_UppercutV1_'+variant+('_PreviewLoop' if preview else '')
    target = DEST+'/'+variant+'/'+name
    asset = u.load_asset(target)
    if not asset:
        raise RuntimeError('Registered skill animation missing: '+target)
    owner = L.get_metadata_tag(asset,'SwordUppercut.AuthorSource')
    if Path(owner) not in (P.parent/variant/'editable_keys.json',
                          P.parent/'ReferenceRevision'/variant/'editable_keys.json',
                          P.parent/'ArrowStepV3'/variant/'editable_keys.json',
                          P.parent/'LowerRightV4'/variant/'editable_keys.json',
                          P.parent/'ThrustGripV5'/variant/'editable_keys.json',
                          P.parent/'BackhandV6'/variant/'editable_keys.json',
                          P.parent/'ForwardLeverV7'/variant/'editable_keys.json',
                          P.parent/'LeftForwardGripV8'/variant/'editable_keys.json',
                          P.parent/'ChargedSnapV9'/variant/'editable_keys.json',source):
        raise RuntimeError('Preserving differently authored animation: '+target)
    disk = PROJECT/'Content'/target.removeprefix('/Game/')
    # Keep the actual previous saved package alongside V1's editable sources.
    for extension in ('.uasset','.uexp','.ubulk'):
        previous = disk.with_suffix(extension)
        backup = P/'PreviousAssets'/variant/(name+extension)
        if previous.exists() and not backup.exists():
            backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(previous,backup)
    samples = patch['samples']
    if preview:
        samples = samples+[samples[-1]]*round(.65*patch['fps'])
    controller = asset.get_editor_property('controller')
    if controller is None:
        controller = u.AnimDataController()
        controller.set_model(asset.get_editor_property('data_model_interface'))
    controller.open_bracket('Uppercut V10: video left overhand grip and neutral wrist support',False)
    try:
        controller.remove_all_bone_tracks(False)
        controller.set_frame_rate(u.FrameRate(numerator=patch['fps'],denominator=1),False)
        controller.set_number_of_frames(u.FrameNumber(value=len(samples)-1),False)
        for bone in samples[0]['bones']:
            if not controller.add_bone_curve(bone,False):
                raise RuntimeError('Cannot author bone '+bone)
            keys = [sample['bones'][bone] for sample in samples]
            if not controller.set_bone_track_keys(bone,[u.Vector(*k['p']) for k in keys],
                    [u.Quat(k['q'][1],k['q'][2],k['q'][3],k['q'][0]) for k in keys],
                    [u.Vector(*k['s']) for k in keys],False):
                raise RuntimeError('Cannot save keys '+bone)
    finally:
        controller.close_bracket(False)
    asset.set_preview_skeletal_mesh(mesh)
    asset.set_editor_property('enable_root_motion',False)
    asset.set_editor_property('force_root_lock',False)
    L.set_metadata_tag(asset,'SwordUppercut.AuthorSource',str(source))
    L.set_metadata_tag(asset,'SwordUppercut.Revision',REVISION)
    L.set_metadata_tag(asset,'SwordUppercut.Provenance',
        'User-video left overhand grip, thumb/index toward right hand; bounded hilt roll and complete left-arm support; V9 right/weapon/timing retained; no paid motion')
    fbx = None
    if not preview:
        fbx = P/variant/('A_Sword_UppercutV10_'+variant+'.fbx')
        task = u.AssetExportTask()
        for key,value in dict(object=asset,filename=str(fbx),automated=True,prompt=False,replace_identical=True).items():
            task.set_editor_property(key,value)
        task.options = u.FbxExportOption()
        task.options.ascii = False
        if not u.Exporter.run_asset_export_task(task):
            raise RuntimeError('FBX export failed '+target)
        import_data = asset.get_editor_property('asset_import_data')
        if import_data and hasattr(import_data,'update_filename_only'):
            import_data.update_filename_only(str(fbx))
    if not L.save_loaded_asset(asset,False):
        raise RuntimeError('Animation save failed '+target)
    receipt['animations'][target] = dict(asset=asset.get_path_name(),previous_author_metadata=owner,
        seconds=(len(samples)-1)/patch['fps'],keys=str(source),fbx=str(fbx) if fbx else None)
    (P/'install_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    u.log('UPPERCUT_V10_SAVED '+target)
