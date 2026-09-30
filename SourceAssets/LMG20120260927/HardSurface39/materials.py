import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/LMG201/HardSurface39';F='/Game/Weapons/LMG201/FitFinish37/Materials';E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
recipes={'Cover':'Coat','Interior':'Interior','Satin':'Satin','Receiver':'Receiver','Handguard':'Surface'};out={'status':'building','materials':{}}
for role,parent in recipes.items():
 name='M_LMG201_H39_'+role;path=P+'/Materials/'+name;mat=u.load_asset(path) or E.duplicate_asset(F+'/M_LMG201_F37_'+parent,path)
 if not mat:raise RuntimeError('Cannot create '+path)
 if role in ['Receiver','Handguard']:
  original=M.get_material_property_input_node(mat,u.MaterialProperty.MP_NORMAL);channel=M.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_NORMAL)
  if not original:raise RuntimeError('Missing original structural normal')
  existing=next((n for n in M.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom) and n.get_editor_property('description')=='H39 fitted panel relief'),None)
  if existing is None:
   color=M.create_material_expression(mat,u.MaterialExpressionVertexColor);node=M.create_material_expression(mat,u.MaterialExpressionCustom);node.set_editor_property('description','H39 fitted panel relief');node.set_editor_property('code','return normalize(lerp(N,float3(0,0,1),saturate(Clean)*.65));');node.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
   inputs=[]
   for key in ['N','Clean']:
    pin=u.CustomInput();pin.set_editor_property('input_name',key);inputs.append(pin)
   node.set_editor_property('inputs',inputs)
   if not M.connect_material_expressions(original,channel,node,'N'):raise RuntimeError('Cannot retain normal')
   if not M.connect_material_expressions(color,'R',node,'Clean'):raise RuntimeError('Cannot connect local panel mask')
   if not M.connect_material_property(node,'',u.MaterialProperty.MP_NORMAL):raise RuntimeError('Cannot connect final normal')
 mat.set_editor_property('two_sided',False);mat.set_editor_property('used_with_skeletal_mesh',True)
 errors=M.recompile_material(mat)
 if errors:raise RuntimeError('Compile failed '+str(errors))
 E.set_metadata_tag(mat,'201Revision','HardSurface39: same body coat; fitted panels use explicit vertex-R mask to reduce old uneven relief only there')
 if not E.save_loaded_asset(mat,False):raise RuntimeError('Cannot save '+path)
 out['materials'][name]=mat.get_path_name()
out['status']='compiled_and_saved';(O/'materials.json').write_text(json.dumps(out,indent=2));print('H39_MATERIALS_SAVED',flush=True)
