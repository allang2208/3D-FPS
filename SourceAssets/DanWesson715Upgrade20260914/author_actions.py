"""Fix mechanical axes and author contact-driven revolver reloads.

GitHub Unlicense third-person clips supply hand-path curvature and finger
motion. The 715 contact targets and mechanical tracks are separately authored.
"""
import bpy,json,math,sys,ast
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion,Euler
O=Path(__file__).parent;(O/'Animations').mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(O/'DanWesson715_Hero_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
s=bpy.context.scene;rig=bpy.data.objects['SK_DW715_Manny'];s.render.fps=60
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};parent={b.name:b.parent.name if b.parent else None for b in rig.data.bones};names=[]
def add(n):
    if n in names:return
    if parent[n]:add(parent[n])
    names.append(n)
for n in rest:add(n)
lr={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
root=rest['WPN_root'];gunlocal={n:root.inverted()@rest[n] for n in names if n.startswith('WPN_')}
tree=ast.parse((O.parent/'DanWesson71520260913/author_weapon.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in {'smooth','mix','hand_at'}],type_ignores=[]),'<Manny arm solve>','exec'))
base={};durations={'idle':3.,'aim':1/30,'fire':.4,'aim_fire':.4,'reload':3.6,'reload_empty':3.85}
for kind in ('idle','aim','fire','aim_fire','equip_charge','inspect'):
    a=bpy.data.actions['DW715_'+kind];rig.animation_data_create();rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    duration=float(a.frame_range[1])/60;durations.setdefault(kind,duration);rows=[]
    for i in range(round(duration*120)+1):
        f=i*.5;s.frame_set(int(f),subframe=f%1);rows.append({b.name:b.matrix.copy() for b in rig.pose.bones})
    base[kind]=rows
idle=base['idle'][0];leftlocal=idle['WPN_root'].inverted()@idle['hand_l'];rightlocal=idle['WPN_root'].inverted()@idle['hand_r']
reference=json.loads((O/'Reference/donor-poses.json').read_text())
for d in reference.values():
    d['rest']={n:Matrix(m) for n,m in d['rest'].items()};d['poses']=[{n:Matrix(m) for n,m in p.items()} for p in d['poses']]
def donor(kind,u):
    d=reference['Revolver'+kind];return d['poses'][min(round(max(0,min(1,u))*(len(d['poses'])-1)),len(d['poses'])-1)]
def anatomy(p,hand,index,pinky,middle):
    forward=(p[middle].translation-p[hand].translation).normalized();side=(p[index].translation-p[pinky].translation).normalized();normal=side.cross(forward).normalized();side=forward.cross(normal).normalized()
    return Matrix((side,forward,normal)).transposed().to_quaternion()
source_rest=reference['RevolverReloadInit']['rest']
src_anatomy=anatomy(source_rest,'R_Hand','R_Index1','R_Pinky1','R_Middle1')
dst_anatomy=anatomy(rest,'hand_r','index_01_r','pinky_01_r','middle_01_r')
handmap=rest['hand_r'].to_quaternion().inverted()@dst_anatomy@src_anatomy.inverted()@source_rest['R_Hand'].to_quaternion()
left_anatomy=anatomy(idle,'hand_l','index_01_l','pinky_01_l','middle_01_l')
left_frame_in_hand=idle['hand_l'].to_quaternion().inverted()@left_anatomy
palm_center=(idle['hand_l'].translation+sum((idle[n].translation for n in ('index_01_l','middle_01_l','ring_01_l','pinky_01_l')),Vector())/4)*.5
palm_offset=idle['hand_l'].inverted()@palm_center
thumb_offset=idle['hand_l'].inverted()@idle['thumb_03_l'].translation
local_normal=idle['WPN_root'].to_quaternion().inverted()@(left_anatomy@Vector((0,0,1)))
current_palm=idle['WPN_root'].inverted()@palm_center
palm_sign=1 if local_normal.dot(Vector((0,.040,-.050))-current_palm)>0 else -1
def hand_goal(point,normal,forward,contact='palm'):
    normal=Vector(normal).normalized()*palm_sign;forward=Vector(forward);forward=(forward-normal*forward.dot(normal)).normalized();side=forward.cross(normal).normalized()
    orientation=Matrix((side,forward,normal)).transposed().to_quaternion()@left_frame_in_hand.inverted()
    offset=thumb_offset if contact=='thumb' else palm_offset
    return Matrix.LocRotScale(Vector(point)-orientation@offset,orientation,Vector((1,1,1)))
def around(point,axis,angle):return Matrix.Translation(point)@Matrix.Rotation(angle,4,axis)@Matrix.Translation(-point)
def mech(bone,axis,angle):return around(gunlocal[bone].translation,axis,angle)
def key_sample(keys,t):
    if t<=keys[0][0]:return keys[0][1]
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return x+(y-x)*smooth((t-a)/(b-a))
    return keys[-1][1]
def curved_hand(a,b,w,kind):
    H=mix(a,b,smooth(w));p=donor(kind,w);p0=donor(kind,0);p1=donor(kind,1)
    def relative(row):return row['R_Hand'].inverted()@row['L_Hand'].translation
    delta=relative(p)-relative(p0).lerp(relative(p1),w)
    # Normalize donor units and constrain path shaping to a small local arc.
    length=(p0['L_Forearm'].translation-p0['L_Hand'].translation).length
    delta=rightlocal.to_quaternion()@handmap@(delta/max(length,.0001))
    if delta.length>.9:delta.normalize();delta*=.9
    H.translation+=delta*.022
    return H
def fingers(p,kind,w,strength):
    data=reference['Revolver'+kind];cur=donor(kind,w);start=donor(kind,0);Drest=data['rest'];Dp=data['parents']
    h='hand_l';HandTarget=rest[h].to_quaternion();HandSource=Drest['L_Hand'].to_quaternion()
    mapping=HandTarget.inverted()@anatomy(rest,h,'index_01_l','pinky_01_l','middle_01_l')@anatomy(Drest,'L_Hand','L_Index1','L_Pinky1','L_Middle1').inverted()@HandSource
    for family,src in [('thumb','Thumb'),('index','Index'),('middle','Middle'),('ring','Ring'),('pinky','Pinky')]:
        for i in range(1,4):
            n=f'{family}_{i:02}_l';dn=f'L_{src}{i}';pn=parent[n];dp=Dp[dn]
            delta=(start[dp].inverted()@start[dn]).to_quaternion().inverted()@(cur[dp].inverted()@cur[dn]).to_quaternion()
            qmap=rest[n].to_quaternion().inverted()@HandTarget@mapping@HandSource.inverted()@Drest[dn].to_quaternion()
            q=qmap@delta@qmap.inverted();axis,angle=q.to_axis_angle()
            if angle>math.pi:axis=-axis;angle=2*math.pi-angle
            q=Quaternion(axis,min(angle,.42)*strength)
            local=idle[pn].inverted()@idle[n];loc,rot,scale=local.decompose()
            p[n]=p[pn]@Matrix.LocRotScale(loc,rot@q,scale)
events={'open':.48,'eject':1.03,'rounds_visible':1.44,'insert':2.20,'seat':2.42,'close':3.05,'ready':3.60}
def pose(kind,t):
    reload=kind.startswith('reload');isfire=kind in ('fire','aim_fire')
    old={n:m.copy() for n,m in (idle if reload else base[kind][min(round(t*120),len(base[kind])-1)]).items()};p={n:old.get(n,rest[n]).copy() for n in names};G=old['WPN_root'].copy()
    u=t*3.6/durations[kind] if reload else t
    if reload:
        pitch=key_sample([(0,0),(.32,-12),(.78,-56),(1.08,-56),(1.44,12),(2.65,12),(3.12,4),(3.6,0)],u)
        roll=key_sample([(0,0),(.48,-5),(1.13,-5),(1.44,-12),(2.67,-12),(3.6,0)],u)
        weight=smooth(u/.38)*(1-smooth((u-3.10)/.50))
        G=G@Matrix.LocRotScale(Vector((.028,.048,.026))*weight,Euler((math.radians(pitch),0,math.radians(roll)),'XYZ').to_quaternion(),Vector((1,1,1)))
        hand_at(p,old,'r',G@rightlocal)
    p['WPN_root']=G
    for n,L in gunlocal.items():
        if n!='WPN_root':p[n]=G@L
    p['WPN_Loader']=G@gunlocal['WPN_Loader']@Matrix.Diagonal((.0001,.0001,.0001,1))
    if isfire:
        # Conjugate around the model-space axle, never around bone-local Y.
        turn=mech('WPN_Cylinder','Y',math.radians(60)*smooth(u/.045));p['WPN_Cylinder']=G@turn@gunlocal['WPN_Cylinder']
        for n in ['WPN_Extractor']+[f'WPN_Case_{i}' for i in range(6)]+[f'WPN_Round_{i}' for i in range(6)]:p[n]=G@turn@gunlocal[n]
        pull=smooth(u/.018)*(1-smooth((u-.085)/.11))
        p['WPN_Trigger']=G@mech('WPN_Trigger','X',-.24*pull)@gunlocal['WPN_Trigger']
        p['WPN_Hammer']=G@mech('WPN_Hammer','X',-.45*(1-smooth(u/.035)))@gunlocal['WPN_Hammer']
    if reload:
        open_amount=smooth((u-.22)/.26)*(1-smooth((u-2.80)/.25));D=mech('WPN_Crane','Y',math.radians(-78)*open_amount)
        for n in ('WPN_Crane','WPN_Cylinder','WPN_SOCKET_Magazine','WPN_SOCKET_Eject'):p[n]=G@D@gunlocal[n]
        lift=smooth((u-.85)/.18)*(1-smooth((u-1.07)/.16));p['WPN_Extractor']=G@D@Matrix.Translation((0,.028*lift,0))@gunlocal['WPN_Extractor']
        travel=key_sample([(1.28,.19),(1.70,.095),(2.20,.017),(2.42,0),(2.53,.012),(2.78,.20)],u)
        down=key_sample([(1.28,-.22),(1.72,-.075),(2.12,0),(2.53,0),(2.78,-.22)],u)
        sideways=key_sample([(1.28,-.07),(1.90,-.015),(2.12,0),(2.53,0),(2.78,-.07)],u)
        load_offset=Vector((sideways,travel-.0135,down))
        loaderframe=D@Matrix.Translation(load_offset)@gunlocal['WPN_Loader']
        if 1.40<=u<=2.76:p['WPN_Loader']=G@loaderframe
        C=(D@gunlocal['WPN_Cylinder']).translation
        latch=hand_goal((-.033,-.022,.026),(1,0,0),(0,-.35,1))
        hold=hand_goal(C+Vector((-.027,.004,-.005)),(1,0,0),(0,-.4,1))
        eject_point=D@Vector((0,-.1195+.028*lift,.03092))
        eject=hand_goal(eject_point,(0,1,0),(0,0,1),'thumb')
        loader_palm=D@(Vector((-.017,.015,.02692))+load_offset)
        load=hand_goal(loader_palm,(1,0,0),(0,-1,.1))
        if u<.22:H=curved_hand(leftlocal,latch,u/.22,'ReloadInit');fk,fw='ReloadInit',u/.48
        elif u<.48:H=curved_hand(latch,hold,(u-.22)/.26,'ReloadInit');fk,fw='ReloadInit',u/.48
        elif u<.85:H=curved_hand(hold,eject,(u-.48)/.37,'ReloadInit');fk,fw='ReloadInit',1
        elif u<1.10:H=eject;fk,fw='ReloadInit',1
        elif u<1.44:H=curved_hand(eject,load,(u-1.10)/.34,'SearchAmmo');fk,fw='SearchAmmo',(u-1.10)/.34
        elif u<2.70:H=load;fk,fw='ReloadLoop',min(1,(u-1.44)/.98)
        elif u<2.84:H=curved_hand(load,hold,(u-2.70)/.14,'ReloadEnd');fk,fw='ReloadEnd',0
        elif u<3.05:H=hold;fk,fw='ReloadEnd',.25
        else:H=curved_hand(hold,leftlocal,(u-3.05)/.55,'ReloadEnd');fk,fw='ReloadEnd',(u-3.05)/.55
        hand_at(p,old,'l',G@H)
        fingers(p,fk,fw,.6*smooth(u/.22)*(1-smooth((u-3.05)/.55)))
        for i in range(6):
            bn=f'WPN_Case_{i}';Cpose=G@D@gunlocal[bn]
            if .85<=u<1.30:
                fall=max(0,u-1.03);Cpose=G@D@Matrix.Translation((0,.036*smooth((u-.85)/.18)+fall*.16,0))@gunlocal[bn];Cpose.translation+=Vector((0,0,-1.2*fall*fall))
            elif 1.30<=u<1.44:Cpose=Cpose@Matrix.Diagonal((.0001,.0001,.0001,1))
            elif 1.44<=u<2.42:Cpose=G@D@Matrix.Translation((sideways,travel,down))@gunlocal[bn]
            p[bn]=Cpose;p[f'WPN_Round_{i}']=Cpose@gunlocal[bn].inverted()@gunlocal[f'WPN_Round_{i}']
    return p
actions={}
for kind,duration in durations.items():
    frames=[i*.5 for i in range(round(duration*120)+1)];rows=[];previous={}
    for f in frames:
        p=pose(kind,f/60);row={}
        for n in names:
            basis=lr[n].inverted()@(p[parent[n]].inverted_safe()@p[n] if parent[n] else p[n]);loc,q,scale=basis.decompose()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();row[n]=(loc,q,scale)
        rows.append(row)
    a=bpy.data.actions.new('DW715V2_'+kind);a.use_fake_user=True;rig.animation_data_create();rig.animation_data.action=a
    for n in names:
        rig.pose.bones[n].rotation_mode='QUATERNION'
        for prop in ('location','rotation_quaternion','scale'):rig.pose.bones[n].keyframe_insert(prop,frame=0)
    curves={(c.data_path,c.array_index):c for c in a.layers[0].strips[0].channelbag(a.slots[0]).fcurves}
    for n in names:
        for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
            for axis in range(count):
                c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(frames));c.keyframe_points.foreach_set('co',[v for f,row in zip(frames,rows) for v in (f,row[n][field][axis])])
                for k in c.keyframe_points:k.interpolation='LINEAR'
                c.update()
    rig.animation_data.action_slot=a.slots[0];s.frame_start=0;s.frame_end=round(duration*60);s.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(O/'Animations'/f'A_DW715_{kind}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
    actions[kind]=a;print('DW715_V2_ACTION_EXPORTED',kind,flush=True)
rig.animation_data_clear()
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();copies=[]
for ob in bpy.data.collections['DW715_LOW'].objects:
    x=ob.copy();x.data=ob.data.copy();s.collection.objects.link(x);x.hide_set(False);copies.append(x)
bpy.ops.object.select_all(action='DESELECT')
for ob in copies:ob.select_set(True)
bpy.context.view_layer.objects.active=copies[-1];bpy.ops.object.join();gun=bpy.context.object;gun.name='DW715_Hero_Export'
bpy.ops.object.select_all(action='DESELECT')
for ob in (rig,gun,bpy.data.objects['SK_Manny_Arms_Export']):ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(O/'SK_DW715_Manny.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.data.objects.remove(gun,do_unlink=True)
rig.animation_data_create();rig.animation_data.action=actions['idle'];rig.animation_data.action_slot=actions['idle'].slots[0];s.frame_start=0;s.frame_end=180;s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_Upgrade_Editable.blend'))
(O/'animation.json').write_text(json.dumps({'durations':durations,'events':events,'sample_rate':120,'axis_fix':'Gun-space pivot conjugation; skeleton rest preserved','reference':'ZenXChaos/ThirdPersonShooter-AnimationSets f19adc2ece4cab0f89c9236223abb97d4d2badea; hand arcs and bounded finger deltas','testing':'No game or rendered test'},indent=2),encoding='utf-8')
print('DW715_V2_AUTHORING_COMPLETE',flush=True)
