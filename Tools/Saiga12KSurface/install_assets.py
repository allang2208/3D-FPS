"""Install a private Saiga surface revision, preserving native hands/animation contracts."""
import unreal as u,json,math,hashlib,sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KSurface20261018';D='/Game/Weapons/Saiga12K/SurfaceRebuild20261018'
C=json.loads((O/'Reports/baseline.json').read_text());F=json.loads((O/'Authoring/gun.json').read_text());X=json.loads((O/'Authoring/ext12.json').read_text())
bake=json.loads((O/'Receipts/bake.json').read_text())
if not bake['complete']:raise RuntimeError('Surface bake incomplete')
for key in ('gun','ext12'):
 if bake['textures'][key]['source_sha256']!=hashlib.sha256((O/('Authoring/'+key+'.json')).read_bytes()).hexdigest():raise RuntimeError('Bake does not match current geometry: '+key)
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;LS=u.GeometryScript_List;ED=u.GeometryScript_MeshEdits;BW=u.GeometryScript_BoneWeights;MT=u.GeometryScript_Materials;ML=u.MathLibrary
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
R=json.loads((O/'Receipts/assets.json').read_text()) if (O/'Receipts/assets.json').exists() else {'complete':False,'saved':[],'materials':{},'bindings':{},'runtime_tested':False}
def record():(O/'Receipts/assets.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 if a.get_path_name() not in R['saved']:R['saved'].append(a.get_path_name())
 record();return a
def clone(src,dst):return load(dst) if E.does_asset_exist(dst) else E.duplicate_asset(src,dst)
def vec(v):return u.Vector(*v)
def xyz(v):return [v.x,v.y,v.z]
def read(mesh):
 dm,st=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if st!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native mesh')
 return dm
tex={}
for key in ('gun','ext12'):
 for suffix in ('N','Mask'):
  name='T_Saiga12K_'+key+'_'+suffix;path=D+'/Textures/'+name
  if not E.does_asset_exist(path):
   task=u.AssetImportTask();task.filename=str(O/('Textures/'+name+'.png'));task.destination_path=D+'/Textures';task.destination_name=name;task.automated=True;task.save=False;AT.import_asset_tasks([task])
  a=load(path);a.srgb=False;a.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if suffix=='N' else u.TextureCompressionSettings.TC_MASKS;a.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;a.never_stream=False
  if suffix=='N':a.flip_green_channel=True
  tex[(key,suffix)]=save(a)
CLEAN={'GrainRoughness':0.,'MottleRoughness':0.,'MottleColor':0.,'ScratchAmount':0.,'HandlingPolish':0.,'Stipple':0.,'EdgeWear':0.,'EdgeHighlight':.025,'CavityDarken':.015,'CavityRoughness':.01,'SourceColorWeight':0.,'SourceRoughnessWeight':0.,'AOStrength':.45,'WeaponWetness':0.}
def gun_material(part,key,density):
 name='MI_Saiga12K_'+part;path=D+'/Materials/'+name
 if name in R['materials']:return load(path)
 poly=part in ('Stock','RearGrip','Handguard','Magazine','ExtMagazine','ShellPlastic');rubber=part=='StockPad';inside=part=='ReceiverInterior'
 preset='CleanPolymer' if poly else 'Rubber' if rubber else 'Interior' if inside else 'CleanPolishedSteel' if part in ('Bolt','ShellBrass') else 'CleanSatinSteel'
 rough=.50 if poly else .68 if rubber else .75 if inside else .36 if part=='ReceiverCover' else .31 if part=='Bolt' else .39
 color=(.019,.019,.018) if poly else (.0103,.0103,.0103) if rubber else (.004,.004,.004) if inside else (.105,.108,.109) if part=='Bolt' else (.034,.035,.037)
 if part=='ShellBrass':color=(.35,.23,.08)
 if part=='ShellPlastic':color=(.19,.025,.018)
 mi=load(path) if E.does_asset_exist(path) else AT.create_asset(name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(mi,load('/Game/Weapons/WeaponSurface/Presets/MI_WS_'+preset))
 values=dict(CLEAN,Roughness=rough,Metallic=0. if poly or rubber or inside else 1.,MaskUVChannel=1.,BeadScale=2.42/max(density,.0001))
 if poly or rubber or inside:values.update(EdgeMetallic=0.,EdgeHighlight=.012)
 for k,v in values.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
 L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(*color,1.));L.set_material_instance_texture_parameter_value(mi,'SurfaceNormal',tex[(key,'N')]);L.set_material_instance_texture_parameter_value(mi,'SurfaceMask',tex[(key,'Mask')])
 overrides=mi.get_editor_property('base_property_overrides');overrides.set_editor_property('override_two_sided',True);overrides.set_editor_property('two_sided',part not in ('ReceiverCover','ReceiverInterior','Barrel','GasTube','Stock','RearGrip','Handguard'));mi.set_editor_property('base_property_overrides',overrides)
 L.update_material_instance(mi);E.set_metadata_tag(mi,'SaigaSurfaceRebuild','Clean WS1.1; structural normals UV0; own mask UV1; grain/mottle/stipple disabled');save(mi);R['materials'][name]={'path':mi.get_path_name(),'scalars':values,'normal':tex[(key,'N')].get_path_name(),'mask':tex[(key,'Mask')].get_path_name()};record();return mi
native=load(C['assets']['native']['path']);dm=read(native);_,boneinfo=BW.get_all_bones_info(dm);bones={str(b.name):b for b in boneinfo};names=[str(b.name) for b in boneinfo]
idle=load('/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle');local=u.AnimationLibrary.get_bone_poses_for_frame(idle,names,0,False,native);pose={}
for b,t in zip(boneinfo,local):pose[str(b.name)]=t if b.parent_index<0 else t.multiply(pose[names[b.parent_index]])
root=pose['WPN_root'];mag=pose['WPN_SOCKET_Magazine']
def bone_for(part):return 'WPN_SOCKET_Magazine' if part in ('Magazine','ShellBrass','ShellPlastic') else 'WPN_bolt' if part=='Bolt' else 'WPN_Trigger' if part=='Trigger' else 'WPN_root'
def bind(p,bone):return ML.transform_location(bones[bone].world_transform,ML.inverse_transform_location(pose[bone],ML.transform_location(root,vec([x*.01 for x in p]))))
def bind_normal(n,bone):return ML.transform_direction(bones[bone].world_transform,ML.inverse_transform_direction(pose[bone],ML.transform_direction(root,vec(n))))
if not R.get('mesh'):
 slots=list(native.materials);mats=[s.material_interface for s in slots];slotnames=[str(s.material_slot_name) for s in slots];gunids={i for i,s in enumerate(slots) if str(s.material_slot_name).startswith('Saiga12K_')}
 tids=list(LS.convert_index_list_to_array(next(x for x in Q.get_all_triangle_i_ds(dm) if isinstance(x,u.GeometryScriptIndexList))))
 ED.delete_triangles_from_mesh(dm,LS.convert_array_to_index_list([t for t in tids if MT.get_triangle_material_id(dm,t)[0] in gunids]),True);u.GeometryScript_UVs.set_num_uv_sets(dm,max(4,Q.get_num_uv_sets(dm)));partslots={}
 for part in sorted(set(F['parts'])):
  mat=gun_material(part,'gun',F['uv_per_cm'][part]);name='Saiga12K_'+part
  if name in slotnames:idx=slotnames.index(name);mats[idx]=mat
  else:idx=len(slotnames);slotnames.append(name);mats.append(mat)
  partslots[part]=idx
 keys=[(v,F['parts'][fi]) for fi,t in enumerate(F['triangles']) for v in t];_,ids=ED.add_vertices_to_mesh(dm,LS.convert_array_to_vector_list([bind(F['positions'][v],bone_for(part)) for v,part in keys]),True);vids=list(LS.convert_index_list_to_array(ids))
 for (v,part),vi in zip(keys,vids):BW.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=bones[bone_for(part)].index,weight=1.)])
 _,ts=ED.add_triangles_to_mesh(dm,LS.convert_array_to_triangle_list([u.IntVector(*vids[i:i+3]) for i in range(0,len(vids),3)]),0,True)
 for fi,tid in enumerate(LS.convert_index_list_to_array(ts)):
  if tid<0:raise RuntimeError('Rejected gun triangle '+str(fi))
  part=F['parts'][fi];MT.set_triangle_material_id(dm,tid,partslots[part],True);ns=[bind_normal(n,bone_for(part)) for n in F['normals'][fi]];u.GeometryScript_Normals.set_mesh_triangle_normals(dm,tid,u.GeometryScriptTriangle(vector0=ns[0],vector1=ns[1],vector2=ns[2]),True);uv=[u.Vector2D(*v) for v in F['uv'][fi]]
  for ch in (0,1):u.GeometryScript_UVs.set_mesh_triangle_u_vs(dm,ch,tid,u.GeometryScriptUVTriangle(uv0=uv[0],uv1=uv[1],uv2=uv[2]),True)
 mesh=clone(native.get_path_name(),D+'/SK_Saiga12K_Manny');opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=True,new_materials=mats,new_material_slot_names=slotnames,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write rebuilt gun')
 sk=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);sk.regenerate_lod(mesh,sk.get_lod_count(native),True,False)
 donor='/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative';payload=json.loads((P/'SourceAssets/BareSkinV9Rollout_20261017/Work/batch1'/(hashlib.sha256(donor.encode()).hexdigest()[:12]+'.json')).read_text());_,positions,_=Q.get_all_vertex_positions(read(mesh),False);positions=list(LS.convert_vector_list_to_array(positions));mapping={}
 for i,p in enumerate(positions):mapping.setdefault(tuple(round(x,4) for x in xyz(p)),[]).append(i)
 oldmap={vid:mapping.get(tuple(round(x,4) for x in p),[]) for vid,p in zip(payload['vertex_ids'],payload['positions'])}
 for name,rows in payload['morphs'].items():
  md=read(mesh)
  for old,x,y,z,nx,ny,nz in rows:
   for vi in oldmap.get(old,[]):ED.set_vertex_position(md,vi,u.Vector(x,y,z),True)
  _,status=G.copy_morph_target_to_skeletal_mesh(md,mesh,name,u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=True,emit_transaction=False,defer_mesh_post_edit_change=False,copy_normals=False),u.GeometryScriptMeshWriteLOD())
  if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot preserve corrective '+name)
 sys.path.insert(0,str(P/'Tools/Saiga12KSurface'));from mesh_contract import arm_contract
 contract=arm_contract(mesh);(O/'Reports/arms-after.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
 if contract!=C['arms']:raise RuntimeError('Native arm/bone/morph/UV contract changed; do not activate')
 E.set_metadata_tag(mesh,'SaigaSurfaceRebuild','20261018; full gun surface reconstruction; native V9 hands and mechanical bones preserved');save(mesh);R['mesh']=mesh.get_path_name();R['gun_triangles']=len(F['triangles']);R['arm_contract_unchanged']=True;R['bindings']['native']={str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.materials if s.material_interface};record();print('SAIGA_REBUILT_NATIVE_SAVED',flush=True)
if not R.get('ext12'):
 em=u.DynamicMesh();u.GeometryScript_UVs.set_num_uv_sets(em,2)
 def socket(p):return ML.inverse_transform_location(mag,ML.transform_location(root,vec([x*.01 for x in p])))*100.
 def socket_normal(n):return ML.inverse_transform_direction(mag,ML.transform_direction(root,vec(n)))
 _,ids=ED.add_vertices_to_mesh(em,LS.convert_array_to_vector_list([socket(X['positions'][v]) for t in X['triangles'] for v in t]),True);ids=list(LS.convert_index_list_to_array(ids));_,ts=ED.add_triangles_to_mesh(em,LS.convert_array_to_triangle_list([u.IntVector(*ids[i:i+3]) for i in range(0,len(ids),3)]),0,True)
 for fi,tid in enumerate(LS.convert_index_list_to_array(ts)):
  ns=[socket_normal(n) for n in X['normals'][fi]];u.GeometryScript_Normals.set_mesh_triangle_normals(em,tid,u.GeometryScriptTriangle(vector0=ns[0],vector1=ns[1],vector2=ns[2]),True);uv=[u.Vector2D(*v) for v in X['uv'][fi]]
  for ch in (0,1):u.GeometryScript_UVs.set_mesh_triangle_u_vs(em,ch,tid,u.GeometryScriptUVTriangle(uv0=uv[0],uv1=uv[1],uv2=uv[2]),True)
 mesh=clone(C['assets']['ext12']['path'],D+'/SM_Saiga12K_Ext12');_,status=G.copy_mesh_to_static_mesh(em,mesh,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write extended magazine')
 mi=gun_material('ExtMagazine','ext12',X['uv_per_cm']['ExtMagazine']);mesh.set_editor_property('static_materials',[u.StaticMaterial(material_interface=mi,material_slot_name='Saiga12K_Magazine')]);opts=u.StaticMeshReductionOptions();opts.auto_compute_lod_screen_size=False;opts.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in [(1.,1.),(.5,.18),(.25,.075)]];SM.set_lods(mesh,opts);save(mesh);R['ext12']=mesh.get_path_name();R['bindings']['ext12']={'Saiga12K_Magazine':mi.get_path_name()};record()
for key,row in C['assets'].items():
 if key in ('native','ext12') or key in R['bindings']:continue
 mesh=clone(row['path'],D+'/Attachments/SM_Saiga12K_'+key);slots=list(mesh.static_materials)
 for i,slot in enumerate(slots):
  src=slot.material_interface
  if not src:continue
  spec=C['materials'][src.get_path_name()];scalars=spec['scalars'];base=spec['base'];normal_params=set(scalars)
  # Optical glass/reticles/emissive shaders retain their authored graph and textures.
  if 'M_WeaponSurface' not in base and not any(n.startswith('R01_') for n in normal_params):continue
  name='MI_Part_'+hashlib.sha256(src.get_path_name().encode()).hexdigest()[:12];path=D+'/Materials/'+name
  if name in R['materials']:mi=load(path)
  else:
   mi=load(path) if E.does_asset_exist(path) else AT.create_asset(name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(mi,src)
   overrides={}
   for n in ('GrainRoughness','MottleRoughness','MottleColor','ScratchAmount','HandlingPolish','Stipple','EdgeWear','R01_GrainRoughness','R01_MottleRoughness','R01_MottleColor'):
    if n in normal_params:L.set_material_instance_scalar_parameter_value(mi,n,0.);overrides[n]=0.
   L.update_material_instance(mi);save(mi);R['materials'][name]={'path':mi.get_path_name(),'parent':src.get_path_name(),'scalars':overrides,'preserves_authored_structure_normal':True};record()
  slot.material_interface=mi;slots[i]=slot
 mesh.set_editor_property('static_materials',slots);save(mesh);R['bindings'][key]={str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials if s.material_interface};record()
R['complete']=True;record();print('SAIGA_SURFACE_ALL_ASSETS_SAVED',len(R['bindings']),flush=True)
