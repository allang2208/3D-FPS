"""Authoring input: native UE reference bones and original arm surfaces, no FBX rebinding."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924')
OUT=ROOT/'NativeSkin';OUT.mkdir(exist_ok=True)
inputs=json.loads((ROOT/'inputs.json').read_text())
Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights;A=u.GeometryScript_AssetUtils
def xyz(v):return [v.x,v.y,v.z]
for key,entry in inputs.items():
    path=OUT/(key+'_source.json')
    if path.exists():continue
    asset=u.load_asset(entry['mesh'])
    dm,outcome=A.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot extract '+key)
    _,bones=B.get_all_bones_info(dm)
    bone_names={b.index:str(b.name) for b in bones}
    _,pos,_=Q.get_all_vertex_positions(dm,False)
    positions=u.GeometryScript_List.convert_vector_list_to_array(pos)
    _,tris,_=Q.get_all_triangle_indices(dm,False)
    triangles=u.GeometryScript_List.convert_triangle_list_to_array(tris)
    materials=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else ''} for s in asset.materials]
    armids=[i for i,s in enumerate(materials) if 'Manny' in s['slot']] if key!='Body' else list(range(len(materials)))
    faces=[];uv=[];mats=[]
    for i,t in enumerate(triangles):
        m,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
        if not valid or m not in armids:continue
        faces.append(xyz(t));mats.append(m)
        a,b,c,valid=Q.get_triangle_u_vs(dm,0,i)
        uv.append([[v.x,v.y] for v in (a,b,c)])
    ids=sorted({v for f in faces for v in f});remap={v:i for i,v in enumerate(ids)}
    weights=[]
    for i in ids:
        _,ws,valid=B.get_vertex_bone_weights(dm,i)
        if not valid:raise RuntimeError('Missing native skin binding: '+key)
        weights.append({bone_names[w.bone_index]:w.weight for w in ws if w.weight>0})
    result={'source':entry['mesh'],'materials':materials,'arm_materials':armids,
        'bones':{str(b.name):{'index':b.index,'parent':b.parent_index,'position':xyz(b.world_transform.translation),
          'axes':[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]} for b in bones},
        'positions':[xyz(positions[i]) for i in ids],'weights':weights,
        'triangles':[[remap[v] for v in f] for f in faces],'uv':uv,'triangle_materials':mats}
    path.write_text(json.dumps(result,separators=(',',':')))
    print('NATIVE_SKIN_SOURCE',key,len(ids),len(faces))
