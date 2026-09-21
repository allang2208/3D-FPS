"""Apply the 0.25-second dash windup to Standard and LongGrip SprintOverhead only."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).parent
L = u.EditorAssetLibrary
receipt_path = P/'import_receipt.json'
receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {'revision':'DashAttackWindupV5','saved':{},'runtime_tested':False}
patches = [(p,json.loads(p.read_text())) for variant in ('Standard','LongGrip') for p in sorted((P/variant).glob('*_keys.json'))]
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE active; new sprint animation import deferred without changing assets.')
targets = {patch['asset'] for _,patch in patches}
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets]
if dirty:raise RuntimeError('Unsaved changes on sprint targets: '+str(dirty))
for file,patch in patches:
    key = file.parent.name+'/'+file.stem
    if key in receipt['saved']:continue
    target = patch['asset']
    if L.does_asset_exist(target):
        asset = u.load_asset(target)
        previous_source = P.parent/'MeleeTacticalSprintReady20260921'/file.parent.name/file.name
        if L.get_metadata_tag(asset,'MeleeSprint.AuthorSource') not in (str(file),str(previous_source)):
            raise RuntimeError('Preserving pre-existing candidate with unknown ownership: '+target)
    else:
        asset = L.duplicate_asset(patch['source'],target)
        if not asset:raise RuntimeError('Could not create '+target)
        L.set_metadata_tag(asset,'MeleeSprint.AuthorSource',str(file))
    controller = asset.get_editor_property('controller')
    if controller is None:
        controller = u.AnimDataController()
        controller.set_model(asset.get_editor_property('data_model_interface'))
    controller.open_bracket('Quarter-second sprint attack windup V5',False)
    try:
        controller.remove_all_bone_tracks(False)
        controller.set_frame_rate(u.FrameRate(numerator=patch['fps'],denominator=1),False)
        controller.set_number_of_frames(u.FrameNumber(value=patch['intervals']),False)
        for name in patch['samples'][0]['bones']:
            if not controller.add_bone_curve(name,False):raise RuntimeError('Cannot create track '+name)
            keys = [row['bones'][name] for row in patch['samples']]
            if not controller.set_bone_track_keys(name,[u.Vector(*k['p']) for k in keys],
                [u.Quat(k['q'][1],k['q'][2],k['q'][3],k['q'][0]) for k in keys],
                [u.Vector(*k['s']) for k in keys],False):
                raise RuntimeError('Cannot write track '+name)
    finally:
        controller.close_bracket(False)
    asset.set_preview_skeletal_mesh(u.load_asset(patch['mesh']))
    L.set_metadata_tag(asset,'MeleeSprint.Revision',patch['revision'])
    L.set_metadata_tag(asset,'MeleeSprint.AuthorSource',str(file))
    export = file.parent/(asset.get_name()+'.fbx')
    task = u.AssetExportTask()
    task.object,task.filename,task.automated,task.prompt,task.replace_identical = asset,str(export),True,False,True
    task.options = u.FbxExportOption()
    task.options.ascii = False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('FBX export failed '+target)
    import_data = asset.get_editor_property('asset_import_data')
    if import_data and hasattr(import_data,'update_filename_only'):import_data.update_filename_only(str(export))
    if not L.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+target)
    receipt['saved'][key] = {'asset':asset.get_path_name(),'seconds':asset.get_play_length(),'fbx':str(export),'source':patch['source']}
    receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    u.log('MELEE_SPRINT_SAVED '+key+' '+target)
