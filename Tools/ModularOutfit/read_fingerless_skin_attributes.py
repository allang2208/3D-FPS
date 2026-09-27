import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2/ClearanceReview'
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils
def xyz(v):return [v.x,v.y,v.z]
for row in json.loads((R/'mesh-manifest.json').read_text()):
    name=row['profile'];path=R/(name+'_skin.json');d=json.loads(path.read_text())
    asset=u.load_asset(d['path']);dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS or dm.get_triangle_count()!=len(d['triangles']):raise RuntimeError('Source changed '+name)
    uv=[];normal=[];extra={f'uv{k}':[] for k in range(1,Q.get_num_uv_sets(dm))};colors=[]
    for i in range(len(d['triangles'])):
        a,b,c,ok=Q.get_triangle_u_vs(dm,0,i)
        if not ok:raise RuntimeError('No skin UV '+name)
        _,n0,n1,n2,ok=Q.get_triangle_normals(dm,i)
        if not ok:raise RuntimeError('No skin normals '+name)
        uv.append([[v.x,v.y] for v in (a,b,c)]);normal.append([xyz(v) for v in (n0,n1,n2)])
        for key,values in extra.items():
            a,b,c,ok=Q.get_triangle_u_vs(dm,int(key[2:]),i)
            if not ok:raise RuntimeError('Missing skin coordinate '+key+' '+name)
            values.append([[v.x,v.y] for v in (a,b,c)])
        _,a,b,c,ok=Q.get_triangle_vertex_colors(dm,i)
        colors.append([[v.r,v.g,v.b,v.a] for v in (a,b,c)] if ok else [[1,1,1,1]]*3)
    d['uv']=uv;d['normals']=normal;d.update(extra);d['colors']=colors
    d['materials']=[dict(name=str(s.material_slot_name),path=s.material_interface.get_path_name() if s.material_interface else '') for s in asset.get_editor_property('materials')]
    path.write_text(json.dumps(d,separators=(',',':')))
    print('FINGERLESS_SKIN_ATTRIBUTES',name,flush=True)
