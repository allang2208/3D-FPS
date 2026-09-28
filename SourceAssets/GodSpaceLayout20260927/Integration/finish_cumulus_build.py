"""Finish the texture/material build after creation-time resource warnings.

No map load, render, gameplay or scene acceptance. Save only owned new assets.
"""
import json
from pathlib import Path
import unreal as u
root=Path(__file__).parent
dest='/Game/Props/GodSpaceLayout20260927/Materials/'
mat=u.load_asset(dest+'M_GodSpaceCloudSea_Cumulus')
noise=u.load_asset(dest+'VT_GodSpaceCloudNoise_LinearMips')
targets={dest+'M_GodSpaceCloudSea_Cumulus',dest+'VT_GodSpaceCloudNoise_LinearMips'}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):raise RuntimeError('Preserve unsaved cumulus assets')
u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
errors=list(u.MaterialEditingLibrary.recompile_material(mat))
if errors:raise RuntimeError('Cumulus final shader compilation failed: '+str(errors))
for asset in [noise,mat]:
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):
        raise RuntimeError('Could not finish saving '+asset.get_path_name())
data=u.EditorAssetLibrary.find_asset_data(dest+'VT_GodSpaceCloudNoise_LinearMips')
report={'material':mat.get_path_name(),'shader_compile_errors':errors,
    'texture_dimensions':data.get_tag_value('Dimensions'),
    'texture_format':data.get_tag_value('Format'),
    'texture_mip_generation':str(noise.get_editor_property('mip_gen_settings')),
    'texture_srgb':noise.get_editor_property('srgb'),
    'runtime_tested':False}
(root/'Receipts/cumulus-build-completed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('CUMULUS_BUILD_COMPLETED '+json.dumps(report))
