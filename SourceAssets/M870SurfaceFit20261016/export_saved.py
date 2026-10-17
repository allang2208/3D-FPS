"""Read saved native bind/skin and outfit, without touching PIE or assets."""
import unreal as u,json,gzip
from pathlib import Path
O=Path(__file__).parent
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
def xyz(v):return [v.x,v.y,v.z]
def tr(t):return [*xyz(t.translation),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*xyz(t.scale3d)]
targets={'m870':'/Game/Weapons/M870/Tactical20261015/SK_M870_V7','native_arms':'/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90/SK_Super90_BareArmsV7','shirt':'/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90/SK_Super90_ue_chainmail_shirt'}
for key,path in targets.items():
 mesh=u.load_asset(path);assert mesh,path
 dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());assert status==u.GeometryScriptOutcomePins.SUCCESS
 _,pv,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(pv)
 _,tv,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(tv)
 _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
 d={'path':path,'vertices':[xyz(p) for p in ps],'faces':[xyz(t) for t in ts],'rest':{str(b.name):tr(b.world_transform) for b in bones},'parents':{str(b.name):names.get(b.parent_index) for b in bones},'weights':[],'materials':[],'uv':[],'slots':[str(s.material_slot_name) for s in mesh.materials]}
 for vi in range(len(ps)):
  _,ws,ok=B.get_vertex_bone_weights(dm,vi);assert ok;d['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
 for ti in range(len(ts)):
  d['materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0]);vs=Q.get_triangle_u_vs(dm,0,ti);d['uv'].append([[v.x,v.y] for v in vs[:3]])
 with gzip.open(O/(key+'.json.gz'),'wt') as f:json.dump(d,f,separators=(',',':'))
 print('NATIVE_SURFACE_EXPORTED',key,len(ps),len(ts))
print('SAVED_SURFACE_COMPLETE')
