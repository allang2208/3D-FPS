"""Import knit long sleeves and charcoal cotton T-shirt as isolated families."""
import json,sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldSweaterKnit20260929';DEST='/Game/Characters/ModularOutfit20260924/FieldSweaterKnit20260929'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save(asset):
 asset.modify()
 if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):raise RuntimeError('Save failed '+asset.get_path_name())
def textures(pattern):
 out={};folder=DEST+'/Textures/'+pattern;E.make_directory(folder)
 for ch in ['BaseColor','Normal','ORM','Relief']:
  name='T_'+pattern+'_'+ch;tex=u.load_asset(folder+'/'+name)
  if not tex:
   task=u.AssetImportTask();task.filename=str(R/'Textures'/pattern/(ch+'.png'));task.destination_path=folder;task.destination_name=name;task.automated=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(folder+'/'+name)
  if not tex:raise RuntimeError('Texture import '+name)
  tex.set_editor_property('srgb',ch=='BaseColor');tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if ch=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if ch=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
  tex.set_editor_property('flip_green_channel',ch=='Normal');tex.set_editor_property('never_stream',False);tex.set_editor_property('address_x',u.TextureAddress.TA_WRAP);tex.set_editor_property('address_y',u.TextureAddress.TA_WRAP);save(tex);out[ch]=tex
 return out

def material(name,tex,color,cotton=False,world=False,inner=False):
 folder=DEST+'/Materials';E.make_directory(folder);mat=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
 if not L.get_material_expressions(mat):
  mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH);mat.set_editor_property('use_material_attributes',True)
  L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_STATIC_MESH)
  def node(cls):return L.create_material_expression(mat,cls)
  def wire(a,b,pin,out=''):
   if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot wire '+pin)
  def scalar(key,v):
   n=node(u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',key);n.set_editor_property('default_value',v);return n
  uv=node(u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',25/1.92*(8 if cotton else 1));uv.set_editor_property('v_tiling',25/1.92*(8 if cotton else 1))
  pos=node(u.MaterialExpressionWorldPosition);pos.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
  inputs={'UV':uv,'Position':pos,'Camera':node(u.MaterialExpressionCameraPositionWS),'VertexNormal':node(u.MaterialExpressionVertexNormalWS),'DepthCm':scalar('TextileReliefDepthCm',0 if world or inner else .006 if cotton else .04),'TextureSize':scalar('TileResolution',2048),'FuzzAmount':scalar('ShortFibreAmount',.15 if cotton else .28)}
  for ch,pin in [('BaseColor','ColorTex'),('Normal','NormalTex'),('ORM','ORMTex'),('Relief','ReliefTex')]:
   n=node(u.MaterialExpressionTextureObjectParameter);n.set_editor_property('parameter_name',ch);n.set_editor_property('texture',tex[ch]);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if ch=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if ch=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS);inputs[pin]=n
  custom=node(u.MaterialExpressionCustom);custom.set_editor_property('code',(P/'Tools/ModularOutfit/black_leather_relief.ush').read_text());custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT4)
  pins=[]
  for key in inputs:i=u.CustomInput();i.set_editor_property('input_name',key);pins.append(i)
  custom.set_editor_property('inputs',pins)
  outs=[]
  for key,kind in [('NormalTangent',u.CustomMaterialOutputType.CMOT_FLOAT3),('AO',u.CustomMaterialOutputType.CMOT_FLOAT1),('Fuzz',u.CustomMaterialOutputType.CMOT_FLOAT1)]:
   o=u.CustomOutput();o.set_editor_property('output_name',key);o.set_editor_property('output_type',kind);outs.append(o)
  custom.set_editor_property('additional_outputs',outs)
  for key,n in inputs.items():wire(n,custom,key)
  attrs=node(u.MaterialExpressionMakeMaterialAttributes)
  if not L.connect_material_property(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):raise RuntimeError('Material attributes')
  tint=node(u.MaterialExpressionVectorParameter);tint.set_editor_property('parameter_name','SurfaceTint');tint.set_editor_property('default_value',u.LinearColor(*color,1))
  for channels,pin in [('rgb','BaseColor'),('a','Roughness')]:
   mask=node(u.MaterialExpressionComponentMask)
   for ch in 'rgba':mask.set_editor_property(ch,ch in channels)
   wire(custom,mask,'')
   if channels=='rgb':
    mul=node(u.MaterialExpressionMultiply);wire(mask,mul,'A');wire(tint,mul,'B','RGB');wire(mul,attrs,pin)
   else:wire(mask,attrs,pin)
  for out,pin in [('NormalTangent','Normal'),('AO','AmbientOcclusion'),('Fuzz','ClearCoat')]:wire(custom,attrs,pin,out)
  wire(tint,attrs,'SubsurfaceColor','RGB');wire(scalar('TextileSpecular',.3),attrs,'Specular');wire(scalar('Metallic',0),attrs,'Metallic')
 if L.recompile_material(mat):raise RuntimeError('Material compilation '+name)
 save(mat);return mat

def mesh(data,group,variant):
 source=u.load_asset(data['binding_source']);native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native binding unavailable')
 _,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones};vertices=[];normals=[];uvs=[];weights=[];triangles=[];lookup={}
 for fi,f in enumerate(data['triangles']):
  row=[]
  for ci,vi in enumerate(f):
   n=data['normals'][fi][ci];uv=data['uv'][fi][ci];key=(vi,data['triangle_materials'][fi],*[round(v,7) for v in n+uv])
   if key not in lookup:lookup[key]=len(vertices);vertices.append(u.Vector(*data['positions'][vi]));normals.append(u.Vector(*n));uvs.append(u.Vector2D(*uv));weights.append(data['weights'][vi])
   row.append(lookup[key])
  triangles.append(u.IntVector(*row))
 dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uvs,triangles=triangles),0,True)
 if dm.get_triangle_count()!=len(triangles):raise RuntimeError('Rejected garment triangles '+data['profile'])
 B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
 for vi,w in enumerate(weights):B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=ids[k],weight=v) for k,v in w.items()])
 for fi,mat in enumerate(data['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,fi,mat,True)
 folder=DEST+'/'+variant+'/'+data['profile'];name='SK_'+data['profile']+'_'+variant;E.make_directory(folder);asset=u.load_asset(folder+'/'+name) or A.duplicate_asset(name,folder,source)
 options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=group,new_material_slot_names=['Textile','RolledHem','InnerTextile'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Garment write failed')
 asset.set_editor_property('physics_asset',None);settings=S.get_lod_build_settings(asset,0);settings.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,0,settings)
 if not u.FPSModularOutfitComponent.configure_outfit_lods(asset) or not S.regenerate_lod(asset,3,True,False):raise RuntimeError('Garment LOD build')
 E.set_metadata_tag(asset,'SourceContract',data['contract']);save(asset);return asset

def pickup(variant,group):
 folder=DEST+'/Pickups';name='SM_'+variant+'_Garment';E.make_directory(folder);task=u.AssetImportTask();task.filename=str(R/(name+'.fbx'));task.destination_path=folder;task.destination_name=name;task.automated=True;task.save=False
 options=u.FbxImportUI();options.import_as_skeletal=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.automated_import_should_detect_type=False;options.import_materials=False;options.import_textures=False;options.static_mesh_import_data.combine_meshes=True;task.options=options;A.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
 if not asset:raise RuntimeError('Pickup import '+variant)
 for i,mat in enumerate(group):asset.set_material(i,mat)
 save(asset);return asset

def main():
 tex={p:textures(p) for p in ['Knit','Rib']};results={}
 for variant,cotton,color,folder in [('Olive',False,(.115,.135,.080),'Authored'),('Charcoal',True,(.045,.053,.065),'ShortSleeve')]:
  groups={}
  for world in [False,True]:
   groups[world]=[material('M_'+variant+'_'+str(i)+('_World' if world else ''),tex['Rib' if i==1 and not cotton else 'Knit'],tuple(x*(.7 if i==2 else 1) for x in color),cotton,world,i==2) for i in range(3)]
  profiles={}
  for row in read(R/'manifest.json'):
   name=row['profile'];receipt=R/'Saved'/(variant+'_'+name+'.json')
   if receipt.exists():profiles[name]=read(receipt)['mesh'];continue
   data=read(R/folder/(name+'.json'));asset=mesh(data,groups[name=='Body'],variant);profiles[name]=asset.get_path_name();write(receipt,dict(mesh=asset.get_path_name(),lods=3,triangles=len(data['triangles']),runtime_tested=False));print('GARMENT_SAVED',variant,name,flush=True)
  drop=pickup(variant,groups[True]);results[variant]=dict(profiles=profiles,pickup=drop.get_path_name())
 write(R/'saved-assets.json',results);print('GARMENT_IMPORT_COMPLETE',flush=True)
if __name__=='__main__':main()
