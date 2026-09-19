"""Import the M1911 quick-combat (grip bash) clip with the live mesh's skeleton."""
import unreal as u, json
from pathlib import Path

out = Path(__file__).parent
manifest = json.loads((out / 'animation.json').read_text(encoding='utf-8'))
asset_tools = u.AssetToolsHelpers.get_asset_tools()
editor = u.EditorAssetLibrary
mesh = u.load_asset('/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny.SK_M1911_Manny')
if not mesh:
    raise RuntimeError('Live M1911 viewmodel mesh not found')
skeleton = mesh.get_editor_property('skeleton')
u.log('skeleton resolved from live mesh: %s' % skeleton.get_path_name())
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
receipt = {'skeleton': skeleton.get_path_name(), 'clips': {}, 'testing': 'Not performed; user testing'}

kind = manifest['clip']
name = 'A_M1911_' + kind
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
options.import_mesh = False
options.import_animations = True
options.skeleton = skeleton
options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
options.anim_sequence_import_data.set_editor_property('custom_sample_rate', manifest['sample_rate'])
task = u.AssetImportTask()
task.filename = str(out / 'Animations' / (name + '.fbx'))
task.destination_path = manifest['destination']
task.destination_name = name
task.automated = True
task.replace_existing = True
task.save = False
task.options = options
asset_tools.import_asset_tasks([task])
clip = u.load_asset(manifest['destination'] + '/' + name)
if not clip:
    raise RuntimeError('Could not import ' + name)
clip.set_editor_property('bone_compression_settings', compression)
if not editor.save_loaded_asset(clip, False):
    raise RuntimeError('Could not save ' + name)
receipt['clips'][kind] = {'path': clip.get_path_name(), 'length': clip.get_play_length()}
u.log('M1911_QUICKCOMBAT_IMPORTED %s length=%.4f' % (kind, clip.get_play_length()))

(out / 'import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('M1911_QUICKCOMBAT_IMPORT_COMPLETE')
