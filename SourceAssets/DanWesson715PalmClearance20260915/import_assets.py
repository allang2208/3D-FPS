"""Import the seven palm-clearance extractor-press clips with the existing skeleton."""
import unreal as u, json
from pathlib import Path

out = Path(__file__).parent
manifest = json.loads((out/'animation.json').read_text(encoding='utf-8'))
asset_tools = u.AssetToolsHelpers.get_asset_tools()
editor = u.EditorAssetLibrary
skeleton = u.load_asset('/Game/Weapons/DanWesson715/Integrated20260913/SK_DW715_Manny_Skeleton')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
receipt = {'clips':{},'testing':'Not performed; user testing'}
for kind,entry in manifest['clips'].items():
    name = 'A_DW715_'+kind
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.skeleton = skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    task = u.AssetImportTask()
    task.filename = str(out/'Animations'/(name+'.fbx'))
    task.destination_path = entry['destination']
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.options = options
    asset_tools.import_asset_tasks([task])
    clip = u.load_asset(entry['destination']+'/'+name)
    if not clip: raise RuntimeError('Could not import '+name)
    clip.set_editor_property('bone_compression_settings',compression)
    if not editor.save_loaded_asset(clip,False): raise RuntimeError('Could not save '+name)
    receipt['clips'][kind] = clip.get_path_name()
    u.log('DW715_PALM_CLEARANCE_IMPORTED '+kind)
(out/'import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('DW715_PALM_CLEARANCE_IMPORT_COMPLETE')
