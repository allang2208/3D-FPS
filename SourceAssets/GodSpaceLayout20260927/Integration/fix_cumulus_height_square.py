"""Repair the HLSL signed-square found during the requested cloud screenshot."""
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
if path in dirty:raise RuntimeError('Preserve unsaved cumulus edits')
mat=u.load_asset(path)
nodes=[n for n in u.MaterialEditingLibrary.get_material_expressions(mat)
    if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='Weather footprint, rounded height profile and conservative empty-space skip']
if len(nodes)!=1:raise RuntimeError('Expected exactly one cumulus height expression')
src=project/'Content/Props/GodSpaceLayout20260927/Materials/M_GodSpaceCloudSea_Cumulus.uasset'
dst=project/'trash/godspace-cumulus-square-20260928'/datetime.now().strftime('%H%M%S-%f')/src.name
dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
nodes[0].set_editor_property('code',(root/'CloudSeaCumulusCoverage.hlsl').read_text(encoding='utf8'))
errors=list(u.MaterialEditingLibrary.recompile_material(mat))
if errors:raise RuntimeError('Material compilation failed: '+str(errors))
if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise RuntimeError('Material save failed')
report={'saved':mat.get_path_name(),'compile_errors':errors,'backup':str(dst),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()}
(root/'Receipts/cumulus-square-fixed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('CUMULUS_HEIGHT_SQUARE_FIXED '+json.dumps(report))
