"""Produce Saiga-12K packages in a background UE Python commandlet.
Source: TastyTony / Sketchfab e9887136eaf14be396bdbea54f76ff3d, CC BY 4.0.
Preserve the current AKM V9 arms, UVs, skin weights and skeleton; replace gun geometry only.
"""
import json,hashlib,math
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12K20261017';ROOT='/Game/Weapons/Saiga12K/Integrated20261017'
DONOR='/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;Ed=u.GeometryScript_MeshEdits;BW=u.GeometryScript_BoneWeights;MAT=u.GeometryScript_Materials;ML=u.MathLibrary
R={'saved':[],'tested':False,'source':str(O/'Original/saiga12k.glb'),'donor':DONOR}
def record(): (O/'Receipts/assets.json').write_text(json.dumps(R,ensure_ascii=False,indent=2),encoding='utf-8')
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def save(a):
 if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost()],False):raise RuntimeError('Save failed '+a.get_path_name())
 R['saved'].append(a.get_path_name());record()
 return a
def pick(v,t):
 for x in v if isinstance(v,tuple) else (v,):
  if isinstance(x,t):return x
 raise RuntimeError('Missing '+str(t))
def vec(a):return u.Vector(*a)
def xyz(a):return [a.x,a.y,a.z]
def trans(t,p):return ML.transform_location(t,p)
def inv(t,p):return ML.inverse_transform_location(t,p)
def direction(t,p):return ML.transform_direction(t,p)
def read(mesh):
 dm,st=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if st!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read mesh failed')
 return dm
src=load(DONOR);dm=read(src)
_,bis=BW.get_all_bones_info(dm);bn={str(b.name):b for b in bis};names=[str(b.name) for b in bis]
idle=load('/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle')
loc=u.AnimationLibrary.get_bone_poses_for_frame(idle,names,0,False,src);pose={}
for b,t in zip(bis,loc):pose[str(b.name)]=t if b.parent_index<0 else t.multiply(pose[names[b.parent_index]])
root=pose['WPN_root']
# Source centimetres -> shared root metres. Uniform scale 1.25 sets overall length 90.23 cm.
# Rear grip centre is registered to AKM's authored grip (component 10 of its source).
S=.0125;shift=(.0008,.11520,-.01230)
def mounted(p):return vec((-p[2]*S+shift[0],p[0]*S+shift[1],p[1]*S+shift[2]))
def bind(p,bone):return trans(bn[bone].world_transform,inv(pose[bone],trans(root,mounted(p))))
def normal(n,bone):
 v=vec((-n[2],n[0],n[1]));v=direction(root,v);v=ML.inverse_transform_direction(pose[bone],v);return direction(bn[bone].world_transform,v)
geo=json.loads((O/'Authoring/source_geometry.json').read_text());islands=json.loads((O/'Authoring/source_islands.json').read_text())
face_part={}
for ii,island in enumerate(islands):
 bone=island['bone'];part='Body'
 if bone=='mag_02':part='Magazine'
 elif bone=='bolt_01':part='Bolt'
 elif bone=='safety_06':part='Safety'
 elif bone=='magrelease_05':part='MagRelease'
 elif bone in ('bullet_03','bullets_04'):part='ShellBrass' if any(m in (9,10,12,13) for m in island['materials']) else 'ShellPlastic'
 elif ii==21:part='Trigger'
 elif ii==1:part='Stock'
 elif ii==8:part='RearGrip'
 elif ii==4:part='Handguard'
 for fi in island['faces']:face_part[fi]=part
partbone={k:'WPN_root' for k in set(face_part.values())}
partbone.update(Magazine='WPN_SOCKET_Magazine',ShellBrass='WPN_SOCKET_Magazine',ShellPlastic='WPN_SOCKET_Magazine',Bolt='WPN_bolt',Trigger='WPN_Trigger')
# Keep donor skin geometry in its native reference frame, removing only weapon material sections.
slots=list(src.materials);skin_slots={i for i,s in enumerate(slots) if s.material_interface and ('BareSkinV9' in s.material_interface.get_path_name() or 'M4SkinV9' in s.material_interface.get_path_name())}
if not skin_slots:raise RuntimeError('Current donor has no V9 skin; do not downgrade the arms')
tids=list(L.convert_index_list_to_array(pick(Q.get_all_triangle_i_ds(dm),u.GeometryScriptIndexList)))
matids=list(L.convert_index_list_to_array(pick(MAT.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList)))
remove=[tid for tid in tids if matids[tid] not in skin_slots]
Ed.delete_triangles_from_mesh(dm,L.convert_array_to_index_list(remove),True)
# Materials are separate semantic slots, preserving polymer/steel separation and factory identity.
parts=sorted(set(face_part.values()));materials=[s.material_interface for s in slots];slotnames=[str(s.material_slot_name) for s in slots]
presets={'Stock':'CleanPolymer','RearGrip':'CleanPolymer','Handguard':'CleanPolymer','Magazine':'CleanPolymer','Bolt':'CleanPolishedSteel','ShellBrass':'CleanPolishedSteel','ShellPlastic':'CleanPolymer'}
for part in parts:
 parent=load('/Game/Weapons/WeaponSurface/Presets/MI_WS_'+presets.get(part,'CleanSatinSteel'))
 path=ROOT+'/Materials/MI_Saiga12K_'+part
 mi=load(path) if E.does_asset_exist(path) else AT.duplicate_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],parent)
 E.set_metadata_tag(mi,'Attribution','Low-Poly Saiga 12k by TastyTony; CC BY 4.0; converted, fitted and resurfaced for FPSGAME. https://sketchfab.com/3d-models/e9887136eaf14be396bdbea54f76ff3d')
 if part=='ShellBrass':u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi,'BaseColor',u.LinearColor(.35,.23,.08,1))
 if part=='ShellPlastic':u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi,'BaseColor',u.LinearColor(.19,.025,.018,1))
 save(mi);materials.append(mi);slotnames.append('Saiga12K_'+part)
partid={p:len(slots)+i for i,p in enumerate(parts)}
# Each source split vertex keeps its original normal. A source face never straddles a mechanical part.
rows={}
for fi,tri in enumerate(geo['triangles']):
 part=face_part[fi]
 for v in tri:rows[(v,part)]=None
keys=list(rows);positions=[bind(geo['positions'][v],partbone[p]) for v,p in keys]
_,newids=Ed.add_vertices_to_mesh(dm,L.convert_array_to_vector_list(positions),True);vids=list(L.convert_index_list_to_array(newids));vmap=dict(zip(keys,vids))
for (old,part),vi in vmap.items():BW.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=bn[partbone[part]].index,weight=1)])
tris=[u.IntVector(vmap[(t[0],face_part[i])],vmap[(t[2],face_part[i])],vmap[(t[1],face_part[i])]) for i,t in enumerate(geo['triangles'])]
_,newtis=Ed.add_triangles_to_mesh(dm,L.convert_array_to_triangle_list(tris),0,True);newtis=list(L.convert_index_list_to_array(newtis))
for fi,tid in enumerate(newtis):
 if tid<0:raise RuntimeError('Source triangle could not be appended')
 part=face_part[fi];bone=partbone[part];tri=geo['triangles'][fi];order=[tri[0],tri[2],tri[1]]
 MAT.set_triangle_material_id(dm,tid,partid[part],True)
 ns=[normal(geo['normals'][vi],bone) for vi in order]
 # Mesh corner APIs retain hard edges; normals correspond to original source split vertices.
 u.GeometryScript_Normals.set_mesh_triangle_normals(dm,tid,u.GeometryScriptTriangle(vector0=ns[0],vector1=ns[1],vector2=ns[2]),True)
 uv=[u.Vector2D(geo['positions'][vi][0]*.05,geo['positions'][vi][1]*.05) for vi in order]
 u.GeometryScript_UVs.set_mesh_triangle_u_vs(dm,0,tid,u.GeometryScriptUVTriangle(uv0=uv[0],uv1=uv[1],uv2=uv[2]),True)
path=ROOT+'/SK_Saiga12K_Manny'
mesh=load(path) if E.does_asset_exist(path) else AT.duplicate_asset('SK_Saiga12K_Manny',ROOT,src)
opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=True,new_materials=materials,new_material_slot_names=slotnames,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,st=G.copy_mesh_to_skeletal_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
if st!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Write Saiga mesh failed')
SKE=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
SKE.regenerate_lod(mesh,SKE.get_lod_count(src),True,False)
E.set_metadata_tag(mesh,'Saiga12KAuthor','20261017');E.set_metadata_tag(mesh,'Attribution','TastyTony / Sketchfab e9887136eaf14be396bdbea54f76ff3d / CC BY 4.0. Adapted geometry and materials.')
save(mesh)
# Donor JC shapes have vertex indices tied to the donor topology; rebuild on the new topology.
key=hashlib.sha256(DONOR.encode()).hexdigest()[:12]
work=P/'SourceAssets/BareSkinV9Rollout_20261017/Work/batch1'/f'{key}.json'
if work.exists():
 payload=json.loads(work.read_text());saved_dm=read(mesh);_,ps,_=Q.get_all_vertex_positions(saved_dm,False);ps=list(L.convert_vector_list_to_array(ps));mapping={}
 for i,q in enumerate(ps):mapping.setdefault(tuple(round(x,4) for x in xyz(q)),[]).append(i)
 oldmap={vid:mapping.get(tuple(round(x,4) for x in pos),[]) for vid,pos in zip(payload['vertex_ids'],payload['positions'])}
 for mi,(name,rows_) in enumerate(payload.get('morphs',{}).items()):
  md=read(mesh)
  for old,x,y,z,nx,ny,nz in rows_:
   for vi in oldmap.get(old,[]):Ed.set_vertex_position(md,vi,vec((x,y,z)),True)
  mo=u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=True,emit_transaction=False,defer_mesh_post_edit_change=False,copy_normals=False)
  _,oc=G.copy_morph_target_to_skeletal_mesh(md,mesh,name,mo,u.GeometryScriptMeshWriteLOD())
  if oc!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Corrective write failed '+name)
 R['correctives']=len(payload.get('morphs',{}));save(mesh)
R.update(complete=True,mesh=mesh.get_path_name(),source_triangles=len(geo['triangles']),parts={p:{'triangles':sum(x==p for x in face_part.values()),'bone':partbone[p]} for p in parts},root_unit_scale=.0125,root_translation=list(shift))
# Explicit root-space mounts are consumed by the gameplay header, independent of donor sight bones.
marks={'Muzzle':(38.299366,4.1464,0),'Rear':(4.7157,8.28,0),'Front':(22.4855,8.3098,0),'Eject':(-.3,5.5,1.2)}
R['mounts']={k:xyz(mounted(v)) for k,v in marks.items()};record()
(O/'Authoring/assembly.json').write_text(json.dumps(R,ensure_ascii=False,indent=2),encoding='utf-8')
print('SAIGA12K_SAVED',mesh.get_path_name(),flush=True)
