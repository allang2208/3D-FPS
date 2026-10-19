import unreal as u,json
from pathlib import Path
L=u.MaterialEditingLibrary
R={}
for part in ('Body','ReceiverCover','Handguard','Stock'):
 m=u.load_asset('/Game/Weapons/Saiga12K/Closure20261018/Materials/MI_Saiga12K_'+part);b=m.get_base_material()
 r={'base':b.get_path_name(),'scalars':{str(n):L.get_material_instance_scalar_parameter_value(m,n) for n in L.get_scalar_parameter_names(m)},'vectors':{},'properties':{},'nodes':[]};R[part]=r
 for n in L.get_vector_parameter_names(m):
  c=L.get_material_instance_vector_parameter_value(m,n);r['vectors'][str(n)]=[c.r,c.g,c.b,c.a]
 for n in ('MP_BASE_COLOR','MP_METALLIC','MP_ROUGHNESS','MP_NORMAL'):
  node=L.get_material_property_input_node(b,getattr(u.MaterialProperty,n));r['properties'][n]=node.get_name() if node else None
 if part=='Body':
  for node in L.get_material_expressions(b):
   row={'name':node.get_name(),'type':node.get_class().get_name(),'inputs':[n.get_name() if n else None for n in L.get_inputs_for_material_expression(b,node)]}
   for prop in ('description','code','parameter_name','default_value','r','g','b','a'):
    try:row[prop]=str(node.get_editor_property(prop))
    except Exception:pass
   r['nodes'].append(row)
Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KClosure20261018/Reports/core-materials.json').write_text(json.dumps(R,indent=2))
print('CORE_MATERIAL_GRAPH_READ')
