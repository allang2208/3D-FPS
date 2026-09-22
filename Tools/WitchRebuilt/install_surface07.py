"""Preserve original cloth charts; shade rebuilt sleeves/yoke with clean weave."""
import unreal as u
DEST='/Game/Monsters/WitchRebuilt';L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
path=DEST+'/Materials/M_WitchRebuilt_UpperFabric07'
mat=u.load_asset(path) if L.does_asset_exist(path) else AT.create_asset('M_WitchRebuilt_UpperFabric07',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
if L.get_metadata_tag(mat,'WitchSurfaceRevision')!='Seams07: alpha-masked clean cuffs and continuous waist':
 for p in ('two_sided','used_with_skeletal_mesh','used_with_clothing'):mat.set_editor_property(p,True)
 mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
 def node(cls):return M.create_material_expression(mat,cls)
 def link(a,b,p,output=''):M.connect_material_expressions(a,output,b,p)
 def con(v):
  n=node(u.MaterialExpressionConstant3Vector if isinstance(v,tuple) else u.MaterialExpressionConstant)
  n.set_editor_property('constant' if isinstance(v,tuple) else 'r',u.LinearColor(*v,1) if isinstance(v,tuple) else v);return n
 def tex(path,kind,uv=None):
  n=node(u.MaterialExpressionTextureSample);n.texture=u.load_asset(path)
  if not n.texture:raise RuntimeError('Missing cloth texture '+path)
  n.set_editor_property('sampler_type',kind)
  if uv:link(uv,n,'Coordinates')
  return n
 def custom(code,inputs):
  n=node(u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
  entries=[]
  for name in inputs:
   entry=u.CustomInput();entry.set_editor_property('input_name',name);entries.append(entry)
  n.set_editor_property('inputs',entries);return n
 uv0=node(u.MaterialExpressionTextureCoordinate);uv0.coordinate_index=0
 tiled=node(u.MaterialExpressionTextureCoordinate);tiled.coordinate_index=0;tiled.u_tiling=32.;tiled.v_tiling=32.
 mask=node(u.MaterialExpressionVertexColor)
 albedo=tex('/Game/Monsters/WitchMeshy/Textures/T_Witch_Body_base_color',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
 oldcolor=node(u.MaterialExpressionLinearInterpolate);link(albedo,oldcolor,'A','RGB');link(con((.12,.10,.068)),oldcolor,'B');link(con(.28),oldcolor,'Alpha')
 weavecolor=custom('float v=0.5+0.22*sin(UV.x*37+sin(UV.y*9))+0.12*sin(UV.y*23+UV.x*11); return lerp(float3(.060,.052,.040),float3(.090,.078,.061),saturate(v));',['UV']);link(uv0,weavecolor,'UV')
 color=node(u.MaterialExpressionLinearInterpolate);link(oldcolor,color,'A');link(weavecolor,color,'B');link(mask,color,'Alpha','A')
 base=tex('/Game/Monsters/WitchMeshy/Textures/T_Witch_Body_normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 detail=tex(DEST+'/Textures/Detail/T_Witch_FabricDetail_N',u.MaterialSamplerType.SAMPLERTYPE_NORMAL,tiled)
 normal=custom('float3 n=normalize(lerp(float3(0,0,1),Base,0.24*(1-saturate(Repair)))); return normalize(float3(n.xy+Detail.xy*0.09,n.z*max(Detail.z,0.7)));',['Base','Detail','Repair'])
 link(base,normal,'Base','RGB');link(detail,normal,'Detail','RGB');link(mask,normal,'Repair','A')
 rd=tex(DEST+'/Textures/Detail/T_Witch_FabricDetail_R',u.MaterialSamplerType.SAMPLERTYPE_MASKS,tiled)
 scale=node(u.MaterialExpressionMultiply);link(rd,scale,'A','R');link(con(.10),scale,'B')
 rough=node(u.MaterialExpressionAdd);link(scale,rough,'A');link(con(.82),rough,'B')
 slab=node(u.MaterialExpressionSubstrateShadingModels)
 for expr,prop,pin in ((color,u.MaterialProperty.MP_BASE_COLOR,'BaseColor'),(normal,u.MaterialProperty.MP_NORMAL,'Normal'),(rough,u.MaterialProperty.MP_ROUGHNESS,'Roughness'),(con(.18),u.MaterialProperty.MP_SPECULAR,'Specular'),(con(0.),u.MaterialProperty.MP_METALLIC,'Metallic')):
  M.connect_material_property(expr,'',prop);link(expr,slab,pin)
 M.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);M.recompile_material(mat)
 L.set_metadata_tag(mat,'WitchSurfaceRevision','Seams07: alpha-masked clean cuffs and continuous waist')
 if not L.save_loaded_asset(mat,False):raise RuntimeError('Surface07 save failed')
print('Saved '+mat.get_path_name())
