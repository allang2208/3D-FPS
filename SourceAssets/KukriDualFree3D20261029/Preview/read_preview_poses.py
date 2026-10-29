"""Read the two currently routed saved Jason clips for the requested preview."""
import json
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
source=json.loads((OUT.parent/'jason-actions.json').read_text())
mesh=u.load_asset(cfg['body_mesh'])
opts=u.AnimPoseEvaluationOptions()
opts.optional_skeletal_mesh=mesh
opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
result={'body':'jason','body_mesh':cfg['body_mesh'],'names':source['names'],'clips':{}}
for role in ('Dual.Slash1','Dual.Slash2'):
    path=cfg['clips']['Kukri.FullBody.'+role]
    if '/DualFree3D20261029/' not in path:
        raise RuntimeError('Current route changed: '+path)
    clip=u.load_asset(path)
    duration=(len(source['clips'][role]['frames'])-1)/120.
    times=[i/20 for i in range(int(duration*20)+1)]
    if duration-times[-1]>.0001: times.append(duration)
    frames=[]
    for time in times:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opts)
        frame=[]
        for name in source['names']:
            t=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.LOCAL)
            frame.append([t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z])
        frames.append(frame)
    result['clips'][role]={'asset':path,'duration':duration,'times':times,'frames':frames}
    print('PREVIEW_READ',role,len(frames),path)
(OUT/'saved-poses.json').write_text(json.dumps(result,separators=(',',':')))

# Read the actual head weights to avoid a rigid neck/chest seam in the preview.
path=cfg['heads']['jason']['mesh'];asset=u.load_asset(path)
G,Q,L,B=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List,u.GeometryScript_BoneWeights
dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read head')
vec=lambda v:[v.x,v.y,v.z]
_,points,_=Q.get_all_vertex_positions(dm,False)
_,faces,_=Q.get_all_triangle_indices(dm,False)
_,bones=B.get_all_bones_info(dm)
head={'source':path,'positions':[vec(v) for v in L.convert_vector_list_to_array(points)],'triangles':[vec(t) for t in L.convert_triangle_list_to_array(faces)],'bones':[{'name':str(b.name),'parent':b.parent_index} for b in bones],'reference':{str(b.name):vec(b.world_transform.translation)+[getattr(b.world_transform.rotation,c) for c in 'xyzw']+vec(b.world_transform.scale3d) for b in bones},'weights':[]}
for i in range(len(head['positions'])):
    _,pairs,valid=B.get_vertex_bone_weights(dm,i)
    if not valid:raise RuntimeError('Missing head weights')
    head['weights'].append([[w.bone_index,w.weight] for w in pairs if w.weight>0])
(OUT/'head-weighted.json').write_text(json.dumps(head,separators=(',',':')))
print('PREVIEW_HEAD_CAPTURED',len(head['positions']))
