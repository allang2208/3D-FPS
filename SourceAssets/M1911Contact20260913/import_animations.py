"""Import contact-adjusted P9 clips against the existing M1911 skeleton."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/M1911/Contact20260913';A=u.AssetToolsHelpers.get_asset_tools()
mesh=u.load_asset('/Game/Weapons/M1911/Hero20260913/SK_M1911_Manny')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel');clips={}
for source in sorted((O/'Animations').glob('A_M1911_*.fbx')):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=P+'/Animations';task.destination_name=source.stem
    task.options=opt;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    clip=u.load_asset(P+'/Animations/'+source.stem)
    if not clip:raise RuntimeError('Animation import failed: '+source.name)
    if compression:clip.set_editor_property('bone_compression_settings',compression)
    if not u.EditorAssetLibrary.save_loaded_asset(clip,False):raise RuntimeError('Animation save failed: '+source.name)
    clips[source.stem]=clip.get_path_name()
(O/'import.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'animations':clips,'state':'Imported; not gameplay tested'},indent=2),encoding='utf-8')
u.log('M1911_CONTACT_IMPORT_COMPLETE')
