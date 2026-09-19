"""Install ASH-only meshes, coatings, grip clips and private wet-material entries."""
import json,os
from pathlib import Path
import unreal as u
O=Path(__file__).parent;ROOT=O.parents[1];D='/Game/Weapons/ASH12/UniversalAttachments20260919'
if '-nullrhi' in u.SystemLibrary.get_command_line().lower().split():
 raise RuntimeError('ASH static meshes require an RHI editor; do not import/finalize with -NullRHI.')
if not u.get_editor_subsystem(u.StaticMeshEditorSubsystem):
 raise RuntimeError('Run ASH attachment import in the full editor, not a commandlet.')
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
 raise RuntimeError('End PIE before importing ASH attachments.')
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
models=json.loads((O/'models.json').read_text());animations=json.loads((O/'animations.json').read_text())
receipt=json.loads((O/'import.json').read_text(encoding='utf-8')) if (O/'import.json').exists() else {'meshes':{},'materials':{},'animations':{},'runtime_test':'Not run; user tests in game.'}
def load(path):
 obj=u.load_asset(path)
 if not obj:raise RuntimeError('Missing authoring asset '+path)
 return obj
def save(obj):
 if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outer()],False):raise RuntimeError('Save failed '+obj.get_path_name())
def node(m,cls,**props):
 n=L.create_material_expression(m,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(src,n,pin):
 x,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_expressions(x,out,n,pin):raise RuntimeError('Connect '+pin)
def output(src,prop):
 x,out=src if isinstance(src,tuple) else (src,'')
 if not L.connect_material_property(x,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Output '+prop)
def custom(m,code,inputs,size,label):
 n=node(m,u.MaterialExpressionCustom,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)),description=label)
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,src in inputs.items():wire(src,n,name)
 return n
def current(m,prop):
 p=getattr(u.MaterialProperty,'MP_'+prop);n=L.get_material_property_input_node(m,p)
 return (n,L.get_material_property_input_node_output_name(m,p)) if n else None
def imported(file,name,folder,options=None):
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
 task.automated=True;task.replace_existing=True;task.save=False;task.options=options;A.import_asset_tasks([task])
 return load(folder+'/'+name)
textures={}
for key in ('NormalDX','ORM'):
 name='T_ASH12_AttachmentCoat_'+key;t=imported(O/'Textures'/(name+'.png'),name,D+'/Textures');t.srgb=False
 t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if key=='NormalDX' else u.TextureCompressionSettings.TC_MASKS
 t.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
 if key=='NormalDX':t.flip_green_channel=False
 save(t);textures[key]=t
def coating(label,color,rough,metal):
 name='M_ASH12_'+label+'_Coat';path=D+'/Materials/'+name
 existing=u.load_asset(path)
 if existing:return existing
 m=A.create_asset(name,D+'/Materials',u.Material,u.MaterialFactoryNew())
 uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=3)
 orm=node(m,u.MaterialExpressionTextureSample,texture=textures['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS);wire(uv,orm,'UVs')
 # Fine isotropic coating normal uses UV0, matching imported tangent space.
 uv0=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0,u_tiling=12.,v_tiling=12.)
 normal=node(m,u.MaterialExpressionTextureSample,texture=textures['NormalDX'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL);wire(uv0,normal,'UVs')
 output(node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*color,1)),'BASE_COLOR')
 output(custom(m,'return clamp(Rough+Offset,.1,.9);',{'Rough':(orm,'G'),'Offset':node(m,u.MaterialExpressionConstant,r=rough-.45)},1,'Coating roughness in ASH material range'),'ROUGHNESS')
 output(node(m,u.MaterialExpressionConstant,r=metal),'METALLIC');output((normal,'RGB'),'NORMAL');output((orm,'R'),'AMBIENT_OCCLUSION')
 output(node(m,u.MaterialExpressionConstant,r=.5),'SPECULAR')
 E.set_metadata_tag(m,'WeaponFinishReference','/Game/Weapons/ASH12/Surface20260919/Materials/M_ASH12_'+('Sights' if label=='OpticShoe' else 'Front'))
 E.set_metadata_tag(m,'CoatingUV','UV3 4cm tile; UV0 tangent normal; no receiver atlas reuse')
 L.recompile_material(m);save(m);return m
dry={'ASH_GripMetal':coating('GripMetal',(.09,.095,.103),.45,.70),'ASH_OpticShoe':coating('OpticShoe',(.065,.068,.072),.50,.65)}
poly_path=D+'/Materials/M_ASH12_GripPolymer'
poly=u.load_asset(poly_path)
if poly:pass
else:
 poly=A.duplicate_asset('M_ASH12_GripPolymer',D+'/Materials',load('/Game/Weapons/ResonanceGrip20260913/MeshyIntegration/M_Resonance_Polymer_M4'))
 if not poly:raise RuntimeError('Polymer material clone failed')
 base=L.get_material_property_input_node(poly,u.MaterialProperty.MP_BASE_COLOR);base.set_editor_property('constant',u.LinearColor(.025,.026,.028,1))
 L.recompile_material(poly);save(poly)
dry['ASH_GripPolymer']=poly
dry['M_Prism_Polymer']=load('/Game/Weapons/PrismHandstopV1/M_Prism_Polymer')
BEADS=(ROOT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text()
wet={}
for label,mat in dry.items():
 path=D+'/Materials/M_ASH12_'+label+'_Wet'
 w=u.load_asset(path)
 if w:pass
 else:
  w=A.duplicate_asset(path.rsplit('/',1)[1],D+'/Materials',mat)
  base=current(w,'BASE_COLOR');rough=current(w,'ROUGHNESS');normal=current(w,'NORMAL') or node(w,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,1,1))
  wetness=node(w,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
  beads=custom(w,BEADS,{'UV':node(w,u.MaterialExpressionTextureCoordinate),'Wet':wetness},4,'ASH adhered water beads')
  output(custom(w,'return Base*(1-Data.a*.055);',{'Base':base,'Data':beads},3,'Thin water film'),'BASE_COLOR')
  output(custom(w,'return lerp(lerp(Base,max(.12,Base*.62),Data.a),.065,Data.b*.85);',{'Base':rough,'Data':beads},1,'Wet roughness'),'ROUGHNESS')
  output(custom(w,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.30)+Data.xy,Base.z));',{'Base':normal,'Data':beads},3,'Water over original structural normal'),'NORMAL')
  L.recompile_material(w);save(w)
 wet[mat.get_path_name()]=w;receipt['materials'][label]={'dry':mat.get_path_name(),'wet':w.get_path_name()}

for key,part in models['parts'].items():
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
 options.import_as_skeletal=False;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
 data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
 data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
 data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
 mesh=imported(part['file'],part['name'],D+'/Meshes',options);u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh);slots=mesh.static_materials
 for i,s in enumerate(slots):
  label=str(s.material_slot_name)
  if label in dry:material=dry[label]
  elif label in part['bindings']:material=load(part['bindings'][label])
  else:raise RuntimeError('Unassigned '+key+' material slot '+label)
  s.material_interface=material;slots[i]=s
 mesh.set_editor_property('static_materials',slots)
 editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
 if editor:
  settings=editor.get_lod_build_settings(mesh,0)
  settings.set_editor_property('recompute_normals',False)
  settings.set_editor_property('recompute_tangents',True)
  settings.set_editor_property('use_mikk_t_space',True)
  settings.set_editor_property('use_high_precision_tangent_basis',True)
  settings.set_editor_property('use_full_precision_u_vs',True)
  editor.set_lod_build_settings(mesh,0,settings)
 E.set_metadata_tag(mesh,'ASHAttachmentSource',part['source']);E.set_metadata_tag(mesh,'ASHRailContact',json.dumps(part['mount_rail_m']))
 if not u.ASH12AttachmentAssetTools.finish_and_validate_build(mesh):raise RuntimeError('Invalid render or distance-field bounds: '+key)
 save(mesh);receipt['meshes'][key]={'mesh':mesh.get_path_name(),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials}}
 (O/'import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')

# Preserve ASH optic/suppressor and gun mappings; append only new exterior entries.
library=load('/Game/Weapons/ASH12/Surface20260919/DA_ASH12_WetMaterials');mapping=dict(library.get_editor_property('wet_materials'));mapping.update(wet)
library.set_editor_property('wet_materials',mapping);save(library);receipt['weather_library']=library.get_path_name()
skeleton=load('/Game/Weapons/ASH12/Integrated20260917/SK_ASH12_Manny_Skeleton');compression=load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
for key,clip in ([] if os.environ.get('ASH_ATTACHMENT_MESH_ONLY')=='1' else animations['clips'].items()):
 options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
 options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
 data=options.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',120)
 asset=imported(clip['file'],clip['name'],D+'/Animations/'+clip['family'],options)
 asset.set_editor_property('bone_compression_settings',compression);save(asset)
 receipt['animations'][key]={'asset':asset.get_path_name(),'duration':asset.get_play_length(),'source_action':clip['source_action']}
 (O/'import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');u.log('ASH_GRIP_CLIP_IMPORTED '+key)
(O/'import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ASH_UNIVERSAL_ATTACHMENTS_IMPORT_COMPLETE')
