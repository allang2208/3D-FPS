"""Install the repaired Saiga assembly and its WS1.1 surfaces at private V2 paths."""
import unreal as u,json,math,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KRefine20261017';D='/Game/Weapons/Saiga12K/Refined20261017'
C=json.loads((O/'inputs.json').read_text());F=json.loads((O/'Authoring/gun.json').read_text())
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;LS=u.GeometryScript_List;ED=u.GeometryScript_MeshEdits;BW=u.GeometryScript_BoneWeights;MT=u.GeometryScript_Materials;ML=u.MathLibrary
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
def pick(v,t):return next(x for x in v if isinstance(x,t))
def vec(v):return u.Vector(*v)
def xyz(v):return [v.x,v.y,v.z]
def read(mesh):
 dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Skeletal source unavailable')
 return dm

if not E.does_asset_exist(D+'/Textures/T_Saiga12K_WS11_Mask'):
 task=u.AssetImportTask();task.filename=str(O/'Textures/T_Saiga12K_WS11_Mask.png');task.destination_path=D+'/Textures';task.destination_name='T_Saiga12K_WS11_Mask';task.automated=True;task.save=False;AT.import_asset_tasks([task])
 mask=load(D+'/Textures/T_Saiga12K_WS11_Mask');mask.srgb=False;mask.compression_settings=u.TextureCompressionSettings.TC_MASKS;mask.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;save(mask)
else:mask=load(D+'/Textures/T_Saiga12K_WS11_Mask')
neutral=load('/Game/Weapons/WeaponSurface/Textures/T_WS_MaskNeutral');flat=load('/Engine/EngineMaterials/DefaultNormal')
COMMON={'GrainTileCm':2.,'GrainRoughness':.012,'MottleRoughness':.005,'MottleColor':0.,'ScratchAmount':0.,'HandlingPolish':0.,'Stipple':0.,'EdgeWear':.025,'EdgeHighlight':.06,'CavityDarken':.025,'CavityRoughness':.018,'SourceColorWeight':0.,'SourceRoughnessWeight':0.,'AOStrength':.65,'WeaponWetness':0.}
def instance(name,preset,rough,normal=None,surface_mask=None,uv=0,density=.04,color=None,two_sided=False,rough_texture=None):
 path=D+'/Materials/MI_'+name
 if name in R['materials']:return load(path)
 mi=load(path) if E.does_asset_exist(path) else AT.create_asset('MI_'+name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
 L.clear_all_material_instance_parameters(mi);L.set_material_instance_parent(mi,load('/Game/Weapons/WeaponSurface/Presets/MI_WS_'+preset))
 values=dict(COMMON,Roughness=rough,MaskUVChannel=float(uv),BeadScale=2.42/max(density,.0001))
 if preset in ('CleanPolymer','Rubber','Interior'):values.update(EdgeMetallic=0.,EdgeWear=0.,EdgeHighlight=.025)
 if preset=='Interior':values.update(EdgeHighlight=0.,GrainRoughness=.005)
 if rough_texture:values['SourceRoughnessWeight']=.15
 for k,v in values.items():L.set_material_instance_scalar_parameter_value(mi,k,v)
 if color:L.set_material_instance_vector_parameter_value(mi,'FinishColor',u.LinearColor(*color,1))
 L.set_material_instance_texture_parameter_value(mi,'SurfaceMask',surface_mask or neutral)
 L.set_material_instance_texture_parameter_value(mi,'SurfaceNormal',normal or flat)
 if rough_texture:L.set_material_instance_texture_parameter_value(mi,'SourceRoughness',rough_texture)
 overrides=mi.get_editor_property('base_property_overrides');overrides.set_editor_property('override_two_sided',two_sided);overrides.set_editor_property('two_sided',two_sided);mi.set_editor_property('base_property_overrides',overrides)
 L.update_material_instance(mi);E.set_metadata_tag(mi,'WeaponSurfaceVersion','WS1.1 Saiga 20261017');save(mi)
 R['materials'][name]={'path':mi.get_path_name(),'parent':mi.parent.get_path_name(),'preset':preset,'scalars':values,'normal':(normal or flat).get_path_name(),'mask':(surface_mask or neutral).get_path_name(),'two_sided':two_sided};record()
 return mi

if not R.get('mesh'):
 native=load(C['assets']['native']['path']);dm=read(native)
 _,boneinfo=BW.get_all_bones_info(dm);bones={str(b.name):b for b in boneinfo};names=[str(b.name) for b in boneinfo]
 idle=load('/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle');local=u.AnimationLibrary.get_bone_poses_for_frame(idle,names,0,False,native);pose={}
 for b,t in zip(boneinfo,local):pose[str(b.name)]=t if b.parent_index<0 else t.multiply(pose[names[b.parent_index]])
 root=pose['WPN_root']
 def bone_for(part):
  return 'WPN_SOCKET_Magazine' if part in ('Magazine','ShellBrass','ShellPlastic') else 'WPN_bolt' if part=='Bolt' else 'WPN_Trigger' if part=='Trigger' else 'WPN_root'
 def bind(p,bone):return ML.transform_location(bones[bone].world_transform,ML.inverse_transform_location(pose[bone],ML.transform_location(root,vec([x*.01 for x in p]))))
 def bind_normal(n,bone):return ML.transform_direction(bones[bone].world_transform,ML.inverse_transform_direction(pose[bone],ML.transform_direction(root,vec(n))))
 slots=list(native.materials);mats=[s.material_interface for s in slots];slotnames=[str(s.material_slot_name) for s in slots]
 gunids={i for i,s in enumerate(slots) if str(s.material_slot_name).startswith('Saiga12K_')}
 tids=list(LS.convert_index_list_to_array(pick(Q.get_all_triangle_i_ds(dm),u.GeometryScriptIndexList)))
 removed=[t for t in tids if MT.get_triangle_material_id(dm,t)[0] in gunids]
 ED.delete_triangles_from_mesh(dm,LS.convert_array_to_index_list(removed),True)
 u.GeometryScript_UVs.set_num_uv_sets(dm,max(4,Q.get_num_uv_sets(dm)))
 partslots={}
 for part in sorted(set(F['parts'])):
  preset='CleanSatinSteel';rough=.42;color=None
  if part in ('Stock','Handguard','Magazine','RearGrip','ShellPlastic'):preset='CleanPolymer';rough=.53 if part=='Magazine' else .55
  elif part=='ReceiverCover':rough=.39
  elif part=='Bolt':preset='CleanPolishedSteel';rough=.32;color=(.095,.096,.095)
  elif part in ('Trigger','Safety','MagRelease'):rough=.36
  elif part=='ReceiverInterior':preset='Interior';rough=.75
  elif part=='ShellBrass':preset='CleanPolishedSteel';rough=.31;color=(.35,.23,.08)
  if part=='ShellPlastic':color=(.19,.025,.018)
  mat=instance('Saiga12K_'+part,preset,rough,surface_mask=mask,uv=1,density=F['uv_per_cm'][part],color=color,two_sided=part not in ('ReceiverCover','ReceiverInterior'))
  name='Saiga12K_'+part
  if name in slotnames:idx=slotnames.index(name);mats[idx]=mat
  else:idx=len(slotnames);slotnames.append(name);mats.append(mat)
  partslots[part]=idx
 # Split import corners retain source hard normals and overlapping mechanical
 # shells without forcing their coincident edges into one non-manifold vertex.
 keys=[(v,F['parts'][fi]) for fi,t in enumerate(F['triangles']) for v in t]
 _,ids=ED.add_vertices_to_mesh(dm,LS.convert_array_to_vector_list([bind(F['positions'][v],bone_for(part)) for v,part in keys]),True)
 vids=list(LS.convert_index_list_to_array(ids))
 for (v,part),vi in zip(keys,vids):BW.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=bones[bone_for(part)].index,weight=1.)])
 tri=[u.IntVector(*vids[i:i+3]) for i in range(0,len(vids),3)]
 _,ts=ED.add_triangles_to_mesh(dm,LS.convert_array_to_triangle_list(tri),0,True)
 for fi,tid in enumerate(LS.convert_index_list_to_array(ts)):
  if tid<0:raise RuntimeError('New gun triangle could not be written')
  part=F['parts'][fi];MT.set_triangle_material_id(dm,tid,partslots[part],True)
  ns=[bind_normal(n,bone_for(part)) for n in F['normals'][fi]];u.GeometryScript_Normals.set_mesh_triangle_normals(dm,tid,u.GeometryScriptTriangle(vector0=ns[0],vector1=ns[1],vector2=ns[2]),True)
  uv=[u.Vector2D(*v) for v in F['uv'][fi]]
  for channel in (0,1):u.GeometryScript_UVs.set_mesh_triangle_u_vs(dm,channel,tid,u.GeometryScriptUVTriangle(uv0=uv[0],uv1=uv[1],uv2=uv[2]),True)
 mesh=clone(native.get_path_name(),D+'/SK_Saiga12K_Manny')
 opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=True,new_materials=mats,new_material_slot_names=slotnames,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save repaired skeletal geometry')
 sk=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);sk.regenerate_lod(mesh,sk.get_lod_count(native),True,False);save(mesh)
 # Retain all native V9 corrective shapes after gun-only topology changes.
 donor='/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative'
 payload=json.loads((P/'SourceAssets/BareSkinV9Rollout_20261017/Work/batch1'/(hashlib.sha256(donor.encode()).hexdigest()[:12]+'.json')).read_text())
 _,positions,_=Q.get_all_vertex_positions(read(mesh),False);positions=list(LS.convert_vector_list_to_array(positions));mapping={}
 for i,p in enumerate(positions):mapping.setdefault(tuple(round(x,4) for x in xyz(p)),[]).append(i)
 oldmap={vid:mapping.get(tuple(round(x,4) for x in p),[]) for vid,p in zip(payload['vertex_ids'],payload['positions'])}
 for name,rows in payload['morphs'].items():
  md=read(mesh)
  for old,x,y,z,nx,ny,nz in rows:
   for vi in oldmap.get(old,[]):ED.set_vertex_position(md,vi,u.Vector(x,y,z),True)
  _,status=G.copy_morph_target_to_skeletal_mesh(md,mesh,name,u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=True,emit_transaction=False,defer_mesh_post_edit_change=False,copy_normals=False),u.GeometryScriptMeshWriteLOD())
  if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Corrective '+name)
 E.set_metadata_tag(mesh,'Saiga12KRefinement','Continuous thick receiver cover; side ejection port; unique gun UV0/UV1; WS1.1; native V9 arms preserved')
 save(mesh);R['mesh']=mesh.get_path_name();R['gun_triangles']=len(F['triangles']);R['correctives']=len(payload['morphs']);R['bindings']['native']={str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.materials if s.material_interface};record()
 print('SAIGA_REPAIRED_BODY_SAVED',flush=True)

# Existing optics / emitter shaders keep their transparency, masks and lit lens.
# All ordinary body, adapter and furniture surfaces use this gun's WS1.1 family.
def normal_source(row):
 for k in ('SurfaceNormal','NormalMap','Normal','NormalTexture'):
  if row.get('textures',{}).get(k):return load(row['textures'][k])
 for p in row.get('literal_textures',[]):
  if any(w in p.lower() for w in ('normal','_n.','_n_')) and 'grain' not in p.lower():return load(p)
 return None
def rough_source(row):
 for k,p in row.get('textures',{}).items():
  if p and ('Roughness' in k or k=='ShininessMap') and 'rough' in p.lower():return load(p)
 for p in row.get('literal_textures',[]):
  if 'roughness' in p.lower() and '/ArmSupport/' not in p and 'Receiver_Roughness' not in p:return load(p)
 return None
def sampled_density(asset):
 md,st=G.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 _,vs,_=Q.get_all_vertex_positions(md,False);vs=list(LS.convert_vector_list_to_array(vs));_,tt,_=Q.get_all_triangle_indices(md,False);tt=list(LS.convert_triangle_list_to_array(tt));areas={}
 step=max(1,len(tt)//600)
 for ti in range(0,len(tt),step):
  t=tt[ti];p=[vs[i] for i in (t.x,t.y,t.z)];a=vec([p[1].x-p[0].x,p[1].y-p[0].y,p[1].z-p[0].z]);b=vec([p[2].x-p[0].x,p[2].y-p[0].y,p[2].z-p[0].z]);cross=ML.cross_vector_vector(a,b);area=ML.v_size(cross)*.5
  uv=Q.get_triangle_u_vs(md,0,ti)[:3];ua=abs((uv[1].x-uv[0].x)*(uv[2].y-uv[0].y)-(uv[1].y-uv[0].y)*(uv[2].x-uv[0].x))*.5
  mid=MT.get_triangle_material_id(md,ti)[0];tot=areas.setdefault(mid,[0.,0.]);tot[0]+=area;tot[1]+=ua
 return {i:math.sqrt(b/a) for i,(a,b) in areas.items() if a>1e-9 and b>1e-12}
for key,row in C['assets'].items():
 if key=='native':continue
 if key in R['bindings']:continue
 source=load(row['path']);target=clone(row['path'],D+'/Attachments/SM_Saiga12K_'+key);slots=list(target.static_materials);density=sampled_density(source)
 for i,slot in enumerate(slots):
  label=str(slot.material_slot_name);low=label.lower();src=source.static_materials[i].material_interface
  if not src:continue
  spec=C['materials'].get(src.get_path_name(),{});base=spec.get('base','').lower()
  special=any(w in low for w in ('glass','reticle','red_dot','objective','display','copper','titanium','legend','marking','gold','champagne','redinset','aperture','optic'))
  mixed=(key=='holographic' and i==0) or (key=='eoth_holographic' and i==0) or ((key.startswith('laser_') or key.startswith('flashlight_')) and i==0)
  mixed=mixed or ('BLEND_OPAQUE' not in spec.get('blend_mode','BLEND_OPAQUE'))
  if special:continue
  if mixed:
   # These material graphs own per-pixel glass / markings / lens emission.
   # Preserve those branches and source normals; tune their existing coat layer.
   name='MI_Saiga12K_'+key+'_Mixed_'+str(i);path=D+'/Materials/'+name
   mat=load(path) if E.does_asset_exist(path) else AT.create_asset(name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
   L.set_material_instance_parent(mat,src)
   if isinstance(mat,u.MaterialInstanceConstant):
    scalars={str(n) for n in L.get_scalar_parameter_names(mat)}
    for name,value in [('R01_Roughness',.42),('R01_GrainRoughness',.012),('R01_MottleRoughness',.005)]:
     if name in scalars:L.set_material_instance_scalar_parameter_value(mat,name,value)
    L.update_material_instance(mat)
   save(mat);slot.material_interface=mat;slots[i]=slot;continue
  preset='CleanSatinSteel';rough=.42
  if any(w in low for w in ('rubber','buttpad')):preset='Rubber';rough=.70
  elif any(w in low for w in ('polymer','black','corestockbody')) or (key in ('vertical','canted','tactical_vertical') and i==0) or (key in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip') and i==0):preset='CleanPolymer';rough=.55
  elif any(w in low for w in ('interior','recess','seam')):preset='Interior';rough=.75
  elif 'steel' in low and key=='legendary_adjustable_tactical_stock':preset='CleanPolishedSteel';rough=.34
  if preset=='CleanSatinSteel' and ('seat' in low or 'adapter' in low or 'interface' in low):rough=.44
  slot.material_interface=instance('Saiga12K_'+key+'_'+str(i),preset,rough,normal=normal_source(spec),rough_texture=rough_source(spec),density=density.get(i,.04));slots[i]=slot
 target.set_editor_property('static_materials',slots)
 E.set_metadata_tag(target,'Saiga12KSurface','WS1.1 by region; source UVs, structure normals, sockets and fitted LODs retained')
 save(target);R['bindings'][key]={str(s.material_slot_name):s.material_interface.get_path_name() for s in target.static_materials if s.material_interface};record();print('SAIGA_WS11_ATTACHMENT_SAVED',key,flush=True)
R['complete']=True;record();print('SAIGA_REFINEMENT_SAVED',flush=True)
