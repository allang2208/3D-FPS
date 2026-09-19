import json
from pathlib import Path
import unreal as u
out=Path(__file__).parent;dest='/Game/ColdSteelUI/Warehouse20260909/RitualV8'
assets=u.AssetToolsHelpers.get_asset_tools();lib=u.MaterialEditingLibrary
task=u.AssetImportTask()
for k,v in {'filename':str(out/'warehouse_chest_rigid.glb'),'destination_path':dest,'automated':True,'replace_existing':False,'save':True}.items():task.set_editor_property(k,v)
assets.import_asset_tasks([task])
aa=[u.EditorAssetLibrary.load_asset(p) for p in u.EditorAssetLibrary.list_assets(dest,recursive=True,include_folder=False)]
meshes=[a for a in aa if isinstance(a,u.SkeletalMesh)];assert len(meshes)==1
report={'mesh':meshes[0].get_path_name()}
for a in aa:
 if isinstance(a,u.AnimSequence):
  for k,duration in [('open',.9),('close',.7)]:
   if k in a.get_name().lower():assert abs(a.get_play_length()-duration)<.001;report[k]=a.get_path_name()
assert len(report)==3

def ex(mat,cls,x,y,**props):
 n=lib.create_material_expression(mat,cls,x,y)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,out,b,pin):assert lib.connect_material_expressions(a,out,b,pin)
def prop(a,out,p):assert lib.connect_material_property(a,out,p)
def instance(name,mat):
 mi=assets.create_asset(name,dest+'/Surfaces',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
 lib.set_material_instance_parent(mi,mat)
 ov=mi.get_editor_property('base_property_overrides');ov.set_editor_property('override_two_sided',True);ov.set_editor_property('two_sided',True);mi.set_editor_property('base_property_overrides',ov)
 return mi
def save(a):assert u.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
mat=assets.create_asset('M_Ritual_Metal',dest+'/Surfaces',u.Material,u.MaterialFactoryNew());assert mat
mat.set_editor_property('two_sided',True);lib.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
tex=u.EditorAssetLibrary.load_asset('/Game/ColdSteelUI/Warehouse20260909/DirtyMetal/T_DirtyMetal_MR_4K');assert tex
uv=ex(mat,u.MaterialExpressionTextureCoordinate,-1500,0,u_tiling=3.6,v_tiling=3.6)
sample=ex(mat,u.MaterialExpressionTextureSampleParameter2D,-1250,0,texture=tex,parameter_name='DirtyMetal',sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS);wire(uv,'',sample,'')
tint=ex(mat,u.MaterialExpressionVectorParameter,-1250,400,parameter_name='MetalTint',default_value=u.LinearColor(.11,.13,.16,1))
strength=ex(mat,u.MaterialExpressionScalarParameter,-1250,250,parameter_name='DirtStrength',default_value=.30)
mask=ex(mat,u.MaterialExpressionMultiply,-950,120);wire(sample,'R',mask,'A');wire(strength,'',mask,'B')
dark=ex(mat,u.MaterialExpressionMultiply,-950,420,const_b=.45);wire(tint,'',dark,'A')
color=ex(mat,u.MaterialExpressionLinearInterpolate,-500,380);wire(tint,'',color,'A');wire(dark,'',color,'B');wire(mask,'',color,'Alpha');prop(color,'',u.MaterialProperty.MP_BASE_COLOR)
metal=ex(mat,u.MaterialExpressionScalarParameter,-700,650,parameter_name='Metallic',default_value=.95)
mixmetal=ex(mat,u.MaterialExpressionLinearInterpolate,-400,650,const_b=.25);wire(metal,'',mixmetal,'A');wire(mask,'',mixmetal,'Alpha');prop(mixmetal,'',u.MaterialProperty.MP_METALLIC)
base=ex(mat,u.MaterialExpressionScalarParameter,-1250,-300,parameter_name='RoughnessBase',default_value=.38)
variation=ex(mat,u.MaterialExpressionMultiply,-950,-80,const_b=.16);wire(sample,'G',variation,'A')
offset=ex(mat,u.MaterialExpressionAdd,-700,-100,const_b=-.08);wire(variation,'',offset,'A')
rough=ex(mat,u.MaterialExpressionAdd,-480,-150);wire(base,'',rough,'A');wire(offset,'',rough,'B')
# Fine directional machining changes roughness subtly, never visible as thick ridges.
cm=ex(mat,u.MaterialExpressionComponentMask,-1250,-550,r=True,g=False,b=False,a=False);wire(uv,'',cm,'')
freq=ex(mat,u.MaterialExpressionMultiply,-1000,-550,const_b=1600);wire(cm,'',freq,'A')
sine=ex(mat,u.MaterialExpressionSine,-780,-550);wire(freq,'',sine,'')
grain=ex(mat,u.MaterialExpressionMultiply,-560,-550,const_b=.012);wire(sine,'',grain,'A')
roughfinal=ex(mat,u.MaterialExpressionAdd,-200,-250);wire(rough,'',roughfinal,'A');wire(grain,'',roughfinal,'B');prop(roughfinal,'',u.MaterialProperty.MP_ROUGHNESS)
lib.recompile_material(mat);save(mat)
recipes={'Frame':([.11,.13,.16],.38,.95,.30),'Strap':([.13,.15,.18],.34,.95,.24),'Hardware':([.17,.19,.21],.27,.95,.18),'Champagne':([.34,.29,.20],.31,.94,.22),'Engraving':([.025,.032,.04],.55,.70,.15)}
paths={}
for name,(color,roughness,metallic,dirt) in recipes.items():
 mi=instance('MI_Ritual_'+name,mat)
 lib.set_material_instance_vector_parameter_value(mi,'MetalTint',u.LinearColor(*color,1))
 for key,value in {'RoughnessBase':roughness,'Metallic':metallic,'DirtStrength':dirt}.items():lib.set_material_instance_scalar_parameter_value(mi,key,value)
 lib.update_material_instance(mi);save(mi);paths[name]=mi.get_path_name()
gem=assets.create_asset('M_Ritual_Sapphire',dest+'/Surfaces',u.Material,u.MaterialFactoryNew());gem.set_editor_property('two_sided',True);lib.set_material_usage(gem,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
bc=ex(gem,u.MaterialExpressionConstant3Vector,-400,0,constant=u.LinearColor(.004,.015,.055,1));prop(bc,'',u.MaterialProperty.MP_BASE_COLOR)
for i,(value,p) in enumerate([(.14,u.MaterialProperty.MP_ROUGHNESS),(.03,u.MaterialProperty.MP_METALLIC),(.65,u.MaterialProperty.MP_SPECULAR)]):prop(ex(gem,u.MaterialExpressionConstant,-400,150+i*140,r=value),'',p)
lib.recompile_material(gem);save(gem);mi=instance('MI_Ritual_Sapphire',gem);lib.update_material_instance(mi);save(mi);paths['Sapphire']=mi.get_path_name()
report['materials']={'Gold_PBR':paths['Frame'],'Brass_Frame':paths['Frame'],'Brass_Strap':paths['Strap'],'Brass_Hardware':paths['Hardware'],'Ritual_Gunmetal':paths['Frame'],'Ritual_Champagne':paths['Champagne'],'Ritual_Engraving':paths['Engraving'],'Sapphire_PBR':paths['Sapphire']}
report['recipes']=recipes
(out/'import_report.json').write_text(json.dumps(report,indent=2));u.log('CHEST_RITUAL_IMPORT_PASS')
