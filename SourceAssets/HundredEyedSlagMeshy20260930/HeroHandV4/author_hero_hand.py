"""Re-articulate the existing body and the signature right hand on the V3 game surface."""
import bpy, json, math, ast
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
OUT=Path(__file__).resolve().parent; ROOT=OUT.parent; OLD=ROOT/'RuntimeV3'
DELIVERY=OUT/'Delivery'; (DELIVERY/'Animations').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OLD/'HundredEyedSlag_RuntimeV3.blend'))
scene=bpy.context.scene; scene.render.fps=30
rig=next(o for o in scene.objects if o.type=='ARMATURE'); mesh=next(o for o in scene.objects if o.type=='MESH')
rig.animation_data.action=None
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(1)
original_rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
spec=json.loads((ROOT/'AuthoringV1/skeleton_spec.json').read_text()); byname={r['name']:r for r in spec}
meta=json.loads((ROOT/'AuthoringV1/source_geometry.json').read_text())
v=np.empty(len(mesh.data.vertices)*3,dtype=np.float32); mesh.data.vertices.foreach_get('co',v); v=v.reshape(-1,3)
limbs={}
for key,pad in meta['feet_centres_m'].items():
    kind,side=key.split('.')
    ns=[f'{kind}_{part}.{side}' for part in ('upper','lower','palm')]
    d={k:Vector(byname[n]['head']) for k,n in zip(('shoulder','elbow','wrist'),ns)}
    d.update(pad=Vector(pad),bones=ns,parent=byname[ns[0]]['parent'])
    d['a']=(d['elbow']-d['shoulder']).length; d['b']=(d['wrist']-d['elbow']).length
    d['axis']=(d['wrist']-d['shoulder']).normalized()
    pole=d['elbow']-d['shoulder']; pole-=d['axis']*pole.dot(d['axis']); d['pole']=pole.normalized()
    d['min_reach']=math.sqrt(d['a']**2+d['b']**2+2*d['a']*d['b']*math.cos(math.radians(112)))
    d['max_reach']=math.sqrt(d['a']**2+d['b']**2+2*d['a']*d['b']*math.cos(math.radians(8)))
    d['toes']=[r['name'] for r in spec if r['name'].startswith(kind+'_digit_') and r['name'].endswith('.'+side)]
    limbs[key]=d
d=limbs['front.R']; shoulder,elbow,wrist=d['shoulder'],d['elbow'],d['wrist']
upper_axis=(elbow-shoulder).normalized(); lower_axis=(wrist-elbow).normalized()
new_bones=[
    ('front_shoulder.R',shoulder,shoulder+upper_axis*.12,'chest'),
    ('front_upper_twist.R',shoulder.lerp(elbow,.52),shoulder.lerp(elbow,.80),'front_upper.R'),
    ('front_lower_twist_01.R',elbow.lerp(wrist,.32),elbow.lerp(wrist,.55),'front_lower.R'),
    ('front_lower_twist_02.R',elbow.lerp(wrist,.72),elbow.lerp(wrist,.93),'front_lower.R'),
    ('front_elbow_support.R',elbow,elbow+lower_axis*.09,'front_upper.R'),
    ('front_wrist_support.R',wrist,d['pad'],'front_lower.R')]
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for name,head,tail,parent in new_bones:
    bone=rig.data.edit_bones.new(name); bone.head=head; bone.tail=tail
    bone.parent=rig.data.edit_bones[parent]; bone.use_connect=False; bone.use_deform=True
    axis=(tail-head).normalized(); bone.align_roll(Vector((0,0,1)) if abs(axis.z)<.85 else Vector((1,0,0)))
bpy.ops.object.mode_set(mode='OBJECT'); arm=rig.data
rest={b.name:b.matrix_local.copy() for b in arm.bones}; inv={n:m.inverted() for n,m in rest.items()}
# Reuse clean V3 poses for the actions outside this targeted edit.
namespace=dict(np=np,math=math,Matrix=Matrix,Vector=Vector,Quaternion=Quaternion,arm=arm,rest=rest,inv=inv,
    limbs=limbs,keys=list(limbs))
tree=ast.parse((OLD/'author_runtime.py').read_text())
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name in {'smooth','step','rotation','around','track','aim','solve','pose'}:
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(OLD/'author_runtime.py'),'exec'),namespace)
base_pose=namespace['pose']; smooth=namespace['smooth']; step=namespace['step']
rotation=namespace['rotation']; around=namespace['around']; track=namespace['track']; aim=namespace['aim']; solve=namespace['solve']

# Transfer only the signature limb's weights onto the added neutral support bones.
skin=np.load(OLD/'skin_weights.npz'); names=list(skin['bone_names'])+[row[0] for row in new_bones]
weights=np.zeros((len(v),len(names)),dtype=np.float32)
rows=np.arange(len(v))[:,None]; weights[rows,skin['indices']]=skin['weights']
def col(name): return names.index(name)
right=weights[:,[col(n) for n in d['bones']]].sum(axis=1)
def projected(a,b):
    a=np.asarray(a); axis=np.asarray(b)-a
    return np.clip(((v-a)*axis).sum(axis=1)/(axis@axis),0,1)
tu=projected(shoulder,elbow); tl=projected(elbow,wrist)
upper=weights[:,col('front_upper.R')].copy()
part=upper*.65*smooth(.15,.85,tu)
weights[:,col('front_upper.R')]-=part; weights[:,col('front_upper_twist.R')]+=part
lower=weights[:,col('front_lower.R')].copy()
f1=.62*smooth(.06,.25,tl)*(1-smooth(.40,.76,tl)); f2=.70*smooth(.40,.90,tl)
weights[:,col('front_lower.R')]-=lower*(f1+f2)
weights[:,col('front_lower_twist_01.R')]+=lower*f1; weights[:,col('front_lower_twist_02.R')]+=lower*f2
for centre,support,bones,radius in [(elbow,'front_elbow_support.R',d['bones'][:2]+['front_upper_twist.R','front_lower_twist_01.R'],.10),
    (wrist,'front_wrist_support.R',d['bones'][1:]+['front_lower_twist_01.R','front_lower_twist_02.R'],.065)]:
    field=np.exp(-((v-np.asarray(centre))**2).sum(axis=1)/(2*radius**2))*.48
    for n in bones:
        part=weights[:,col(n)]*field; weights[:,col(n)]-=part; weights[:,col(support)]+=part
scapula=np.exp(-((v-np.asarray(shoulder))**2).sum(axis=1)/(2*.145**2))*.55
scapula*=smooth(.03,.18,-v[:,1])
for n in ('chest','front_upper.R','front_upper_twist.R','spine'):
    part=weights[:,col(n)]*scapula; weights[:,col(n)]-=part; weights[:,col('front_shoulder.R')]+=part
# Activate the five existing claw bones lightly; palm/contact areas stay stable.
fields=[]
for toe in d['toes']:
    a=np.asarray(byname[toe]['head']); b=np.asarray(byname[toe]['tail']); axis=b-a
    t=np.clip(((v-a)*axis).sum(axis=1)/(axis@axis),0,1)
    distance=((v-a-t[:,None]*axis)**2).sum(axis=1)
    fields.append(np.exp(-distance/(2*.026**2))*smooth(.30,.70,t))
fields=np.asarray(fields).T
amount=weights[:,col('front_palm.R')]*.32*np.clip(fields.max(axis=1),0,1)
weights[:,col('front_palm.R')]-=amount
normal=fields/np.maximum(fields.sum(axis=1,keepdims=True),1e-10)
for i,n in enumerate(d['toes']): weights[:,col(n)]+=amount*normal[:,i]
indices=np.argpartition(weights,-4,axis=1)[:,-4:]; values=weights[rows,indices]
values/=np.maximum(values.sum(axis=1,keepdims=True),1e-10)
mesh.vertex_groups.clear()
for i,n in enumerate(names):
    group=mesh.vertex_groups.new(name=n); rr,cc=np.nonzero(indices==i)
    for vertex,slot in zip(rr,cc):
        value=float(values[vertex,slot])
        if value>1e-6: group.add([int(vertex)],value,'REPLACE')
np.savez_compressed(OUT/'skin_weights.npz',bone_names=np.asarray(names),indices=indices,weights=values)

def core(G,pelvis_q,spine_q,chest_q,lag_q):
    target={'root':rest['root'].copy(),'death_pivot':G@rest['death_pivot']}
    for name,q in [('pelvis',pelvis_q),('spine',spine_q),('chest',chest_q),('carapace',lag_q),
        ('front_plate',rotation()),('shell.L',lag_q),('shell.R',lag_q)]:
        b=arm.bones[name]; base=target[b.parent.name]@inv[b.parent.name]@rest[name]
        target[name]=Matrix.Translation(base.translation)@q.to_matrix().to_4x4()@base.to_3x3().to_4x4()
    return target

def signature_pose(role,t,duration):
    old,info=base_pose(role,t,duration)
    if role not in ('Run','Move','AttackSweep_R','AttackSlam_R'): return old,info,0.
    pads={}; rolls={}; support={k:foot['stance'] for k,foot in info.items()}
    for k,limb in limbs.items():
        palm=limb['bones'][2]; rot=(old[palm]@inv[palm]).to_quaternion()
        pads[k]=old[palm].translation-rot@(limb['wrist']-limb['pad']); rolls[k]=rot
    curl=0.; sh_shift=Vector((0,0,0))
    if role in ('Run','Move'):
        phase=2*math.pi*t/duration; moving=role=='Run'
        G=old['pelvis']@inv['pelvis']
        target=core(G,rotation(.027*math.sin(phase),.030*math.sin(phase*2),-.020*math.sin(phase)),
            rotation(0,.040*math.sin(phase*2-.35),.020*math.sin(phase-.25)),
            rotation(-.035*math.sin(phase-.45),-.060*math.sin(phase*2-.45),.030*math.sin(phase-.45)),
            rotation(.020*math.sin(phase-.8),.035*math.sin(phase*2-.8),-.018*math.sin(phase-.8)))
        duty=.48 if moving else .62; speed=2.8 if moving else 1.2; stride=speed*duration*duty
        f=(t/duration)%1; pads['front.R']=d['pad'].copy()
        if f<duty:
            pads['front.R'].x+=stride*(.5-f/duty); support['front.R']=True
        else:
            u=(f-duty)/(1-duty); velocity=-speed*duration*(1-duty)
            pads['front.R'].x+=(2*u**3-3*u*u+1)*(-stride/2)+(u**3-2*u*u+u)*velocity+(-2*u**3+3*u*u)*stride/2+(u**3-u*u)*velocity
            lift=math.sin(math.pi*u)**2; pads['front.R'].z+=(.19 if moving else .11)*lift
            pads['front.R'].y-=.050*lift; rolls['front.R']=rotation(ry=-.24*math.sin(2*math.pi*u)*lift)
            curl=.20*lift; support['front.R']=False
        sh_shift=Vector((.050*math.cos(phase),-.015*math.sin(phase),.025*math.sin(phase-.35)))
    else:
        pads={k:limb['pad'].copy() for k,limb in limbs.items()}; rolls={k:rotation() for k in limbs}; support={k:True for k in limbs}
        support['front.R']=False
        if role=='AttackSweep_R':
            pads['front.R']=track(t,[(0,tuple(d['pad'])),(.38,(.13,-.80,.50)),(.54,(.57,-.75,.53)),
                (.64,(.88,-.24,.44)),(.73,(.72,.12,.30)),(.95,(.58,-.15,.19)),(1.4,tuple(d['pad']))])
            load=track(t,[(0,(0,0,0)),(.38,(1,0,0)),(.54,(.7,0,0)),(.73,(-.8,0,0)),(1.4,(0,0,0))]).x
            move=track(t,[(0,(0,0,0)),(.38,(-.05,.05,-.025)),(.64,(.075,.025,-.045)),(.85,(.04,0,-.02)),(1.4,(0,0,0))])
            G=around((-.04,0,.64),move,rotation(0,.035,-.11*load))
            target=core(G,rotation(0,.025,.08*load),rotation(0,-.035,-.08*load),rotation(-.055*load,-.045,-.22*load),rotation(0,0,-.05*load))
            sh_shift=Vector((.045-.035*load,-.055*max(0,load),.030*max(0,load)))
            angle=track(t,[(0,(0,0,0)),(.38,(-.25,.20,-.35)),(.64,(.08,.45,.25)),(.73,(.20,.65,.35)),(1.4,(0,0,0))])
            rolls['front.R']=rotation(*angle); curl=.22*max(0,load)
            support['front.R']=t<.035 or t>1.34
        else:
            pads['front.R']=track(t,[(0,tuple(d['pad'])),(.24,(.36,-.53,.34)),(.55,(.46,-.56,1.11)),
                (.72,(.55,-.51,1.06)),(.84,(.78,-.29,.28)),(.90,(.72,-.29,d['pad'].z)),
                (1.04,(.71,-.30,d['pad'].z)),(1.35,(.57,-.33,.11)),(1.8,tuple(d['pad']))])
            load=track(t,[(0,(0,0,0)),(.55,(1,0,0)),(.72,(1,0,0)),(.90,(-.8,0,0)),(1.15,(-.3,0,0)),(1.8,(0,0,0))]).x
            move=track(t,[(0,(0,0,0)),(.55,(-.065,.045,.045)),(.72,(-.05,.045,.04)),(.90,(.085,.025,-.065)),(1.12,(.05,0,-.02)),(1.8,(0,0,0))])
            G=around((-.04,0,.64),move,rotation(.015*load,-.07*load,-.055*load))
            target=core(G,rotation(0,.035*load,.04*load),rotation(0,-.055*load,-.025*load),
                rotation(-.020*load,-.115*load,-.035*load),rotation(0,-.025*load,0))
            sh_shift=Vector((.055*max(0,load),-.050*max(0,load),.085*max(0,load)))
            pitch=track(t,[(0,(0,0,0)),(.55,(.85,0,0)),(.72,(.80,0,0)),(.90,(0,0,0)),(1.8,(0,0,0))]).x
            rolls['front.R']=rotation(ry=pitch,rz=-.08*max(0,load)); curl=.26*max(0,load)
            support['front.R']=t<.035 or .90<=t<=1.04 or t>1.72
    target['front_shoulder.R']=target['chest']@inv['chest']@rest['front_shoulder.R']
    target['front_shoulder.R'].translation+=target['chest'].to_quaternion()@sh_shift
    parents={}
    for k,limb in limbs.items():
        if k=='front.R':
            parent=target['chest']@inv['chest']; parent.translation+=target['chest'].to_quaternion()@sh_shift
        else: parent=target[limb['parent']]@inv[limb['parent']]
        parents[k]=parent
    # Stance feet constrain body translation; leave the animated hip/chest rotations intact.
    lower,upper=-1.,1.
    for k,limb in limbs.items():
        if not support[k]: continue
        sh=parents[k]@limb['shoulder']; w=pads[k]+rolls[k]@(limb['wrist']-limb['pad'])
        horizontal=(sh-w).to_2d().length; vertical=sh.z-w.z
        minimum=limb['min_reach']; maximum=limb['max_reach']
        lower=max(lower,math.sqrt(max(0,minimum**2-horizontal**2))-vertical)
        upper=min(upper,math.sqrt(max(0,maximum**2-horizontal**2))-vertical)
    dz=max(lower,min(0.,upper)) if lower<=upper else min(0.,upper)
    for n in target:
        if n!='root': target[n].translation.z+=dz
    for parent in parents.values(): parent.translation.z+=dz
    info={}
    for k,limb in limbs.items():
        limits=dict(limb)
        if k=='front.R': limits['min_reach']=math.sqrt(limb['a']**2+limb['b']**2+2*limb['a']*limb['b']*math.cos(math.radians(128)))
        sh,e,w,error=solve(limits,parents[k],pads[k],rolls[k]); up,lo,palm=limb['bones']
        target[up]=aim(up,sh,e); target[lo]=aim(lo,e,w)
        target[palm]=Matrix.Translation(w)@rolls[k].to_matrix().to_4x4()@rest[palm].to_3x3().to_4x4()
        for toe in limb['toes']:
            target[toe]=target[palm]@inv[palm]@rest[toe]
            if k=='front.R':
                base=target[toe]; target[toe]=Matrix.Translation(base.translation)@rotation(ry=curl).to_matrix().to_4x4()@base.to_3x3().to_4x4()
        info[k]={'stance':support[k],'reach_error_cm':error*100,'bend_degrees':math.degrees((e-sh).angle(w-e))}
    for n,p in [('ash_origin','front_plate'),('attack_origin','front_palm.R')]: target[n]=target[p]@inv[p]@rest[n]
    return target,info,curl

def support_bones(target):
    def deformation(n): return (target[n]@inv[n]).to_quaternion()
    def inherit(helper,parent): return target[parent]@inv[parent]@rest[helper]
    if 'front_shoulder.R' not in target: target['front_shoulder.R']=inherit('front_shoulder.R','chest')
    for helper,parent,distal,factor in [('front_upper_twist.R','front_upper.R','front_lower.R',.42),
        ('front_lower_twist_01.R','front_lower.R','front_palm.R',.32),('front_lower_twist_02.R','front_lower.R','front_palm.R',.72)]:
        base=inherit(helper,parent); delta=deformation(distal)@deformation(parent).inverted()
        if delta.w<0: delta.negate()
        axis=(target[parent].to_3x3()@Vector((0,1,0))).normalized()
        angle=2*math.atan2(Vector((delta.x,delta.y,delta.z)).dot(axis),delta.w)
        angle=max(-math.radians(110),min(math.radians(110),angle))*factor
        q=Quaternion(axis,angle)@base.to_quaternion()
        target[helper]=Matrix.Translation(base.translation)@q.to_matrix().to_4x4()
    for helper,a,b,anchor in [('front_elbow_support.R','front_upper.R','front_lower.R','front_lower.R'),
        ('front_wrist_support.R','front_lower.R','front_palm.R','front_palm.R')]:
        qa,qb=deformation(a),deformation(b)
        if qa.dot(qb)<0: qb.negate()
        q=qa.slerp(qb,.5)@rest[helper].to_quaternion()
        target[helper]=Matrix.Translation(target[anchor].translation)@q.to_matrix().to_4x4()

contracts=json.loads((OLD/'animation_contract.json').read_text())['actions']; metrics={}
for c in contracts:
    c['action']='A_HundredEyedSlag_'+c['name']+'_V4'
    c['file']='Animations/'+c['action']+'.fbx'
    action=bpy.data.actions.new(c['action']); action.use_fake_user=True; rig.animation_data.action=action
    palms=[]; requested_stance=[]; twists=[]; previous={}
    for frame in range(1,c['end_frame_inclusive']+1):
        target,info,curl=signature_pose(c['name'],(frame-1)/30,c['seconds']); support_bones(target)
        palms.append(list(target['front_palm.R'].translation)); requested_stance.extend(r['reach_error_cm'] for r in info.values() if r['stance'])
        for b in arm.bones:
            basis=inv[b.name]@rest[b.parent.name]@target[b.parent.name].inverted()@target[b.name] if b.parent else inv[b.name]@target[b.name]
            pb=rig.pose.bones[b.name]; pb.rotation_mode='QUATERNION'; pb.matrix_basis=basis
            if b.name in previous and pb.rotation_quaternion.dot(previous[b.name])<0: pb.rotation_quaternion.negate()
            previous[b.name]=pb.rotation_quaternion.copy(); pb.scale=(1,1,1)
            for path in ('location','rotation_quaternion','scale'): pb.keyframe_insert(path,frame=frame)
        if not rig.animation_data.action_slot: rig.animation_data.action_slot=action.slots[0]
    bag=action.layers[0].strips[0].channelbag(action.slots[0])
    for curve in bag.fcurves:
        for point in curve.keyframe_points: point.interpolation='LINEAR'
    pts=np.asarray(palms)
    metrics[c['name']]={'right_palm_bounds_cm':(100*np.asarray([pts.min(axis=0),pts.max(axis=0)])).tolist(),
        'right_palm_path_cm':float(100*np.linalg.norm(np.diff(pts,axis=0),axis=1).sum()),
        'stance_target_error_cm':max(requested_stance,default=0)}
    print('V4_ACTION '+c['name']+' '+json.dumps(metrics[c['name']]),flush=True)
rig.animation_data.action=None
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(1); mesh.name='SK_HundredEyedSlag_HeroHandV4'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_HeroHandV4.blend'))
fbx=dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.)
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(DELIVERY/'SK_HundredEyedSlag_HeroHandV4.fbx'),object_types={'ARMATURE','MESH'},
    bake_anim=False,use_mesh_modifiers=False,mesh_smooth_type='OFF',path_mode='AUTO',embed_textures=False,**fbx)
mesh.select_set(False)
for c in contracts:
    action=bpy.data.actions[c['action']]; rig.animation_data.action=action; rig.animation_data.action_slot=action.slots[0]
    scene.frame_end=c['end_frame_inclusive']; scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=str(DELIVERY/'Animations'/(c['action']+'.fbx')),object_types={'ARMATURE'},bake_anim=True,**fbx)
(OUT/'animation_contract.json').write_text(json.dumps({'actions':contracts,'targeted_roles':['Run','Move','AttackSweep_R','AttackSlam_R'],
    'original_rest_and_hierarchy_preserved':True,'added_bones':[n for n,h,t,p in new_bones],'bone_count':len(arm.bones),
    'game_triangles':len(mesh.data.polygons),'max_influences':4},indent=2))
(OUT/'authoring_receipt.json').write_text(json.dumps({'animation_metrics':metrics,'baked_normal_and_uv_preserved':True,
    'runtime_tested':False,'added_bones':6,'source_bones':len(original_rest),'total_bones':len(arm.bones)},indent=2))
print('V4_HERO_HAND_AUTHORED_AND_EXPORTED',flush=True)
