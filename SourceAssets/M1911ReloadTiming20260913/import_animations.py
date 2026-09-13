"""Import the two shortened reload clips, retaining the accepted M1911 rig."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/M1911/ReloadReady20260913/Animations';A=u.AssetToolsHelpers.get_asset_tools()
mesh=u.load_asset('/Game/Weapons/M1911/Hero20260913/SK_M1911_Manny');compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel');report={}
for kind in ['reload','reload_empty']:
    name='A_M1911_'+kind;opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    task=u.AssetImportTask();task.filename=str(O/'Animations'/(name+'.fbx'));task.destination_path=D;task.destination_name=name
    task.options=opt;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);clip=u.load_asset(D+'/'+name)
    if not clip:raise RuntimeError('Import failed '+name)
    if compression:clip.set_editor_property('bone_compression_settings',compression)
    if not u.EditorAssetLibrary.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+name)
    report[kind]={'path':clip.get_path_name(),'duration':clip.get_play_length(),'skeleton':clip.get_editor_property('skeleton').get_path_name()}
    (O/'import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('M1911_READY_RELOAD_IMPORT_COMPLETE')
