"""Read-only saved mesh/LOD capture in a separate content-only commandlet host."""
import json,hashlib,gc,math,os
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/SetFitReview20261115';OUT=R/'Captured';OUT.mkdir(exist_ok=True)
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
def xyz(v):return [v.x,v.y,v.z]
def geometry(dm):
    _,vs,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False)
    _,mids,_=u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm)
    return dict(positions=[xyz(v) for v in L.convert_vector_list_to_array(vs)],triangles=[xyz(t) for t in L.convert_triangle_list_to_array(fs)],triangle_materials=list(L.convert_index_list_to_array(mids)))
plan=read(R/'plan.json');records=[]
for row in plan['rows']:
    file=OUT/(row['key']+'.json');current=sha(row['disk'])
    if current!=row['asset_sha256']:raise RuntimeError('Input changed during review: '+row['key'])
    if file.exists() and read(file).get('asset_sha256')==current:
        records.append(dict(key=row['key'],file=str(file)));continue
    a=u.load_asset(row['path'])
    if not a:raise RuntimeError('Missing saved asset '+row['path'])
    static=row['role']=='helmet';copy=G.copy_mesh_from_static_mesh if static else G.copy_mesh_from_skeletal_mesh
    result=dict(**row,materials=[x.material_interface.get_path_name() if x.material_interface else None for x in (a.static_materials if static else a.materials)],material_slots=[str(x.material_slot_name) for x in (a.static_materials if static else a.materials)],metadata={k:u.EditorAssetLibrary.get_metadata_tag(a,k) for k in ['CombatSourceSHA','TS01SourceSHA','HelmetHairSourceSHA','HelmetSourceSHA']},lods=[])
    for lod in range(3):
        dm,status=copy(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=lod))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:
            result['lods'].append(dict(lod=lod,error=str(status)));continue
        d=geometry(dm);d['lod']=lod;result['lods'].append(d)
    if not static:
        dm,status=copy(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Source model unavailable '+row['key'])
        d=geometry(dm);_,bs=B.get_all_bones_info(dm)
        d['bones']=[dict(name=str(x.name),index=x.index,parent=x.parent_index,position=xyz(x.world_transform.translation),axes=[xyz(x.world_transform.transform_location(v)-x.world_transform.translation) for v in [u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1)]]) for x in bs]
        d['weights']=[]
        for i in range(len(d['positions'])):
            _,ws,valid=B.get_vertex_bone_weights(dm,i)
            d['weights'].append([[w.bone_index,w.weight] for w in ws] if valid else [])
        # Only core meshes need per-corner data for the requested fit views.
        if row['role'] not in ['fp_shirt','fp_gloves']:
            d['uv']=[];d['normals']=[]
            for i in range(len(d['triangles'])):
                ua,ub,uc,_=Q.get_triangle_u_vs(dm,0,i);_,na,nb,nc,_=Q.get_triangle_normals(dm,i)
                d['uv'].append([[v.x,v.y] for v in [ua,ub,uc]]);d['normals'].append([xyz(v) for v in [na,nb,nc]])
        d['materials']=result['materials'];d['material_slots']=result['material_slots'];d['source']=row['path'];result['source_model']=d;result['skeleton']=a.skeleton.get_path_name() if a.skeleton else None
    file.write_text(json.dumps(result,separators=(',',':')),encoding='utf-8');records.append(dict(key=row['key'],file=str(file)))
    (R/'capture-progress.json').write_text(json.dumps(dict(rows=records,total=len(plan['rows']))),encoding='utf-8')
    print('SET_REVIEW_CAPTURED',len(records),len(plan['rows']),row['key'],flush=True)
    del a,dm,result;gc.collect();u.SystemLibrary.collect_garbage()
(R/'captured.json').write_text(json.dumps(dict(completed=True,rows=records,packages_saved=False,gameplay=False),indent=2),encoding='utf-8')
materials=[]
for name in ['CombatRipstop','CombatCarrier','CombatStretch','CombatCuff','CombatLining','CombatThread']:
    path='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3/Materials/M_'+name
    mat=u.load_asset(path);entry=dict(name=name,path=path,shading_model=str(mat.get_editor_property('shading_model')),two_sided=mat.get_editor_property('two_sided'),uses_attributes=mat.get_editor_property('use_material_attributes'),textures={})
    for channel in ['BaseColor','NormalGL','ORM']:
        tex=u.MaterialEditingLibrary.get_material_default_texture_parameter_value(mat,channel)
        entry['textures'][channel]=dict(path=tex.get_path_name(),srgb=tex.get_editor_property('srgb'),compression=str(tex.get_editor_property('compression_settings')),flip_green=tex.get_editor_property('flip_green_channel'),source_sha256=u.EditorAssetLibrary.get_metadata_tag(tex,'CombatTextureSHA')) if tex else None
    materials.append(entry)
(R/'materials-review.json').write_text(json.dumps(materials,indent=2),encoding='utf-8')
print('SET_REVIEW_CAPTURE_COMPLETE',len(records),flush=True)
