import unreal as u,json
from pathlib import Path
M=u.MaterialEditingLibrary;out={}
for role in ['Coat','Interior','Satin','Sight']:
 p=u.load_asset('/Game/Weapons/LMG201/Detail35/Materials/M_LMG201_D35_'+role)
 out[role]={'parent':p.get_path_name(),'scalar_names':[str(n) for n in M.get_scalar_parameter_names(p)],'vector_names':[str(n) for n in M.get_vector_parameter_names(p)]}
 for kind,fn in [('scalars',M.get_material_default_scalar_parameter_value),('vectors',M.get_material_default_vector_parameter_value)]:
  out[role][kind]={str(n):str(fn(p,n)) for n in (M.get_scalar_parameter_names(p) if kind=='scalars' else M.get_vector_parameter_names(p))}
print('R36_PARAMETERS',json.dumps(out),flush=True);(Path(__file__).parent/'parameters.json').write_text(json.dumps(out,indent=2))
