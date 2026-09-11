import unreal,json
from pathlib import Path
lib=unreal.MaterialEditingLibrary
tools=unreal.AssetToolsHelpers.get_asset_tools()
D='/Game/Items/LootFX'
report={'reviewed':[]}
for path in ['/Game/NiagaraExamples/Materials/MasterMaterials/M_Glow_Capsule','/Game/NiagaraExamples/Materials/MasterMaterials/M_FresnelGlow','/Game/NiagaraExamples/Materials/MasterMaterials/M_Flare','/Niagara/DefaultAssets/Templates/Emitters/StaticBeam','/Niagara/DefaultAssets/Templates/Emitters/DynamicBeam']:
 a=unreal.load_asset(path)
 entry={'path':path,'loaded':bool(a),'class':a.get_class().get_name() if a else None}
 if isinstance(a,unreal.Material):
  entry['blend']=str(a.get_editor_property('blend_mode'))
  entry['vector_parameters']=[str(n) for n in lib.get_vector_parameter_names(a)]
  entry['scalar_parameters']=[str(n) for n in lib.get_scalar_parameter_names(a)]
 report['reviewed'].append(entry)
for name,code in {
 'M_LootBeam':'''float h=saturate(UV.x); float w=abs(UV.y-.5);
 float body=exp(-w*w*90)*.20+exp(-w*w*2000)*.62;
 float ends=smoothstep(0,.018,h)*pow(1-h,1.4);
 return body*ends*(.94+.06*sin(Time*2.4));''',
 'M_LootCenter':'''float2 p=UV-.5;float r=length(p);
 float halo=exp(-r*r*34)*.23;float core=exp(-r*r*420)*.65;
 float spark=exp(-abs(p.x)*150-abs(p.y)*20)*.15+exp(-abs(p.y)*150-abs(p.x)*20)*.15;
 return saturate((halo+core+spark)*smoothstep(.5,.37,r))*(.95+.05*sin(Time*2.4));'''
}.items():
 m=unreal.load_asset(D+'/'+name) or tools.create_asset(name,D,unreal.Material,unreal.MaterialFactoryNew())
 for e in list(lib.get_material_expressions(m)):lib.delete_material_expression(m,e)
 m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_ADDITIVE)
 m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
 m.set_editor_property('two_sided',True)
 m.set_editor_property('disable_depth_test',False)
 uv=lib.create_material_expression(m,unreal.MaterialExpressionTextureCoordinate)
 time=lib.create_material_expression(m,unreal.MaterialExpressionTime)
 custom=lib.create_material_expression(m,unreal.MaterialExpressionCustom);custom.set_editor_property('code',code);custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
 inputs=[]
 for n in ['UV','Time']:
  i=unreal.CustomInput();i.set_editor_property('input_name',n);inputs.append(i)
 custom.set_editor_property('inputs',inputs)
 assert lib.connect_material_expressions(uv,'',custom,'UV')
 assert lib.connect_material_expressions(time,'',custom,'Time')
 color=lib.create_material_expression(m,unreal.MaterialExpressionVectorParameter);color.set_editor_property('parameter_name','LootColor');color.set_editor_property('default_value',unreal.LinearColor(.55,.05,1.,1.))
 power=lib.create_material_expression(m,unreal.MaterialExpressionScalarParameter);power.set_editor_property('parameter_name','Intensity');power.set_editor_property('default_value',5.)
 mul=lib.create_material_expression(m,unreal.MaterialExpressionMultiply)
 assert lib.connect_material_expressions(color,'',mul,'A')
 assert lib.connect_material_expressions(power,'',mul,'B')
 inverse=lib.create_material_expression(m,unreal.MaterialExpressionEyeAdaptationInverse)
 inverse_inputs=lib.get_material_expression_input_names(inverse)
 assert lib.connect_material_expressions(mul,'',inverse,str(inverse_inputs[0]))
 assert lib.connect_material_property(inverse,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
 fade=lib.create_material_expression(m,unreal.MaterialExpressionDepthFade);fade.set_editor_property('fade_distance_default',4.)
 assert lib.connect_material_expressions(custom,'',fade,'Opacity')
 assert lib.connect_material_property(fade,'',unreal.MaterialProperty.MP_OPACITY)
 lib.recompile_material(m);unreal.EditorAssetLibrary.save_loaded_asset(m)
report['implementation']='Original analytic soft beam and center flare, UE basic plane and material billboard. Reviewed examples remain unchanged; no Borderlands assets used.'
Path('D:/FPS3D/FPSGAME/Saved/LootFXAssetReview.json').write_text(json.dumps(report,indent=2))
unreal.log('LOOT_FX_MATERIAL_PASS')
