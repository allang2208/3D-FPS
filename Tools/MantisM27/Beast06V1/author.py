"""Fit native Beast06 motion to M27 guard, exact limb lengths and rigid scythes."""
from pathlib import Path
import json, math
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27'); ROOT=BASE/'Beast06V1'
OUT=ROOT/'Delivery'; OUT.mkdir(parents=True,exist_ok=True)
DATA=json.loads((ROOT/'native_poses.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(BASE/'ClawV14/Delivery/MantisM27_ClawV14.blend'))
scene=bpy.context.scene; scene.render.fps=FPS=60; scene.render.fps_base=1.
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for tr in rig.animation_data.nla_tracks: tr.mute=True
names=[b.name for b in rig.data.bones]; parent={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
rig.animation_data.action=bpy.data.actions['A_M27_LeftSlash_ClawV14']
if rig.animation_data.action.slots: rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(1)
guard={n:rig.pose.bones[n].matrix.copy() for n in names}
guardlocal={n:guard[parent[n]].inverted()@guard[n] if parent[n] else guard[n] for n in names}
accepted={}
for side,label in [('l','LeftSlash'),('r','RightSlash')]:
    rig.animation_data.action=bpy.data.actions['A_M27_'+label+'_ClawV14']
    if rig.animation_data.action.slots: rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    accepted[side]=[]
    for i in range(40):
        scene.frame_set(i+1)
        accepted[side].append({n:rig.pose.bones[n].matrix.copy() for n in names})
reflect=Matrix.Diagonal((1.,-1.,1.))
helpers=lambda n:n.startswith(('blade_','hand_','ball_','headfront','head_tip','chain_','membrane_'))

def smooth(x):
    x=min(1.,max(0.,x)); return x*x*(3.-2.*x)
def angle(a,b): return math.degrees(2.*math.acos(min(1.,abs(a.dot(b)))))
def world_from_local(rot,hip):
    m={}
    for n in names:
        rel=local[n].copy(); rel=Matrix.LocRotScale(rel.translation,rot.get(n,rel.to_quaternion()),Vector((1,1,1)))
        m[n]=m[parent[n]]@rel if parent[n] else rel
        if n=='pelvis': m[n].translation=hip
    return m
def rebuild(m,overrides):
    out={}
    for n in names:
        rel=m[parent[n]].inverted()@m[n] if parent[n] else m[n].copy()
        p=out[parent[n]]@rel if parent[n] else rel.copy()
        if n in overrides:
            pos=p.translation.copy(); p=overrides[n].to_matrix().to_4x4(); p.translation=pos
        out[n]=p
    return out

raw={}
for role,info in DATA['clips'].items():
    seq=[]; ref=info['reference']
    for fr in info['frames']:
        m={}
        for n in names:
            p=m[parent[n]]@local[n] if parent[n] else local[n].copy()
            if not helpers(n):
                dq=Quaternion(fr[n]['q'])@Quaternion(ref[n]['q']).inverted()
                q=(reflect@dq.to_matrix()@reflect).to_quaternion()@rest[n].to_quaternion()
                pos=p.translation.copy(); p=q.to_matrix().to_4x4(); p.translation=pos
            if n=='pelvis': p.translation=rest[n].translation+reflect@(Vector(fr[n]['p'])-Vector(ref[n]['p']))
            m[n]=p
        seq.append(m)
    raw[role]=seq

weights=np.load(BASE/'BindingV2/binding_weights_v2.npz'); topo=np.load(BASE/'BindingV2/connected_source.npz')
p=topo['points']; points=np.column_stack((p[:,0],-p[:,2],p[:,1]-p[:,1].min()))*100.
wi={n:i for i,n in enumerate(weights['names'])}; cages={}; footpoints={}; floor={}
for side in ['l','r']:
    for part,store in [('blade_root',cages),('foot',footpoints)]:
        n=part+'_'+side; cloud=points[weights['weights'][:,wi[n]]>.999]; inv=np.asarray(rest[n].inverted())
        cloud=cloud@inv[:3,:3].T+inv[:3,3]
        if part=='blade_root':
            # Conservative section boxes contain the entire blade, not just its tip.
            axis=np.linalg.svd(cloud-cloud.mean(0),full_matrices=False)[2][0]; d=cloud@axis
            bins=np.minimum(13,((d-d.min())/np.ptp(d)*14).astype(int)); cage=[]
            for k in range(14):
                sub=cloud[bins==k]
                if not len(sub): continue
                lo,hi=sub.min(0),sub.max(0)
                cage.extend((x,y,z) for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]])
            store[side]=np.asarray(cage)
        else: store[side]=cloud
    gm=np.asarray(guard['foot_'+side]); floor[side]=float((footpoints[side]@gm[:3,:3].T+gm[:3,3])[:,2].min())

def source_pose(role,t):
    f=min(len(raw[role])-1,max(0.,t*FPS)); i=int(f); j=min(i+1,len(raw[role])-1); a=f-i
    out={}
    for n in names:
        r0=raw[role][i][parent[n]].inverted()@raw[role][i][n] if parent[n] else raw[role][i][n]
        r1=raw[role][j][parent[n]].inverted()@raw[role][j][n] if parent[n] else raw[role][j][n]
        out[n]=r0.to_quaternion().slerp(r1.to_quaternion(),a)
    hip=raw[role][i]['pelvis'].translation.lerp(raw[role][j]['pelvis'].translation,a)
    return out,hip

# One monotone, differentiable clock for the complete body. Keep the existing
# 0.25--0.30 s melee window; native peak is identified from active forearm motion.
def timing_map(t,xs,ys):
    sec=np.diff(ys)/np.diff(xs); slopes=np.r_[sec[0],2/(1/sec[:-1]+1/sec[1:]),sec[-1]]
    i=min(len(xs)-2,max(0,int(np.searchsorted(xs,t)-1))); h=xs[i+1]-xs[i]; x=min(1,max(0,(t-xs[i])/h))
    return (2*x**3-3*x*x+1)*ys[i]+(x**3-2*x*x+x)*h*slopes[i]+(-2*x**3+3*x*x)*ys[i+1]+(x**3-x*x)*h*slopes[i+1]

def grounded(m,role,src_t):
    rotations={}
    for side in ['l','r']:
        a,b,c=[s+'_'+side for s in ['thigh','calf','foot']]
        # Keep stable support for these short stationary clips. Donor pelvis,
        # knee pole and toe orientation still drive weight transfer.
        target=guard[c].translation.copy(); footq=guard[c].to_quaternion()
        hip=m[a].translation; delta=target-hip; axis=delta.normalized()
        l1=(rest[b].translation-rest[a].translation).length; l2=(rest[c].translation-rest[b].translation).length
        distance=max(abs(l1-l2)+.01,min(delta.length,l1+l2-.01))
        pole=m[b].translation-hip; pole-=axis*pole.dot(axis)
        if pole.length<.01: pole=Vector((0,-1,0))-axis*Vector((0,-1,0)).dot(axis)
        pole.normalize(); along=(l1*l1-l2*l2+distance*distance)/(2*distance)
        knee=hip+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
        rotations[a]=(m[b].translation-hip).rotation_difference(knee-hip)@m[a].to_quaternion()
        rotations[b]=(m[c].translation-m[b].translation).rotation_difference(target-knee)@m[b].to_quaternion()
        rotations[c]=footq
    return rebuild(m,rotations)

def fit_blades(m,active,t,duration):
    corrections={}; metrics={}
    # Front/rear separation allows the active blade to cross the chest without
    # forcing two long scythes through the same plane.
    lane=0.
    sign=1. if active=='l' else -1.
    separation=Vector((sign*math.cos(lane*math.pi*.5),-math.sin(lane*math.pi*.5),0.))
    for side in ['l','r']:
        shoulder=m['upperarm_'+side].translation
        mat=np.asarray(m['blade_root_'+side]); vectors=[Vector(v)-shoulder for v in cages[side]@mat[:3,:3].T+mat[:3,3]]
        if active:
            normal=separation*(1. if side==active else -1.); center=Vector((0,-62*lane,0))
        else: normal=Vector((1 if side=='l' else -1,0,0)); center=Vector((0,0,0))
        planes=[(normal,normal.dot(center)+15.),(Vector((0,0,1)),10.)]
        # Bull's short hands cannot supply the cutting plane of M27's long
        # scythes. Keep the accepted V14 rigid frame and local elbow chain,
        # while donor hips, spine, clavicles and neck supply the new body drive.
        turn=Quaternion()
        if active:
            frame=accepted[active][min(39,round(t*FPS))]
            turn=frame['blade_root_'+side].to_quaternion()@m['blade_root_'+side].to_quaternion().inverted()
        for _ in range(48):
            settled=True
            for normal,plane in planes:
                low=min((turn@p for p in vectors),key=lambda p:p.dot(normal)); bound=plane-shoulder.dot(normal)
                if low.dot(normal)>=bound-.01: continue
                settled=False; length=low.length
                old=math.acos(max(-1,min(1,low.dot(normal)/length))); new=math.acos(max(-1,min(1,(bound+.06)/length)))
                axis=low.cross(normal)
                if axis.length<1.e-5: axis=Vector((1,0,0))
                turn=Quaternion(axis.normalized(),max(0,old-new))@turn
            if settled: break
        corrections['upperarm_'+side]=turn@m['upperarm_'+side].to_quaternion()
        metrics[side]=angle(Quaternion(),turn)
    return rebuild(m,corrections),metrics

manifest={'revision':'Beast06V1','mesh_revision':'BindingV2','fps':FPS,'stage':'fitted_candidates',
          'runtime_connected':False,'runtime_tested':False,'accepted_guard':'ClawV14',
          'source_listing':'https://www.fab.com/listings/126120a3-996e-4dc3-94f1-6550f0adac03',
          'source_license':'User-installed Fab SciFi Beast06 Bull; retain source asset license.',
          'method':'35 percent native IK donor body motion layered into accepted V14 attack body and arm chain; signed blade frame retained; native reaction/idle deltas; exact limb lengths and foot IK',
          'clips':{}}
metrics={}
for role,source,active,duration in [('LeftSlash','Attack1','l',.65),('RightSlash','Attack6','r',.65),
        ('HitF','GetHitF',None,.8),('HitB','GetHitB',None,.8),('HitL','GetHitL',None,.8),('HitR','GetHitR',None,.8),('Idle','Idle1',None,20/3)]:
    isidle=role=='Idle'; attack=active is not None; initial,hip0=source_pose(source,0.)
    peak=.417 if source=='Attack1' else .206
    xs=[0.,.18,.265,.35,.65]; ys=[0.,max(.03,peak-.15),peak,min(2/3-.05,peak+.10),2/3]
    action=bpy.data.actions.new('A_M27_'+role+'_Beast06V1'); action.use_fake_user=True; rig.animation_data.action=action
    count=round(duration*FPS)+1; scene.frame_start=1; scene.frame_end=count
    prev={}; poses=[]; maxcorrection={'l':0.,'r':0.}
    for i in range(count):
        t=i/FPS; st=timing_map(t,xs,ys) if attack else t
        sr,hip=source_pose(source,st)
        envelope=1. if isidle else smooth(t/(.10 if attack else .045))*(1.-smooth((t-(.43 if attack else .52))/(.22 if attack else .28)))
        rotations={}
        for n in names:
            dq=initial[n].inverted()@sr[n]
            weight=envelope*(.55 if isidle else .80 if role.startswith('Hit') else 1.)
            rotations[n]=guardlocal[n].to_quaternion()@Quaternion().slerp(dq,weight)
            if attack:
                ap=accepted[active][min(39,i)]
                accepted_q=(ap[parent[n]].inverted()@ap[n] if parent[n] else ap[n]).to_quaternion()
                rotations[n]=accepted_q.slerp(rotations[n],.35)
            if attack and n.startswith(('upperarm_','lowerarm_','hand_','blade_')):
                ap=accepted[active][min(39,i)]
                rotations[n]=(ap[parent[n]].inverted()@ap[n]).to_quaternion()
        motion=hip-hip0; motion.x*=.50; motion.y*=.55; motion.z*=.65
        if isidle: motion*=.55
        hip_target=guard['pelvis'].translation+motion*envelope
        if attack: hip_target=accepted[active][min(39,i)]['pelvis'].translation.lerp(hip_target,.35)
        m=world_from_local(rotations,hip_target)
        m=grounded(m,source,st); m,corr=fit_blades(m,active,t,duration)
        for side in ['l','r']: maxcorrection[side]=max(maxcorrection[side],corr[side])
        poses.append(m)
        for n in names:
            basis=local[n].inverted()@(m[parent[n]].inverted()@m[n] if parent[n] else m[n])
            pb=rig.pose.bones[n]; q=basis.to_quaternion()
            if n in prev and prev[n].dot(q)<0: q.negate()
            prev[n]=q.copy(); pb.location=basis.translation; pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=q; pb.scale=(1,1,1)
            for channel in ['location','rotation_quaternion','scale']: pb.keyframe_insert(channel,frame=i+1,group=n)
    scene.frame_set(1); bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
    filename=action.name+'.fbx'
    bpy.ops.export_scene.fbx(filepath=str(OUT/filename),use_selection=True,object_types={'ARMATURE'},apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',global_scale=1.,axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0.)
    manifest['clips'][role]={'file':filename,'source':DATA['clips'][source]['source'],'frames':count,'seconds':duration,
        'active_side':active,'source_clock':{'target':xs,'source':ys} if attack else 'native',
        'contact_window_seconds':[.25,.30] if attack else None}
    metrics[role]={'max_shoulder_fit_degrees':maxcorrection,
        'max_blade_step_degrees':max(angle(poses[i]['blade_root_'+s].to_quaternion(),poses[i-1]['blade_root_'+s].to_quaternion()) for s in ['l','r'] for i in range(1,count)),
        'loop_or_guard_boundary_degrees':max(angle(poses[0][n].to_quaternion(),poses[-1][n].to_quaternion()) for n in names),
        'minimum_blade_z_cm':min(float((cages[s]@np.asarray(m['blade_root_'+s])[:3,:3].T+np.asarray(m['blade_root_'+s])[:3,3])[:,2].min()) for m in poses for s in ['l','r']),
        'max_foot_drift_cm':max((m['foot_'+s].translation-guard['foot_'+s].translation).length for m in poses for s in ['l','r'])}
    print('M27_BEAST06_FITTED '+role,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MantisM27_Beast06V1.blend'))
(OUT/'motion_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'fit_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
