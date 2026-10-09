"""Import new V04 revision, connect pose curves, then switch the existing BP."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V04')
DEST='/Game/Monsters/FacelessReceptionist';LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE is active; V04 sources retained, asset import deferred')
report=json.loads((ROOT/'ue_delivery.json').read_text()) if (ROOT/'ue_delivery.json').exists() else {'stage':'importing','saved':[],'runtime_tested':False}
def record():(ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(a):
 if not LIB.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 if a.get_path_name() not in report['saved']:report['saved'].append(a.get_path_name())
 record()
def import_one(file,folder,name,options=None):
 path=folder+'/'+name
 if LIB.does_asset_exist(path):return u.load_asset(path)
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name;task.automated=True;task.save=False
 if options:task.options=options;task.factory=u.FbxFactory()
 AT.import_asset_tasks([task]);a=u.load_asset(path)
 if not a:raise RuntimeError('Import failed '+path)
 return a
textures={}
for family in ['Suit','Shirt','Trim']:
 for suffix in ['BaseColor','Normal','ORM']:
  stem='Receptionist_'+family+'_'+suffix
  t=import_one(ROOT/'Textures'/(stem+'.png'),DEST+'/Textures','T_FR4_'+stem)
  t.set_editor_property('srgb',suffix=='BaseColor');t.set_editor_property('never_stream',False)
  if suffix=='Normal':t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);t.set_editor_property('flip_green_channel',True)
  elif suffix=='ORM':t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
  save(t);textures[(family,suffix)]=t
materials={}
def connect(src,out,dst,pin):
 names=MEL.get_material_expression_input_names(dst)
 norm=lambda s:''.join(c.lower() for c in str(s) if c.isalnum())
 actual=next((p for p in names if norm(p)==norm(pin)),None)
 if actual is None:actual=next((p for p in names if norm(p).startswith(norm(pin))),None)
 if actual is None or not MEL.connect_material_expressions(src,out,dst,actual):raise RuntimeError('Material input '+pin+' available '+str(names))
for family in ['Skin','Suit','Shirt','Badge','Trim','Shoes']:
 path=DEST+'/Materials/M_FR4_'+family
 if LIB.does_asset_exist(path):mat=u.load_asset(path)
 elif family not in ['Suit','Shirt','Trim']:
  mat=LIB.duplicate_asset(DEST+'/Materials/M_Receptionist_'+family,path)
 else:
  mat=AT.create_asset('M_FR4_'+family,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
  slab=MEL.create_material_expression(mat,u.MaterialExpressionSubstrateSlabBSDF,400,0)
  for i,(suffix,pin,channel,sampler) in enumerate([
   ('BaseColor','DiffuseAlbedo','RGB',u.MaterialSamplerType.SAMPLERTYPE_COLOR),
   ('Normal','Normal','RGB',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
   ('ORM','Roughness','G',u.MaterialSamplerType.SAMPLERTYPE_MASKS)]):
   node=MEL.create_material_expression(mat,u.MaterialExpressionTextureSample,0,i*180);node.texture=textures[(family,suffix)];node.sampler_type=sampler;connect(node,channel,slab,pin)
   if suffix=='BaseColor':connect(node,'RGB',slab,'FuzzColor')
  for pin,value in [('F0',.022),('FuzzAmount',.18 if family=='Suit' else .09),('FuzzRoughness',.82)]:
   node=MEL.create_material_expression(mat,u.MaterialExpressionConstant,200,0);node.r=value;connect(node,'',slab,pin)
  if not MEL.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate front material')
 mat.set_editor_property('two_sided',False)
 MEL.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);mat.set_editor_property('used_with_morph_targets',True)
 errors=MEL.recompile_material(mat)
 if errors:raise RuntimeError('Material compile '+str(errors))
 save(mat);materials['Receptionist_'+family]=mat
skeleton=u.load_asset(DEST+'/SKEL_FacelessReceptionist');physics=u.load_asset(DEST+'/PA_FacelessReceptionist')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
options.skeleton=skeleton;options.create_physics_asset=False;options.physics_asset=physics
data=options.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1
data.set_editor_property('import_morph_targets',True);data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
meshes={}
for key,name in [('outfit','SK_FacelessReceptionist_V04'),('clothes','SK_FacelessReceptionist_Clothing_V04'),('body','SK_FacelessReceptionist_Body_V04')]:
 mesh=import_one(ROOT/'Delivery'/(name+'.fbx'),DEST,name,options)
 slots=list(mesh.materials)
 for slot in slots:
  imported=str(slot.get_editor_property('imported_material_slot_name'))
  chosen=next((mat for family,mat in materials.items() if imported.startswith(family)),None)
  if not chosen:raise RuntimeError('Unmapped material '+imported)
  slot.material_interface=chosen
 mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
 save(mesh);meshes[key]=mesh
names=[m.get_name() for m in meshes['outfit'].get_editor_property('morph_targets')]
requested=json.loads((ROOT/'export_receipt.json').read_text())['morph_names'];mapping={}
for name in requested:
 matches=[n for n in names if n==name or n.endswith('_'+name)]
 if len(matches)!=1:raise RuntimeError('Missing/ambiguous morph '+name+' '+str(matches))
 mapping[name]=matches[0]
curves=json.loads((ROOT/'corrective_curves.json').read_text());sources=json.loads((ROOT/'live_source.json').read_text())
clips={}
for role in ['idle','walk','attack']:
 path=DEST+'/Animations/A_Receptionist_V04_'+role
 clip=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(sources['clips'][role]['asset'],path)
 clip.set_preview_skeletal_mesh(meshes['outfit'])
 count=round(clip.get_play_length()*30)+1
 for requested,values in curves[role].items():
  name=mapping[requested]
  if u.AnimationLibrary.does_curve_exist(clip,name,u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(clip,name)
  u.AnimationLibrary.add_curve(clip,name)
  times=[min(i/30,clip.get_play_length()) for i in range(min(count,len(values)))]
  u.AnimationLibrary.add_float_curve_keys(clip,name,times,values[:len(times)])
  u.AnimationLibrary.set_curve_meta_data_morph_target(skeleton,name,True)
 save(clip);clips[role]=clip
save(skeleton)
bp=u.load_asset(DEST+'/BP_FacelessReceptionist');u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
report['previous_mesh']=cdo.get_editor_property('visual_mesh').get_path_name()
cdo.set_editor_property('visual_mesh',meshes['outfit']);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(meshes['outfit'])
for role,clip in clips.items():cdo.set_editor_property(role+'_clip',clip)
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report.update(stage='saved',version='V04',blueprint=bp.get_path_name(),meshes={k:v.get_path_name() for k,v in meshes.items()},clips={k:v.get_path_name() for k,v in clips.items()},morph_names=mapping,curve_counts={r:len(curves[r]) for r in curves},bone_tracks='Copied from the current V03 clips; only clothing morph curves added',material='Substrate woven cloth fuzz + 20 cm UV tile + shared microheight normal/roughness',complete_body_preserved=True,outfit_body_culling='Only hidden interior torso/upper-leg faces; complete body in separate source and UE mesh')
record();print('V04_UE_SAVED '+json.dumps({'saved':len(report['saved']),'morphs':len(mapping),'mesh':report['meshes']['outfit']}))
