"""Persist the cloud renderer usage omitted by the initial cumulus authoring."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

root=Path(__file__).parent
project=root.parents[2]
path='/Game/Props/GodSpaceLayout20260927/Materials/M_GodSpaceCloudSea_Cumulus'
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty:raise RuntimeError('Preserve unsaved cumulus edits; material not changed')
mat=u.load_asset(path)
src=project/'Content/Props/GodSpaceLayout20260927/Materials/M_GodSpaceCloudSea_Cumulus.uasset'
dst=project/'trash/godspace-cloud-usage-20260928'/datetime.now().strftime('%H%M%S-%f')/src.name
dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
before=mat.get_editor_property('used_with_volumetric_cloud')
mat.set_editor_property('used_with_volumetric_cloud',True)
errors=list(u.MaterialEditingLibrary.recompile_material(mat))
if errors:raise RuntimeError('Cloud renderer shader compilation failed: '+str(errors))
u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
mi=u.load_asset('/Game/Props/GodSpaceLayout20260927/Materials/MI_GodSpaceCloudSea')
u.MaterialEditingLibrary.update_material_instance(mi)
if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise RuntimeError('Cloud usage save failed')
report={'saved':mat.get_path_name(),'used_with_volumetric_cloud_before':before,
    'used_with_volumetric_cloud_after':mat.get_editor_property('used_with_volumetric_cloud'),
    'compile_errors':errors,'backup':str(dst),'backup_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),
    'saved_sha256':hashlib.sha256(src.read_bytes()).hexdigest()}
(root/'Receipts/cumulus-cloud-usage-fixed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('CUMULUS_CLOUD_USAGE_FIXED '+json.dumps(report))
