"""Bake left-arm fit on copies of the current sword animation family.

All source keys/timing, the weapon, right hand and finger poses stay intact.
No gameplay run, render or regression is performed.
"""
import unreal as u,json,math
from pathlib import Path
P=Path(__file__).parent;OUT=P/'LongGripExport';OUT.mkdir(exist_ok=True)
D='/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations'
L=u.EditorAssetLibrary
mesh=u.load_asset('/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms')
component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
chain=['clavicle_l','upperarm_l','lowerarm_l','hand_l']
parents={n:str(component.get_parent_bone(n)) for n in chain}
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
inputs=[{'name':'WhirlwindV5','source':'/Game/Weapons/AzureRunesword20260913/A_RuneSword_WhirlwindV5'}]

def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def mul(a,s):return tuple(x*s for x in a)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def length(a):return math.sqrt(dot(a,a))
def unit(a):return mul(a,1/max(1e-12,length(a)))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def inverse(q):return (-q[0],-q[1],-q[2],q[3])
def qmul(a,b):return (*add(add(mul(b[:3],a[3]),mul(a[:3],b[3])),cross(a[:3],b[:3])),a[3]*b[3]-dot(a[:3],b[:3]))
def rotate(q,p):
    t=mul(cross(q[:3],p),2);return add(add(p,mul(t,q[3])),cross(q[:3],t))
def between(a,b):
    a,b=unit(a),unit(b);d=max(-1,min(1,dot(a,b)))
    if d>.999999999:return (0,0,0,1)
    if d<-.9999999:
        axis=cross(a,(1,0,0))
        if length(axis)<.001:axis=cross(a,(0,1,0))
        return (*unit(axis),0)
    return unit((*cross(a,b),1+d))
def unpack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return {'p':(p.x,p.y,p.z),'q':(q.x,q.y,q.z,q.w),'s':(s.x,s.y,s.z)}
def smooth(v):v=max(0,min(1,v));return v*v*(3-2*v)
def fit(points,goal):
    """Preserve all three segment lengths and start from the authored elbow bend."""
    pts=list(points);lengths=[length(sub(b,a)) for a,b in zip(pts,pts[1:])]
    # Prefer the two-arm-bone solve; clavicle only participates near full reach.
    shoulder=points[1];delta=sub(goal,shoulder);dist=length(delta)
    if abs(lengths[1]-lengths[2])+.001<dist<lengths[1]+lengths[2]-.001:
        axis=unit(delta);elbow=sub(points[2],shoulder);bend=sub(elbow,mul(axis,dot(elbow,axis)))
        if length(bend)<1e-6:bend=cross(axis,(0,0,1))
        along=(lengths[1]**2-lengths[2]**2+dist**2)/(2*dist)
        height=math.sqrt(max(0,lengths[1]**2-along**2))
        return [points[0],shoulder,add(add(shoulder,mul(axis,along)),mul(unit(bend),height)),goal]
    origin=points[0]
    if length(sub(goal,origin))>=sum(lengths)-.001:
        # Reduce only the extra long-grip offset rather than stretching an arm.
        lo,hi=0.,1.;offset=sub(goal,points[-1])
        for _ in range(24):
            f=(lo+hi)/2;candidate=add(points[-1],mul(offset,f))
            if length(sub(candidate,origin))<sum(lengths)-.001:lo=f
            else:hi=f
        goal=add(points[-1],mul(offset,lo))
    for _ in range(64):
        pts[-1]=goal
        for i in range(2,-1,-1):pts[i]=add(pts[i+1],mul(unit(sub(pts[i],pts[i+1])),lengths[i]))
        pts[0]=origin
        for i in range(1,4):pts[i]=add(pts[i-1],mul(unit(sub(pts[i],pts[i-1])),lengths[i-1]))
        if length(sub(pts[-1],goal))<.0001:break
    return pts

receipts=[]
for info in inputs:
    source=u.load_asset(info['source']);name='A_RuneSword_'+info['name'];target=D+'/'+name
    if L.does_asset_exist(target):raise RuntimeError('Output already exists; use a new revision before rebaking '+target)
    frames=u.AnimationLibrary.get_num_frames(source);seconds=source.get_play_length();rows=[]
    for frame in range(frames+1):
        t=frame*seconds/frames;pose=u.AnimPoseExtensions.get_anim_pose_at_time(source,t,options)
        local={n:unpack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in chain}
        world={n:unpack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in set(chain+list(parents.values()))}
        weapon=u.AnimPoseExtensions.get_bone_pose(pose,'WPN_root',u.AnimPoseSpaces.WORLD)
        relative=weapon.inverse_transform_location(u.Vector(*world['hand_l']['p']))
        radius=math.hypot(relative.x,relative.y)
        # The lower wrist sits at z=-0.173063m when gripping, rotating around
        # the handle during strikes. Blade-bracing and free-hand poses disengage.
        weight=(1-smooth((abs(relative.z+.173063)-.008)/.05))*(1-smooth((radius-.095)/.065))
        if weight>1e-7:
            w=unpack(weapon);delta=mul(rotate(w['q'],(0,0,-1)),1.8*weight)
            points=[world[n]['p'] for n in chain];fitted=fit(points,add(points[-1],delta))
            desired={}
            for i,n in enumerate(chain):
                desired[n]=unit(qmul(between(sub(points[i+1],points[i]),sub(fitted[i+1],fitted[i])),world[n]['q'])) if i<3 else world[n]['q']
                pq=desired.get(parents[n],world[parents[n]]['q'])
                q=unit(qmul(inverse(pq),desired[n]))
                if rows and dot(q,rows[-1]['bones'][n]['q'])<0:q=mul(q,-1)
                local[n]['q']=q
        rows.append({'seconds':t,'contact_weight':weight,'bones':local})
    (OUT/(name+'_editable_keys.json')).write_text(json.dumps({'source':info['source'],'intervals':frames,'seconds':seconds,'left_grip_shift_cm':1.8,'parents':parents,'samples':rows},separators=(',',':')))
    clip=L.duplicate_asset(info['source'],target)
    if not clip:raise RuntimeError('Failed to duplicate '+target)
    controller=clip.get_editor_property('controller')
    if controller is None:
        controller=u.AnimDataController();controller.set_model(clip.get_editor_property('data_model_interface'))
    controller.open_bracket('Fit long grip using original sword motion and hand contact',False)
    try:
        for n in chain:
            keys=[r['bones'][n] for r in rows]
            if not controller.set_bone_track_keys(n,[u.Vector(*k['p']) for k in keys],[u.Quat(*k['q']) for k in keys],[u.Vector(*k['s']) for k in keys],False):raise RuntimeError('Failed bone track '+n)
    finally:controller.close_bracket(False)
    clip.set_preview_skeletal_mesh(mesh)
    L.set_metadata_tag(clip,'FrostGrip.Source',info['source']);L.set_metadata_tag(clip,'FrostGrip.Revision','LongGrip20260919_18mm')
    if not L.save_loaded_asset(clip,False):raise RuntimeError('Failed to save '+target)
    task=u.AssetExportTask();task.object=clip;task.filename=str(OUT/(name+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True
    task.options=u.FbxExportOption();task.options.ascii=False
    exported=u.Exporter.run_asset_export_task(task)
    receipts.append({'source':info['source'],'asset':clip.get_path_name(),'seconds':seconds,'intervals':frames,'editable_fbx_exported':exported})
    (P/'long_grip_receipt.json').write_text(json.dumps(receipts,indent=2))
    u.log('LONG_GRIP_AUTHORED '+info['name'])
