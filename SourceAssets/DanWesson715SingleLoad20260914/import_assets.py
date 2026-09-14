"""Import single-round clips and the gunsmith category icon; no PIE or render."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent
D='/Game/Weapons/DanWesson715/SingleLoad20260914/Animations'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
skeleton=u.load_asset('/Game/Weapons/DanWesson715/Integrated20260913/SK_DW715_Manny_Skeleton')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
receipt={'animations':{},'testing':'Not performed; user testing'}

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())

for filename in sorted((O/'Animations').glob('*.fbx')):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.skeleton=skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    t=u.AssetImportTask();t.filename=str(filename);t.destination_path=D;t.destination_name=filename.stem
    t.automated=True;t.replace_existing=True;t.save=False;t.options=opt
    A.import_asset_tasks([t]);clip=u.load_asset(D+'/'+filename.stem)
    if not clip:raise RuntimeError('Import failed: '+str(filename))
    clip.set_editor_property('bone_compression_settings',compression);save(clip)
    receipt['animations'][filename.stem]=clip.get_path_name()
    u.log('DW715_SINGLE_IMPORTED '+filename.stem)

t=u.AssetImportTask();t.filename=str(O/'Icons/T_Category_reload_device.png');t.destination_path='/Game/UI/GunsmithWorkbench/ColdGlass'
t.destination_name='T_Category_reload_device';t.automated=True;t.replace_existing=True;t.save=False
A.import_asset_tasks([t]);icon=u.load_asset(t.destination_path+'/'+t.destination_name)
if not icon:raise RuntimeError('Category icon import failed')
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('srgb',True);save(icon)
receipt['category_icon']=icon.get_path_name()
(O/'import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('DW715_SINGLE_IMPORT_COMPLETE')
