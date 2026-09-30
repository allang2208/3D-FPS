"""Import and save the 201 drum, private finish, native reloads and option icon."""
import unreal as u,json,gzip,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];D='/Game/Weapons/LMG201/Drum46';S=json.loads((O/'sources.json').read_text());G=json.loads((O/'model.json').read_text());AN=json.loads((O/'animations.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'saved':{},'runtime_tested':False,'acceptance_rendered':False}
if (O/'install_receipt.json').exists():receipt=json.loads((O/'install_receipt.json').read_text())
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def sha(path):return hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
def record():(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
 receipt['saved'][a.get_path_name()]={'sha256':sha(a.get_path_name()),'saved':True};record()
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def link(a,b,p):
 n,ch=a if isinstance(a,tuple) else (a,'')
 if not L.connect_material_expressions(n,ch,b,p):raise RuntimeError('Link '+p)
def custom(m,code,inputs,dimension=1):
 n=node(m,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(dimension)))
 pins=[]
 for key in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
 n.set_editor_property('inputs',pins)
 for key,src in inputs.items():link(src,n,key)
 return n
def scalar(m,key,val):return node(m,u.MaterialExpressionScalarParameter,parameter_name=key,default_value=val)
def vector(m,key,val):return node(m,u.MaterialExpressionVectorParameter,parameter_name=key,default_value=u.LinearColor(*val,1))
body=load(S['rigs']['201']['asset']);slots={str(s.material_slot_name):s.material_interface for s in body.materials}
if sha(S['rigs']['201']['asset'])!=S['rigs']['201']['sha256']:raise RuntimeError('201 body changed; recapture factory interface')
# Read the currently installed finish values. Keep the drum's own UV0 atlas.
def parameter(mat,key,default):
 for n in L.get_material_expressions(mat.get_base_material()):
  if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter)) and str(n.get_editor_property('parameter_name'))==key:
   return n.get_editor_property('default_value')
 return default
coat=slots['M_LMG201_Magazine'];poly=slots['M_LMG201_FactoryRearGrip_J44']
rough_poly=float(parameter(poly,'G43_Roughness',.46));rough_coat=float(parameter(coat,'G43_Roughness',.40))
ct=parameter(coat,'G43_FinishTint',u.LinearColor(.0175,.021,.0255,1));pt=parameter(poly,'G43_FinishTint',u.LinearColor(.010,.013,.016,1))
materials={}
for role in ['Shell','Hardware','Transition']:
 name='M_LMG201_D46_'+role;path=D+'/Materials/'+name
 m=u.load_asset(path) or A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
 uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
 wet=scalar(m,'WeaponWetness',0.)
 tint=vector(m,'201FinishTint',(ct.r,ct.g,ct.b) if role=='Hardware' else (pt.r,pt.g,pt.b))
 rough=scalar(m,'201FinishRoughness',rough_coat if role=='Hardware' else rough_poly)
 if role!='Transition':
  tex={}
  for key,typ in [('BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR),('MetalRough',u.MaterialSamplerType.SAMPLERTYPE_MASKS),('Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)]:
   tex[key]=node(m,u.MaterialExpressionTextureSample,texture=load('/Game/Weapons/LargeDrumUpgrade20260920/AKM/T_AKM_Drum_'+key),sampler_type=typ,const_coordinate=0)
  base=custom(m,'float l=dot(Base,float3(.2126,.7152,.0722));return Tint*clamp(l/.013,.55,1.5)*(1-.12*saturate(Wet));',{'Base':(tex['BaseColor'],'RGB'),'Tint':tint,'Wet':wet},3)
  r=custom(m,'float r=clamp(Center+(Map-.53)*.23,.28,.64);return lerp(r,r*.73,saturate(Wet));',{'Center':rough,'Map':(tex['MetalRough'],'G'),'Wet':wet})
  normal=custom(m,'return normalize(float3(N.xy*.55,N.z));',{'N':(tex['Normal'],'RGB')},3)
  L.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL)
 else:
  base=custom(m,'return Tint*(1-.12*saturate(Wet));',{'Tint':tint,'Wet':wet},3)
  r=custom(m,'return lerp(Center,Center*.73,saturate(Wet));',{'Center':rough,'Wet':wet})
 for n,prop in [(base,u.MaterialProperty.MP_BASE_COLOR),(r,u.MaterialProperty.MP_ROUGHNESS),(scalar(m,'201Metallic',float(parameter(coat,'G43_Metallic',.72)) if role=='Hardware' else 0.),u.MaterialProperty.MP_METALLIC),(scalar(m,'Specular',.42),u.MaterialProperty.MP_SPECULAR)]:L.connect_material_property(n,'',prop)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Material '+str(errors))
 E.set_metadata_tag(m,'201DrumFinish','201 current finish parameters, retained donor UV0 PBR surface, single wetness layer');save(m);materials[role]=m
path=D+'/SM_LMG201_LargeDrum';task=u.AssetImportTask();task.filename=G['mesh'];task.destination_path=D;task.destination_name='SM_LMG201_LargeDrum';task.automated=True;task.replace_existing=True;task.save=False
opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;task.options=opt;A.import_asset_tasks([task]);mesh=load(path)
bind={'D46_DrumPolymer':materials['Shell'],'D46_DrumIndex':materials['Shell'],'D46_DrumFasteners':materials['Hardware'],'D46_FactoryNeck':coat,'D46_FactoryInside':slots['M_LMG201_MagazineInside'],'D46_TransitionPolymer':materials['Transition']}
for i,slot in enumerate(mesh.static_materials):
 name=str(slot.material_slot_name)
 if name not in bind:raise RuntimeError('Unexpected drum slot '+name)
 mesh.set_material(i,bind[name])
E.set_metadata_tag(mesh,'SourceModel',str(O/'LMG201_Drum46.blend'));E.set_metadata_tag(mesh,'MountFrame','201 magazine bone; relative identity and 0.01 units');save(mesh)
wetpath='/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials'
if wetpath in dirty:raise RuntimeError('Unsaved wet material table retained')
table=load(wetpath);mapping=dict(table.get_editor_property('wet_materials'))
for m in materials.values():mapping[m.get_path_name()]=m
table.set_editor_property('wet_materials',mapping);save(table)
for key,spec in AN['clips'].items():
 for field in ['source','donor']:
  if sha(spec[field])!=spec[field+'_sha256']:raise RuntimeError('Animation source changed '+spec[field])
 path=spec['destination'];clip=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(spec['source'],path)
 if not clip:raise RuntimeError('Cannot duplicate '+path)
 with gzip.open(spec['keys'],'rt',encoding='utf8') as f:tracks=json.load(f)
 model=clip.get_editor_property('data_model_interface');controller=clip.get_editor_property('controller');controller.open_bracket('201 accepted drum contacts and support return',False)
 try:
  for name,rows in tracks.items():
   if not model.is_valid_bone_track_name(name):controller.add_bone_curve(name,False)
   if not controller.set_bone_track_keys(name,[u.Vector(*v['p']) for v in rows],[u.Quat(*v['q']) for v in rows],[u.Vector(*v['s']) for v in rows],False):raise RuntimeError('Bone '+name)
 finally:controller.close_bracket(False)
 E.set_metadata_tag(clip,'DrumMotionSource',spec['donor']);E.set_metadata_tag(clip,'201DrumRevision','Drum46: native AKM PalmGripV3 full-chain contact, 201 support return, existing 201 right grip retained')
 u.AKMAnimationAuditLibrary.finish_animation_compression(clip);save(clip);print('DRUM46_ANIMATION_SAVED',key,flush=True)
icon=json.loads((O/'icon.json').read_text());dest='/Game/ColdSteelData/AttachmentIcons20260913';png=P/'Content/ColdSteelData/AttachmentIcons20260913'/(icon['key']+'.png');shutil.copy2(icon['file'],png)
task=u.AssetImportTask();task.filename=str(png);task.destination_path=dest;task.destination_name=icon['key'];task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);texture=load(dest+'/'+icon['key']);texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(texture)
receipt.update(status='assets_saved',mesh=mesh.get_path_name(),materials={k:v.get_path_name() for k,v in materials.items()},finish={'polymer_roughness':rough_poly,'coating_roughness':rough_coat},animation_count=len(AN['clips']));record();print('DRUM46_ASSETS_SAVED',flush=True)
