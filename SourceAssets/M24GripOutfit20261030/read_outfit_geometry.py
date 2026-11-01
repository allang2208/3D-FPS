import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent
config=json.loads((O.parents[1]/'Content/ColdSteelData/modular_outfits.json').read_text())
variant=config['body_variants']['kaitlin'];profile=variant['profiles']['/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9.SK_M24_MotionV9']
paths={'kaitlin_skin':profile['native_bare_skin']}
for item in ('ue_field_sweater','ue_field_gloves_black','ue_st6_sleeves'):
    paths[item]=variant['items'][item]['rig_meshes']['M4']
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
def xyz(v):return [v.x,v.y,v.z]
def tr(t):
    p,q,s=t.translation,t.rotation,t.scale3d;return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
manifest={}
for name,path in paths.items():
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing registered outfit '+path)
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh read '+path)
    _,ps,_=Q.get_all_vertex_positions(dm,False);ps=list(u.GeometryScript_List.convert_vector_list_to_array(ps))
    _,ts,_=Q.get_all_triangle_indices(dm,False);ts=list(u.GeometryScript_List.convert_triangle_list_to_array(ts))
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones};weights={}
    for i in range(len(ps)):
        _,ws,ok=B.get_vertex_bone_weights(dm,i);weights[i]={names[w.bone_index]:w.weight for w in ws if w.weight>0} if ok else {}
    faces=[]
    for i,t in enumerate(ts):
        mat,ok=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
        faces.append({'vertices':[int(x) for x in xyz(t)],'material':mat})
    result={'path':path,'positions':[xyz(p) for p in ps],'faces':faces,'weights':weights,'rest':{str(b.name):tr(b.world_transform) for b in bones},'materials':[str(m.material_slot_name) for m in mesh.materials]}
    (O/(name+'_geometry.json')).write_text(json.dumps(result));manifest[name]={'path':path,'vertices':len(ps),'faces':len(faces)}
(O/'outfit_geometry_manifest.json').write_text(json.dumps(manifest,indent=2));print('M24_OUTFIT_GEOMETRY',json.dumps(manifest),flush=True)
