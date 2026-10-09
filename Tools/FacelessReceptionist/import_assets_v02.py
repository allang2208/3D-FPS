"""Save receptionist assets in a new package tree; no gameplay or render checks."""
import unreal as u,json,os
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V02')
DEST='/Game/Monsters/FacelessReceptionist'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
report=json.loads((ROOT/'ue_delivery.json').read_text(encoding='utf-8')) if (ROOT/'ue_delivery.json').exists() else {'stage':'importing','saved':[],'runtime_tested':False}
if os.environ.get('RECEPTIONIST_FORCE_REIMPORT')=='1':report['saved']=[]
def record():
 (ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(a):
 if not LIB.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
 if a.get_path_name() not in report['saved']:report['saved'].append(a.get_path_name())
 record()
def owned_copy(src,name):
 path=DEST+'/'+name
 a=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(src,path)
 if not a:raise RuntimeError('Missing source '+src)
 return a
def import_one(file,path,name,options=None):
 if path+'/'+name+'.'+name in report['saved']:return u.load_asset(path+'/'+name)
 t=u.AssetImportTask();t.filename=str(file);t.destination_path=path;t.destination_name=name
 t.automated=True;t.save=False;t.replace_existing=True;t.replace_existing_settings=True
 if options:t.options=options;t.factory=u.FbxFactory()
 AT.import_asset_tasks([t])
 a=u.load_asset(path+'/'+name)
 if not a:raise RuntimeError('Import did not create '+path+'/'+name)
 return a
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
skeleton=owned_copy('/Game/ZombieFemale/Asset/Meshes/SK_ZombieFemale','SKEL_FacelessReceptionist')
physics=owned_copy('/Game/ZombieFemale/Asset/Meshes/PA_ZombieFemale','PA_FacelessReceptionist')
save(skeleton);save(physics)
textures={}
for f in sorted((ROOT/'Textures').glob('*.png')):
 name='T_FR_'+f.stem
 tex=import_one(f,DEST+'/Textures',name)
 linear=('_Normal' in name or 'Source_normal' in name or '_ORM' in name or 'metallic_roughness' in name)
 tex.set_editor_property('srgb',not linear)
 if '_Normal' in name or 'Source_normal' in name:
  tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
  tex.set_editor_property('flip_green_channel',True)
 elif linear:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
 tex.set_editor_property('never_stream',False)
 save(tex);textures[f.stem]=tex
materials={}
mapping={'Receptionist_Skin':('Source_texture_0','Source_normal','Source_texture_0_metallic_roughness')}
for n in ['Suit','Shirt','Shoes','Badge','Trim']:mapping['Receptionist_'+n]=tuple('Receptionist_'+n+s for s in ['_BaseColor','_Normal','_ORM'])
for name,(base,normal,orm) in mapping.items():
 path=DEST+'/Materials/M_'+name
 if path+'.M_'+name in report['saved']:
  materials[name]=u.load_asset(path);continue
 mat=u.load_asset(path) if LIB.does_asset_exist(path) else AT.create_asset('M_'+name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
 MEL.delete_all_material_expressions(mat)
 mat.set_editor_property('two_sided',False)
 MEL.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
 slab=MEL.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels,400,0)
 for key,pin,channel in [(base,'BaseColor','RGB'),(normal,'Normal','RGB'),(orm,'Roughness','G'),(orm,'Metallic','B')]:
  node=MEL.create_material_expression(mat,u.MaterialExpressionTextureSample,0,0)
  node.texture=textures[key]
  node.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key==normal else u.MaterialSamplerType.SAMPLERTYPE_MASKS if key==orm else u.MaterialSamplerType.SAMPLERTYPE_COLOR
  if not MEL.connect_material_expressions(node,channel,slab,pin):raise RuntimeError('Material pin '+pin)
 if not MEL.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output')
 MEL.recompile_material(mat);save(mat);materials[name]=mat
opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opts.import_mesh=True;opts.import_as_skeletal=True;opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
opts.skeleton=skeleton;opts.create_physics_asset=False;opts.physics_asset=physics
data=opts.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.;data.force_front_x_axis=False
data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
meshes={}
for key,file,name in [('outfit','SK_FacelessReceptionist_V02.fbx','SK_FacelessReceptionist'),('body','SK_FacelessReceptionist_Body_V02.fbx','SK_FacelessReceptionist_Body')]:
 mesh=import_one(ROOT/'Delivery'/file,DEST,name,opts)
 slots=list(mesh.materials)
 for slot in slots:
  imported=str(slot.get_editor_property('imported_material_slot_name'))
  chosen=next((mat for key,mat in materials.items() if imported.startswith(key)),None)
  if not chosen:raise RuntimeError('Unmapped material slot '+imported)
  slot.material_interface=chosen
 mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
 LIB.set_metadata_tag(mesh,'Source','User Meshy GLB, original body UVs preserved; independent locally authored clothes; Nurse skeleton frame')
 LIB.set_metadata_tag(mesh,'Status','V02: anatomical skin repair and continuous outfit. Blender reference rendered; no gameplay test.')
 save(mesh);meshes[key]=mesh
save(skeleton)
clips={}
for role in ['idle','walk','attack']:
 clip=owned_copy('/Game/Monsters/NurseZombie/A_Nurse_'+role,'Animations/A_Receptionist_'+role)
 if not u.WeaponAnimationAuthoring.rebind_native_animation(clip,skeleton):raise RuntimeError('Animation skeleton reassignment failed')
 clip.set_preview_skeletal_mesh(meshes['outfit'])
 save(clip);clips[role]=clip
bp=owned_copy('/Game/Monsters/NurseZombie/BP_NurseZombie','BP_FacelessReceptionist')
u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class())
cdo.set_editor_property('visual_mesh',meshes['outfit'])
cdo.get_editor_property('mesh').set_skeletal_mesh_asset(meshes['outfit'])
for role,clip in clips.items():cdo.set_editor_property(role+'_clip',clip)
tags=[t for t in cdo.get_editor_property('tags') if str(t) not in ['NurseZombie','FacelessReceptionist']];tags.append(u.Name('FacelessReceptionist'))
cdo.set_editor_property('tags',tags)
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report.update(version='V02',stage='saved',blueprint=bp.get_path_name(),mesh=meshes['outfit'].get_path_name(),body_mesh=meshes['body'].get_path_name(),skeleton=skeleton.get_path_name(),physics=physics.get_path_name(),animations={k:v.get_path_name() for k,v in clips.items()},navigation='Inherited Nurse profile: capsule radius 34 cm, half-height 92 cm; existing supported agent. No new navigation profile or map edit.',clothing='Native skin deformation; no Chaos cloth simulation.')
record()
print('RECEPTIONIST_UE_SAVED '+json.dumps({'blueprint':report['blueprint'],'saved_count':len(report['saved'])}),flush=True)
