"""Read full original lower equipment to restore a deep overlap inside the hem."""
import json,hashlib,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018/HemContinuity20261019';OUT=R/'Read';OUT.mkdir(parents=True,exist_ok=True)
c=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'));recipe=c['items']['ue_blue_mage_robe'];known={}
def add(path,profile,kind):
    if path:known[path]=(profile,kind)
for row in c['profiles'].values():
    if row.get('rig_profile') in ('Body','Jason'):add(row.get('native_bare_skin',row['base']),row['rig_profile'],'skin')
for item in c['items'].values():
    for profile in ('Body','Jason'):
        if item.get('slot') in (13,15):
            kind='shoes' if item['slot']==13 else 'pants';add(item.get('rig_meshes',{}).get(profile),profile,kind)
            for fits in item.get('shoe_fit_meshes',{}).values():add(fits.get(profile),profile,kind)
        if item.get('slot')==3:add(item.get('skin_meshes',{}).get(profile),profile,'skin')
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
def xyz(v):return [v.x,v.y,v.z]
rows=[]
for original,path in recipe['underlayer_meshes'].items():
    if not path:continue
    path=original
    if original not in known:raise RuntimeError('Unknown robe underlayer role '+original)
    profile,kind=known[original];key=profile+'_'+hashlib.sha256(path.encode()).hexdigest()[:12];file=OUT/(key+'.json');disk=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset');sha=hashlib.sha256(disk.read_bytes()).hexdigest()
    row=dict(original=original,source=path,profile=profile,kind=kind,key=key,file=str(file),asset_sha256=sha);rows.append(row)
    if file.exists() and json.loads(file.read_text()).get('asset_sha256')==sha:continue
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing saved source '+path)
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read source '+path)
    _,vs,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False);_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    d=dict(source=path,asset_sha256=sha,skeleton=mesh.skeleton.get_path_name(),positions=[xyz(v) for v in L.convert_vector_list_to_array(vs)],triangles=[xyz(f) for f in L.convert_triangle_list_to_array(fs)],weights=[],triangle_materials=[],normals=[],uv=[],materials=[s.material_interface.get_path_name() if s.material_interface else '' for s in mesh.materials],material_slots=[str(s.material_slot_name) for s in mesh.materials],bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones})
    for i in range(len(d['positions'])):
        _,weights,valid=B.get_vertex_bone_weights(dm,i)
        if not valid:raise RuntimeError('Source binding missing')
        d['weights'].append({names[w.bone_index]:w.weight for w in weights if w.weight>0})
    for i in range(len(d['triangles'])):
        a,b,cc,_=Q.get_triangle_u_vs(dm,0,i);_,na,nb,nc,_=Q.get_triangle_normals(dm,i)
        d['uv'].append([[v.x,v.y] for v in (a,b,cc)]);d['normals'].append([xyz(v) for v in (na,nb,nc)]);d['triangle_materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
    file.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8');print('ROBE_STAIR_SOURCE',key,kind,len(d['triangles']),flush=True)
    del d,dm,mesh;gc.collect();u.SystemLibrary.collect_garbage()
(R/'inputs.json').write_text(json.dumps(dict(rows=rows,underlayer_meshes=recipe['underlayer_meshes']),indent=2),encoding='utf-8');print('ROBE_STAIR_SOURCES_READY',len(rows),flush=True)
