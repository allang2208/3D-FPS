"""Finish material shader compilation and save; no game, screenshots or preview."""
from pathlib import Path
import json,unreal as u
O=Path(__file__).resolve().parent
report={'compiled_and_saved':[],'shader_statistics':{},'game_tested':False,'rendered':False}
for name in ('M_PhysicalScopeLens','M_PhysicalScopeHideReticle','M_PhysicalThermalScene'):
 m=u.load_asset('/Game/Weapons/SharedPhysicalOptics20261030/'+name)
 if not m:raise RuntimeError(name)
 if name=='M_PhysicalScopeLens':
  u.MaterialEditingLibrary.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True)
  u.MaterialEditingLibrary.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_MORPH_TARGETS,True)
 errors=u.MaterialEditingLibrary.recompile_material(m)
 if errors:raise RuntimeError(str(errors))
 stats=u.MaterialEditingLibrary.get_statistics(m)
 report['shader_statistics'][name]={'pixel_instructions':stats.num_pixel_shader_instructions,'vertex_instructions':stats.num_vertex_shader_instructions,'samplers':stats.num_samplers}
 if name=='M_PhysicalScopeLens' and stats.num_pixel_shader_instructions<=0:raise RuntimeError('Lens shader did not compile')
 if not u.EditorLoadingAndSavingUtils.save_packages([m.get_outermost()],False):raise RuntimeError('Save '+name)
 report['compiled_and_saved'].append(m.get_path_name())
 (O/'material-build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('OPTIC_MATERIAL_BUILT',name,flush=True)
