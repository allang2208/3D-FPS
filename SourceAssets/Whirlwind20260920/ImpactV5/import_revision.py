"""Import V5, keeping the existing background blur material.

Run through the serialized bridge, or a Python commandlet when UE is closed.
Only creates this revision's assets; never starts PIE or renders a preview.
"""
import json
from pathlib import Path
import unreal as u

P=Path(__file__).parent
L=u.EditorAssetLibrary
M=u.MaterialEditingLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
folder='/Game/Weapons/AzureRunesword20260913'
name='A_RuneSword_WhirlwindV5'
asset=folder+'/'+name
if L.does_asset_exist(asset):
    raise RuntimeError('Revision already exists; resume from the completed import instead: '+asset)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
options=u.FbxImportUI()
options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
options.import_mesh=False;options.import_animations=True
options.import_materials=False;options.import_textures=False
options.skeleton=u.load_asset(folder+'/SK_AzureRunesword_Manny').skeleton
options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
options.anim_sequence_import_data.set_editor_property('custom_sample_rate',480)
task=u.AssetImportTask();task.filename=str(P/'Export'/f'{name}.fbx')
task.destination_path=folder;task.destination_name=name;task.automated=True
task.replace_existing=False;task.save=False;task.options=options
tools.import_asset_tasks([task])
clip=u.load_asset(asset)
if not task.imported_object_paths or not clip:raise RuntimeError('V5 animation import failed')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
if compression:clip.set_editor_property('bone_compression_settings',compression)
if not L.save_loaded_asset(clip):raise RuntimeError('V5 animation save failed')
(P/'import_receipt.json').write_text(json.dumps({'asset':clip.get_path_name(),'source':task.filename,'seconds':clip.get_play_length(),'saved':True},indent=2),encoding='utf-8')
u.log('WHIRLWIND_V5_IMPORTED '+clip.get_path_name())

exec(compile((P/'author_long_grip.py').read_text(encoding='utf-8'),str(P/'author_long_grip.py'),'exec'),{'__file__':str(P/'author_long_grip.py')})
u.log('WHIRLWIND_V5_ASSETS_SAVED')
