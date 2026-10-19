"""Read all other active FP shirts and native inputs; no live-component conversion."""
import json,hashlib,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentSleeveRepair20261018';R.mkdir(parents=True,exist_ok=True)
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
def xyz(v):return [v.x,v.y,v.z]
def asset_file(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def read(path,file):
    sha=hashlib.sha256(asset_file(path).read_bytes()).hexdigest()
    if file.exists():
        old=json.loads(file.read_text(encoding='utf-8'))
        if old.get('asset_sha256')==sha and old['source']==path:return str(file)
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing '+path)
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
    _,vs,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False);_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    d=dict(source=path,asset_sha256=sha,skeleton=mesh.skeleton.get_path_name(),positions=[xyz(v) for v in L.convert_vector_list_to_array(vs)],triangles=[xyz(f) for f in L.convert_triangle_list_to_array(fs)],weights=[],triangle_materials=[],normals=[],uv=[],colors=[],materials=[s.material_interface.get_path_name() for s in mesh.materials],material_slots=[str(s.material_slot_name) for s in mesh.materials],bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones})
    for i in range(len(d['positions'])):
        _,ws,valid=B.get_vertex_bone_weights(dm,i)
        if not valid:raise RuntimeError('Missing native weights')
        d['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    has_color=Q.get_has_vertex_colors(dm)
    for i in range(len(d['triangles'])):
        a,b,c,_=Q.get_triangle_u_vs(dm,0,i);_,na,nb,nc,_=Q.get_triangle_normals(dm,i);d['uv'].append([[v.x,v.y] for v in (a,b,c)]);d['normals'].append([xyz(v) for v in (na,nb,nc)]);d['triangle_materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
        if has_color:
            _,a,b,c,valid=Q.get_triangle_vertex_colors(dm,i)
            d['colors'].append([[v.r,v.g,v.b,v.a] for v in (a,b,c)])
    d['lod_count']=S.get_lod_count(mesh);d['lod_policy']=[dict(ratio=m.get_editor_property('reduction_settings').get_editor_property('num_of_triangles_percentage'),welding_threshold=m.get_editor_property('reduction_settings').get_editor_property('welding_threshold'),max_bones=m.get_editor_property('reduction_settings').get_editor_property('max_bones_per_vertex')) for m in mesh.get_editor_property('source_models')]
    file.parent.mkdir(parents=True,exist_ok=True);file.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8');print('GARMENT_SOURCE_READ',file.stem,len(d['triangles']),flush=True);return str(file)
c=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'));items={k:v for k,v in c['items'].items() if v.get('slot')==7 and k!='ue_st6_sleeves'};native_rows=json.loads((P/'SourceAssets/ST6SleeveRepair20261018/before.json').read_text(encoding='utf-8'))['inventory'];native_by={r['profile']:r for r in native_rows};rows=[]
for item,recipe in items.items():
    for profile,asset in recipe['rig_meshes'].items():
        if profile in ('Body','Jason'):continue
        old=native_by[profile];native_file=Path(old['file']);native=json.loads(native_file.read_text(encoding='utf-8'))
        if hashlib.sha256(asset_file(native['source']).read_bytes()).hexdigest()!=native['asset_sha256']:
            native_file=Path(read(native['source'],R/'Native'/(profile+'.json')))
        file=read(asset,R/'Before'/item/(profile+'.json'));rows.append(dict(item=item,profile=profile,asset=asset,file=file,native_file=str(native_file),aliases=old['aliases'],covers=recipe.get('covers')))
        gc.collect();u.SystemLibrary.collect_garbage()
(R/'inventory.json').write_text(json.dumps(dict(recipes=items,rows=rows),ensure_ascii=False,indent=2),encoding='utf-8');print('GARMENT_INVENTORY_CAPTURED',len(rows),flush=True)
