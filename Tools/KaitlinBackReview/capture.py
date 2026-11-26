"""Read current female upper-back geometry; never alter the active world."""
import json, hashlib, struct, gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME'); R=P/'SourceAssets/KaitlinBackReview20261117'
(R/'BackViews').mkdir(exist_ok=True)
manifest=json.loads((R/'manifest.json').read_text())
assets=[a for a in manifest['assets'] if any('pants_underlayer' not in x['route'] for x in a['routes'])]
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))['body_variants']['kaitlin']
assets.append(dict(path=cfg['body_mesh'],routes=[dict(item='native_body',route='base_body')],base=True))
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;M=u.GeometryScript_Materials
ss=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
editor_world=u.get_editor_subsystem(u.UnrealEditorSubsystem)
report={'pie_active':bool(editor_world and editor_world.get_game_world()),'assets':[]}
for k,a in enumerate(assets):
    mesh=u.load_asset(a['path'])
    if not mesh:raise RuntimeError('Missing referenced mesh '+a['path'])
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+a['path'])
    _,points,_=Q.get_all_vertex_positions(dm,False);points=[[v.x,v.y,v.z] for v in L.convert_vector_list_to_array(points)]
    _,triangles,_=Q.get_all_triangle_indices(dm,False);triangles=[[v.x,v.y,v.z] for v in L.convert_triangle_list_to_array(triangles)]
    _,ids,_=M.get_all_triangle_material_i_ds(dm);ids=list(L.convert_index_list_to_array(ids))
    slots=[str(m.material_slot_name) for m in mesh.materials]
    selected={i for i,(x,y,z) in enumerate(points) if -29<x<29 and y<1 and 112<z<150}
    faces=[i for i,t in enumerate(triangles) if all(v in selected for v in t)]
    used=sorted({v for i in faces for v in triangles[i]})
    values=sorted(set(tuple(round(c,4) for c in points[v]) for v in used))
    signature=hashlib.sha256(b''.join(struct.pack('<3f',*v) for v in values)).hexdigest()
    hood=slots.index('RobeHood') if 'RobeHood' in slots else None
    row=dict(path=a['path'],routes=a['routes'],back_geometry_sha256=signature,back_vertices=len(used),back_triangles=len(faces),material_slots=slots,hood_triangle_count=ids.count(hood) if hood is not None else 0,lods=ss.get_lod_count(mesh),cloth_assets=[x.get_path_name() for x in mesh.mesh_clothing_assets])
    if a['base']:
        remap={v:i for i,v in enumerate(used)}
        view=dict(path=a['path'],positions=[points[v] for v in used],triangles=[[remap[v] for v in triangles[i]] for i in faces],triangle_materials=[ids[i] for i in faces],materials=slots)
        filename=a['routes'][0]['item']+('_owner' if 'owner' in a['routes'][0]['route'] else '_world')+'.json'
        (R/'BackViews'/filename).write_text(json.dumps(view,separators=(',',':')),encoding='utf-8')
        row['back_view']=filename
    report['assets'].append(row)
    if k%15==0:print('KAITLIN_BACK_CAPTURE',k+1,len(assets),flush=True)
    del mesh,dm,points,triangles;gc.collect()
(R/'captured.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('KAITLIN_BACK_CAPTURED',len(report['assets']),'hood meshes',sum(a['hood_triangle_count']>0 for a in report['assets']),'PIE',report['pie_active'],flush=True)
