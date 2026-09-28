"""Persist the actual post-import LOD budget; no reimport or runtime test."""
import json
import runpy
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

root=Path(__file__).parent
project=root.parents[2]
path='/Game/Props/GodSpaceLayout20260927/Meshes/SM_GodSpaceDistantOcean'
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty:raise RuntimeError('Preserve unsaved ocean mesh edits')
mesh=u.load_asset(path)
if not mesh:raise RuntimeError('Existing ocean mesh missing')
src=project/'Content'/(path.removeprefix('/Game/')+'.uasset')
dst=project/'trash/godspace-fountain-reuse-20260928'/datetime.now().strftime('%H%M%S-%f')/src.name
dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
runpy.run_path(str(root/'ocean_mesh_budget.py'))['apply'](mesh)
u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Ocean LOD budget save failed')
report={'saved':mesh.get_path_name(),'backup':str(dst),'distance_field_resolution_scale':0.,
    'lightmap_uvs':False,'ray_tracing_geometry':False,'cpu_access':False,'runtime_tested':False}
(root/'Receipts/ocean-reused-budget-saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('GODSPACE_REUSED_OCEAN_BUDGET_SAVED '+json.dumps(report))
