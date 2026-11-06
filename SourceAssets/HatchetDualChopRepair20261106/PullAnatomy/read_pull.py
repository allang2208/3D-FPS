"""Read the loaded third-person single/dual pull clips; no gameplay changes."""
import json,hashlib
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;TASK=P.parent;ROOT=TASK.parents[1]
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text('utf-8-sig'));A=u.AnimPoseExtensions
def pack(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
receipt={'pie_worlds':[w.get_path_name() for w in u.EditorLevelLibrary.get_pie_worlds(False)],'assets':{}}
for label,body in [('Jason',cfg),('Kaitlin',cfg['body_variants']['kaitlin'])]:
    src=json.loads((TASK/(label+'-source.json')).read_text());mesh=u.load_asset(body['body_mesh'])
    if body['body_mesh']!=src['mesh']:raise RuntimeError('Body mesh changed; refresh geometry first')
    data={k:src[k] for k in ('mesh','names','parents','reference')};data['clips']={};receipt['assets'][label]={}
    options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh;options.evaluation_type=u.AnimDataEvalType.SOURCE
    for role,key in [('Release','Kukri.Falcon.Release'),('DualRelease','Kukri.Falcon.DualRelease')]:
        clip=u.load_asset(body['clips'][key]);u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
        if not clip:raise RuntimeError(key)
        path=clip.get_path_name();frames=[]
        for f in range(round(clip.get_play_length()*60)+1):
            pose=A.get_anim_pose_at_time(clip,min(f/60,clip.get_play_length()),options)
            frames.append([pack(A.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in data['names']])
        data['clips'][role]=dict(path=path,frames=frames,length=clip.get_play_length())
        disk=ROOT/'Content'/(path.removeprefix('/Game/').split('.')[0]+'.uasset')
        receipt['assets'][label][role]=dict(path=path,sha256=hashlib.sha256(disk.read_bytes()).hexdigest())
    (P/(label+'-source.json')).write_text(json.dumps(data,separators=(',',':')),'utf8')
(P/'read-receipt.json').write_text(json.dumps(receipt,indent=2),'utf8')
print('Read current Jason/Kaitlin single and dual heavy release clips; gameplay unchanged.')
