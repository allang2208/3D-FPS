"""Import and save body assets and their actual part icons, without launching gameplay."""
from pathlib import Path
import json,hashlib
import unreal as u
P=Path(__file__).parent;ROOT=P.parents[1];DEST='/Game/Weapons/DarkBow20260925/BodyVariantsV14'
ICONS='/Game/ColdSteelData/AttachmentIcons20260913';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt=P/'import-receipt.json';r=json.loads(receipt.read_text()) if receipt.exists() else dict(saved={},sources={},gameplay_tested=False)
rows=json.loads((P/'authoring.json').read_text())['assets']
owned={DEST+'/'+row['mesh'] for row in rows}|{ICONS+'/bow_dark_riser_'+row['id'] for row in rows}
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/') or p.get_name() in owned]
if dirty:raise RuntimeError('Preserve unsaved packages '+str(dirty))
def save(a,source=None):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 r['saved'][a.get_name()]=a.get_path_name()
 if source:r['sources'][a.get_name()]=hashlib.sha256(source.read_bytes()).hexdigest()
 receipt.write_text(json.dumps(r,indent=2),encoding='utf8')
def fresh(name,folder):
 if name not in r['saved'] and E.does_asset_exist(folder+'/'+name):raise RuntimeError('Unowned asset '+folder+'/'+name)
def texture(name,source,kind,folder):
 if name in r['saved']:return u.load_asset(r['saved'][name])
 fresh(name,folder);task=u.AssetImportTask();task.filename=str(source);task.destination_path=folder;task.destination_name=name
 task.automated=True;task.replace_existing=False;task.save=False;A.import_asset_tasks([task]);a=u.load_asset(folder+'/'+name)
 if not a:raise RuntimeError('Texture import failed '+name)
 a.srgb=kind in ['BaseColor','Icon']
 a.compression_settings={'BaseColor':u.TextureCompressionSettings.TC_DEFAULT,'ORM':u.TextureCompressionSettings.TC_MASKS,'Normal':u.TextureCompressionSettings.TC_NORMALMAP,'Icon':u.TextureCompressionSettings.TC_EDITOR_ICON}[kind]
 if kind=='Normal':a.set_editor_property('flip_green_channel',True)
 if kind=='Icon':a.lod_group=u.TextureGroup.TEXTUREGROUP_UI;a.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
 else:a.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
 save(a,source);return a
old={kind:u.load_asset('/Game/Weapons/DarkBow20260925/WoodLongbow20260925/Textures/T_WoodLongbow_'+kind) for kind in ['BaseColor','ORM','Normal']}
if not all(old.values()):raise RuntimeError('Retained wood textures missing')
def node(m,cls,**props):
 a=L.create_material_expression(m,cls)
 for k,v in props.items():a.set_editor_property(k,v)
 return a
def wire(a,b,pin='',output=''):
 if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect material '+str(pin))
def output(a,prop,pin=''):
 if not L.connect_material_property(a,pin,prop):raise RuntimeError('Cannot connect material output')
def scalar(m,value):return node(m,u.MaterialExpressionConstant,r=value)
def material(row,tex):
 name=row['material']
 if name in r['saved']:return u.load_asset(r['saved'][name])
 fresh(name,DEST);m=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
 uv0=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
 uv1=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=1)
 mask=node(m,u.MaterialExpressionVertexColor)
 sampled={}
 for layer,maps,uv in [('old',old,uv0),('new',tex,uv1)]:
  for kind,a in maps.items():
   sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' and a.compression_settings==u.TextureCompressionSettings.TC_MASKS else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR
   n=node(m,u.MaterialExpressionTextureSample,texture=a,sampler_type=sampler);wire(uv,n,'UVs');sampled[(layer,kind)]=n
 for kind,prop,channel in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR,'RGB'),('ORM',u.MaterialProperty.MP_ROUGHNESS,'G')]:
  lerp=node(m,u.MaterialExpressionLinearInterpolate);wire(sampled[('old',kind)],lerp,'A',channel);wire(sampled[('new',kind)],lerp,'B',channel);wire(mask,lerp,'Alpha','R');output(lerp,prop)
 ao=node(m,u.MaterialExpressionLinearInterpolate);wire(sampled[('old','ORM')],ao,'A','R');wire(sampled[('new','ORM')],ao,'B','R');wire(mask,ao,'Alpha','R');output(ao,u.MaterialProperty.MP_AMBIENT_OCCLUSION)
 output(scalar(m,0),u.MaterialProperty.MP_METALLIC)
 # UV1 has its own grain direction. Convert its normal through a derivative
 # tangent frame before blending with the retained UV0 normal at fitted mounts.
 code='''float3 N=normalize(SurfaceNormal);
 float3 dx=ddx(Position),dy=ddy(Position);
 float2 tx=ddx(TimberUV),ty=ddy(TimberUV);
 float determinant=tx.x*ty.y-tx.y*ty.x;
 float signDet=determinant<0 ? -1 : 1;
 float3 T=(dx*ty.y-dy*tx.y)*signDet;
 float3 B=(dy*tx.x-dx*ty.x)*signDet;
 T=T-N*dot(N,T); B=B-N*dot(N,B);
 T=T*rsqrt(max(dot(T,T),1e-12)); B=B*rsqrt(max(dot(B,B),1e-12));
 return normalize(T*Detail.x*.6+B*Detail.y*.6+N*Detail.z);'''
 custom=node(m,u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,desc='Timber UV1 tangent frame')
 inputs=[]
 for key in ['Detail','TimberUV','Position','SurfaceNormal']:
  pin=u.CustomInput();pin.set_editor_property('input_name',key);inputs.append(pin)
 custom.set_editor_property('inputs',inputs)
 wire(sampled[('new','Normal')],custom,'Detail','RGB');wire(uv1,custom,'TimberUV')
 wire(node(m,u.MaterialExpressionWorldPosition),custom,'Position');wire(node(m,u.MaterialExpressionVertexNormalWS),custom,'SurfaceNormal')
 transform=node(m,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
 wire(custom,transform)
 strength=node(m,u.MaterialExpressionMultiply);wire(sampled[('old','Normal')],strength,'A','RGB');wire(node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.6,.6,1,1)),strength,'B')
 normal=node(m,u.MaterialExpressionLinearInterpolate);wire(strength,normal,'A');wire(transform,normal,'B');wire(mask,normal,'Alpha','R')
 normalized=node(m,u.MaterialExpressionNormalize);wire(normal,normalized,'VectorInput');output(normalized,u.MaterialProperty.MP_NORMAL)
 L.layout_material_expressions(m);L.recompile_material(m);save(m);return m
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for row in rows:
 tex={kind:texture('T_Bow_'+row['name']+'_'+kind,P/'Textures'/('T_Bow_'+row['name']+'_'+kind+'.png'),kind,DEST+'/Textures') for kind in ['BaseColor','ORM','Normal']}
 mat=material(row,tex);name=row['mesh']
 if name not in r['saved']:
  fresh(name,DEST);opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
  opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
  opt.static_mesh_import_data.generate_lightmap_u_vs=False
  opt.static_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
  task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name
  task.automated=True;task.replace_existing=False;task.save=False;task.options=opt;A.import_asset_tasks([task]);a=u.load_asset(DEST+'/'+name)
  if not a:raise RuntimeError('Mesh import failed '+name)
  a.set_material(0,mat);save(a,P/'Export'/(name+'.fbx'))
 # UV1 is authored timber mapping, not a lightmap destination. Rebuild the
 # owned mesh from its imported source with automatic lightmap UVs disabled.
 if r.get('timber_uv_preserved',{}).get(name)!=True:
  mesh=u.load_asset(r['saved'][name]);sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
  settings=sub.get_lod_build_settings(mesh,0);settings.set_editor_property('generate_lightmap_u_vs',False)
  sub.set_lod_build_settings(mesh,0,settings)
  r.setdefault('timber_uv_preserved',{})[name]=True;save(mesh)
 icon='bow_dark_riser_'+row['id'];texture(icon,P/'Icons'/(icon+'.png'),'Icon',ICONS)
print('BOW_BODY_VARIANTS_SAVED',json.dumps(r))
