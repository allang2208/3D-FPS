"""Save Saiga-only fitted common parts and shared-animation profiles, headlessly."""
import unreal as u
import json,hashlib,math
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KCommon20261017'
D='/Game/Weapons/Saiga12K/Common20261017'
sources=json.loads((O/'sources.json').read_text());inputs=json.loads((O/'inputs.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE: preserve the current session')
 if any(p.get_name().startswith(D+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved Saiga common assets; preserve current edits')
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;ED=u.GeometryScript_MeshEdits;LS=u.GeometryScript_List;MT=u.GeometryScript_Materials
R={'complete':False,'saved':[],'parts':{},'profiles':[],'runtime_tested':False}
def record():(O/'Receipts/assets.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(path):
 o=u.load_asset(path)
 if not o:raise RuntimeError('Missing '+path)
 return o
def save(o):
 if not E.save_loaded_asset(o,False):raise RuntimeError('Save failed '+o.get_path_name())
 if o.get_path_name() not in R['saved']:R['saved'].append(o.get_path_name())
 record();return o
def clone(src,path):return load(path) if E.does_asset_exist(path) else E.duplicate_asset(src,path)
def vector(v):return u.Vector(*v)
def xyz(v):return [v.x,v.y,v.z]
def transform(dm,offset=(0,0,0),yaw=0,pitch=0):
 t=u.Transform(location=vector(offset),rotation=u.Rotator(pitch=pitch,yaw=yaw,roll=0),scale=u.Vector(1,1,1))
 u.GeometryScript_MeshTransforms.transform_mesh(dm,t);return t
def geometry(dm):
 _,vp,_=Q.get_all_vertex_positions(dm,False);vp=list(LS.convert_vector_list_to_array(vp))
 _,tp,_=Q.get_all_triangle_indices(dm,False);tp=list(LS.convert_triangle_list_to_array(tp))
 return vp,tp
def shell(dm,vertices,faces,mid):
 _,vi=ED.add_vertices_to_mesh(dm,LS.convert_array_to_vector_list([vector(v) for v in vertices]),True)
 vi=list(LS.convert_index_list_to_array(vi));tris=[]
 for face in faces:
  for j in range(1,len(face)-1):tris.append(u.IntVector(vi[face[0]],vi[face[j]],vi[face[j+1]]))
 _,ti=ED.add_triangles_to_mesh(dm,LS.convert_array_to_triangle_list(tris),0,True)
 for tid,t in zip(LS.convert_index_list_to_array(ti),tris):
  MT.set_triangle_material_id(dm,tid,mid,True)
  ps=[vector(vertices[vi.index(i)]) for i in (t.x,t.y,t.z)]
  a,b,c=ps;ab=[b.x-a.x,b.y-a.y,b.z-a.z];ac=[c.x-a.x,c.y-a.y,c.z-a.z]
  n=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
  d=math.sqrt(sum(x*x for x in n));n=vector([x/d for x in n]);axes=sorted(range(3),key=lambda i:abs(xyz(n)[i]))[:2]
  u.GeometryScript_Normals.set_mesh_triangle_normals(dm,tid,u.GeometryScriptTriangle(vector0=n,vector1=n,vector2=n),True)
  uv=[u.Vector2D(xyz(p)[axes[0]]*.25,xyz(p)[axes[1]]*.25) for p in ps]
  u.GeometryScript_UVs.set_mesh_triangle_u_vs(dm,0,tid,u.GeometryScriptUVTriangle(uv0=uv[0],uv1=uv[1],uv2=uv[2]),True)
def box(dm,lo,hi,mid):
 x,y,z=lo;X,Y,Z=hi
 shell(dm,[(x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],
 [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mid)
def extrude_x(dm,x0,x1,profile,mid):
 n=len(profile);v=[(x,y,z) for x in (x0,x1) for y,z in profile]
 faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
 shell(dm,v,faces,mid)
def remove_materials(dm,slots,words):
 ids={i for i,s in enumerate(slots) if any(w in str(s.material_slot_name).lower() for w in words)}
 vp,tp=geometry(dm);remove=[i for i in range(len(tp)) if MT.get_triangle_material_id(dm,i)[0] in ids]
 if remove:ED.delete_triangles_from_mesh(dm,LS.convert_array_to_index_list(remove),True)
 return len(remove)
def material_bounds(dm,mid):
 vp,tp=geometry(dm);points=[]
 ids=next(x for x in Q.get_all_triangle_i_ds(dm) if isinstance(x,u.GeometryScriptIndexList))
 for i in LS.convert_index_list_to_array(ids):
  t=tp[i]
  if MT.get_triangle_material_id(dm,i)[0]==mid:points.extend([vp[t.x],vp[t.y],vp[t.z]])
 return [[min(getattr(v,c) for v in points) for c in 'xyz'],[max(getattr(v,c) for v in points) for c in 'xyz']]
metal=save(clone('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanSatinSteel',D+'/Materials/MI_Saiga12K_AdapterSteel'))
polymer=save(clone('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanPolymer',D+'/Materials/MI_Saiga12K_AdapterPolymer'))
finished={}
def finish(source,label):
 if not source:return None
 # Optical/coloured detail is intentionally shared. Body UVs and normal maps remain intact.
 if any(w in label.lower() for w in ('glass','reticle','red_dot','objective','display','rubber','copper','titanium','legend','marking','gold','champagne','redinset','optic','aperture')):return source
 sp=source.get_path_name()
 if sp in finished:return finished[sp]
 dst=D+'/Materials/MI_Saiga12K_'+hashlib.sha256(sp.encode()).hexdigest()[:12]
 mat=clone(sp,dst)
 if isinstance(mat,u.MaterialInstanceConstant):
  scalars={str(n) for n in L.get_scalar_parameter_names(mat)}
  for param in ('R01_Roughness','DryRoughness'):
   if param in scalars:L.set_material_instance_scalar_parameter_value(mat,param,.34)
  # Parent masks, source textures and polymer/steel separation are retained.
  L.update_material_instance(mat)
 finished[sp]=save(mat);return mat

# Receiver support heights are taken from original source triangles, in root cm.
geo=json.loads((P/'SourceAssets/Saiga12K20261017/Authoring/source_geometry.json').read_text())
islands=json.loads((P/'SourceAssets/Saiga12K20261017/Authoring/source_islands.json').read_text())
points=[(-v[2]*1.25+.08,v[0]*1.25+11.52,v[1]*1.25-1.23) for v in geo['positions']]
def surface_z(x,y,part,top=True):
 hits=[]
 for fi in islands[part]['faces']:
  a,b,c=[points[i] for i in geo['triangles'][fi]]
  den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
  if abs(den)<1e-9:continue
  p=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
  q=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den
  if p>=-1e-5 and q>=-1e-5 and p+q<=1.00001:hits.append(p*a[2]+q*b[2]+(1-p-q)*c[2])
 if not hits:raise RuntimeError('No source interface at '+str((x,y,part)))
 return max(hits) if top else min(hits)

for key,sourcepath in sources.items():
 source=load(sourcepath);mesh=clone(sourcepath,D+'/Meshes/SM_Saiga12K_'+key)
 dm,status=G.copy_mesh_from_static_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=True),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read '+key)
 slots=list(source.static_materials);mats=[finish(s.material_interface,str(s.material_slot_name)) for s in slots];names=[str(s.material_slot_name) for s in slots]
 adapter=len(mats);mats.append(metal);names.append('Saiga12K_InterfaceMetal')
 socket_transform=None;notes=[]
 if key in ('skeleton','core_stock','qr_performance','tactical_telescopic'):
  transform(dm,(.08,-7.92,3.5),yaw=-90)
  # Closed receiver tenon overlaps the original stock socket at the rear wall.
  box(dm,(-.94,-8.12,2.42),(1.10,-7.25,4.58),adapter)
  notes.append('Canonical stock, yaw -90; receiver tenon at source stock front interface')
 elif key=='legendary_adjustable_tactical_stock':
  transform(dm,(0,.38,0));box(dm,(-.94,-8.12,2.42),(1.10,-7.25,4.58),adapter)
  notes.append('AKM root fit translated +0.38 cm to Saiga stock socket')
 elif key in ('vertical','tactical_vertical','canted','prism','angled'):
  # The accepted hand contact remains fixed in the common AKM frame. Replace
  # its obsolete AKM rail with a closed Saiga handguard bearing.
  removed=remove_materials(dm,slots,('adaptersteel','mountsteel'))
  top=surface_z(.08,30,4,False)
  box(dm,(-1.20,26.55,min(.7,top-.20)),(1.36,33.45,top+.10),adapter)
  notes.append('Fixed common hand contact; Saiga underside bearing; removed donor adapter triangles '+str(removed))
 elif key in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'):
  removed=remove_materials(dm,slots,('collar',))
  # Copy the actual top neck of the original grip, preserving its interface
  # silhouette; add a closed shallow joint to the compatible replacement head.
  neckverts=sorted({v for fi in islands[8]['faces'] for v in geo['triangles'][fi]})
  capz=max(points[v][2] for v in neckverts)
  neckfaces=[fi for fi in islands[8]['faces'] if min(points[v][2] for v in geo['triangles'][fi])>capz-1.0]
  if neckfaces:
   ids=sorted({v for fi in neckfaces for v in geo['triangles'][fi]});lookup={v:i for i,v in enumerate(ids)}
   shell(dm,[points[v] for v in ids],[[lookup[v] for v in reversed(geo['triangles'][fi])] for fi in neckfaces],adapter)
  box(dm,(-1.10,-4.15,-.30),(1.26,-1.10,.65),adapter)
  notes.append('Original grip neck; donor wrap collar removed '+str(removed)+' triangles; hand contact preserved')
 elif key.startswith('OpticSeat_'):
  # This rail matches the existing saddle jaw profile exactly, with legs
  # sampled on Saiga receiver cover island 19. It is part of the seat asset.
  extrude_x(dm,-4.5,4.5,[(-.7254785,0),(-.964036,-.255),(-.964036,-.335),(.964036,-.335),(.964036,-.255),(.7254785,0)],adapter)
  for x0,x1 in [(-3.9,-2.9),(2.9,3.9)]:
   z0=surface_z(.08,6+(x0+x1)/2,19)-9.2
   box(dm,(x0,-.64,z0-.06),(x1,.64,-.28),adapter)
  notes.append('19.28072 mm rail wing and sampled receiver feet; canonical X forward cm')
 elif key.endswith(('_1','_2')):
  remove_materials(dm,slots,('fitted_bearing',))
  # Device bracket joins the actual narrower Saiga handguard at the same
  # body mounting surface; move it forward clear of the shared support grasp.
  bodylo,bodyhi=material_bounds(dm,0)
  inner=1.44;outer=bodylo[0]+.15
  box(dm,(inner,29,4.95),(max(outer,inner+.25),33,6.45),adapter)
  if key.endswith('_2'):
   socket_transform=transform(dm,(.16,4,2*5.699730664491653-1.30),pitch=180)
  else:socket_transform=transform(dm,(0,4,-1.30))
  notes.append('Closed side bearing, +4 cm forward, -1.3 cm down; side 2 uses positive 180 degree rotation')
 opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,use_original_vertex_order=False,replace_materials=True,new_materials=mats,new_material_slot_names=names)
 _,status=G.copy_mesh_to_static_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Write '+key)
 if socket_transform:
  for label,pos in inputs[key]['sockets'].items():
   socket=mesh.find_socket(label)
   if not socket:socket=u.StaticMeshSocket(outer=mesh);socket.set_editor_property('socket_name',label);mesh.add_socket(socket)
   socket.set_editor_property('relative_location',u.MathLibrary.transform_location(socket_transform,vector(pos)))
 u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
 E.set_metadata_tag(mesh,'Saiga12KSource',sourcepath)
 E.set_metadata_tag(mesh,'Saiga12KFit','; '.join(notes))
 save(mesh);R['parts'][key]={'path':mesh.get_path_name(),'source':sourcepath,'fit':notes};record()
 print('SAIGA_PART_SAVED',key,flush=True)
for family in ('angled','vertical','canted','prism'):
 profile=clone('/Game/Weapons/AnimationProfiles20261001/ue_akm/DA_'+family,D+'/Profiles/DA_'+family)
 E.set_metadata_tag(profile,'Saiga12KSharedAnimations','Native AKM base sequence references and sparse grip corrections; same support contact frame')
 save(profile);R['profiles'].append(profile.get_path_name());record()
R['complete']=True;record();print('SAIGA_COMMON_ASSETS_SAVED',len(R['parts']),flush=True)
