"""Read only the active ranger shirt's native body geometry."""
import gc, hashlib, json, shutil, sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020'
R.mkdir(parents=True,exist_ok=True)
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def xyz(v):return [v.x,v.y,v.z]
def capture(path,file):
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing shirt source '+path)
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read shirt '+path)
    _,vs,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False);_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    d=dict(source=path,binding_source=path,skeleton=mesh.skeleton.get_path_name(),positions=[xyz(v) for v in L.convert_vector_list_to_array(vs)],triangles=[xyz(f) for f in L.convert_triangle_list_to_array(fs)],weights=[],triangle_materials=[],normals=[],uv=[],material_slots=[str(s.material_slot_name) for s in mesh.materials],bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones})
    for i in range(len(d['positions'])):
        _,ws,valid=B.get_vertex_bone_weights(dm,i)
        if not valid:raise RuntimeError('Missing shirt native weights')
        d['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    for i in range(len(d['triangles'])):
        a,b,c,_=Q.get_triangle_u_vs(dm,0,i);_,na,nb,nc,_=Q.get_triangle_normals(dm,i)
        d['uv'].append([[v.x,v.y] for v in (a,b,c)]);d['normals'].append([xyz(v) for v in (na,nb,nc)]);d['triangle_materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
    write(file,d);print('RANGER_SOURCE',file.stem,len(d['triangles']),flush=True)
cfg=read(P/'Content/ColdSteelData/modular_outfits.json');recipe=cfg['items']['ue_field_sweater']
for name in ('modular_outfits.json','items.json'):
    target=R/'Before'/name;target.parent.mkdir(exist_ok=True)
    if not target.exists():shutil.copy2(P/'Content/ColdSteelData'/name,target)
saved=read(P/'SourceAssets/GarmentSleeveRepair20261018/saved_assets.json')['saved'];rows=[]
for profile,asset in recipe['rig_meshes'].items():
    group='World' if profile in ('Body','Jason') else 'FP'
    if group=='FP':
        file=P/'SourceAssets/GarmentSleeveRepair20261018/Authored/ue_field_sweater'/(profile+'.json')
        record=saved['ue_field_sweater/'+profile]
        if record['asset']!=asset or hashlib.sha256(file.read_bytes()).hexdigest()!=record['author_sha256']:
            raise RuntimeError('Current sleeve differs from its author source '+profile)
    else:
        file=R/'Sources'/(profile+'.json');capture(asset,file)
    rows.append(dict(profile=profile,group=group,source=asset,file=str(file)))
    gc.collect();u.SystemLibrary.collect_garbage()
for profile,asset in recipe.get('owner_body_meshes',{}).items():
    file=R/'Sources'/('Owner_'+profile+'.json');capture(asset,file)
    rows.append(dict(profile='Owner_'+profile,group='Owner',source=asset,file=str(file)))
write(R/'inputs.json',dict(item='ue_field_sweater',recipe=recipe,rows=rows,
    aliases={k:v['rig_profile'] for k,v in cfg['profiles'].items()},concept='Design/FieldRangerTop_Concept01.png',
    approved=True,runtime_tested=False))
print('RANGER_INPUTS_COMPLETE',len(rows),flush=True)
