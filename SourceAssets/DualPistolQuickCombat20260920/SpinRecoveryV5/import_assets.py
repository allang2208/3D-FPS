"""Install the authored profiles into their new directory; retain V3 and V4."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent;ROOT='/Game/Weapons/DualPistolQuickCombat20260920/SpinRecoveryV5'
receipt_path=P/'import.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'revision':'SpinRecoveryV5','assets':[],'testing':'Not performed; user testing'}
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE still active; stop play before saving animations.')
editor=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools();compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
jobs=[]
for weapon in ('M1911','DW715'):
    manifest=json.loads((P/f'{weapon}-authoring.json').read_text())
    for side,entry in manifest['sides'].items():
        mesh=u.load_asset(f'/Game/Weapons/PistolDualWield20260914/{weapon}/{side}/SK_Dual_{weapon}_{side}')
        if not mesh:raise RuntimeError('Missing dual mesh '+weapon+'/'+side)
        for kind,info in entry['clips'].items():
            name=f'A_Dual_{weapon}_{side}_{kind}';folder=f'{ROOT}/{weapon}/{side}/Animations';path=folder+'/'+name
            if path+'.'+name in receipt['assets']:continue
            if editor.does_asset_exist(path):raise RuntimeError('Unrecorded target already exists; preserved: '+path)
            jobs.append((mesh,folder,name,path,info['fbx']))
for mesh,folder,name,path,fbx in jobs:
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opts.import_mesh=False;opts.import_animations=True;opts.import_materials=False;opts.import_textures=False;opts.skeleton=mesh.skeleton
    opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    task=u.AssetImportTask();task.filename=fbx;task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=False;task.save=False;task.options=opts
    assets.import_asset_tasks([task]);clip=u.load_asset(path)
    if not clip:raise RuntimeError('Animation import failed '+path)
    if compression:clip.set_editor_property('bone_compression_settings',compression)
    editor.set_metadata_tag(clip,'DualQuickCombat.Revision','SpinRecoveryV5')
    if not editor.save_loaded_asset(clip,False):raise RuntimeError('Animation save failed '+path)
    receipt['assets'].append(clip.get_path_name());receipt_path.write_text(json.dumps(receipt,indent=2))
u.log('DUAL_SPIN_RECOVERY_SAVED '+str(len(receipt['assets']))+' animations to '+ROOT)
