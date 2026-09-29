"""Preserve a native wrist underlap when clothing hides the main forearm section.

Duplicate current first-person skin companions, retaining positions, weights,
UVs and normals. Only reclassify distal forearm triangles into an extra skin
material section, outside shirt/glove coverage. No accepted naked asset changes.
"""
import hashlib,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME'); R=P/'SourceAssets/WristCoverage20260929'
DEST='/Game/Characters/ModularOutfit20260924/WristCoverage20260929'
E=u.EditorAssetLibrary; A=u.AssetToolsHelpers.get_asset_tools()
G=u.GeometryScript_AssetUtils; Q=u.GeometryScript_MeshQueries; B=u.GeometryScript_BoneWeights
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def plan():
 path=R/'plan.json'
 if path.exists():return read(path)
 c=read(P/'Content/ColdSteelData/modular_outfits.json');sources={};refs=[]
 for key,profile in c['profiles'].items():
  rig=profile.get('rig_profile')
  if rig=='Body':continue
  field='native_bare_skin' if profile.get('native_bare_skin') else 'base'
  source=profile.get(field)
  if not source:continue
  sources[source]=rig;refs.append(dict(kind='profile',key=key,field=field,source=source))
 for key,recipe in c['items'].items():
  for rig,source in recipe.get('skin_meshes',{}).items():
   if rig=='Body':continue
   sources[source]=rig;refs.append(dict(kind='item',key=key,field=rig,source=source))
 jobs=[dict(source=source,rig=rig,key=rig+'_'+hashlib.sha256(source.encode()).hexdigest()[:10]) for source,rig in sources.items()]
 result=dict(jobs=jobs,refs=refs,band_depth_cm=8.0);write(path,result);return result

def build(job):
 receipt=R/'Saved'/(job['key']+'.json')
 if receipt.exists():return read(receipt)
 source=u.load_asset(job['source'])
 if not source:raise RuntimeError('Missing current skin '+job['source'])
 slots=list(source.get_editor_property('materials'))
 lower=next((i for i,s in enumerate(slots) if str(s.material_slot_name)=='BareLowerArms'),None)
 if lower is None:raise RuntimeError('No authored lower-arm section '+job['source'])
 extra=len(slots);materials=[s.material_interface for s in slots]+[slots[lower].material_interface]
 names=[s.material_slot_name for s in slots]+['WristUnderlapSkin']
 folder=DEST+'/'+job['rig'];name='SK_'+job['key']+'_WristCoverage'
 E.make_directory(folder);mesh=u.load_asset(folder+'/'+name) or A.duplicate_asset(name,folder,source)
 if not mesh:raise RuntimeError('Cannot duplicate '+job['source'])
 # Edit LOD0 source and regenerate existing distances from its protected section.
 # Edge locking keeps both ends of the wrist strip throughout LOD reduction.
 dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native skin '+job['key'])
 _,bones=B.get_all_bones_info(dm);bones={str(b.name):b for b in bones}
 frames=[]
 for side in ['l','r']:
  if 'hand_'+side not in bones or 'lowerarm_'+side not in bones:continue
  wrist=bones['hand_'+side].world_transform.translation;elbow=bones['lowerarm_'+side].world_transform.translation
  dx,dy,dz=wrist.x-elbow.x,wrist.y-elbow.y,wrist.z-elbow.z;length=(dx*dx+dy*dy+dz*dz)**.5
  frames.append((wrist,(dx/length,dy/length,dz/length)))
 if not frames:raise RuntimeError('Missing native wrist frame '+job['key'])
 _,vl,_=Q.get_all_vertex_positions(dm,False);positions=u.GeometryScript_List.convert_vector_list_to_array(vl)
 _,tl,_=Q.get_all_triangle_indices(dm,False);triangles=u.GeometryScript_List.convert_triangle_list_to_array(tl)
 selected=[]
 for ti,t in enumerate(triangles):
  mat,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
  if not valid or mat!=lower:continue
  for wrist,axis in frames:
   near=False
   for vi in [t.x,t.y,t.z]:
    v=positions[vi];x,y,z=v.x-wrist.x,v.y-wrist.y,v.z-wrist.z
    axial=x*axis[0]+y*axis[1]+z*axis[2]
    if axial>=-8.0 and x*x+y*y+z*z<144:near=True;break
   if near:
    u.GeometryScript_Materials.set_triangle_material_id(dm,ti,extra,True);selected.append(ti);break
 if not selected:raise RuntimeError('No forearm underlap found '+job['key'])
 options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,new_material_slot_names=names,
  enable_recompute_normals=False,enable_recompute_tangents=False,
  bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
 _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write wrist skin '+job['key'])
 if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):raise RuntimeError('Cannot configure native LODs')
 if not S.regenerate_lod(mesh,3,True,False):raise RuntimeError('Cannot build wrist LODs')
 mesh.modify();E.set_metadata_tag(mesh,'WristCoverageSource',job['source'])
 E.set_metadata_tag(mesh,'WristCoverageContract','Keep WristUnderlapSkin visible beneath all first-person sleeves and gloves')
 if not (u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outer()],False) or E.save_loaded_asset(mesh,False)):
  raise RuntimeError('Cannot save '+mesh.get_path_name())
 result=dict(job,mesh=mesh.get_path_name(),wrist_slot=extra,forearm_slot=lower,protected_triangles=len(selected),lods=3,
  positions_unchanged=True,weights_unchanged=True,source_triangles=len(triangles),runtime_tested=False)
 write(receipt,result);print('WRIST_SKIN_SAVED',job['key'],len(selected),flush=True);return result

def main(limit=100):
 commandlet='-run=' in u.SystemLibrary.get_command_line().lower()
 world=None if commandlet else u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
 if world:raise RuntimeError('End current play session before asset authoring')
 data=plan();count=0
 for job in data['jobs']:
  if (R/'Saved'/(job['key']+'.json')).exists():continue
  build(job);count+=1
  if count>=limit:break
 print('WRIST_BATCH',len(list((R/'Saved').glob('*.json'))),'/',len(data['jobs']),flush=True)

if __name__=='__main__':main()
