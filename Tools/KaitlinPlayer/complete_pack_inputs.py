"""Capture current native pack masks and jacket surfaces for a new fitting revision."""
import gc,hashlib,json
from pathlib import Path
import unreal as u
def main():
    P=Path('D:/FPS3D/FPSGAME');W=P/'SourceAssets/KaitlinCompletion20261024';O=W/'Packs';O.mkdir(exist_ok=True)
    read=lambda p:json.loads(p.read_text('utf-8-sig'))
    body=read(W/'body_before.json');modular=read(W/'modular_before.json')
    sources={};rigs={}
    def add(path,kind):
        if path:sources[path]=kind
    def garments(obj,rig,out):
        if isinstance(obj,dict):
            if 'rig_meshes' in obj and rig in obj['rig_meshes']:out.add(obj['rig_meshes'][rig])
            for k,v in obj.items():
                if k not in ('owner_body_meshes','underlayer_meshes','base_material_overrides'):garments(v,rig,out)
        elif isinstance(obj,list):
            for v in obj:garments(v,rig,out)
    for rig,key in [('Jason','jason'),('Kaitlin','kaitlin')]:
        b=body if key=='jason' else body['body_variants'][key];m=modular if key=='jason' else modular['body_variants'][key]
        shirt=m['items']['ue_work_jacket'];paths=set();garments(shirt,rig,paths)
        rigs[rig]={'body':b['body_mesh'],'shirts':sorted(paths),'packs':b['outfits']}
        add(b['body_mesh'],'body')
        for path in paths:add(path,'garment')
        for recipe in b['outfits'].values():
            add(recipe['world_mesh'],'pack')
            if 'rigid_pack' in recipe:add(recipe['rigid_pack']['mesh'],'static')
    index_path=O/'inputs.json';index=read(index_path) if index_path.exists() else {}
    G,Q,L,B=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List,u.GeometryScript_BoneWeights
    xyz=lambda v:[v.x,v.y,v.z]
    count=0
    for path,kind in sources.items():
        package=P/'Content'/(path[6:].split('.')[0]+'.uasset');digest=hashlib.sha256(package.read_bytes()).hexdigest()
        if path in index:
            if index[path]['sha256']!=digest:raise RuntimeError('Production source changed: '+path)
            continue
        asset=u.load_asset(path)
        copier=G.copy_mesh_from_static_mesh if kind=='static' else G.copy_mesh_from_skeletal_mesh
        dm,status=copier(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot capture '+path)
        _,points,_=Q.get_all_vertex_positions(dm,False);points=L.convert_vector_list_to_array(points)
        data={'source':path,'sha256':digest,'kind':kind,'positions':[xyz(v) for v in points]}
        if kind=='static':data['positions']=data['positions'][::max(1,len(points)//80000)]
        if kind in ('body','garment'):
            _,bones=B.get_all_bones_info(dm)
            data['bones']=[{'name':str(b.name),'index':b.index,'parent':b.parent_index,'position':xyz(b.world_transform.translation),
                           'axes':[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]} for b in bones]
            data['weights']=[]
            for i in range(len(points)):
                _,weights,valid=B.get_vertex_bone_weights(dm,i)
                if not valid:raise RuntimeError('Missing weight '+path)
                data['weights'].append([[w.bone_index,w.weight] for w in weights if w.weight>0])
            _,faces,_=Q.get_all_triangle_indices(dm,False);faces=L.convert_triangle_list_to_array(faces)
            data['triangles']=[xyz(t) for t in faces]
            data['triangle_materials']=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(faces))]
            data['materials']=[{'slot':str(m.material_slot_name),'asset':m.material_interface.get_path_name() if m.material_interface else ''} for m in asset.materials]
        if kind=='pack':
            _,colors,valid,gaps=u.GeometryScript_VertexColors.get_mesh_per_vertex_colors(dm,False)
            if not valid or gaps:raise RuntimeError('Missing sewn motion mask '+path)
            data['mask']=[c.r for c in L.convert_color_list_to_array(colors)]
        filename=hashlib.sha256(path.encode()).hexdigest()[:16]+'.json'
        (O/filename).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
        index[path]={'file':filename,'sha256':digest,'kind':kind}
        index_path.write_text(json.dumps(index,indent=2),encoding='utf-8')
        print('JACKET_PACK_INPUT',kind,path,flush=True)
        # Release reflected array views before the mesh/package can be collected.
        # Four captures per process bound memory without forcing UE GC mid-read.
        bones=faces=colors=weights=None
        del dm,asset,points,data;gc.collect()
        count+=1
        if count>=4:break
    (O/'rigs.json').write_text(json.dumps(rigs,indent=2),encoding='utf-8')
    remaining=sum(path not in index for path in sources)
    (P/'SourceAssets/KaitlinPlayer20261023/complete_pack_inputs_status.json').write_text(json.dumps({'remaining':remaining,'complete':remaining==0}))
    print('JACKET_PACK_INPUTS_REMAINING',remaining,flush=True)

main()
