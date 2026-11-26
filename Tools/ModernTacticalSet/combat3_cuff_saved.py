"""Read the reported cuff region from saved render LODs, never gameplay poses."""
import math,json,hashlib
from pathlib import Path
import unreal as u
C=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1')
def inspect(asset,d,source_sha256):
    glove=bool(d.get('wrist_strap_fit'))
    bones={b['name']:b for b in d['bones']};frames={}
    for side in ['l','r']:
        w=bones['hand_'+side]['position'];e=bones['lowerarm_'+side]['position'];axis=[x-y for x,y in zip(w,e)];length=math.sqrt(sum(x*x for x in axis));cut=d.get('cloth_production',{}).get('contact',{}).get(side,{}).get('cut_cm',0.);frames[side]=(w,[x/length for x in axis],max(3.9,cut+1.5))
    def region(p):
        for side,(w,axis,end) in frames.items():
            delta=[x-y for x,y in zip(p,w)];dist=-sum(x*y for x,y in zip(delta,axis));radial=sum(x*x for x in delta)-dist*dist
            if -.5<dist<end and radial<49:return side
        return None
    grid={}
    for p in d['positions']:
        if region(p):grid.setdefault(tuple(math.floor(x/.05) for x in p),[]).append(p)
    report=[];G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
    for lod in range(3):
        dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=lod))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read actual cuff LOD '+str(lod))
        _,ps,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(ps);counts={};worst=0.;finger=0.
        for i,v in enumerate(ps):
            p=[v.x,v.y,v.z];side=region(p)
            if side is None:continue
            cell=tuple(math.floor(x/.05) for x in p);nearest=float('inf')
            for a in [-1,0,1]:
                for b in [-1,0,1]:
                    for c in [-1,0,1]:
                        for q in grid.get((cell[0]+a,cell[1]+b,cell[2]+c),[]):nearest=min(nearest,sum((x-y)**2 for x,y in zip(p,q)))
            worst=max(worst,math.sqrt(nearest));counts[side]=counts.get(side,0)+1
        # UE's render-data conversion omits skin weights/bone attributes. Read
        # saved source weights separately; do not label them render weights.
        source,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read saved cuff source LOD 0')
        _,bs=B.get_all_bones_info(source);names={b.index:str(b.name) for b in bs}
        _,source_ps,_=Q.get_all_vertex_positions(source,False);source_ps=u.GeometryScript_List.convert_vector_list_to_array(source_ps);strap_vertices=set();weight_counts={}
        if glove:
            _,tris,_=Q.get_all_triangle_indices(source,False);tris=u.GeometryScript_List.convert_triangle_list_to_array(tris);_,material_ids,has_ids=u.GeometryScript_Materials.get_all_triangle_material_i_ds(source);material_ids=u.GeometryScript_List.convert_index_list_to_array(material_ids);webbing={i for i,name in enumerate(d['material_slots']) if 'Webbing' in name}
            if not has_ids:raise RuntimeError('Saved cuff source has no material IDs')
            for tri,mat in zip(tris,material_ids):
                if mat in webbing:strap_vertices.update([tri.x,tri.y,tri.z])
        for i,v in enumerate(source_ps):
            side=region([v.x,v.y,v.z])
            if side is None:continue
            _,ws,valid=B.get_vertex_bone_weights(source,i)
            if not valid:raise RuntimeError('Missing saved cuff weights')
            weight_counts[side]=weight_counts.get(side,0)+1
            if not glove or i in strap_vertices:finger=max(finger,sum(w.weight for w in ws if names[w.bone_index].startswith(('thumb','index','middle','ring','pinky'))))
        if not counts or not weight_counts or worst>.02 or finger>1e-5:raise RuntimeError('Saved cuff changed in LOD '+str(lod)+': '+str((counts,worst,finger)))
        report.append(dict(lod=lod,cuff_vertices=counts,max_source_distance_cm=worst,max_finger_weight=finger,render_data=True,weight_data='saved_source_model',weight_lod=0,weight_vertices=weight_counts,render_weights_read=False))
    key=hashlib.sha256(asset.get_path_name().encode()).hexdigest()[:12];out=C/'Review/Saved';out.mkdir(exist_ok=True)
    (out/(key+'.json')).write_text(json.dumps(dict(asset=asset.get_path_name(),source_sha256=source_sha256,lods=report,gameplay_tested=False),indent=2),encoding='utf-8')
