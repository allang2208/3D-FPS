"""Reimport the 23 corrected reloads at their current runtime paths."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
manifest=json.loads((O/'animation.json').read_text(encoding='utf-8'))
tools=u.AssetToolsHelpers.get_asset_tools();editor=u.EditorAssetLibrary
skeleton=u.load_asset('/Game/Weapons/DanWesson715/Integrated20260913/SK_DW715_Manny_Skeleton')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
receipt={'clips':{},'scope':'21 individual-loading clips and 2 speedloader reloads','testing':'Not performed; user testing'}
for kind,entry in manifest['clips'].items():
    name='A_DW715_'+kind;destination=entry['destination']
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh=False;options.import_animations=True;options.skeleton=skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    task=u.AssetImportTask();task.filename=str(O/'Animations'/(name+'.fbx'))
    task.destination_path=destination;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;task.options=options
    tools.import_asset_tasks([task]);clip=u.load_asset(destination+'/'+name)
    if not clip:raise RuntimeError('Could not import '+name)
    clip.set_editor_property('bone_compression_settings',compression)
    if not editor.save_loaded_asset(clip,False):raise RuntimeError('Could not save '+name)
    receipt['clips'][kind]=clip.get_path_name()
    u.log('DW715_FLICK_IMPORTED '+kind)
(O/'import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('DW715_FLICK_IMPORT_COMPLETE')
