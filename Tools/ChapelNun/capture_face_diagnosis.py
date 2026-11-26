"""Read current saved source/render LODs and material settings without changing assets."""
import unreal as u,json
from pathlib import Path
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');O=globals().get('OUTPUT_DIR',N/'FaceDiagnosisR1');O.mkdir(parents=True,exist_ok=True)
path='/Game/Characters/ChapelNun20261115/RefinementR4/Meshes/SK_Nun_OriginalMeshyFace_Final';mesh=u.load_asset(path)
if not mesh:raise RuntimeError(path)
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;B=u.GeometryScript_BoneWeights;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
xyz=lambda p:[p.x,p.y,p.z]
report={'asset':mesh.get_path_name(),'materials':[m.material_interface.get_path_name() for m in mesh.materials],'lod_count':S.get_lod_count(mesh),'lods':[],'textures':{},'region':'Full anterior lower face including chin; abs(x)<5.5, z>142.5 and z<153.2, y>4.0 cm'}
for label,lod,kind in [('source',0,u.GeometryScriptLODType.SOURCE_MODEL)]+[('render',i,u.GeometryScriptLODType.RENDER_DATA) for i in range(S.get_lod_count(mesh))]:
 read=u.GeometryScriptMeshReadLOD(lod_type=kind,lod_index=lod);dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),read)
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read '+label+str(lod))
 _,ps,_=Q.get_all_vertex_positions(dm,False);_,ts,_=Q.get_all_triangle_indices(dm,False)
 ps=[xyz(p) for p in L.convert_vector_list_to_array(ps)];ts=[xyz(t) for t in L.convert_triangle_list_to_array(ts)]
 selected=[];ids=set()
 for i,t in enumerate(ts):
  c=[sum(ps[v][k] for v in t)/3 for k in range(3)]
  if abs(c[0])<5.5 and 142.5<c[2]<153.2 and c[1]>4.0:selected.append((i,t));ids.update(t)
 remap={v:i for i,v in enumerate(sorted(ids))};out={'positions':[ps[v] for v in sorted(ids)],'triangles':[],'uv':[],'normals':[],'material_ids':[],'weights':[]}
 for i,t in selected:
  a,b,c,_=Q.get_triangle_u_vs(dm,0,i);_,na,nb,nc,_=Q.get_triangle_normals(dm,i)
  out['triangles'].append([remap[v] for v in t]);out['uv'].append([[x.x,x.y] for x in (a,b,c)]);out['normals'].append([xyz(n) for n in (na,nb,nc)]);out['material_ids'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
 if label=='source':
  for v in sorted(ids):
   _,weights,valid=B.get_vertex_bone_weights(dm,v);out['weights'].append([[w.bone_index,w.weight] for w in weights])
  _,bones=B.get_all_bones_info(dm);out['bones']=[{'index':b.index,'name':str(b.name)} for b in bones]
 (O/(label+'_lod'+str(lod)+'_lowerface.json')).write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
 build=S.get_lod_build_settings(mesh,lod)
 report['lods'].append({'type':label,'lod':lod,'vertices':len(ps),'triangles':len(ts),'lowerface_triangles':len(selected),'build':build.export_text(),'sections':[{'section':s,'material_slot':S.get_lod_material_slot(mesh,lod,s)} for s in range(S.get_num_sections(mesh,lod))]})
 print('FACE_READBACK',label,lod,len(ts),len(selected),flush=True)
for channel in ('base_color','metallic_roughness','normal'):
 tex=u.load_asset('/Game/Characters/ChapelNun20261115/OriginalMeshyFaceR3/Textures/T_NunOriginal_'+channel)
 report['textures'][channel]={k:str(tex.get_editor_property(k)) for k in ('srgb','compression_settings','flip_green_channel','lod_bias','max_texture_size','lod_group')}
 report['textures'][channel]['path']=tex.get_path_name()
mat=u.load_asset(report['materials'][0]);report['material_settings']={k:str(mat.get_editor_property(k)) for k in ('two_sided','shading_model','blend_mode','tangent_space_normal')}
(O/'engine_readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FACE_DIAGNOSIS_CAPTURED',flush=True)
