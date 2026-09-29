"""201-only finishes sampled from the actual receiver; explicit skeletal cloth support."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/LMG201/Repair36';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; save deferred')
sample=json.loads((O/'coating_sample.json').read_text());color=sample['base_linear_median'];metal=sample['metallic_median'];rough=sample['roughness_median'];materials={}
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
recipes={'Coat':(color,metal,rough),'Interior':([v*.78 for v in color],metal,.68),'Satin':([v*1.65 for v in color],.65,.50),'Sight':([v*.82 for v in color],.25,.68)}
for role,(rgb,met,r) in recipes.items():
 name='MI_LMG201_R36_'+role;mat=u.load_asset(P+'/Materials/'+name) or A.create_asset(name,P+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());parent=u.load_asset('/Game/Weapons/LMG201/Detail35/Materials/M_LMG201_D35_'+role)
 M.set_material_instance_parent(mat,parent);M.update_material_instance(mat)
 for n,v in [('Metallic',met),('DryRoughness',r),('Specular',.28)]:
  M.set_material_instance_scalar_parameter_value(mat,n,v)
  if abs(M.get_material_instance_scalar_parameter_value(mat,n)-v)>1e-5:raise RuntimeError('Cannot set '+n)
 M.set_material_instance_vector_parameter_value(mat,'FinishColor',u.LinearColor(*rgb,1))
 actual=M.get_material_instance_vector_parameter_value(mat,'FinishColor')
 if max(abs(x-y) for x,y in zip([actual.r,actual.g,actual.b],rgb))>1e-5:raise RuntimeError('Cannot set coating color')
 M.update_material_instance(mat);E.set_metadata_tag(mat,'201FinishRevision','Repair36: actual current receiver color, metal and roughness sampled; retained part identities');save(mat);materials[role]=mat.get_path_name()
# Original cloth was authored for a static box and never compiled for the
# skeletal feed. Preserve its complete woven graph in a private usable copy.
cloth_path=P+'/Materials/M_LMG201_R36_Cloth';cloth=u.load_asset(cloth_path) or E.duplicate_asset('/Game/Weapons/LMG201/Install30/Materials/M_LMG201_R30_Cloth',cloth_path)
cloth.set_editor_property('used_with_skeletal_mesh',True);cloth.set_editor_property('automatically_set_usage_in_editor',False)
errors=M.recompile_material(cloth)
if errors:raise RuntimeError(str(errors))
E.set_metadata_tag(cloth,'201ClothRevision','Repair36: woven source graph retained, skeletal mesh usage explicitly compiled');save(cloth);materials['Cloth']=cloth.get_path_name()
# The existing R29 maps are OpenGL tangent normals, imported in Install30 with
# flipped green. Detail35 retained that source convention but lost the flip.
normal_path=P+'/Textures/T_LMG201_R36_Receiver_Normal';normal=u.load_asset(normal_path) or E.duplicate_asset('/Game/Weapons/LMG201/Detail35/Textures/T_LMG201_D35_Receiver_Normal',normal_path);normal.set_editor_property('flip_green_channel',True);save(normal)
def node(m,cls,**props):
 n=M.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,p):
 n,ch=a if isinstance(a,tuple) else (a,'')
 if not M.connect_material_expressions(n,ch,b,p):raise RuntimeError('Cannot connect '+p)
def output(a,p):
 n,ch=a if isinstance(a,tuple) else (a,'')
 if not M.connect_material_property(n,ch,p):raise RuntimeError('Cannot connect output')
def scalar(m,n,v):return node(m,u.MaterialExpressionScalarParameter,parameter_name=n,default_value=v)
name='M_LMG201_R36_Receiver';mat=u.load_asset(P+'/Materials/'+name) or A.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew());M.delete_all_material_expressions(mat);mat.set_editor_property('used_with_skeletal_mesh',True);mat.set_editor_property('automatically_set_usage_in_editor',False);mat.set_editor_property('two_sided',False)
textures={'Normal':normal,'BaseColor':u.load_asset('/Game/Weapons/LMG201/Detail35/Textures/T_LMG201_D35_Receiver_BaseColor'),'ORM':u.load_asset('/Game/Weapons/LMG201/Detail35/Textures/T_LMG201_D35_Receiver_ORM')}
samples={k:node(mat,u.MaterialExpressionTextureSample,texture=t,sampler_type={'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'ORM':u.MaterialSamplerType.SAMPLERTYPE_MASKS,'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL}[k]) for k,t in textures.items()}
output((samples['Normal'],'RGB'),u.MaterialProperty.MP_NORMAL);output((samples['ORM'],'B'),u.MaterialProperty.MP_METALLIC);output((samples['ORM'],'R'),u.MaterialProperty.MP_AMBIENT_OCCLUSION);output(scalar(mat,'Specular',.28),u.MaterialProperty.MP_SPECULAR);wet=scalar(mat,'WeaponWetness',0);sat=node(mat,u.MaterialExpressionSaturate);wire(wet,sat,'')
for original,mult,floor,prop in [((samples['BaseColor'],'RGB'),.90,None,u.MaterialProperty.MP_BASE_COLOR),((samples['ORM'],'G'),.85,.48,u.MaterialProperty.MP_ROUGHNESS)]:
 mul=node(mat,u.MaterialExpressionMultiply,const_b=mult);wire(original,mul,'A');wet_value=mul
 if floor is not None:
  bounded=node(mat,u.MaterialExpressionMax,const_b=floor);wire(mul,bounded,'A');wet_value=bounded
 blend=node(mat,u.MaterialExpressionLinearInterpolate);wire(original,blend,'A');wire(wet_value,blend,'B');wire(sat,blend,'Alpha');output(blend,prop)
errors=M.recompile_material(mat)
if errors:raise RuntimeError(str(errors))
save(mat);materials['Receiver']=mat.get_path_name()
slots={'M_LMG201_D35_'+k:v for k,v in materials.items() if k!='Cloth'};slots.update(M_LMG201_D35_ControlCoat=materials['Coat'],M_LMG201_D35_ControlSatin=materials['Satin'],M_LMG201_Cloth33__NewBox_Cloth=materials['Cloth'],M_LMG201_Cloth33__OldBox_Cloth=materials['Cloth'])
report={'status':'compiled_and_saved','materials':materials,'slot_bindings':slots,'sample':sample,'recipes':recipes,'cloth_skeletal_usage':bool(cloth.get_editor_property('used_with_skeletal_mesh')),'cloth_textures':[t.get_path_name() for t in M.get_used_textures(cloth)],'receiver_normal_green_flip':bool(normal.get_editor_property('flip_green_channel'))}
(O/'materials.json').write_text(json.dumps(report,indent=2));print('REPAIR36_MATERIALS',json.dumps({'cloth_skeletal_usage':report['cloth_skeletal_usage'],'receiver_normal_green_flip':report['receiver_normal_green_flip'],'materials':materials}),flush=True)
