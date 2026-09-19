"""导入 M4 枪托砸击的作者源 clip（6 个握把配置），沿用 M4 视模骨架与压缩设置。

只导入与保存；不跑运行时检查（按项目规则由用户实测）。
"""
import json
from pathlib import Path

import unreal as u

O = Path(__file__).resolve().parent
root = '/Game/Weapons/M4QuickMeleeReplica20260919'
mesh = u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
asset_tools = u.AssetToolsHelpers.get_asset_tools()

flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    receipt = {}
    for folder in sorted(p for p in O.glob('*/Animations/A_M4_QuickCombat_*.fbx')):
        profile = folder.stem.replace('A_M4_QuickCombat_', '')
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh = False
        options.import_animations = True
        options.import_materials = False
        options.import_textures = False
        options.skeleton = mesh.skeleton
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
        task = u.AssetImportTask()
        task.filename = str(folder)
        task.destination_path = '%s/%s' % (root, profile)
        task.destination_name = folder.stem
        task.options = options
        task.automated = True
        task.replace_existing = True
        task.save = False
        asset_tools.import_asset_tasks([task])
        clip = u.load_asset('%s/%s/%s' % (root, profile, folder.stem))
        if not clip:
            raise RuntimeError('Import failed: %s' % folder)
        clip.set_editor_property('bone_compression_settings', compression)
        if not u.EditorAssetLibrary.save_loaded_asset(clip, False):
            raise RuntimeError('Save failed: %s' % clip.get_path_name())
        receipt[profile] = {'path': clip.get_path_name(), 'length': clip.get_play_length()}
        u.log('M4_QUICKCOMBAT_IMPORTED %s length=%.4f' % (profile, clip.get_play_length()))

    (O / 'import.json').write_text(json.dumps(
        {'animations': receipt, 'status': 'Imported and saved; user testing pending'}, indent=2), encoding='utf-8')
    u.log('M4_QUICKCOMBAT_IMPORT_COMPLETE %d' % len(receipt))
finally:
    u.SystemLibrary.execute_console_command(None,f'{flag} {previous}')
