"""Authored rest skeleton + deterministic skinning + two baked animation clips.
Blender coordinates: Z up, -Y forward. GLB export converts to Y up, +Z forward.
Animation reference: game-dev ordinary zombie v2 sheets, not extracted mocap.
"""
import bpy, bmesh, math, json, sys
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'zombie-model.blend'))
scene=bpy.context.scene
meshes=[o for o in scene.objects if o.type=='MESH']
mesh=meshes[0]
# UV seams are loop data in Blender. Welding their duplicate positions retains UVs.
bm=bmesh.new();bm.from_mesh(mesh.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.00001)
bm.to_mesh(mesh.data);bm.free();mesh.data.update()
mesh.name='ZombieBody'
arm=bpy.data.objects.new('ZombieRig',bpy.data.armatures.new('ZombieSkeleton'))
scene.collection.objects.link(arm);arm.show_in_front=True
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='EDIT')
defs={}
def bone(name,head,tail,parent=None,deform=True):
    b=arm.data.edit_bones.new(name);b.head=head;b.tail=tail;b.use_deform=deform
    if parent:b.parent=arm.data.edit_bones[parent]
    defs[name]={'head':Vector(head),'tail':Vector(tail),'parent':parent}
bone('root',(0,0,0),(0,0,.2),deform=False)
bone('pelvis',(0,.015,.98),(0,.015,1.12),'root')
bone('spine',(0,.015,1.12),(0,.02,1.32),'pelvis')
bone('chest',(0,.02,1.32),(0,.025,1.53),'spine')
bone('neck',(0,.025,1.53),(0,.01,1.67),'chest')
bone('head',(0,.01,1.67),(0,.005,1.88),'neck')
bone('jaw',(0,-.025,1.735),(0,-.115,1.68),'head')
for side,s in [('L',1),('R',-1)]:
    bone('clavicle.'+side,(s*.035,.02,1.49),(s*.305,.035,1.49),'chest')
    bone('upper_arm.'+side,(s*.305,.035,1.49),(s*.505,.045,1.265),'clavicle.'+side)
    bone('forearm.'+side,(s*.505,.045,1.265),(s*.733,-.01,1.025),'upper_arm.'+side)
    bone('hand.'+side,(s*.733,-.01,1.025),(s*.81,-.035,.875),'forearm.'+side)
    bone('thigh.'+side,(s*.16,.025,.985),(s*.235,.025,.585),'pelvis')
    bone('shin.'+side,(s*.235,.025,.585),(s*.275,.035,.135),'thigh.'+side)
    bone('foot.'+side,(s*.275,.035,.135),(s*.30,-.155,.045),'shin.'+side)
bpy.ops.object.mode_set(mode='OBJECT')
for pb in arm.pose.bones:pb.rotation_mode='QUATERNION'
mesh.parent=arm
mod=mesh.modifiers.new('Skeletal deformation','ARMATURE');mod.object=arm
# Semantic region masks avoid cross-body leakage and shorts stretching to hands.
groups={n:mesh.vertex_groups.new(name=n) for n in defs if n!='root'}
def segment_distance(p,a,b):
    ab=b-a;t=max(0,min(1,(p-a).dot(ab)/ab.length_squared));return (p-(a+ab*t)).length
for v in mesh.data.vertices:
    p=v.co;x=abs(p.x);z=p.z;side='L' if p.x>=0 else 'R'
    if z>1.63:
        names=['head','neck']
        if z<1.745 and p.y<-.045 and x<.105:names=['head','jaw','neck']
    elif x>.29 and z>.74:
        names=['clavicle.'+side,'upper_arm.'+side,'forearm.'+side,'hand.'+side]
        if z>1.36 and x<.40:names+=['chest']
    elif z<1.03:
        names=['thigh.'+side,'shin.'+side,'foot.'+side]
        if z>.83:names+=['pelvis']
        if z>.92 and x<.19:names+=['spine']
    else:
        names=['pelvis','spine','chest','neck']
        if z>1.38:names+=['clavicle.'+side,'upper_arm.'+side]
    weights=[]
    for n in names:
        d=segment_distance(p,defs[n]['head'],defs[n]['tail'])
        weights.append((n,1.0/(d+.012)**4))
    weights.sort(key=lambda a:a[1],reverse=True);weights=weights[:4];total=sum(w for n,w in weights)
    for n,w in weights:groups[n].add([v.index],w/total,'REPLACE')
for p in mesh.data.polygons:p.use_smooth=True
# Rest geometry and material remain in the .blend for editable correction.
rest={n:arm.data.bones[n].matrix_local.copy() for n in defs}
lengths={n:(d['tail']-d['head']).length for n,d in defs.items()}
def orient(name,h,t,axial_twist=0):
    d=defs[name];rot=(d['tail']-d['head']).rotation_difference(t-h) @ rest[name].to_quaternion()
    if axial_twist:rot=Quaternion((t-h).normalized(),axial_twist) @ rot
    mat=rot.to_matrix().to_4x4();mat.translation=h
    arm.pose.bones[name].matrix=mat
    bpy.context.view_layer.update()
    return mat
def solve_two(a,target,l1,l2,pole):
    delta=target-a;dist=max(.0001,min(delta.length,l1+l2-.0001));u=delta.normalized()
    middle=(l1*l1-l2*l2+dist*dist)/(2*dist)
    v=pole-u*pole.dot(u)
    if v.length<.001:v=Vector((0,1,0))-u*u.y
    v.normalize();b=a+u*middle+v*math.sqrt(max(0,l1*l1-middle*middle))
    return b,a+u*dist
def lerp(a,b,t):return a+(b-a)*t
def sample(t,keys):
    for i in range(len(keys)-1):
        a,b=keys[i],keys[i+1]
        if t<=b[0]:
            u=max(0,min(1,(t-a[0])/(b[0]-a[0])));u=u*u*(3-2*u)
            return {k:lerp(a[1][k],b[1][k],u) for k in a[1]}
    return keys[-1][1]
def params(lean=.15,drop=.025,forward=0,reach=0,spread=0,twist=0,step=0,jaw=0):return locals()
attack_keys=[(0,params()),(.12,params()),(.22,params(lean=.04,drop=.065,forward=-.035,reach=-.13,twist=-.28)),(.32,params(lean=.08,drop=.085,forward=-.01,reach=.2,twist=-.48,step=.12)),(.375,params(lean=.42,drop=.065,forward=.16,reach=.70,twist=.20,step=.30,jaw=.22)),(.458333,params(lean=.38,drop=.055,forward=.16,reach=.58,twist=.25,step=.30,jaw=.17)),(.62,params(lean=.29,drop=.065,forward=.13,reach=.27,twist=.08,step=.26,jaw=.07)),(.82,params(lean=.21,drop=.045,forward=.06,reach=.08,twist=.025,step=.10)),(1,params())]
# Shoulder-relative wrist targets reconstructed from the source's asymmetric sweep:
# one arm rises out/back during windup, then rakes down as the other reaches lower.
def arms(l,r):return {'L':Vector(l),'R':Vector(r)}
attack_arm_keys=[
 (0,arms((.075,-.12,-.59),(-.075,-.12,-.59))),
 (.12,arms((.075,-.12,-.59),(-.075,-.12,-.59))),
 (.22,arms((.24,.06,-.12),(-.08,-.14,-.40))),
 (.32,arms((.40,.06,.27),(-.24,-.27,-.12))),
 (.375,arms((.10,-.56,.035),(-.08,-.50,-.22))),
 (.458333,arms((-.03,-.52,-.12),(-.06,-.40,-.30))),
 (.62,arms((.05,-.29,-.17),(-.12,-.22,-.42))),
 (.82,arms((.08,-.17,-.47),(-.08,-.14,-.54))),
 (1,arms((.075,-.12,-.59),(-.075,-.12,-.59)))]
def apply_pose(p):
    for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    lean=p['lean'];twist=p['twist'];base=Vector((p.get('sway',0),-p['forward'],.98-p['drop']))
    rot=Matrix.Rotation(twist,3,'Z') @ Matrix.Rotation(p.get('roll',0),3,'Y') @ Matrix.Rotation(lean,3,'X')
    up=rot @ Vector((0,0,1))
    pelvis_tail=base+Vector((0,0,lengths['pelvis']))
    orient('pelvis',base,pelvis_tail)
    spine_tail=pelvis_tail+up*lengths['spine'];orient('spine',pelvis_tail,spine_tail)
    chest_tail=spine_tail+up*lengths['chest'];chest_mat=orient('chest',spine_tail,chest_tail,twist if 'attack_time' in p else 0)
    neck_tail=chest_tail+(Matrix.Rotation(lean+.12,3,'X') @ Vector((0,0,lengths['neck'])))
    orient('neck',chest_tail,neck_tail)
    head_tail=neck_tail+(Matrix.Rotation(lean-.04,3,'X') @ Vector((0,0,lengths['head'])))
    head_mat=orient('head',neck_tail,head_tail)
    head_delta=head_mat @ rest['head'].inverted()
    jh=head_delta @ defs['jaw']['head'];jt=head_delta @ defs['jaw']['tail']
    orient('jaw',jh,jh+(Matrix.Rotation(-p['jaw'],3,'X') @ (jt-jh)))
    chest_delta=chest_mat @ rest['chest'].inverted()
    for side,s in [('L',1),('R',-1)]:
        cl='clavicle.'+side;u='upper_arm.'+side;f='forearm.'+side;h='hand.'+side
        ch=chest_delta @ defs[cl]['head'];shoulder=chest_delta @ defs[cl]['tail'];orient(cl,ch,shoulder)
        reach=p['reach']
        if 'walk_phase' in p:
            reach+=(.035 if side=='L' else .018)*math.sin(p['walk_phase']*math.tau+(0 if side=='L' else math.pi))
            if side=='R':reach+=.035
        # Wrist moves from hanging idle, through retracted windup, into a forward claw.
        wrist=shoulder+Vector((s*(.075+p['spread']),-.12-reach,-.59+max(0,reach)*.68))
        if 'attack_time' in p:wrist=shoulder+sample(p['attack_time'],attack_arm_keys)[side]
        elbow,wrist=solve_two(shoulder,wrist,lengths[u],lengths[f],Vector((s*.5,.8,-.2)))
        orient(u,shoulder,elbow);orient(f,elbow,wrist)
        hand_dir=Vector((s*.08,-.20-max(0,reach),-1+max(0,reach)*1.25)).normalized()
        orient(h,wrist,wrist+hand_dir*lengths[h])
        th='thigh.'+side;sh='shin.'+side;fo='foot.'+side
        hip=base+(defs[th]['head']-defs['pelvis']['head'])
        ankle=defs[sh]['tail'].copy()
        if side=='L':ankle.y-=p['step']
        if side=='L' and 'attack_time' in p:
            at=p['attack_time']
            if .22<at<.375:ankle.z+=.055*math.sin(math.pi*(at-.22)/.155)
            elif .62<at<1:ankle.z+=.035*math.sin(math.pi*(at-.62)/.38)
        if 'walk_phase' in p:
            # Strong leg carries the body longer; weak leg takes a short, low drag step.
            # Both planted feet move backward at ~0.305 m/s in this in-place clip.
            phase=(p['walk_phase']+(0 if side=='L' else .44))%1
            stance=.76 if side=='L' else .48
            travel=.522 if side=='L' else .330
            lift=.07 if side=='L' else .018
            if phase<stance:
                ankle.y+=-travel/2+travel*phase/stance
            else:
                u=(phase-stance)/(1-stance)
                ankle.y+=travel/2-travel*(u*u*(3-2*u))
                ankle.z+=lift*math.sin(math.pi*u)
        knee,ankle=solve_two(hip,ankle,lengths[th],lengths[sh],Vector((s*.08,-1,0)))
        orient(th,hip,knee);orient(sh,knee,ankle)
        orient(fo,ankle,ankle+(defs[fo]['tail']-defs[fo]['head']))
def death_params(pitch=.15,hip_y=0,hip_z=.955,arm_reach=0,leg_extend=0):return locals()
death_keys=[(0,death_params()),(.35,death_params()),(.65,death_params(pitch=.23,hip_y=.055,hip_z=.79)),(.95,death_params(pitch=.13,hip_y=.21,hip_z=.53,arm_reach=.15)),(1.10,death_params(pitch=-.52,hip_y=.40,hip_z=.28,arm_reach=.25)),(1.25,death_params(pitch=-1.48,hip_y=.55,hip_z=.17,arm_reach=.12,leg_extend=.55)),(1.40,death_params(pitch=-1.40,hip_y=.58,hip_z=.20,arm_reach=.07,leg_extend=.8)),(1.60,death_params(pitch=-math.pi/2,hip_y=.62,hip_z=.16,leg_extend=1)),(2,death_params(pitch=-math.pi/2,hip_y=.62,hip_z=.16,leg_extend=1))]
def apply_death(t):
    p=sample(t,death_keys)
    for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    base=Vector((0,p['hip_y'],p['hip_z']))
    up=Matrix.Rotation(p['pitch'],3,'X') @ Vector((0,0,1))
    head=base;mats={}
    for n in ['pelvis','spine','chest','neck','head']:
        tail=head+up*lengths[n];mats[n]=orient(n,head,tail);head=tail
    hd=mats['head'] @ rest['head'].inverted()
    orient('jaw',hd @ defs['jaw']['head'],hd @ defs['jaw']['tail'])
    cd=mats['chest'] @ rest['chest'].inverted()
    pd=mats['pelvis'] @ rest['pelvis'].inverted()
    for side,s in [('L',1),('R',-1)]:
        cl='clavicle.'+side;ua='upper_arm.'+side;fa='forearm.'+side;ha='hand.'+side
        sh=cd @ defs[cl]['tail'];orient(cl,cd @ defs[cl]['head'],sh)
        # Arms hang toward the knees, then settle beside the hips after the back lands.
        down=Vector((s*.09,-.12-p['arm_reach'],-.59))
        final=Vector((s*.11,-.59,-.055))
        blend=max(0,min(1,(t-1.02)/.45));blend=blend*blend*(3-2*blend)
        target=sh+down.lerp(final,blend)
        el,wr=solve_two(sh,target,lengths[ua],lengths[fa],Vector((s*.6,.2,.4)))
        orient(ua,sh,el);orient(fa,el,wr)
        hdir=Vector((s*.08,-.2,-1)).lerp(Vector((s*.1,-1,0)),blend).normalized()
        orient(ha,wr,wr+hdir*lengths[ha])
        th='thigh.'+side;sn='shin.'+side;fo='foot.'+side
        hip=pd @ defs[th]['head'];ankle=defs[sn]['tail'].copy()
        ankle.y-=.275*p['leg_extend'];ankle.z+=.025*p['leg_extend']
        pole=Vector((s*.05,-1,0)).lerp(Vector((s*.05,-.15,1)),blend)
        knee,ankle=solve_two(hip,ankle,lengths[th],lengths[sn],pole)
        orient(th,hip,knee);orient(sn,knee,ankle)
        fd=Matrix.Rotation(-1.2*p['leg_extend'],3,'X') @ (defs[fo]['tail']-defs[fo]['head'])
        orient(fo,ankle,ankle+fd)
    if t>=1.10:
        deps=bpy.context.evaluated_depsgraph_get();ev=mesh.evaluated_get(deps);me=ev.to_mesh()
        low=min((ev.matrix_world @ v.co).z for v in me.vertices);ev.to_mesh_clear()
        arm.pose.bones['root'].location.z+=.003-low
        bpy.context.view_layer.update()

def bake(name,duration):
    arm.animation_data_create();action=bpy.data.actions.new(name);arm.animation_data.action=action
    ticks=sorted(set(list(range(0,round(duration*120)+1,5))+[round(duration*120)]+([45,55] if name=='Attack' else [])))
    for tick in ticks:
        t=tick/120
        if name=='Attack':p=sample(t,attack_keys);p['attack_time']=t
        elif name=='Walk':
            phase=t/duration
            weak_phase=(phase+.44)%1
            buckle=math.sin(math.pi*weak_phase/.48)**2 if weak_phase<.48 else 0
            p=params(lean=.24+.055*buckle,drop=.075+.048*buckle,twist=.018*math.sin(phase*math.tau))
            p.update(walk_phase=phase,sway=.012-.057*buckle,roll=.07*buckle)
        else:p=params(lean=.15+.014*math.sin(t/duration*math.tau),drop=.025+.005*math.sin(t/duration*math.tau),twist=.012*math.sin(t/duration*math.tau))
        scene.frame_set(tick)
        if name=='Death':apply_death(t)
        else:apply_pose(p)
        for pb in arm.pose.bones:
            pb.keyframe_insert('location',frame=tick,group=pb.name)
            pb.keyframe_insert('rotation_quaternion',frame=tick,group=pb.name)
            pb.keyframe_insert('scale',frame=tick,group=pb.name)
    action.use_fake_user=True
    return action
scene.render.fps=120
idle=bake('Idle',4.8);attack=bake('Attack',1);walk=bake('Walk',2.25);death=bake('Death',2)
arm.animation_data.action=None
for action in [idle,attack,walk,death]:
    track=arm.animation_data.nla_tracks.new();track.name=action.name
    strip=track.strips.new(action.name,0,action);track.mute=True
arm.animation_data.action=idle;scene.frame_set(0)
scene.frame_start=0;scene.frame_end=576
report={'bones':len(defs),'vertices_after_welding':len(mesh.data.vertices),'triangles':len(mesh.data.polygons),'clips':{'Idle':4.8,'Attack':1.0,'Walk':2.25},'walk':{'in_place':True,'matching_speed_mps':.305,'style':'asymmetric limp','strong_leg':'L','weak_leg':'R','stance_fractions':[.76,.48],'foot_lift_m':[.07,.018],'weak_load_body_drop_m':.048},'max_influences':4,'animation_source':'hand-authored skeletal reconstruction from 2D sprites','rig_stage':'preview','front':'Blender -Y / glTF +Z','height_m':1.9}
report['clips']['Death']=2.0
(ROOT/'rig-report.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'zombie-rigged.blend'))
bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.export_scene.gltf(filepath=str(ROOT/'zombie-preview.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_frame_step=1,export_def_bones=True)
print(json.dumps(report),flush=True)
if '--export-only' in sys.argv:raise SystemExit(0)
# Offline preview renders: both cameras render actual deformed model, no AI enhancement.
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.cycles.samples=12
camera=scene.camera;camera.data.ortho_scale=2.3
camera.location=(3,-5,1.85);camera.rotation_euler=(Vector((0,-.12,.94))-camera.location).to_track_quat('-Z','Y').to_euler()
for name,action,ticks in [('idle',idle,list(range(0,576,24))),('attack',attack,list(range(0,120,5))),('walk',walk,list(range(0,270,5))),('death',death,list(range(0,240,5)))]:
    if '--walk-only' in sys.argv and name!='walk':continue
    if '--attack-only' in sys.argv and name!='attack':continue
    if '--death-only' in sys.argv and name!='death':continue
    camera.location=(3,-5,1.85);camera.rotation_euler=(Vector((0,-.12,.94))-camera.location).to_track_quat('-Z','Y').to_euler()
    if name=='death':
        camera.data.ortho_scale=2.65;camera.location=(4,-3,2.6);camera.rotation_euler=(Vector((0,.4,.8))-camera.location).to_track_quat('-Z','Y').to_euler()
    arm.animation_data.action=action
    out=ROOT/('frames-'+name);out.mkdir(exist_ok=True)
    for index,tick in enumerate(ticks):
        scene.frame_set(tick);scene.render.filepath=str(out/f'{index:03d}.png');bpy.ops.render.render(write_still=True)
    if name=='attack':
        scene.frame_set(45)
        for v,pos in [('front',(0,-5,1.05)),('side',(5,0,1.05))]:
            camera.location=pos;camera.rotation_euler=(Vector((0,-.12,.94))-camera.location).to_track_quat('-Z','Y').to_euler()
            scene.render.filepath=str(ROOT/f'attack-contact-{v}.png');bpy.ops.render.render(write_still=True)
print('Preview frames complete',flush=True)
