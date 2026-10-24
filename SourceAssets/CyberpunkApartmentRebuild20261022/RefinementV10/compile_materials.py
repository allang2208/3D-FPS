"""Produce shader permutations for the three authored materials, without a game/view."""
from pathlib import Path
import unreal as u,json,traceback
R=Path(__file__).resolve().parent;receipt=json.loads((R/'assets_saved.json').read_text())
result=dict(stage='compiling',materials=[],game_run=False,acceptance_rendered=False)
try:
 for key in ['M_AP10_Portrait','M_AP10_Ribbon','M_AP10_BayWater']:
  path=receipt['materials'][key];mat=u.load_asset(path)
  errors=list(u.MaterialEditingLibrary.recompile_material(mat))
  if errors:raise RuntimeError(path+'\n'+'\n'.join(str(e) for e in errors))
  # UE's public barrier submits pending shader jobs and calls FinishCompilation.
  # RecompileMaterial alone can return before the generated HLSL has finished.
  shader=u.MaterialEditingLibrary.get_statistics(mat)
  if shader.get_editor_property('num_pixel_shader_instructions')<=0:raise RuntimeError('Shader production returned no pixel program: '+path)
  if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise RuntimeError('Material save failed '+path)
  result['materials'].append(path)
  (R/'material-compilation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
 result['stage']='compiled_and_saved';result['shader_completion_barrier']='MaterialEditingLibrary.GetStatistics / FMaterialResource.FinishCompilation'
except Exception:result['stage']='failed';result['error']=traceback.format_exc();raise
finally:(R/'material-compilation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
