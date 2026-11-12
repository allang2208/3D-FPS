"""Finish compiling the saved lens graph, after all new input wires exist."""
from pathlib import Path
import json,unreal as u
P=Path('D:/FPS3D/FPSGAME/SourceAssets/PeakwatchPhysicalOptics20261109')
pkg='/Game/Weapons/SharedPhysicalOptics20261030/M_PhysicalScopeLens'
if any(p.get_path_name()==pkg for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserving unsaved material')
m=u.load_asset(pkg)
if not m:raise RuntimeError('Lens material missing')
errors=u.MaterialEditingLibrary.recompile_material(m)
if errors:raise RuntimeError(str(errors))
stats=u.MaterialEditingLibrary.get_statistics(m)
if stats.num_pixel_shader_instructions<=0:raise RuntimeError('Lens shader did not compile')
if not u.EditorAssetLibrary.save_loaded_asset(m,False):raise RuntimeError('Lens material save failed')
(P/'material-build.json').write_text(json.dumps(dict(saved=m.get_path_name(),
    pixel_instructions=stats.num_pixel_shader_instructions,vertex_instructions=stats.num_vertex_shader_instructions,
    samplers=stats.num_samplers,runtime_tested=False),indent=2),encoding='utf-8')
print('PEAKWATCH_LENS_COMPILED_AND_SAVED',flush=True)
