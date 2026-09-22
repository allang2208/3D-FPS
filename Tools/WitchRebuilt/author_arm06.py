"""Anatomical elbow plane, distributed forearm roll and a continuous bottle toss.
Starts from Revision06/Before; preserves body/feet, scale and 0.75 s release.
"""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'Revision06'
ROLES=('Idle','Walk','CastPoison','Hit','TurnLeft','TurnRight','ThrowPoisonBottle')
def smooth(v):v=max(0.,min(1.,v));return v*v*(3-2*v)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def arc(t,keys):
    for j,((ta,a),(tb,b)) in enumerate(zip(keys,keys[1:])):
        if ta<=t<=tb:
            v=(t-ta)/(tb-ta);a=Vector(a);b=Vector(b)
            ma=Vector() if j==0 else (b-Vector(keys[j-1][1]))/(tb-keys[j-1][0])
            mb=Vector() if j+2==len(keys) else (Vector(keys[j+2][1])-a)/(keys[j+2][0]-ta)
            return a*(2*v**3-3*v*v+1)+ma*(tb-ta)*(v**3-2*v*v+v)+b*(-2*v**3+3*v*v)+mb*(tb-ta)*(v**3-v*v)
    return Vector(keys[-1][1])
def frame_basis(direction,normal):
    x=direction.normalized();z=(normal-x*normal.dot(x)).normalized();y=z.cross(x).normalized()
    return Matrix((x,y,z)).transposed()
def export(r,role):
    bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(ROOT/f'Delivery/A_WitchRebuilt_{role}.fbx'),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,
        use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,
        bake_anim_step=1,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')

closed=None;reports={}
for role in ROLES:
    bpy.ops.wm.open_mainfile(filepath=str(OUT/f'Before/Authoring/WitchRebuilt_{role}.blend'))
    s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE');r.data.pose_position='POSE'
    rest={b.name:r.matrix_world@b.matrix_local for b in r.data.bones}
    a0,b0,c0=[rest[n].translation for n in ('upperarm_r','lowerarm_r','hand_r')]
    upper0=(b0-a0).normalized();lower0=(c0-b0).normalized();normal0=upper0.cross(lower0)
    if normal0.length<.03:normal0=Vector((0,-1,0))
    normal0.normalize()
    hand_along=(rest['middle_01_r'].translation-c0).normalized()
    hand_across=(rest['index_01_r'].translation-rest['pinky_01_r'].translation).normalized()
    hand_ref=frame_basis(hand_along,hand_across)
    fingers=[f'{f}_{j:02d}_r' for f in ('thumb','index','middle','ring','pinky') for j in (1,2,3)]
    twists=[n for n in rest if n.startswith(('upperarm_twist_','lowerarm_twist_')) and n.endswith('_r')]
    names=['upperarm_r','lowerarm_r','hand_r','ik_hand_r']+twists+fingers
    cache=[]
    for f in range(s.frame_start,s.frame_end+1):
        s.frame_set(f);cache.append({n:r.pose.bones[n].matrix_basis.copy() for n in names})
    def update():bpy.context.view_layer.update()
    def world(n):return r.matrix_world@r.pose.bones[n].matrix
    def orient(n,q):
        m=world(n);r.pose.bones[n].matrix=r.matrix_world.inverted()@Matrix.LocRotScale(m.translation,q,m.to_scale());update()
    metrics=[];opening=[];last_q={}
    keys=[(0,(0,0,0)),(.22,(.03,-.045,.045)),(.48,(.055,.005,.15)),(.64,(.025,.18,.23)),(.75,(0,.30,.19)),(.88,(-.015,.33,.10)),(1.10,(0,.16,.055)),(1.5,(0,0,0))]
    for i,original in enumerate(cache):
        f=s.frame_start+i;t=i/s.render.fps;s.frame_set(f)
        for n,m in original.items():r.pose.bones[n].matrix_basis=m
        update()
        torso=world('spine_03').to_quaternion()@rest['spine_03'].to_quaternion().inverted()
        forward=torso@Vector((0,-1,0));forward.z=0;forward.normalize();up=Vector((0,0,1));out=forward.cross(up)
        shoulder=world('upperarm_r').translation.copy();b=world('lowerarm_r').translation.copy();c=world('hand_r').translation.copy()
        l1=(b-shoulder).length;l2=(c-b).length
        phase=2*math.pi*i/max(1,len(cache)-1);sway=math.sin(phase);lag=math.sin(phase-.5)-math.sin(-.5)
        target=shoulder+out*(.08+.004*sway)+forward*(.20+.011*lag)-up*(.36+.006*sway)
        pole=shoulder+out*.16+forward*.015-up*.30
        if role=='ThrowPoisonBottle':
            offset=arc(t,keys);target+=out*offset.x+forward*offset.y+up*offset.z
            lead=ramp(t,.27,.61)*(1-ramp(t,.85,1.4));pole+=forward*(.085*lead)+up*(.065*lead)
        direction=(target-shoulder).normalized();length=max(abs(l1-l2)+.015,min((target-shoulder).length,(l1+l2)*.96));target=shoulder+direction*length
        bend=pole-shoulder;bend-=direction*bend.dot(direction);bend.normalize()
        along=(l1*l1-l2*l2+length*length)/(2*length)
        elbow=shoulder+direction*along+bend*math.sqrt(max(0.,l1*l1-along*along))
        udir=(elbow-shoulder).normalized();ldir=(target-elbow).normalized();hinge=udir.cross(ldir).normalized()
        ur=frame_basis(udir,hinge)@frame_basis(upper0,normal0).transposed()
        lr=frame_basis(ldir,hinge)@frame_basis(lower0,normal0).transposed()
        orient('upperarm_r',ur.to_quaternion()@rest['upperarm_r'].to_quaternion())
        orient('lowerarm_r',lr.to_quaternion()@rest['lowerarm_r'].to_quaternion())
        # Keep the bottle upright with an almost straight wrist. The forearm roll
        # is shared by the parent and its existing deformation helpers.
        wrist_dir=(ldir*.85+forward*.15).normalized()
        if role=='ThrowPoisonBottle':wrist_dir=(wrist_dir-up*(.16*ramp(t,.73,.9)*(1-ramp(t,1.05,1.4)))).normalized()
        wanted=frame_basis(wrist_dir,up)@hand_ref.transposed()
        hand_q=wanted.to_quaternion()@rest['hand_r'].to_quaternion()
        neutral_q=world('lowerarm_r').to_quaternion()@rest['lowerarm_r'].to_quaternion().inverted()@rest['hand_r'].to_quaternion()
        delta=hand_q@neutral_q.inverted();v=Vector((delta.x,delta.y,delta.z));project=ldir*v.dot(ldir)
        roll=Quaternion((delta.w,project.x,project.y,project.z)).normalized()
        if roll.w<0:roll.negate()
        parent_roll=Quaternion().slerp(roll,.35)
        orient('lowerarm_r',parent_roll@world('lowerarm_r').to_quaternion())
        for n in twists:
            pb=r.pose.bones[n];pb.matrix_basis=Matrix.Identity(4);update()
            if n.startswith('lowerarm'):
                fraction=max(0.,min(1.,(rest[n].translation-b0).dot(lower0)/(c0-b0).length))
                orient(n,Quaternion().slerp(roll,.65*fraction)@world(n).to_quaternion())
        orient('hand_r',hand_q)
        if role=='ThrowPoisonBottle':
            for finger,delay,amount in [('thumb',-.018,.72),('index',-.008,.92),('middle',0,.90),('ring',.014,.82),('pinky',.024,.75)]:
                release=ramp(t,.724+delay,.790+delay)*(1-ramp(t,1.10+delay,1.47+delay))
                for j in (1,2,3):
                    n=f'{finger}_{j:02d}_r';loc,q,scale=closed[n].decompose();r.pose.bones[n].matrix_basis=Matrix.LocRotScale(loc,q.slerp(Quaternion(),release*amount),scale)
            opening.append(ramp(t,.724,.790)*(1-ramp(t,1.10,1.47)))
        update();r.pose.bones['ik_hand_r'].matrix=r.pose.bones['hand_r'].matrix;update()
        for n in names:
            pb=r.pose.bones[n];pb.rotation_mode='QUATERNION';q=pb.rotation_quaternion.copy()
            if n in last_q and q.dot(last_q[n])<0:q.negate();pb.rotation_quaternion=q
            last_q[n]=q;pb.keyframe_insert('rotation_quaternion',frame=f)
            if n in twists or n=='ik_hand_r':pb.keyframe_insert('location',frame=f);pb.keyframe_insert('scale',frame=f)
        if role=='Idle' and i==0:closed={n:r.pose.bones[n].matrix_basis.copy() for n in fingers}
        points=[world(n).translation for n in ('upperarm_r','lowerarm_r','hand_r')]
        metrics.append({'time':t,'points':[list(p) for p in points],'elbow_flex_degrees':math.degrees((points[1]-points[0]).angle(points[2]-points[1])),'upper_length_cm':(points[1]-points[0]).length*100,'lower_length_cm':(points[2]-points[1]).length*100})
    r['carry_revision']='Arm06';s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/f'Authoring/WitchRebuilt_{role}.blend'));export(r,role)
    reports[role]=metrics
    if role=='ThrowPoisonBottle':throw_opening=opening
manifest_path=ROOT/'Authoring/motion_manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
for role in ROLES:manifest[role]['carry_revision']='Arm06: explicit elbow plane, distributed forearm twist; fixed segment lengths and body tracks retained'
manifest['ThrowPoisonBottle']['source']='Arm06 authored short forward toss based on retained 1.5 s source: elbow lead, continuous release/follow-through, staggered fingers'
manifest['ThrowPoisonBottle']['curves']['GripOpen_r']=throw_opening
manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(OUT/'arm06_motion.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
print('Arm06 authored seven right-arm tracks; 0.75 s release, body and source units retained')
