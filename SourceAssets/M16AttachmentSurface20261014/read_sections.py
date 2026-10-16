import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;C=json.loads((O/'inputs.json').read_text())
for key,row in C['meshes'].items():
 mesh=u.load_asset(row['path'])
 mats,indices,names,status=u.GeometryScript_AssetUtils.get_section_material_list_from_static_mesh(mesh,u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
 row['sections']=[{'slot_index':i,'name':str(n),'material':m.get_path_name()} for m,i,n in zip(mats,indices,names)]
 print(key,json.dumps(row['sections']))
for comp in u.ObjectIterator(u.StaticMeshComponent):
 mesh=comp.get_editor_property('static_mesh')
 if not mesh or mesh.get_path_name().split('.')[0] not in [C['meshes'][k]['path'] for k in ('M16_stock','M16_balanced')]:continue
 for i in range(comp.get_num_materials()):
  m=comp.get_material(i)
  if isinstance(m,u.MaterialInstanceDynamic):print('ACTIVE_MID',i,m.parent.get_path_name(),'wet',m.get_scalar_parameter_value('WeaponWetness'))
(O/'inputs.json').write_text(json.dumps(C,indent=2),encoding='utf-8')
