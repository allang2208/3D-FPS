"""Read saved ST6 and native arm assets, never a live skinned component."""
import json,hashlib,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6SleeveRepair20261018';R.mkdir(parents=True,exist_ok=True);OUT=R/'Read';OUT.mkdir(exist_ok=True)
c=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'));recipe=c['items']['ue_st6_sleeves']
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
def xyz(v):return [v.x,v.y,v.z]
def read(path,key):
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing '+path)
    disk=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset');sha=hashlib.sha256(disk.read_bytes()).hexdigest();file=OUT/(key+'.json')
    if file.exists():
        old=json.loads(file.read_text())
        if old.get('asset_sha256')==sha and old['source']==path:return str(file)
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
    _,vs,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False);_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    d=dict(source=path,asset_sha256=sha,skeleton=mesh.skeleton.get_path_name(),positions=[xyz(v) for v in L.convert_vector_list_to_array(vs)],triangles=[xyz(f) for f in L.convert_triangle_list_to_array(fs)],weights=[],triangle_materials=[],normals=[],uv=[],materials=[s.material_interface.get_path_name() for s in mesh.materials],material_slots=[str(s.material_slot_name) for s in mesh.materials],bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones})
    for i in range(len(d['positions'])):
        _,ws,valid=B.get_vertex_bone_weights(dm,i)
        if not valid:raise RuntimeError('Missing native binding')
        d['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    for i in range(len(d['triangles'])):
        a,b,c,_=Q.get_triangle_u_vs(dm,0,i);_,na,nb,nc,_=Q.get_triangle_normals(dm,i)
        d['uv'].append([[v.x,v.y] for v in (a,b,c)]);d['normals'].append([xyz(v) for v in (na,nb,nc)]);d['triangle_materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
    file.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8');print('ST6_NATIVE_READ',key,len(d['triangles']),flush=True);return str(file)
inventory=[];cache={}
for profile,asset in recipe['rig_meshes'].items():
    if profile in ('Body','Jason'):continue
    entries=[(source,p) for source,p in c['profiles'].items() if p['rig_profile']==profile]
    skins=list(dict.fromkeys(p.get('native_bare_skin',p['base']) for _,p in entries))
    # Bow ContactV9 is the current accepted bow fit; the ArmsV4 alias remains
    # inventoried but must not select the older contact geometry as the master.
    skins.sort(key=lambda s:(0 if 'WristCoverage' in s else 1,0 if '3cced8ec73' in s else 1))
    # Retain every alias in the inventory. Bind-compatible alternative skins
    # are read too, so their wrist geometry is not silently assumed identical.
    files=[]
    for path in skins:
        if path not in cache:cache[path]=read(path,profile+'_'+hashlib.sha256(path.encode()).hexdigest()[:8]);gc.collect();u.SystemLibrary.collect_garbage()
        files.append(cache[path])
    inventory.append(dict(profile=profile,previous=asset,native=skins[0],file=files[0],native_variants=files,aliases=[s for s,_ in entries]))
read(recipe['rig_meshes']['RuneSword'],'Old_RuneSword_ST6')
(R/'before.json').write_text(json.dumps(dict(recipe=recipe,inventory=inventory),ensure_ascii=False,indent=2),encoding='utf-8');print('ST6_CAPTURE_COMPLETE',len(inventory),flush=True)
