"""Retarget the original P9 motion onto the existing Manny skin and M1911.

Keeps target rest matrices, skin weights and bone lengths. Source shoulder,
elbow and palm frames drive the complete arms; no M4 grasp pose is reused.
"""
import bpy, pickle, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
O=Path(__file__).parent
with (O/'donor.pkl').open('rb') as f:donor=pickle.load(f)
sr={n:Matrix(m) for n,m in donor['rest'].items()}
for clip in donor['clips'].values():
    for row in clip['samples']:
        row['arms']={n:Matrix(m) for n,m in row['arms'].items()}
        row['weapon']={n:Matrix(m) for n,m in row['weapon'].items()}
        row['gun']=Matrix(row['gun'])
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M1911Integration20260913/M1911_Manny_Editable.blend'))
original=bpy.data.objects['SK_M4_Infima']
scene=bpy.data.scenes.new('M1911_P9_Authoring');bpy.context.window.scene=scene
rig=original.copy();rig.data=original.data.copy();rig.animation_data_clear();scene.collection.objects.link(rig)
hands=bpy.data.objects['SK_Manny_Arms_Export'].copy();hands.data=hands.data.copy();scene.collection.objects.link(hands)
gun=bpy.data.objects['M1911_Export'].copy();gun.data=gun.data.copy();scene.collection.objects.link(gun)
for mesh in (hands,gun):
    mesh.parent=rig;mesh.matrix_parent_inverse=Matrix.Identity(4);mesh.matrix_basis=Matrix.Identity(4)
    for modifier in mesh.modifiers:
        if modifier.type=='ARMATURE':modifier.object=rig
for ob in list(bpy.data.objects):
    if ob not in (rig,hands,gun):bpy.data.objects.remove(ob,do_unlink=True)
for other in list(bpy.data.scenes):
    if other!=scene:bpy.data.scenes.remove(other)
rig.name='SK_M1911_Manny';hands.name='SK_Manny_Arms_Export';gun.name='M1911_Export'
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.render.fps=60
tr={b.name:b.matrix_local.copy() for b in rig.data.bones}
parent={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
names=[]
def add(n):
    if n in names:return
    if parent[n]:add(parent[n])
    names.append(n)
for n in tr:add(n)
lr={n:tr[parent[n]].inverted()@tr[n] if parent[n] else tr[n] for n in names}
for b in rig.pose.bones:
    b.matrix_basis=Matrix.Identity(4)
    for c in list(b.constraints):b.constraints.remove(c)
def rot(m):return m.to_quaternion().to_matrix()
def rigid(p,q):return Matrix.LocRotScale(p,q.to_quaternion() if isinstance(q,Matrix) else q,Vector((1,1,1)))
def smooth(v):v=max(0.,min(1.,v));return v*v*(3-2*v)
def blend(A,B,t):return rigid(A.translation.lerp(B.translation,t),A.to_quaternion().slerp(B.to_quaternion(),t))
def frame(axis,guide):
    x=axis.normalized();z=guide-x*guide.dot(x)
    if z.length<1e-7:z=Vector((0,0,1))-x*x.z
    z.normalize();y=z.cross(x).normalized();return Matrix((x,y,z)).transposed()
def palm(rest,side):
    wrist=rest['hand_'+side].translation
    forward=(rest['middle_01_'+side].translation-wrist).normalized()
    across=rest['index_01_'+side].translation-rest['pinky_01_'+side].translation
    across=(across-forward*across.dot(forward)).normalized()
    return Matrix((across,forward,across.cross(forward))).transposed()
sf={side:palm(sr,side) for side in ['l','r']};tf={side:palm(tr,side) for side in ['l','r']}
localgun={n:tr['WPN_root'].inverted()@m for n,m in tr.items() if n.startswith('WPN_')}
# Align grip volumes, preserving the M1911's original dimensions and geometry.
meta=json.loads((O/'donor.json').read_text())
sourcegrip=next(x for x in meta['weapon_meshes'] if x['material']=='Grip')
sg=(Vector(sourcegrip['min'])+Vector(sourcegrip['max']))*.5
gripids={i for poly in gun.data.polygons if gun.data.materials[poly.material_index].name=='M_M1911_Grip' for i in poly.vertices}
gp=[tr['WPN_root'].inverted()@gun.data.vertices[i].co for i in gripids]
tg=Vector([(min(v[k] for v in gp)+max(v[k] for v in gp))*.5 for k in range(3)])
gunfit=Matrix.Translation(sg-tg)
idle=donor['clips']['idle']['samples'][0]
mechbind={n:idle['gun'].inverted()@m for n,m in idle['weapon'].items()}

def source(key,t):
    clip=donor['clips'][key];i=min(round(max(0,t)*120),len(clip['samples'])-1)
    return clip['samples'][i]

def arms_pose(sp):
    p={n:m.copy() for n,m in tr.items()}
    for side in ['l','r']:
        un,fn,hn='upperarm_'+side,'lowerarm_'+side,'hand_'+side
        a,e,w=[sp[n].translation for n in (un,fn,hn)]
        upper=(e-a).normalized();fore=(w-e).normalized()
        l1=(tr[fn].translation-tr[un].translation).length;l2=(tr[hn].translation-tr[fn].translation).length
        # Work backward from the contact wrist with Manny's fixed bone lengths.
        # Both segment directions and the changing elbow plane come from P9.
        W=w.copy();E=W-fore*l2;A=E-upper*l1
        for n,child,pos,axis in [(un,fn,A,upper),(fn,hn,E,fore)]:
            sd=rot(sp[n])@rot(sr[n]).transposed()
            targetframe=frame(tr[child].translation-tr[n].translation,tf[side].col[2])
            poseframe=frame(axis,sd@sf[side].col[2])
            p[n]=rigid(pos,poseframe@targetframe.transposed()@rot(tr[n]))
        sd=rot(sp[hn])@rot(sr[hn]).transposed()
        p[hn]=rigid(W,sd@sf[side]@tf[side].transposed()@rot(tr[hn]))
        cn='clavicle_'+side
        # Keep the clavicle/upperarm rest offset intact at the shoulder seam.
        cq=rot(p[un])@rot(tr[un]).transposed()@rot(tr[cn])
        p[cn]=rigid(A-cq@rot(tr[cn]).transposed()@(tr[un].translation-tr[cn].translation),cq)
        hd=rot(p[hn])@rot(tr[hn]).transposed();Amap=tf[side]@sf[side].transposed()
        shd=rot(sp[hn])@rot(sr[hn]).transposed()
        for n in names:
            if not (n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))):continue
            pn=parent[n];restloc=lr[n].translation
            position=p[pn]@restloc
            if n in sp:
                delta=shd.transposed()@rot(sp[n])@rot(sr[n]).transposed()
                q=hd@Amap@delta@Amap.transposed()@rot(tr[n])
            else:
                # Manny metacarpals have no P9 track: retain their local rest
                # frame instead of applying a proximal-finger rotation twice.
                q=rot(p[pn])@rot(lr[n])
            p[n]=rigid(position,q)
        for n in names:
            if not(n.endswith('_'+side) and n.startswith(('upperarm_twist','lowerarm_twist'))):continue
            base=un if n.startswith('upperarm') else fn
            pose=p[base]@tr[base].inverted()@tr[n]
            if base==fn:
                predicted=rot(p[fn])@rot(tr[fn]).transposed()@rot(tr[hn])
                delta=(rot(p[hn])@predicted.transposed()).to_quaternion()
                projected=fore*Vector((delta.x,delta.y,delta.z)).dot(fore)
                twist=Quaternion((delta.w,*projected));twist.normalize()
                span=tr[hn].translation-tr[fn].translation
                fraction=max(0.,min(1.,(tr[n].translation-tr[fn].translation).dot(span)/span.length_squared))
                q=Quaternion((1,0,0,0)).slerp(twist,fraction)@pose.to_quaternion()
                pose=rigid(pose.translation,q)
            p[n]=pose
        for n in ['ik_hand_'+side]:
            if n in p:p[n]=p[hn].copy()
    return p

def mechanical(row,bone):return row['gun'].inverted()@row['weapon'][bone]@mechbind[bone].inverted()
# Derive the actual mechanical contact clock from the original continuous tracks.
events={}
for key in ['reload','reload_empty']:
    clip=donor['clips'][key];samples=clip['samples']
    magdist=[mechanical(row,'SOCKET_Magazine').translation.length for row in samples]
    far=max(range(len(magdist)),key=magdist.__getitem__)
    outtime=next((i/120 for i,d in enumerate(magdist) if d>.012),0.)
    inserttime=next((i/120 for i in range(far,len(magdist)) if magdist[i]<.045),clip['duration']-.4)
    seattime=next((i/120 for i in range(far,len(magdist)) if magdist[i]<.002),clip['duration']-.25)
    events[key]={'mag_out':outtime,'mag_insert':inserttime,'mag_seat':seattime}
empty=donor['clips']['reload_empty']
slide_dist=[mechanical(row,'slide').translation.length for row in empty['samples']]
slide_max=max(slide_dist)
seat_index=round(events['reload_empty']['mag_seat']*120)
release_index=next((i for i in range(seat_index,len(slide_dist)) if slide_dist[i]<max(.001,slide_max*.1)),len(slide_dist)-1)
events['reload_empty']['slide_release']=release_index/120
# P9 releases the locked slide; it does not contain an overhand slide pull.
# Its original Unholster is the equip donor. The former Godot 1.75-second
# crop starts after slide release and is therefore not a slide-rack animation.
equip_duration=donor['clips']['draw']['duration']
events['equip_charge']={}

def pose(kind,t):
    equip=kind.startswith('equip_charge')
    sourcekey='draw' if equip else {'idle_empty':'idle','aim_empty':'aim','fire_last':'fire','aim_fire_last':'aim_fire'}.get(kind,kind)
    st=t
    row=source(sourcekey,st);p=arms_pose(row['arms'])
    G=row['gun']@gunfit
    p['WPN_root']=G
    if 'ik_hand_gun' in p:p['ik_hand_gun']=G@localgun.get('WPN_root',Matrix.Identity(4))
    for n,L in localgun.items():
        if n!='WPN_root':p[n]=G@L
    # Carry the donor magazine's translation/rotation, preserving target pivots.
    if not equip:p['WPN_SOCKET_Magazine']=G@mechanical(row,'SOCKET_Magazine')@localgun['WPN_SOCKET_Magazine']
    slide_delta=mechanical(row,'slide')
    if slide_max>.001:slide_delta.translation*=.033/slide_max
    if kind in ['idle_empty','aim_empty'] or kind.endswith('fire_last'):
        amount=.033 if not kind.endswith('fire_last') else .033*smooth(t/.035)
        slide_delta=Matrix.Translation((0,amount,0))
    if equip:
        slide_delta=Matrix.Translation((0,.033 if kind.endswith('empty') else 0,0))
    p['WPN_Slide']=G@slide_delta@localgun['WPN_Slide']
    travel=slide_delta.translation.y
    p['WPN_Barrel']=G@Matrix.Translation((0,travel*.07,-travel*.05))@localgun['WPN_Barrel']
    if kind in ['fire','aim_fire','fire_last','aim_fire_last']:
        trigger=.002*smooth(t/.018)*(1-smooth((t-.06)/.06))
        p['WPN_Trigger']=G@Matrix.Translation((0,trigger,0))@localgun['WPN_Trigger']
    if 'hammer' in row['weapon']:p['WPN_Hammer']=G@mechanical(row,'hammer')@localgun['WPN_Hammer']
    for n in ['WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Eject']:p[n]=p['WPN_Slide']@lr[n]
    for n in ['WPN_Bullet','WPN_Follower']:p[n]=p['WPN_SOCKET_Magazine']@lr[n]
    if kind in ['idle_empty','aim_empty','equip_charge_empty'] or kind=='reload_empty' and t<events['reload_empty']['mag_out']:
        p['WPN_Bullet'].translation+=G.to_quaternion()@Vector((0,0,-.065))
    return p

durations={'idle':3.,'idle_empty':3.,'aim':1/30,'aim_empty':1/30,
           'fire':donor['clips']['fire']['duration'],'aim_fire':donor['clips']['aim_fire']['duration'],
           'fire_last':donor['clips']['fire']['duration'],'aim_fire_last':donor['clips']['aim_fire']['duration'],
           'reload':donor['clips']['reload']['duration'],'reload_empty':empty['duration'],
           'equip_charge':equip_duration,'equip_charge_empty':equip_duration,
           'inspect':donor['clips']['inspect']['duration']}
actions={}
for kind,duration in durations.items():
    frames=[i*.5 for i in range(round(duration*120)+1)]
    samples=[];previous={}
    for f in frames:
        p=pose(kind,f/60);sample={}
        for n in names:
            basis=lr[n].inverted()@(p[parent[n]].inverted()@p[n] if parent[n] else p[n])
            loc,q,scale=basis.decompose()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();sample[n]=(loc,q,scale)
        samples.append(sample)
    a=bpy.data.actions.new('M1911_P9_'+kind);a.use_fake_user=True;rig.animation_data_create();rig.animation_data.action=a
    for n in names:
        b=rig.pose.bones[n];b.rotation_mode='QUATERNION'
        for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
    bag=a.layers[0].strips[0].channelbag(a.slots[0]);curves={(fc.data_path,fc.array_index):fc for fc in bag.fcurves}
    for n in names:
        for prop,idx,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
            for axis in range(count):
                fc=curves[(f'pose.bones["{n}"].{prop}',axis)];fc.keyframe_points.clear();fc.keyframe_points.add(len(frames))
                fc.keyframe_points.foreach_set('co',[v for f,row in zip(frames,samples) for v in (f,row[n][idx][axis])])
                for k in fc.keyframe_points:k.interpolation='LINEAR'
                fc.update()
    rig.animation_data.action_slot=a.slots[0];scene.frame_start=0;scene.frame_end=math.ceil(frames[-1]);actions[kind]=a
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(O/f'A_M1911_{kind}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
# Export the mesh in its true bind pose, separately from the animated idle pose.
rig.animation_data_clear()
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
for ob in (rig,hands,gun):ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(O/'SK_M1911_Manny.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False)
rig.animation_data_create();rig.animation_data.action=actions['idle'];rig.animation_data.action_slot=actions['idle'].slots[0]
scene.frame_set(0);scene.frame_start=0;scene.frame_end=180
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_P9_Manny_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'durations':durations,'events':events,'sample_rate':120,'grip_offset':list(gunfit.translation),'source_slide_travel':slide_max,'source':'Original Infima P9 FBX tracks','manny':'Existing target rest, mesh and weights preserved','runtime_testing':'Not performed; user testing pending'},indent=2),encoding='utf-8')
print('M1911_P9_AUTHORED',flush=True)
