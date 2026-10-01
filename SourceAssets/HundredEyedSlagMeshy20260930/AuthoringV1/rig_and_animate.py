"""Fit and skin the source creature, then author sixteen original skeletal actions.
No UE operations, acceptance renders, self-tests or regression checks.
"""
import bpy
import json
import math
import shutil
import time
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
DELIVERY=ROOT/'DeliveryV1'
DELIVERY.mkdir(exist_ok=True)
ANIMS=DELIVERY/'Animations';ANIMS.mkdir(exist_ok=True)
META=json.loads((OUT/'source_geometry.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(OUT/'HundredEyedSlag_Source.blend'))
scene=bpy.context.scene;scene.render.fps=30;scene.frame_start=1
mesh=next(o for o in scene.objects if o.type=='MESH')
mesh.name='SK_HundredEyedSlag_V1'
v=np.load(OUT/'source_vertices.npy').astype(np.float32)
feet={k:Vector(x) for k,x in META['feet_centres_m'].items()}
print('AUTHOR: material packaging',flush=True)

# Explicitly package the original service maps beside the authoring file.
material=bpy.data.materials.new('M_HundredEyedSlag_PBR');material.use_nodes=True
nodes=material.node_tree.nodes;links=material.node_tree.links
shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
maps={'BaseColor':('base_color','sRGB','Base Color'),
      'Metallic':('metallic','Non-Color','Metallic'),
      'Roughness':('roughness','Non-Color','Roughness'),
      'Normal':('normal','Non-Color',None)}
texture_files=[]
for label,(source,space,socket) in maps.items():
    destination=OUT/'Textures'/('T_HundredEyedSlag_'+label+'.png')
    shutil.copy2(ROOT/'Meshy/body/downloads'/('texture_urls_0_'+source+'.png'),destination)
    image=bpy.data.images.load(str(destination),check_existing=True)
    image.colorspace_settings.name=space;image.pack()
    image.filepath='//Textures/'+destination.name
    tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.label=label
    if socket:links.new(tex.outputs['Color'],shader.inputs[socket])
    else:
        normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=1.0
        links.new(tex.outputs['Color'],normal.inputs['Color'])
        links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    texture_files.append(destination.name)
mesh.data.materials.clear();mesh.data.materials.append(material)
for poly in mesh.data.polygons:poly.material_index=0

spec=[]
def bone(name,head,tail,parent=None,region='body',radius=.15,deform=True):
    spec.append({'name':name,'head':list(head),'tail':list(tail),
                 'parent':parent,'region':region,'radius':radius,'deform':deform})
bone('root',(0,0,0),(0,0,.12),deform=False)
bone('death_pivot',(0,0,.55),(0,0,.72),'root',deform=False)
bone('pelvis',(-.32,0,.59),(-.12,0,.66),'death_pivot',radius=.29)
bone('spine',(-.12,0,.66),(.08,0,.77),'pelvis',radius=.28)
bone('chest',(.08,0,.77),(.20,.02,.89),'spine',radius=.26)
bone('carapace',(-.12,.045,.91),(-.08,.06,1.13),'spine',radius=.25)
bone('front_plate',(.16,.05,.86),(.32,.05,.89),'chest',region='plate',radius=.16)
bone('shell.L',(-.14,.31,.69),(-.12,.47,.84),'spine',radius=.18)
bone('shell.R',(-.13,-.29,.68),(-.12,-.46,.82),'spine',radius=.18)

limbs={
'front.R':{'shoulder':(.08,-.27,.68),'elbow':(.24,-.53,.39),
           'wrist':(.44,-.37,.165),'parent':'chest','digits':5,'radius':.14},
'front.L':{'shoulder':(.09,.23,.67),'elbow':(-.01,.41,.36),
           'wrist':(.17,.43,.145),'parent':'chest','digits':3,'radius':.095},
'rear.L':{'shoulder':(-.35,.24,.59),'elbow':(-.58,.44,.35),
          'wrist':(-.53,.416,.135),'parent':'pelvis','digits':3,'radius':.105},
'rear.R':{'shoulder':(-.35,-.21,.55),'elbow':(-.60,-.29,.30),
          'wrist':(-.54,-.26,.130),'parent':'pelvis','digits':3,'radius':.105}}
for key,d in limbs.items():
    for p in ['shoulder','elbow','wrist']:d[p]=Vector(d[p])
    d['pad']=feet[key]
    kind,side=key.split('.')
    d['bones']=[kind+'_upper.'+side,kind+'_lower.'+side,kind+'_palm.'+side]
    bone(d['bones'][0],d['shoulder'],d['elbow'],d['parent'],key,d['radius'])
    bone(d['bones'][1],d['elbow'],d['wrist'],d['bones'][0],key,d['radius']*.78)
    bone(d['bones'][2],d['wrist'],d['pad'],d['bones'][1],key,.095)
    d['toe_bones']=[]
    spread=.105 if key=='front.R' else .068
    region_vertices=v[(v[:,2]<.14)&(((v[:,:2]-np.array(d['pad'])[:2])**2).sum(axis=1)<.055)]
    reach=.15 if kind=='front' else .105
    for i in range(d['digits']):
        side_offset=spread*(2*i/(d['digits']-1)-1)
        root=d['pad']+Vector((.028,side_offset*.75,-.003))
        tip=d['pad']+Vector((reach,side_offset,.010))
        # Fit the fingertip elevation to the nearby source support surface.
        local=region_vertices[np.abs(region_vertices[:,1]-tip.y)<.025]
        if len(local):
            tip.x=float(np.quantile(local[:,0],.83))
            tip.z=float(np.quantile(local[:,2],.20))
        if (tip-root).length<.028:tip.x=root.x+.05
        name=kind+'_digit_%02d.'%(i+1)+side
        bone(name,root,tip,d['bones'][2],key+'_digit',radius=.044)
        d['toe_bones'].append(name)
bone('ash_origin',(.30,0,.72),(.46,0,.72),'front_plate',deform=False)
bone('attack_origin',feet['front.R'],feet['front.R']+Vector((.14,0,0)),
     'front_palm.R',deform=False)

arm=bpy.data.armatures.new('HundredEyedSlag_Skeleton_V1')
rig=bpy.data.objects.new('RIG_HundredEyedSlag_V1',arm)
scene.collection.objects.link(rig);rig.show_in_front=True
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for s in spec:
    b=arm.edit_bones.new(s['name']);b.head=s['head'];b.tail=s['tail'];b.use_deform=s['deform']
    if s['parent']:b.parent=arm.edit_bones[s['parent']]
    b.use_connect=False
    direction=(b.tail-b.head).normalized()
    b.align_roll(Vector((0,0,1)) if abs(direction.z)<.85 else Vector((1,0,0)))
bpy.ops.object.mode_set(mode='OBJECT')
for label,regions in [('Body',['body','plate']),('Forelimbs',['front']),
                      ('Hindlimbs',['rear']),('Sockets',['socket'])]:
    collection=arm.collections.new(label)
    for s in spec:
        if (label=='Sockets' and not s['deform']) or any(s['region'].startswith(r) for r in regions):
            collection.assign(arm.bones[s['name']])
deforms=[s for s in spec if s['deform']]
names=[s['name'] for s in deforms]
x,y,z=v.T
def smooth(a,b,values):
    t=np.clip((values-a)/(b-a),0,1)
    return t*t*(3-2*t)
def segment_distance(points,a,b):
    a=np.asarray(a,dtype=np.float32);b=np.asarray(b,dtype=np.float32)
    axis=b-a
    t=np.clip(((points-a)*axis).sum(axis=1)/float(np.dot(axis,axis)),0,1)
    return np.linalg.norm(points-(a+t[:,None]*axis),axis=1)
print('AUTHOR: fitted semantic skeleton; solving surface weights',flush=True)
weights=np.zeros((len(v),len(names)),dtype=np.float32)
for j,s in enumerate(deforms):
    distance=segment_distance(v,s['head'],s['tail'])
    score=np.exp(-.5*(distance/s['radius'])**2)
    region=s['region']
    if region.startswith(('front','rear')):
        side=1 if '.L' in region else -1
        sidegate=smooth(-.10,.11,y*side)
        foregate=smooth(-.26,-.035,x) if region.startswith('front') else 1-smooth(-.40,-.14,x)
        heightgate=1-smooth(.65,.82,z)
        score*=sidegate*foregate*heightgate
        if 'digit' in region:score*=(1-smooth(.09,.17,z))*1.7
        elif 'palm' in s['name']:score*=1-smooth(.17,.32,z)
        else:score*=.85
    else:
        score*=smooth(.15,.47,z)
        if region=='plate':score*=smooth(.02,.19,x)*smooth(.61,.79,z)
        if s['name']=='shell.L':score*=smooth(.03,.23,y)
        if s['name']=='shell.R':score*=smooth(.03,.23,-y)
    weights[:,j]=score
# Top-four fields remain continuous at geometric duplicates/UV seams because
# they are computed from the same source coordinates, without changing topology.
indices=np.argpartition(weights,-4,axis=1)[:,-4:]
rows=np.arange(len(v))[:,None]
values=weights[rows,indices]
totals=values.sum(axis=1,keepdims=True)
empty=totals[:,0]<1e-15
indices[empty,:]=names.index('pelvis');values[empty,:]=0;values[empty,0]=1
values/=np.maximum(values.sum(axis=1,keepdims=True),1e-15)
np.savez_compressed(OUT/'skin_weights.npz',bone_names=np.array(names),
                    indices=indices.astype(np.uint16),weights=values)
mesh.vertex_groups.clear()
for j,name in enumerate(names):
    group=mesh.vertex_groups.new(name=name)
    rr,cc=np.nonzero(indices==j)
    for vid,slot in zip(rr,cc):
        weight=float(values[vid,slot])
        if weight>1e-6:group.add([int(vid)],weight,'REPLACE')
    if j%8==0:print('AUTHOR: skin group '+name,flush=True)
del weights
modifier=mesh.modifiers.new('HundredEyedSlag_FittedSkin','ARMATURE')
modifier.object=rig;modifier.use_deform_preserve_volume=False
mesh.parent=rig
rest={b.name:b.matrix_local.copy() for b in arm.bones}
rest_inv={name:m.inverted() for name,m in rest.items()}
rest_np=np.asarray([np.asarray(rest_inv[name],dtype=np.float32) for name in names])
rig['forward_axis']='+X';rig['up_axis']='+Z';rig['height_m']=1.2
rig['rig_method']='Fitted asymmetrical four-limb skeleton with anatomical capsule weight fields'
rig['testing_status']='Not rendered, pose-tested, or imported into UE'
mesh['source_topology_preserved']=True
mesh['source_task']='01a0f0ba-cf66-72c4-8d8e-61c55a3480d8'
(OUT/'skeleton_spec.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_Rigged.blend'))
print('AUTHOR: skinning saved; creating original actions',flush=True)

def sstep(t):
    t=min(1,max(0,t));return t*t*(3-2*t)
def lerp(a,b,t):return a+(b-a)*t
def track(t,keys):
    if t<=keys[0][0]:return np.asarray(keys[0][1],dtype=np.float64)
    for (ta,a),(tb,b) in zip(keys,keys[1:]):
        if t<=tb:return lerp(np.asarray(a,dtype=np.float64),np.asarray(b,dtype=np.float64),sstep((t-ta)/(tb-ta)))
    return np.asarray(keys[-1][1],dtype=np.float64)
def rotation(rx=0,ry=0,rz=0):
    return Quaternion((0,0,1),rz)@Quaternion((0,1,0),ry)@Quaternion((1,0,0),rx)
def around(pivot,shift,rot):
    return Matrix.Translation(Vector(pivot)+Vector(shift))@rot.to_matrix().to_4x4()@Matrix.Translation(-Vector(pivot))
def aim_matrix(name,head,tail):
    old=(arm.bones[name].tail_local-arm.bones[name].head_local).normalized()
    direction=Vector(tail)-Vector(head)
    q=old.rotation_difference(direction.normalized())
    return Matrix.Translation(head)@q.to_matrix().to_4x4()@rest[name].to_3x3().to_4x4()
def solve_limb(key,shoulder,pad,pole,foot_rot):
    d=limbs[key];wrist=pad+foot_rot@(d['wrist']-d['pad'])
    a=(d['elbow']-d['shoulder']).length;b=(d['wrist']-d['elbow']).length
    axis=wrist-shoulder;distance=max(.001,min(axis.length,a+b-.0002))
    axis.normalize()
    elbow_dir=pole-shoulder
    elbow_dir-=axis*elbow_dir.dot(axis)
    if elbow_dir.length<.001:elbow_dir=Vector((0,-1 if key.endswith('R') else 1,0))
    elbow_dir.normalize()
    along=(a*a-b*b+distance*distance)/(2*distance)
    bend=math.sqrt(max(0,a*a-along*along))
    elbow=shoulder+axis*along+elbow_dir*bend
    wrist=shoulder+axis*distance
    return elbow,wrist

contracts=[
 {'name':'Idle','seconds':3.0,'loop':True,'intent':'Slow uneven breathing, shell drift and intermittent front-plate tension'},
 {'name':'Move','seconds':1.6,'loop':True,'reference_speed_m_s':.39,'intent':'Four-beat heavy asymmetric creep; extended support on the large right forelimb'},
 {'name':'Run','seconds':.9,'loop':True,'reference_speed_m_s':.91,'intent':'Low alternating-diagonal scuttle with faster forelimb recovery'},
 {'name':'AttackSweep_R','seconds':1.4,'loop':False,'hit_window_s':[.54,.73],'intent':'Load left supports, raise the large right limb, sweep across the front, recover'},
 {'name':'AttackSlam_R','seconds':1.8,'loop':False,'hit_window_s':[.84,1.00],'intent':'Raise the large right hand, strike downward, absorb impact and recover'},
 {'name':'SpecialAshBurst','seconds':2.4,'loop':False,'release_s':1.0,'hit_window_s':[1.0,1.18],'intent':'Brace all four feet, crouch and tension shell, erupt through the front fissure, recoil; animation only'},
 {'name':'SpecialCharge','seconds':2.0,'loop':False,'hit_window_s':[.56,1.24],'reference_speed_m_s':2.10,'intent':'Crouch and brace, low three-step forward scuttle, decelerate and recover'},
 {'name':'SpecialCharge_RM','seconds':2.0,'loop':False,'root_motion':True,'root_distance_m':1.4,'hit_window_s':[.56,1.24],'intent':'Same charge body motion, with forward root displacement'},
 {'name':'HitFront','seconds':.5,'loop':False,'intent':'Brief backward impulse and damped recovery'},
 {'name':'HitLeft','seconds':.5,'loop':False,'intent':'Impact from left, rightward recoil with supported feet'},
 {'name':'HitRight','seconds':.5,'loop':False,'intent':'Impact from right, leftward recoil with supported feet'},
 {'name':'Stagger','seconds':1.05,'loop':False,'intent':'Strong impact, prolonged loss of support, slow recovery; separate from stun'},
 {'name':'StunEnter','seconds':.6,'loop':False,'intent':'Sink into a braced, drooped stunned pose'},
 {'name':'StunLoop','seconds':2.0,'loop':True,'intent':'Unsteady shell sway, subdued forequarters and asymmetric toe tremor'},
 {'name':'StunExit','seconds':.7,'loop':False,'intent':'Restore shoulder load and return to neutral support'},
 {'name':'Death','seconds':2.8,'loop':False,'ragdoll_handoff_s':1.68,'hold_from_s':2.2,'intent':'Final recoil, buckle large right support, collapse onto right shell, settle and hold'}
]
# Surface samples are used as an authoring floor constraint, not a test.
sample=np.unique(np.concatenate([np.arange(0,len(v),48),np.where(v[:,2]<.025)[0][::5]]))
sv=np.concatenate([v[sample],np.ones((len(sample),1),dtype=np.float32)],axis=1)
si=indices[sample];sw=values[sample]
ground_lifts={}
def deform_floor(target):
    matrices=np.asarray([np.asarray(target[n],dtype=np.float32) for n in names])@rest_np
    zz=np.zeros(len(sample),dtype=np.float32)
    for k in range(4):
        chosen=matrices[si[:,k]]
        zz+=(chosen[:,2,:]*sv).sum(axis=1)*sw[:,k]
    return max(0.0,-float(zz.min()))

def pose_for(action,t,duration):
    body=Vector((0,0,0));angles=Vector((0,0,0));front_angle=0.0;shell_scale=1.0
    pads={k:d['pad'].copy() for k,d in limbs.items()}
    rolls={k:rotation() for k in limbs};digit_curl={k:0.0 for k in limbs}
    phase=2*math.pi*t/duration
    if action=='Idle':
        body.z=.004*math.sin(phase)
        angles.x=.010*math.sin(phase);angles.y=.007*math.sin(phase*2)
        front_angle=.020*math.sin(phase*2)
    elif action in ('Move','Run'):
        run=action=='Run'
        offsets={'front.R':0,'rear.L':0 if run else .25,'front.L':.5,'rear.R':.5 if run else .75}
        stance=.62 if run else .72
        stride=.28 if run else .225
        for k,d in limbs.items():
            f=(t/duration+offsets[k])%1
            if f<stance:
                step=1-2*f/stance;lift=0;pitch=0
            else:
                u=(f-stance)/(1-stance);step=-math.cos(math.pi*u)
                lift=(.11 if run else .066)*math.sin(math.pi*u)**1.3
                pitch=.20*math.sin(math.pi*u)
            pads[k].x+=stride*step
            pads[k].z+=lift
            rolls[k]=rotation(ry=pitch)
            digit_curl[k]=.20*math.sin(math.pi*max(0,(f-stance)/(1-stance))) if f>=stance else 0
        body.z=(.018 if run else .010)*(.5-.5*math.cos(phase*2))
        body.y=.008*math.sin(phase);angles.x=.018*math.sin(phase)
        angles.y=(.020 if run else .012)*math.sin(phase*2)
    elif action=='AttackSweep_R':
        delta=track(t,[(0,(0,0,0)),(.40,(-.03,-.15,.22)),
                      (.54,(.14,-.10,.27)),(.70,(.20,.38,.19)),
                      (.95,(.11,.10,.11)),(1.4,(0,0,0))])
        pads['front.R']+=Vector(delta)
        load=float(track(t,[(0,(0,)),(.40,(1,)),(.70,(.7,)),(1.4,(0,))])[0])
        body.y=.038*load;body.x=.025*load
        angles.z=.12*load;digit_curl['front.R']=.22*load
        front_angle=-.07*load
    elif action=='AttackSlam_R':
        delta=track(t,[(0,(0,0,0)),(.55,(-.03,-.025,.41)),
                      (.72,(.08,0,.36)),(.88,(.12,0,0)),
                      (1.05,(.11,0,0)),(1.8,(0,0,0))])
        pads['front.R']+=Vector(delta)
        load=float(track(t,[(0,(0,)),(.55,(1,)),(.72,(.9,)),(.88,(-.25,)),(1.8,(0,))])[0])
        body.x=-.030*load;body.z=.040*load;body.y=.035*max(0,load)
        angles.y=-.11*load;front_angle=-.06*load;digit_curl['front.R']=.26*max(0,load)
    elif action=='SpecialAshBurst':
        charge=float(track(t,[(0,(0,)),(.78,(1,)),(1.0,(1,)),(1.18,(0,)),(2.4,(0,))])[0])
        pulse=float(track(t,[(0,(0,)),(1.0,(0,)),(1.10,(1,)),(1.34,(-.35,)),(2.4,(0,))])[0])
        body.z=-.075*charge+.045*pulse;body.x=-.025*charge+.06*pulse
        angles.y=.06*charge-.085*pulse;front_angle=-.14*charge-.13*pulse
        shell_scale=1+.030*charge
        if 1.05<t<1.45:
            angles.x=.018*math.sin((t-1.05)*math.pi*24)*(1-(t-1.05)/.4)
    elif action.startswith('SpecialCharge'):
        load=float(track(t,[(0,(0,)),(.45,(1,)),(.55,(1,)),(1.3,(.65,)),(2.0,(0,))])[0])
        body.z=-.055*load;body.x=.045*load;angles.y=.10*load;front_angle=-.06*load
        if .55<t<1.35:
            f0=(t-.55)/.4
            blend=math.sin(math.pi*(t-.55)/.8)**.7
            for k in limbs:
                f=(f0+(0 if k in ('front.R','rear.L') else .5))%1
                pads[k].x+=.20*math.cos(2*math.pi*f)*blend
                pads[k].z+=.080*max(0,math.sin(2*math.pi*f))*blend
                digit_curl[k]=.16*max(0,math.sin(2*math.pi*f))*blend
            body.z+=.014*(1-math.cos(f0*math.pi*4))*blend
    elif action.startswith('Hit') or action=='Stagger':
        impact=float(track(t,[(0,(0,)),(.10,(1,)),(.21,(.35,)),(duration,(0,))])[0])
        if action=='Stagger':
            impact=float(track(t,[(0,(0,)),(.12,(1,)),(.36,(.8,)),(.72,(.4,)),(duration,(0,))])[0])
        sign=-1 if action=='HitLeft' else 1 if action=='HitRight' else 0
        body.x=-.050*impact if not sign else -.008*impact
        body.y=.045*sign*impact;body.z=-.020*impact
        angles.x=-.065*sign*impact;angles.y=-.065*impact if not sign else 0
        front_angle=.06*impact
        if action=='Stagger':
            body.x*=1.5;body.z=-.065*impact;angles.z=.07*impact
    elif action.startswith('Stun'):
        amount=sstep(t/.6) if action=='StunEnter' else 1-sstep(t/.7) if action=='StunExit' else 1
        sway=2*math.pi*t/2 if action=='StunLoop' else 0
        body.z=-.065*amount;body.y=.018*math.sin(sway)*amount
        angles.x=.045*math.sin(sway)*amount;angles.y=.080*amount
        front_angle=.12*amount
        if action=='StunLoop':
            digit_curl['front.R']=.030*(1-math.cos(sway*4))
            digit_curl['front.L']=.020*(1-math.cos(sway*3))
    elif action=='Death':
        fall=sstep((t-.32)/1.50);settle=sstep((t-1.82)/.38)
        body=Vector((-.045*fall,-.12*fall,-.29*fall))
        angles=Vector((1.22*fall,.10*fall,-.12*fall))
        front_angle=.16*fall
        if t<.32:
            recoil=math.sin(math.pi*t/.32);body.x=-.045*recoil;body.z=.012*recoil
        body.z-=.022*settle
        for k in limbs:digit_curl[k]=.50*fall
    global_body=around((-.04,0,.64),body,rotation(*angles))
    target={'root':rest['root'].copy(),'death_pivot':global_body@rest['death_pivot']}
    for name in ['pelvis','spine','chest','carapace','front_plate','shell.L','shell.R']:
        goal=global_body@rest[name]
        if name=='front_plate':
            p=goal.translation.copy()
            goal=Matrix.Translation(p)@rotation(ry=front_angle).to_matrix().to_4x4()@goal.to_3x3().to_4x4()
        if name=='carapace':
            goal=goal@Matrix.Diagonal((1,shell_scale,shell_scale,1))
        target[name]=goal
    for k,d in limbs.items():
        sh=global_body@d['shoulder'];pole=global_body@d['elbow']
        if action=='Death':
            fall=sstep((t-.32)/1.50)
            elbow=global_body@(d['elbow']+Vector((-.035*fall,0,.07*fall)))
            wrist=global_body@(d['wrist']+Vector((-.06*fall,0,.11*fall)))
            pad=global_body@(d['pad']+Vector((-.08*fall,0,.12*fall)))
        else:
            pad=pads[k];elbow,wrist=solve_limb(k,sh,pad,pole,rolls[k])
            # Keep the skin and toes attached even when reach is clamped.
            pad=wrist-rolls[k]@(d['wrist']-d['pad'])
        up,low,palm=d['bones']
        target[up]=aim_matrix(up,sh,elbow)
        target[low]=aim_matrix(low,elbow,wrist)
        target[palm]=aim_matrix(palm,wrist,pad)
        for toe in d['toe_bones']:
            goal=target[palm]@rest[palm].inverted()@rest[toe]
            p=goal.translation.copy()
            q=rotation(ry=digit_curl[k])
            target[toe]=Matrix.Translation(p)@q.to_matrix().to_4x4()@goal.to_3x3().to_4x4()
    for name,parent in [('ash_origin','front_plate'),('attack_origin','front_palm.R')]:
        target[name]=target[parent]@rest[parent].inverted()@rest[name]
    lift=deform_floor(target)
    if lift>0:
        translation=Matrix.Translation((0,0,lift))
        for name in target:
            if name!='root':target[name]=translation@target[name]
    if action=='SpecialCharge_RM':
        distance=1.4*sstep((t-.55)/.70)
        move=Matrix.Translation((distance,0,0))
        for name in target:target[name]=move@target[name]
    return target,lift

rig.animation_data_create()
action_receipts=[]
for contract in contracts:
    name=contract['name'];duration=contract['seconds'];end=round(duration*30)+1
    action=bpy.data.actions.new('A_HundredEyedSlag_'+name)
    action.use_fake_user=True;rig.animation_data.action=action
    lifts=[]
    for f in range(1,end+1):
        t=(f-1)/30;target,lift=pose_for(name,t,duration);lifts.append(lift)
        for b in arm.bones:
            parent=b.parent
            basis=(rest_inv[b.name]@rest[parent.name]@target[parent.name].inverted()@target[b.name]
                   if parent else rest_inv[b.name]@target[b.name])
            pb=rig.pose.bones[b.name];pb.rotation_mode='QUATERNION';pb.matrix_basis=basis
            pb.keyframe_insert('location',frame=f)
            pb.keyframe_insert('rotation_quaternion',frame=f)
            pb.keyframe_insert('scale',frame=f)
        if not rig.animation_data.action_slot and action.slots:rig.animation_data.action_slot=action.slots[0]
    channelbag=action.layers[0].strips[0].channelbag(action.slots[0])
    for curve in channelbag.fcurves:
        for point in curve.keyframe_points:point.interpolation='LINEAR'
    contract={**contract,'fps':30,'start_frame':1,'end_frame_inclusive':end,
              'frame_time_formula':'(frame - 1) / 30',
              'file':'Animations/A_HundredEyedSlag_'+name+'.fbx',
              'action':action.name,'root_motion':contract.get('root_motion',False)}
    for marker,value in [('ContactStart',contract.get('hit_window_s',[None,None])[0]),
                         ('ContactEnd',contract.get('hit_window_s',[None,None])[1]),
                         ('Release',contract.get('release_s')),
                         ('RagdollHandoff',contract.get('ragdoll_handoff_s')),
                         ('CorpseHold',contract.get('hold_from_s'))]:
        if value is not None:action.pose_markers.new(marker).frame=round(value*30)+1
    action_receipts.append(contract);ground_lifts[name]=max(lifts)
    print('AUTHOR: action saved '+name,flush=True)
    (OUT/'animation_contract.json').write_text(
        json.dumps({'actions':action_receipts,'status':'authoring','tested':False},indent=2),encoding='utf-8')

rig.animation_data.action=bpy.data.actions['A_HundredEyedSlag_Idle']
rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_end=91;scene.frame_set(1)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=3.5
            area.spaces.active.region_3d.view_location=(0,0,.55)
            area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_RigAndAnimations.blend'))
receipt={'stage':'rig_and_original_actions_authored','source_task':META['source_task'],
         'bones':len(spec),'deform_bones':len(deforms),'vertices':len(v),
         'source_triangles':META['polygons'],'max_skin_influences':4,
         'weight_method':'Anatomically gated fitted-capsule distance fields, normalized top four',
         'original_topology_and_uv_preserved':True,'height_m':1.2,
         'forward_axis':'+X','up_axis':'+Z','actions':action_receipts,
         'floor_constraint':'Baked surface-sample floor constraint; authoring only, not acceptance',
         'floor_constraint_max_lifts_m':ground_lifts,
         'textures':texture_files,'eye_limit':'Embedded eyes follow shell; no independent pupil or eyelid geometry authored',
         'ue_imported':False,'animation_tested':False,'acceptance_rendered':False}
(OUT/'authoring_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('AUTHORING_COMPLETE '+json.dumps({'bones':len(spec),'deform_bones':len(deforms),
       'actions':len(action_receipts),'vertices':len(v)}),flush=True)
