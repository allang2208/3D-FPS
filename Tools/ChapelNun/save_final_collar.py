"""Write the final collar envelope into the asset already used by the NPC."""
from pathlib import Path
base=Path('D:/FPS3D/FPSGAME/Tools/ChapelNun/save_assets.py').read_text(encoding='utf-8-sig')
exec(compile(base.split('E.make_directory(DEST)')[0],'<nun helpers>','exec'))
R=P/'SourceAssets/ChapelNun20261115/RefinementR4';O=R/'Authored';DEST='/Game/Characters/ChapelNun20261115/RefinementR4'
surface_file=globals().get('SURFACE_FILE','trim.json');surface_name=globals().get('SURFACE_NAME','SK_Nun_CollarCross_Final')
d=read(O/surface_file);source=load(d['binding_source']);mesh=load(DEST+'/Meshes/'+surface_name)
ref,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read binding source')
ps=[];ns=[];uvs=[];ws=[];faces=[];lookup={}
for fi,t in enumerate(d['triangles']):
 tri=[]
 for ci,vi in enumerate(t):
  n=d['normals'][fi][ci];uv=d['uv'][fi][ci];key=(vi,*[round(v,6) for v in n+uv])
  if key not in lookup:
   lookup[key]=len(ps);ps.append(u.Vector(*d['positions'][vi]));ns.append(u.Vector(*n));uvs.append(u.Vector2D(*uv));ws.append(d['weights'][vi])
  tri.append(lookup[key])
 faces.append(u.IntVector(*tri))
dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=ps,normals=ns,uv0=uvs,triangles=faces),0,True)
B.copy_bones_from_mesh(ref,dm);B.mesh_create_bone_weights(dm)
for i,weights in enumerate(ws):B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=int(b),weight=float(w)) for b,w in weights])
for i,mi in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,mi,True)
mats=[load('/Game/Characters/ChapelNun20261115/Materials/'+name) for name in ('M_Nun_IvoryLinen','M_Nun_BlackWool','M_Nun_WornIron')]
if 'SURFACE_MATS' in globals():mats=[load(path) for path in SURFACE_MATS]
opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write final collar')
ss=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
build=ss.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True);ss.set_lod_build_settings(mesh,0,build)
u.FPSModularOutfitComponent.configure_outfit_lods(mesh)
if not ss.regenerate_lod(mesh,3,True,False):raise RuntimeError('Cannot generate collar LODs')
if surface_file=='head.json':
 for lod in range(ss.get_lod_count(mesh)):
  for section in range(ss.get_num_sections(mesh,lod)):
   if ss.get_lod_material_slot(mesh,lod,section)==2:ss.set_section_cast_shadow(mesh,lod,section,False)
save(mesh)
import hashlib
receipt={'asset':mesh.get_path_name(),'saved':True,'source_sha256':hashlib.sha256((O/surface_file).read_bytes()).hexdigest(),'source_triangles':len(d['triangles']),'lod_count':ss.get_lod_count(mesh)}
if surface_file=='trim.json':receipt['geometry_check']=read(R/'collar_geometry_final.json')
(R/({'head.json':'final_head_saved.json','trim.json':'final_collar_saved.json','boots.json':'final_boots_saved.json'}[surface_file])).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('FINAL_SURFACE_SAVED',json.dumps(receipt),flush=True)
