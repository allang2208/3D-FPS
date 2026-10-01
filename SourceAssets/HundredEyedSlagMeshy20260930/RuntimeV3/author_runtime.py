"""Anatomical branch skinning, bounded IK, and replacement of all runtime actions."""
import bpy, json, math, heapq, ast
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
DELIVERY=OUT/'Delivery'; DELIVERY.mkdir(exist_ok=True)
(DELIVERY/'Animations').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'HundredEyedSlag_GameSurfaceV3.blend'))
scene=bpy.context.scene; scene.render.fps=30
rig=next(o for o in scene.objects if o.type=='ARMATURE')
mesh=next(o for o in scene.objects if o.type=='MESH'); arm=rig.data
spec=json.loads((ROOT/'AuthoringV1/skeleton_spec.json').read_text())
meta=json.loads((ROOT/'AuthoringV1/source_geometry.json').read_text())
byname={s['name']:s for s in spec}
names=[s['name'] for s in spec if s['deform']]
rest={b.name:b.matrix_local.copy() for b in arm.bones}
inv={n:m.inverted() for n,m in rest.items()}
v=np.empty(len(mesh.data.vertices)*3,dtype=np.float32)
mesh.data.vertices.foreach_get('co',v); v=v.reshape(-1,3)
limbs={}
for key,pad in meta['feet_centres_m'].items():
    kind,side=key.split('.')
    up,low,palm=[f'{kind}_{part}.{side}' for part in ('upper','lower','palm')]
    d={'pad':Vector(pad),'shoulder':Vector(byname[up]['head']),
       'elbow':Vector(byname[low]['head']),'wrist':Vector(byname[palm]['head']),
       'parent':byname[up]['parent'],'bones':[up,low,palm]}
    d['a']=(d['elbow']-d['shoulder']).length
    d['b']=(d['wrist']-d['elbow']).length
    d['axis']=(d['wrist']-d['shoulder']).normalized()
    bend=d['elbow']-d['shoulder']; bend-=d['axis']*bend.dot(d['axis'])
    d['pole']=bend.normalized()
    # Bend is the angle between upper and lower segments, not the interior knee angle.
    d['min_reach']=math.sqrt(d['a']**2+d['b']**2+2*d['a']*d['b']*math.cos(math.radians(112)))
    d['max_reach']=math.sqrt(d['a']**2+d['b']**2+2*d['a']*d['b']*math.cos(math.radians(8)))
    d['toes']=[n for n in names if n.startswith(kind+'_digit_') and n.endswith('.'+side)]
    limbs[key]=d

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1); return t*t*(3-2*t)
def step(x): return float(smooth(0,1,x))
def rotation(rx=0,ry=0,rz=0):
    return Quaternion((0,0,1),rz)@Quaternion((0,1,0),ry)@Quaternion((1,0,0),rx)
def around(pivot,shift,q):
    return Matrix.Translation(Vector(pivot)+Vector(shift))@q.to_matrix().to_4x4()@Matrix.Translation(-Vector(pivot))
def track(t,keys):
    if t<=keys[0][0]: return Vector(keys[0][1])
    for (ta,a),(tb,b) in zip(keys,keys[1:]):
        if t<=tb: return Vector(a).lerp(Vector(b),step((t-ta)/(tb-ta)))
    return Vector(keys[-1][1])

# Surface graph paths prevent a close neighbouring leg from attracting weights.
print('V3: anatomical surface branches',flush=True)
edge_indices=np.empty(len(mesh.data.edges)*2,dtype=np.int32)
mesh.data.edges.foreach_get('vertices',edge_indices); edge_indices=edge_indices.reshape(-1,2)
adj=[[] for _ in v]
for i,j in edge_indices:
    dist=float(np.linalg.norm(v[i]-v[j])); adj[i].append((int(j),dist)); adj[j].append((int(i),dist))
# Connect coincident UV-seam vertices in the graph without changing mesh UV/topology.
seams={}
for i,p in enumerate(v):
    token=tuple(np.round(p,5))
    if token in seams:
        j=seams[token]; adj[i].append((j,1e-6)); adj[j].append((i,1e-6))
    else: seams[token]=i
keys=list(limbs); distances=[]
for key,d in limbs.items():
    distance=np.full(len(v),np.inf)
    xy=((v[:,:2]-np.asarray(d['pad'])[:2])**2).sum(axis=1)
    seeds=np.where((xy<.08**2)&(v[:,2]<.11))[0]
    if not len(seeds): seeds=[int(np.argmin(xy+v[:,2]**2))]
    queue=[]
    for seed in seeds: distance[seed]=0; heapq.heappush(queue,(0.,int(seed)))
    while queue:
        total,i=heapq.heappop(queue)
        if total>distance[i]+1e-8: continue
        for j,cost in adj[i]:
            if v[j,2]>.58: continue
            value=total+cost
            if value<distance[j]: distance[j]=value; heapq.heappush(queue,(value,j))
    distances.append(distance)
    print('V3: branch '+key,flush=True)
geodesic=np.asarray(distances).T
labels=np.argmin(geodesic,axis=1)
unreachable=~np.isfinite(geodesic.min(axis=1))
# Disconnected decorations inherit their nearest anatomical branch only in the low region.
fallback=[]
for d in limbs.values():
    a=np.asarray(d['shoulder']); b=np.asarray(d['pad']); axis=b-a
    f=np.clip(((v-a)*axis).sum(axis=1)/(axis@axis),0,1)
    fallback.append(((v-a-f[:,None]*axis)**2).sum(axis=1))
labels[unreachable]=np.argmin(np.asarray(fallback).T[unreachable],axis=1)
weights=np.zeros((len(v),len(names)),dtype=np.float32)
body=np.zeros_like(weights)
front=smooth(-.23,.12,v[:,0]); body[:,names.index('pelvis')]=1-front; body[:,names.index('chest')]=front
mid=.66*np.exp(-((v[:,0]+.10)/.14)**2)*smooth(.36,.58,v[:,2])*(1-smooth(.80,1.,v[:,2]))
body*=1-mid[:,None]; body[:,names.index('spine')]+=mid
shell=smooth(.69,.92,v[:,2])*.88
body*=1-shell[:,None]; body[:,names.index('carapace')]+=shell
for side,sign in [('L',1),('R',-1)]:
    amount=smooth(.28,.47,sign*v[:,1])*smooth(.45,.65,v[:,2])*(1-smooth(.83,1.02,v[:,2]))*.6
    body*=1-amount[:,None]; body[:,names.index('shell.'+side)]+=amount
plate=smooth(.12,.30,v[:,0])*smooth(.59,.78,v[:,2])*.55
body*=1-plate[:,None]; body[:,names.index('front_plate')]+=plate
for label,key in enumerate(keys):
    d=limbs[key]; mask=labels==label; p=v[mask]
    points=[np.asarray(d[n]) for n in ('shoulder','elbow','wrist','pad')]
    candidates=[]; arclength=[]; cumulative=0
    for a,b in zip(points,points[1:]):
        axis=b-a; length=np.linalg.norm(axis)
        f=np.clip(((p-a)*axis).sum(axis=1)/(axis@axis),0,1)
        candidates.append(((p-a-f[:,None]*axis)**2).sum(axis=1))
        arclength.append(cumulative+f*length); cumulative+=length
    closest=np.argmin(np.asarray(candidates).T,axis=1)
    s=np.asarray(arclength).T[np.arange(len(p)),closest]
    elbow=smooth(d['a']-.065,d['a']+.065,s)
    ankle=smooth(d['a']+d['b']-.045,d['a']+d['b']+.025,s)
    # Entire contact sole belongs to the palm, irrespective of finger proximity.
    ankle=np.maximum(ankle,1-smooth(.08,.145,p[:,2]))
    limb=np.zeros((len(p),len(names)),dtype=np.float32)
    limb[:,names.index(d['bones'][0])]=(1-elbow)*(1-ankle)
    limb[:,names.index(d['bones'][1])]=elbow*(1-ankle)
    limb[:,names.index(d['bones'][2])]=ankle
    attachment=smooth(.33,.60,p[:,2])
    attachment=np.maximum(attachment,1-smooth(0,.20,s))
    weights[mask]=limb*(1-attachment[:,None])+body[mask]*attachment[:,None]
rows=np.arange(len(v))[:,None]
indices=np.argpartition(weights,-4,axis=1)[:,-4:]
values=weights[rows,indices]; values/=np.maximum(values.sum(axis=1,keepdims=True),1e-10)
mesh.vertex_groups.clear()
for j,n in enumerate(names):
    group=mesh.vertex_groups.new(name=n); rr,cc=np.nonzero(indices==j)
    for vid,slot in zip(rr,cc):
        w=float(values[vid,slot])
        if w>1e-6: group.add([int(vid)],w,'REPLACE')
np.savez_compressed(OUT/'skin_weights.npz',bone_names=np.asarray(names),indices=indices,weights=values)
np.save(OUT/'surface_vertices.npy',v)

def aim(name,head,tail):
    old=(arm.bones[name].tail_local-arm.bones[name].head_local).normalized()
    q=old.rotation_difference((tail-head).normalized())
    return Matrix.Translation(head)@q.to_matrix().to_4x4()@rest[name].to_3x3().to_4x4()

def solve(d,parent,pad,footrot):
    shoulder=parent@d['shoulder']; requested=pad+footrot@(d['wrist']-d['pad'])
    delta=requested-shoulder; axis=delta.normalized()
    distance=max(d['min_reach'],min(delta.length,d['max_reach']))
    reference_axis=parent.to_quaternion()@d['axis']
    # Parallel transport keeps the bend plane continuous and has no pole projection singularity.
    pole=reference_axis.rotation_difference(axis)@(parent.to_quaternion()@d['pole'])
    along=(d['a']**2-d['b']**2+distance**2)/(2*distance)
    elbow=shoulder+axis*along+pole*math.sqrt(max(0,d['a']**2-along**2))
    wrist=shoulder+axis*distance
    return shoulder,elbow,wrist,float((wrist-requested).length)

contracts=json.loads((ROOT/'AuthoringV1/animation_contract.json').read_text())['actions']
for c in contracts:
    if c['name']=='Run': c.update(seconds=14/30,reference_speed_m_s=2.8)
    if c['name']=='Move': c.update(seconds=20/30,reference_speed_m_s=1.2)
    if c['name']=='Death': c.update(seconds=1.,ragdoll_handoff_s=.42)
    c.update(action='A_HundredEyedSlag_'+c['name']+'_V3',end_frame_inclusive=round(c['seconds']*30)+1)

def pose(role,t,duration):
    phase=2*math.pi*t/duration
    body=Vector((0,0,0)); angles=Vector((0,0,0))
    pads={k:d['pad'].copy() for k,d in limbs.items()}
    rolls={k:rotation() for k in keys}; support={k:True for k in keys}
    if role in ('Run','Move') or (role.startswith('SpecialCharge') and .55<t<1.35):
        fast=role!='Move'; cycle=14/30 if fast else 20/30
        local=t if role in ('Run','Move') else t-.55
        phase=2*math.pi*local/cycle
        duty=.39 if fast else .58; speed=2.8 if role=='Run' else 1.2 if role=='Move' else 2.1
        stride=speed*cycle*duty
        offsets={'front.R':0,'rear.L':0,'front.L':.5,'rear.R':.5}
        if not fast: offsets={'front.R':0,'rear.L':.25,'front.L':.5,'rear.R':.75}
        envelope=1 if role in ('Run','Move') else math.sin(math.pi*(t-.55)/.8)
        for k,d in limbs.items():
            f=(local/cycle+offsets[k])%1
            if f<duty:
                pads[k].x+=envelope*stride*(.5-f/duty)
            else:
                support[k]=False; u=(f-duty)/(1-duty)
                h00=2*u**3-3*u*u+1; h10=u**3-2*u*u+u
                h01=-2*u**3+3*u*u; h11=u**3-u*u
                velocity=-speed*cycle*(1-duty)
                pads[k].x+=envelope*(h00*(-stride/2)+h10*velocity+h01*stride/2+h11*velocity)
                pads[k].z+=envelope*(.095 if fast else .060)*math.sin(math.pi*u)**2
                rolls[k]=rotation(ry=-.15*math.sin(2*math.pi*u)*math.sin(math.pi*u)**2)
        body.z=-.065+.012*math.cos(phase*2)
        body.y=.006*math.sin(phase); angles.x=.012*math.sin(phase); angles.y=.022*math.sin(phase*2)
    elif role=='AttackSweep_R':
        pads['front.R']+=track(t,[(0,(0,0,0)),(.40,(-.025,-.08,.17)),(.54,(.08,-.06,.20)),
            (.70,(.16,.24,.14)),(.95,(.10,.07,.08)),(1.4,(0,0,0))])
        load=track(t,[(0,(0,0,0)),(.40,(1,0,0)),(.70,(.7,0,0)),(1.4,(0,0,0))]).x
        body.y=.030*load; body.z=-.025*load; angles.z=.08*load
        support['front.R']=t<.06 or t>1.32
    elif role=='AttackSlam_R':
        pads['front.R']+=track(t,[(0,(0,0,0)),(.55,(-.02,-.04,.29)),(.72,(.07,0,.26)),
            (.88,(.13,0,0)),(1.05,(.13,0,0)),(1.8,(0,0,0))])
        load=track(t,[(0,(0,0,0)),(.55,(1,0,0)),(.72,(.9,0,0)),(.88,(-.25,0,0)),(1.8,(0,0,0))]).x
        body.y=.025*max(0,load); body.x=-.025*load; angles.y=-.055*load
        support['front.R']=t<.06 or t>=.86
    elif role=='SpecialAshBurst':
        load=track(t,[(0,(0,0,0)),(.78,(1,0,0)),(1.,(1,0,0)),(1.18,(0,0,0)),(2.4,(0,0,0))]).x
        body.z=-.050*load; body.x=-.015*load; angles.y=.035*load
    elif role.startswith('SpecialCharge'):
        load=track(t,[(0,(0,0,0)),(.45,(1,0,0)),(1.3,(.65,0,0)),(2.,(0,0,0))]).x
        body.z=-.050*load; body.x=.025*load; angles.y=.045*load
    elif role.startswith('Hit') or role=='Stagger':
        load=track(t,[(0,(0,0,0)),(.12,(1,0,0)),(.36,(.4,0,0)),(duration,(0,0,0))]).x
        sign=-1 if role=='HitLeft' else 1 if role=='HitRight' else 0
        body.x=-.035*load; body.z=-.025*load; body.y=.025*sign*load
        angles.x=-.035*sign*load; angles.y=-.035*load
    elif role.startswith('Stun'):
        amount=step(t/.6) if role=='StunEnter' else 1-step(t/.7) if role=='StunExit' else 1
        body.z=-.040*amount; angles.y=.035*amount
        if role=='StunLoop': body.y=.010*math.sin(phase); angles.x=.025*math.sin(phase)
    elif role=='Death':
        fall=step(t/.55); body=Vector((-.020*fall,-.050*fall,-.12*fall))
        angles=Vector((.55*fall,.07*fall,-.06*fall))
        for k in keys:
            loss=step((t-.10)/.35)*(1 if k=='front.R' else .5 if k=='rear.R' else .2)
            pads[k]+=Vector((-.04*loss,.015*loss,.07*loss)); support[k]=False
    else:
        body.z=.003*math.sin(phase); angles.x=.005*math.sin(phase)
    global_body=around((-.04,0,.64),body,rotation(*angles))
    # Find a common body-height interval with all stance soles still in reach.
    if role!='Death':
        lower,upper=-1.,1.
        for k,d in limbs.items():
            if not support[k]: continue
            shoulder=global_body@d['shoulder']; wrist=pads[k]+rolls[k]@(d['wrist']-d['pad'])
            horizontal=(shoulder-wrist).to_2d().length; vertical=shoulder.z-wrist.z
            lower=max(lower,math.sqrt(max(0,d['min_reach']**2-horizontal**2))-vertical)
            upper=min(upper,math.sqrt(max(0,d['max_reach']**2-horizontal**2))-vertical)
        dz=max(lower,min(0.,upper)) if lower<=upper else min(0.,upper)
        global_body=Matrix.Translation((0,0,dz))@global_body
    target={'root':rest['root'].copy(),'death_pivot':global_body@rest['death_pivot']}
    for n in ('pelvis','spine','chest','carapace','front_plate','shell.L','shell.R'):
        target[n]=global_body@rest[n]
    diagnostics={}
    for k,d in limbs.items():
        shoulder,elbow,wrist,error=solve(d,global_body,pads[k],rolls[k])
        up,low,palm=d['bones']
        target[up]=aim(up,shoulder,elbow); target[low]=aim(low,elbow,wrist)
        target[palm]=Matrix.Translation(wrist)@rolls[k].to_matrix().to_4x4()@rest[palm].to_3x3().to_4x4()
        for toe in d['toes']: target[toe]=target[palm]@inv[palm]@rest[toe]
        diagnostics[k]={'bend_degrees':math.degrees((elbow-shoulder).angle(wrist-elbow)),
            'reach_error_cm':100*error,'stance':support[k],
            'segment_error_cm':100*max(abs((elbow-shoulder).length-d['a']),abs((wrist-elbow).length-d['b']))}
    for n,p in [('ash_origin','front_plate'),('attack_origin','front_palm.R')]: target[n]=target[p]@inv[p]@rest[n]
    if role=='SpecialCharge_RM':
        move=Matrix.Translation((1.4*step((t-.55)/.70),0,0))
        target={n:move@m for n,m in target.items()}
    return target,diagnostics

summary={}; contacts={}
for c in contracts:
    action=bpy.data.actions.new(c['action']); action.use_fake_user=True
    rig.animation_data.action=action
    records=[]
    for frame in range(1,c['end_frame_inclusive']+1):
        target,info=pose(c['name'],(frame-1)/30,c['seconds']); records.append(info)
        for b in arm.bones:
            basis=inv[b.name]@rest[b.parent.name]@target[b.parent.name].inverted()@target[b.name] if b.parent else inv[b.name]@target[b.name]
            pb=rig.pose.bones[b.name]; pb.rotation_mode='QUATERNION'; pb.matrix_basis=basis
            for channel in ('location','rotation_quaternion','scale'): pb.keyframe_insert(channel,frame=frame)
        if not rig.animation_data.action_slot: rig.animation_data.action_slot=action.slots[0]
    bag=action.layers[0].strips[0].channelbag(action.slots[0])
    for curve in bag.fcurves:
        for point in curve.keyframe_points: point.interpolation='LINEAR'
    allfeet=[foot for record in records for foot in record.values()]
    summary[c['name']]={'max_bend_degrees':max(r['bend_degrees'] for r in allfeet),
        'max_stance_reach_error_cm':max((r['reach_error_cm'] for r in allfeet if r['stance']),default=0),
        'max_segment_error_cm':max(r['segment_error_cm'] for r in allfeet)}
    contacts[c['name']]=records
    print('V3_ACTION '+c['name']+' '+json.dumps(summary[c['name']]),flush=True)
rig.animation_data.action=None
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(1)
mesh['high_poly_source']=str(ROOT/'PolishV2/HundredEyedSlag_PolishV2.blend')
mesh['skin_method']='Surface-geodesic anatomical branches; joint arclength transitions; rigid soles; four influences'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_RuntimeV3.blend'))
fbx=dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
    bake_anim_step=1.,bake_anim_simplify_factor=0.)
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); mesh.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(DELIVERY/'SK_HundredEyedSlag_RuntimeV3.fbx'),object_types={'ARMATURE','MESH'},
    bake_anim=False,use_mesh_modifiers=False,mesh_smooth_type='OFF',path_mode='AUTO',embed_textures=False,**fbx)
mesh.select_set(False)
for c in contracts:
    action=bpy.data.actions[c['action']]; rig.animation_data.action=action; rig.animation_data.action_slot=action.slots[0]
    scene.frame_end=c['end_frame_inclusive']; scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=str(DELIVERY/'Animations'/(c['action']+'.fbx')),object_types={'ARMATURE'},bake_anim=True,**fbx)
(OUT/'animation_contract.json').write_text(json.dumps({'actions':contracts,'game_triangles':len(mesh.data.polygons),
    'skeleton_rest_preserved':True,'max_influences':4},indent=2))
(OUT/'authoring_diagnosis.json').write_text(json.dumps({'actions':summary,'foot_paths':contacts,
    'runtime_tested':False,'source_vertices':len(v),'geodesic_disconnected_vertices':int(unreachable.sum())},indent=2))
print('V3_AUTHORING_AND_EXPORT_COMPLETE',flush=True)
