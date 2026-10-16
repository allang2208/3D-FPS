import unreal as u, json
from pathlib import Path
O=Path(__file__).parent; R=[]
for comp in u.ObjectIterator(u.MeshComponent):
 path=comp.get_path_name()
 if 'UEDPIE_' not in path or 'FPSGAMECharacter' not in path:continue
 try:mesh=comp.static_mesh if isinstance(comp,u.StaticMeshComponent) else comp.get_skinned_asset()
 except Exception:continue
 if not mesh:continue
 slots=[]
 for i in range(comp.get_num_materials()):
  m=comp.get_material(i)
  if not m:continue
  row={'slot':i,'material':m.get_path_name(),'base':m.get_base_material().get_path_name()}
  if isinstance(m,u.MaterialInstanceDynamic):
   row['parent']=m.parent.get_path_name()
   row['scalars']={str(n):m.get_scalar_parameter_value(n) for n in u.MaterialEditingLibrary.get_scalar_parameter_names(m.get_base_material())}
   row['textures']={str(n):t.get_path_name() if t else None for n in u.MaterialEditingLibrary.get_texture_parameter_names(m.get_base_material()) for t in [m.get_texture_parameter_value(n)]}
  slots.append(row)
 R.append({'component':path,'mesh':mesh.get_path_name(),'slots':slots})
(O/'runtime.json').write_text(json.dumps(R,indent=2))
print('A762_RUNTIME_MATERIALS',len(R))
