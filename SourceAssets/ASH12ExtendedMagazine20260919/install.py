"""Import local continuity revisions and preserve each rifle's material graph."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/ASH12/ExtendedMagazine20260919';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def node(m,c,**props):
 n=L.create_material_expression(m,c)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def link(a,out,b,pin):
 if pin=='Input':
  names=list(map(str,L.get_material_expression_input_names(b)))
  if pin not in names:pin=names[0]
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Connect failed '+a.get_name()+' '+out+' -> '+b.get_name()+' '+pin)
def clone(src,dst):return u.load_asset(dst) if E.does_asset_exist(dst) else E.duplicate_asset(src,dst)
def custom(m,code,inputs):
 n=node(m,u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
 rows=[]
 for k in inputs:
  row=u.CustomInput();row.set_editor_property('input_name',k);rows.append(row)
 n.set_editor_property('inputs',rows)
 for k,(a,out) in inputs.items():link(a,out,n,k)
 return n
def seam_material(gun,original):
 path=D+'/Materials/M_'+gun+'_Continuous';base=original.get_base_material();m=clone(base.get_path_name(),path+'_Graph')
 # These materials are exclusive to the static magazine's seven-channel seam UVs.
 for usage in ['used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing','automatically_set_usage_in_editor']:
  m.set_editor_property(usage,False)
 if isinstance(original,u.MaterialInstanceConstant):
  result=clone(original.get_path_name(),path);values={kind:{str(n):getattr(L,'get_material_instance_'+kind+'_parameter_value')(original,n) for n in getattr(L,'get_'+kind+'_parameter_names')(base)} for kind in ['scalar','vector','texture','static_switch']}
  L.set_material_instance_parent(result,m)
  for kind,ps in values.items():
   for key,v in ps.items():
    if v is not None:getattr(L,'set_material_instance_'+kind+'_parameter_value')(result,key,v)
 else:result=m
 if E.get_metadata_tag(m,'MagazineSeamContinuity')!='20260919':
  original_nodes=list(L.get_material_expressions(m));props=[u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_METALLIC,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_AMBIENT_OCCLUSION,u.MaterialProperty.MP_SPECULAR]
  uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=1)
  packed=[node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=i) for i in range(2,7)]
  weight=node(m,u.MaterialExpressionComponentMask,r=True,g=False,b=False,a=False);link(packed[0],'',weight,'Input')
  samples=[n for n in original_nodes if isinstance(n,u.MaterialExpressionTextureSample)]
  for sample in samples:
   if isinstance(sample,u.MaterialExpressionTextureSampleParameter2D) and str(sample.get_editor_property('parameter_name')) not in ['DiffuseColorMap','ShininessMap','NormalMap','AmbientOcclusionMap']:continue
   if not isinstance(sample,u.MaterialExpressionTextureSampleParameter2D):
    texture=sample.get_editor_property('texture')
    if not texture or '/Weapons/' not in texture.get_path_name():continue
   consumers=[]
   for n in original_nodes:
    ins=L.get_inputs_for_material_expression(m,n);names=L.get_material_expression_input_names(n)
    for source,pin in zip(ins,names):
     if source==sample:
      out=L.get_input_node_output_name_for_material_expression(n,sample)
      if isinstance(out,tuple):out=next(x for x in out if isinstance(x,str))
      consumers.append((n,str(pin),out or 'RGB'))
   roots=[(p,L.get_material_property_input_node_output_name(m,p)) for p in props if L.get_material_property_input_node(m,p)==sample]
   alt=node(m,type(sample),**{k:sample.get_editor_property(k) for k in ['texture','sampler_type','sampler_source']})
   if isinstance(sample,u.MaterialExpressionTextureSampleParameter2D):alt.set_editor_property('parameter_name',sample.get_editor_property('parameter_name'))
   link(uv,'',alt,'UVs')
   if sample.get_editor_property('sampler_type')==u.MaterialSamplerType.SAMPLERTYPE_NORMAL:
    # UE's texture-V tangent convention is the opposite of Blender's.
    # Conjugate the stored frame matrix by diag(1,-1,1); texture import settings stay unchanged.
    rotate=custom(m,'return float3(dot(N,float3(A.g,-B.r,B.g)),dot(N,float3(-C.r,C.g,-D.r)),dot(N,float3(D.g,-E.r,E.g)));',dict(N=(alt,'RGB'),**{k:(v,'') for k,v in zip('ABCDE',packed)}))
    blend=custom(m,'return normalize(lerp(N0,N1,W));',{'N0':(sample,'RGB'),'N1':(rotate,''),'W':(weight,'')})
   else:
    blend=node(m,u.MaterialExpressionLinearInterpolate);link(sample,'RGB',blend,'A');link(alt,'RGB',blend,'B');link(weight,'',blend,'Alpha')
   masks={}
   def channel(out):
    if out in ['R','G','B']:
     if out not in masks:
      masks[out]=node(m,u.MaterialExpressionComponentMask,r=out=='R',g=out=='G',b=out=='B',a=False);link(blend,'',masks[out],'Input')
     return masks[out],''
    if out in ['','RGB']:return blend,''
    # No opacity/emissive changes: keep any unrequested alpha consumer.
    return sample,out
   for n,pin,out in consumers:
    src,output=channel(out);link(src,output,n,pin)
   for prop,out in roots:
    src,output=channel(out);L.connect_material_property(src,output,prop)
  E.set_metadata_tag(m,'MagazineSeamContinuity','20260919');E.set_metadata_tag(m,'SourceRifleMaterial',original.get_path_name());L.recompile_material(m)
 save(m)
 if result!=m:L.update_material_instance(result);save(result)
 return result

dry=seam_material('ASH12',u.load_asset('/Game/Weapons/ASH12/Surface20260919/Materials/M_ASH12_Magazine'))
wet=seam_material('ASH12Wet',u.load_asset('/Game/Weapons/ASH12/Surface20260919/Materials/M_ASH12_Magazine_Wet'))
base=u.load_asset('/Game/Weapons/ASH12/Surface20260919/Materials/M_ASH12_Magazine_Base')
name='SM_ASH12_ExtMag30';t=u.AssetImportTask();t.filename=str(O/(name+'.fbx'));t.destination_path=D;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene_unit=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.generate_lightmap_u_vs=False;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;t.options=opts;t.factory=u.FbxFactory();A.import_asset_tasks([t])
mesh=u.load_asset(D+'/'+name)
if not mesh:raise RuntimeError('ASH12 import failed')
slots=mesh.get_editor_property('static_materials')
for i,slot in enumerate(slots):
 slot.material_interface=base if 'Base' in str(slot.material_slot_name) else dry;slots[i]=slot
mesh.set_editor_property('static_materials',slots);save(mesh)
(O/'installed.json').write_text(json.dumps(dict(mesh=mesh.get_path_name(),materials=[x.material_interface.get_path_name() for x in mesh.static_materials],dry=dry.get_path_name(),wet=wet.get_path_name(),tested=False),indent=2))
