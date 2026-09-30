"""One continuous polymer finish per grip; no extra grain bump layer."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/LMG201/GripJunction44';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;cap=json.loads((O/'capture.json').read_text());model=json.loads((O/'model.json').read_text());out={}
for key in ['factory','stable','balanced','phantom']:
 slots=cap['Body' if key=='factory' else key]['slots'];slot=next(s for s in slots if s['name']=='M_LMG201_FactoryRearGrip_G43') if key=='factory' else slots[1];path=P+'/Materials/M_J44_'+key+'_Polymer';m=u.load_asset(path)
 if not m:
  source=u.load_asset(slot['material']);m=E.duplicate_asset(source.get_base_material().get_path_name(),path)
  for n in L.get_material_expressions(m):
   if isinstance(n,u.MaterialExpressionScalarParameter):
    name=str(n.get_editor_property('parameter_name'))
    if name=='G43_Roughness':n.set_editor_property('default_value',.46)
    elif name=='G43_MicroNormalStrength':n.set_editor_property('default_value',0.)
   if isinstance(n,u.MaterialExpressionCustom):
    desc=n.get_editor_property('description')
    if desc=='G43 roughness hierarchy and single wet film':n.set_editor_property('code','float fresh=Center+(D.r-.5)*.012+(D.a-.5)*.018;float r=lerp(Base,clamp(fresh,.30,.62),Region);return lerp(r,max(.20,r*.73),saturate(Wet)*Region);')
    if desc=='G43 base coating and restrained wear':n.set_editor_property('code','float v=dot(Base,float3(.2126,.7152,.0722));float3 tone=Tint*(.98+.04*D.g)*lerp(1.,clamp(v/.032,.6,1.6),.04);return lerp(Base,tone,Region)*(1-saturate(Wet)*.12);')
  legacy=L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL);legacy_pin=L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_NORMAL);uv=L.create_material_expression(m,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('coordinate_index',model['grips'][key]['mask_uv_channel'])
  blend=L.create_material_expression(m,u.MaterialExpressionCustom);blend.set_editor_property('description','J44 continuous neck structural normal fade');blend.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3);blend.set_editor_property('code','float a=1-smoothstep(0.,.12,UV.x);return normalize(float3(N.xy*a,lerp(1.,N.z,a)));');pins=[]
  for name in ['N','UV']:
   pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
  blend.set_editor_property('inputs',pins)
  if not L.connect_material_expressions(legacy,legacy_pin,blend,'N') or not L.connect_material_expressions(uv,'',blend,'UV') or not L.connect_material_property(blend,'',u.MaterialProperty.MP_NORMAL):raise RuntimeError('Material link '+key)
  ao=L.get_material_property_input_node(m,u.MaterialProperty.MP_AMBIENT_OCCLUSION)
  if ao:
   ao_pin=L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_AMBIENT_OCCLUSION);fade=L.create_material_expression(m,u.MaterialExpressionCustom);fade.set_editor_property('description','J44 neck has independent occlusion');fade.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1);fade.set_editor_property('code','return lerp(AO,1.,smoothstep(0.,.12,UV.x));');pins=[]
   for name in ['AO','UV']:
    pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
   fade.set_editor_property('inputs',pins)
   if not L.connect_material_expressions(ao,ao_pin,fade,'AO') or not L.connect_material_expressions(uv,'',fade,'UV') or not L.connect_material_property(fade,'',u.MaterialProperty.MP_AMBIENT_OCCLUSION):raise RuntimeError('AO link '+key)
  m.set_editor_property('used_with_skeletal_mesh',key=='factory');m.set_editor_property('automatically_set_usage_in_editor',False);E.set_metadata_tag(m,'201GripFinishRevision','J44: continuous polymer, physical roughness detail, no added grain normal; preserved lower structure')
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Compile '+key+' '+str(errors))
 if not E.save_loaded_asset(m,False):raise RuntimeError('Save '+key)
 out[key]={'material':m.get_path_name(),'roughness':.46,'extra_micro_normal_strength':0,'mask_uv':model['grips'][key]['mask_uv_channel']}
(O/'materials.json').write_text(json.dumps(out,indent=2));print('J44_MATERIALS_SAVED',len(out),flush=True)
