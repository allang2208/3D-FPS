"""Author native RSH-12 fire/cock clips from the user's 102-104 s reference.

Four independent fire clips have a new one-second source clock. Other 715
motions stay shared through private sparse profiles. No acceptance rendering.
"""
import bpy,json,math,sys,copy,bisect
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;B=O.parent/'RSH12Integration20261003'
FAMILY=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'single'
SRC=B/('Single' if FAMILY=='single' else 'Dual/'+FAMILY)
OUT=O/FAMILY;OUT.mkdir(parents=True,exist_ok=True)
D=json.loads((O/(FAMILY+'_sources.json')).read_text(encoding='utf8'))
PROFILE=json.loads((SRC/'profile.json').read_text(encoding='utf8'))
META=json.loads((SRC/'authoring.json').read_text(encoding='utf8'))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SRC/('RSH12_'+FAMILY+'_Editable.blend')))
r=next(o for o in bpy.data.objects if o.type=='ARMATURE');r.animation_data_clear()
# The mesh authoring file intentionally uses REST for its bind export. Animation
# baking must evaluate POSE; otherwise FBX exports constant reference transforms.
r.data.pose_position='POSE'
scene=bpy.context.scene;scene.render.fps=120;scene.frame_start=0;scene.frame_end=120
names=[b.name for b in r.data.bones];parents=D['parents']
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
local_rest={n:rest[r.data.bones[n].parent.name].inverted()@rest[n] if r.data.bones[n].parent else rest[n] for n in names}
S=Matrix.Diagonal((1,-1,1,1));cm=Matrix.Diagonal((.01,.01,.01,1))
alignment=Matrix(META['alignment'])
root_rest=rest['WPN_root'];hammer_rest=rest['WPN_Hammer']
# Source geometry is inverse-bound from its new mechanical pivot onto the
# unchanged 715 bind skeleton. Contact must use that transported local surface.
hammer_geometry_bind=Matrix(META['mechanical_bind_matrices']['WPN_Hammer'])
spur_local=hammer_geometry_bind.inverted()@root_rest@alignment@Vector((0,.141,.065))
COCK=math.radians(-27)
def matrix(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
def pack(m):
    p,q,s=m.decompose();return [*p,q.x,q.y,q.z,q.w,*s]
def mix(a,b,w):
    pa,qa,sa=a.decompose();pb,qb,sb=b.decompose()
    return Matrix.LocRotScale(pa.lerp(pb,w),qa.slerp(qb,w),sa.lerp(sb,w))
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def curve(t,keys):
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return x+(y-x)*smooth((t-a)/(b-a))
    return keys[-1][1]
def track_at(track,t):
    tt=track['times'];vv=track['values'];k=max(0,min(len(tt)-1,bisect.bisect_right(tt,t)-1))
    a=vv[k*10:k*10+10]
    if k==len(tt)-1:return a
    b=vv[(k+1)*10:(k+2)*10];w=(t-tt[k])/(tt[k+1]-tt[k])
    qa=Quaternion((a[6],*a[3:6]));qb=Quaternion((b[6],*b[3:6]));q=qa.slerp(qb,w)
    return [*(Vector(a[:3]).lerp(Vector(b[:3]),w)),q.x,q.y,q.z,q.w,*(Vector(a[7:]).lerp(Vector(b[7:]),w))]
def apply_profile(local,entry,t=0):
    result={n:m.copy() for n,m in local.items()}
    for track in entry['tracks']:
        n=track['bone'];v=track_at(track,t);p,q,s=result[n].decompose()
        result[n]=Matrix.LocRotScale(p+Vector(v[:3]),Quaternion((v[6],*v[3:6]))@q,s+Vector(v[7:]))
    return result
def worlds(local):
    result={}
    for n in D['rest']:
        result[n]=result[parents[n]]@local[n] if parents[n] in result else local[n]
    return result
def native_pose(local):
    world=worlds(local)
    return {n:r.matrix_world.inverted()@S@cm@world[n]@S for n in names}
def arm_at(p,old,side,H):
    hn='hand_'+side;delta=H@old[hn].inverted()
    for n in names:
        if n==hn or n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):p[n]=delta@old[n]
    a,b='upperarm_'+side,'lowerarm_'+side
    shoulder=old[a].translation.copy();elbow=old[b].translation;wrist=old[hn].translation;target=H.translation
    l1=(elbow-shoulder).length;l2=(wrist-elbow).length;axis=(target-shoulder).normalized()
    dist=(target-shoulder).length;reach=(l1+l2)*.985
    if dist>reach:
        shoulder+=axis*(dist-reach);dist=reach
        clavicle='clavicle_'+side;p[clavicle]=old[clavicle].copy()
        p[clavicle].translation+=shoulder-old[a].translation
    dist=max(abs(l1-l2)+1e-5,dist)
    along=(l1*l1-l2*l2+dist*dist)/(2*dist)
    pole=elbow-old[a].translation-axis*(elbow-old[a].translation).dot(axis)
    if pole.length<1e-7:pole=Vector((0,0,-1))
    newelbow=shoulder+axis*along+pole.normalized()*math.sqrt(max(0,l1*l1-along*along))
    qa=(elbow-old[a].translation).rotation_difference(newelbow-shoulder)
    qb=(wrist-elbow).rotation_difference(target-newelbow)
    p[a]=Matrix.LocRotScale(shoulder,qa@old[a].to_quaternion(),old[a].to_scale())
    p[b]=Matrix.LocRotScale(newelbow,qb@old[b].to_quaternion(),old[b].to_scale())
    for n in names:
        if n.endswith('_'+side) and n.startswith(('upperarm_twist','lowerarm_twist')):
            owner=a if n.startswith('upperarm') else b;p[n]=p[owner]@old[owner].inverted()@old[n]
    if 'ik_hand_'+side in p:p['ik_hand_'+side]=H.copy()
def finger_pad(side,digit='thumb'):
    bone=digit+'_03_'+side;points=[]
    for ob in bpy.data.objects:
        if ob.type!='MESH':continue
        vg=ob.vertex_groups.get(bone)
        if not vg:continue
        for v in ob.data.vertices:
            if any(g.group==vg.index and g.weight>.6 for g in v.groups):
                points.append(rest[bone].inverted()@r.matrix_world.inverted()@ob.matrix_world@v.co)
    # Finger-pad centroid of the distal third, taken from the actual native skin.
    axis=Vector((0,1,0));points.sort(key=lambda v:v.dot(axis))
    distal=points[-max(1,len(points)//3):]
    return sum(distal,Vector())/len(distal) if distal else Vector((0,.020,0))
def finger_at(p,side,pad,target,weight,digit='thumb',metacarpal=False):
    chain=[digit+'_%02d_%s'%(i,side) for i in (1,2,3)]
    if metacarpal:chain.insert(0,digit+'_metacarpal_'+side)
    old={n:p[n].copy() for n in chain}
    # Offline CCD changes only joint rotations, preserving all phalanx lengths.
    for _ in range(35):
        for i in reversed(range(len(chain))):
            pivot=p[chain[i]].translation;tip=p[chain[-1]]@pad
            a=tip-pivot;b=target-pivot
            if min(a.length,b.length)<1e-7:continue
            q=a.rotation_difference(b);q=Quaternion().slerp(q,.65)
            delta=Matrix.Translation(pivot)@q.to_matrix().to_4x4()@Matrix.Translation(-pivot)
            for n in chain[i:]:p[n]=delta@p[n]
            if metacarpal and i==0:
                n=chain[0];parent=p[parents[n]];local=parent.inverted()@p[n];source=parent.inverted()@old[n]
                angle=source.to_quaternion().rotation_difference(local.to_quaternion()).angle
                if angle>math.radians(25):
                    bounded=Matrix.LocRotScale(local.translation,source.to_quaternion().slerp(local.to_quaternion(),math.radians(25)/angle),local.to_scale())
                    correction=(parent@bounded)@p[n].inverted()
                    for fn in chain:p[fn]=correction@p[fn]
    # Blend local rotations, then reconstruct the chain so no bone is stretched.
    solved_local={n:p[parents[n]].inverted()@p[n] for n in chain}
    previous=p[parents[chain[0]]]
    for n in chain:
        parent=parents[n];base=old[parent] if parent in old else p[parent]
        authored=solved_local[n]
        source=base.inverted()@old[n];m=mix(source,authored,weight);m.translation=source.translation
        p[n]=previous@m;previous=p[n]
    return (p[chain[-1]]@pad-target).length
side='r' if FAMILY in ('single','r') else 'l';pad=finger_pad(side)
hold_pads={digit:finger_pad(side,digit) for digit in ('middle','ring','pinky')}
index_pad=finger_pad(side,'index');canonical_basis=alignment.to_quaternion()
cock_contract=json.loads((O.parent/'RSH12Grip20261003'/('cock_contact_'+FAMILY+'.json')).read_text(encoding='utf8'))
jobs=('fire','aim_fire') if FAMILY=='single' else ('fire',)
receipt=dict(family=FAMILY,duration=1.,sample_hz=120,armature_pose_position=r.data.pose_position,reference='BV1pj411e7Jw 102-104s',
    hammer_fall=.008,thumb_contact=.30,cock_begin=.34,cock_latch=.60,thumb_home=.85,ready=1.,
    cylinder_step_degrees=72,thumb_pad_local=list(pad),hammer_spur_transported_local=list(spur_local),cock_contact_contract=cock_contract,clips=[],contact_samples=[],aim_lower=[.14,.30],aim_return=[.78,1.],testing='Offline local inspection only; no game run')
for kind in jobs:
    basekind='aim' if kind=='aim_fire' else 'idle'
    trigger_recipe=json.loads((O.parent/'RSH12Grip20261003'/('trigger_contact_'+FAMILY+'_'+basekind+'.json')).read_text(encoding='utf8'))
    entry=next(c for c in PROFILE['clips'] if c['kind']==basekind)
    local=apply_profile({n:matrix(v) for n,v in D['clips'][basekind]['samples'][0]['local'].items()},entry)
    base=native_pose(local);oldhammer=base['WPN_Hammer'].copy()
    idle_entry=next(c for c in PROFILE['clips'] if c['kind']=='idle')
    idle=native_pose(apply_profile({n:matrix(v) for n,v in D['clips']['idle']['samples'][0]['local'].items()},idle_entry))
    alternate=idle if kind=='aim_fire' else base
    # Hammer geometry/pivot has already been transported by the RSH profile.
    hp=parents['WPN_Hammer'];hl=base[hp].inverted()@oldhammer
    grip=base['WPN_root'].inverted();native_hand={s:grip@base['hand_'+s] for s in ('r','l') if 'hand_'+s in base}
    act=bpy.data.actions.new('RSH12_'+FAMILY+'_'+kind);act.use_fake_user=True;r.animation_data_create();r.animation_data.action=act
    previous={}
    for frame in range(121):
        t=frame/120
        lower=curve(t,[(0,0),(.14,0),(.30,1),(.78,1),(1,0)]) if kind=='aim_fire' else 0
        held={n:mix(base[n],alternate[n],lower) for n in names};p={n:m.copy() for n,m in held.items()}
        kick=curve(t,[(0,0),(.025,.8),(.06,1),(.13,.45),(.22,0),(1,0)])
        manipulate=curve(t,[(0,0),(.18,0),(.32,1),(.64,1),(.94,0),(1,0)])
        cock=curve(t,[(0,1),(.008,0),(.34,0),(.60,1),(1,1)])
        direction=-1 if side=='r' else 1
        # Source-space -Y forward: recoil rotates muzzle upward about negative X.
        offset=Vector((direction*.006*manipulate,.026*kick+.005*manipulate,.009*kick-.005*manipulate))
        pitch=math.radians(-12 if kind=='aim_fire' else -15)*kick+math.radians(9)*manipulate
        roll=math.radians(20)*direction*manipulate
        motion=Matrix.Translation(offset)@Matrix.Rotation(pitch,4,'X')@Matrix.Rotation(roll,4,'Y')
        gun=held['WPN_root']@motion;delta=gun@held['WPN_root'].inverted()
        for n in names:
            if n.startswith('WPN_'):p[n]=delta@held[n]
        approach=curve(t,[(0,0),(.17,0),(.30,1),(.62,1),(.85,0),(1,0)])
        for s in (('r','l') if FAMILY=='single' else (side,)):
            hand=held['WPN_root'].inverted()@held['hand_'+s]
            if s==side:
                # Surface-fitted regrip clears the palm and proximal fingers.
                pivot=alignment@Vector((0,.153,-.033))
                angles=cock_contract['wrist_rotation_xyz']
                wrist_rotation=Matrix.Rotation(angles[0]*approach,4,'X')@Matrix.Rotation(angles[1]*approach,4,'Y')@Matrix.Rotation(angles[2]*approach,4,'Z')
                wrist_turn=canonical_basis.to_matrix().to_4x4()@wrist_rotation@canonical_basis.inverted().to_matrix().to_4x4()
                hand=Matrix.Translation(pivot)@wrist_turn@Matrix.Translation(-pivot)@hand
                hand.translation+=canonical_basis@Vector(cock_contract['hand_translation_canonical'])*approach
            arm_at(p,held,s,gun@hand)
        hl2=(held[hp].inverted()@held['WPN_Hammer'])@Matrix.Rotation(COCK*cock,4,'X');p['WPN_Hammer']=p[hp]@hl2
        # Index the five-chamber cylinder while cocking, not while pulling the trigger.
        cn='WPN_Cylinder';cl=base[parents[cn]].inverted()@base[cn]
        p[cn]=p[parents[cn]]@(held[parents[cn]].inverted()@held[cn])@Matrix.Rotation(math.radians(72)*curve(t,[(0,0),(.34,0),(.60,1),(1,1)]),4,Vector(META['cylinder_bore_axis_local']))
        for n in names:
            if n.startswith(('WPN_Case_','WPN_Round_')):p[n]=p[cn]@held[cn].inverted()@held[n]
        for digit,held_pad in hold_pads.items():
            n=digit+'_03_'+side;target=delta@held[n]@held_pad
            shift=Vector(cock_contract['grasp_target_translation_canonical'])+Vector(cock_contract.get('digit_target_offsets',{}).get(digit,(0,0,0)))
            target+=p['WPN_root'].to_quaternion()@(canonical_basis@shift)*approach
            finger_at(p,side,held_pad,target,1. if approach>0 else 0.,digit)
        # Descend onto the actual hammer spur and travel with it to the latch.
        contact=p['WPN_Hammer']@spur_local
        side_sign=1 if side=='r' else -1
        contact_offset=Vector(cock_contract['thumb_center_offset_canonical'])
        contact+=p['WPN_root'].to_quaternion()@(canonical_basis@contact_offset)
        held_thumb=delta@held['thumb_03_'+side]@pad
        target=held_thumb.lerp(contact,approach)
        target+=p['WPN_root'].to_quaternion()@(canonical_basis@Vector((side_sign*.015,0,.015)))*math.sin(math.pi*approach)
        error=finger_at(p,side,pad,target,1. if approach>0 else 0.)
        if frame in (36,42,54,72):receipt['contact_samples'].append(dict(clip=kind,time=t,thumb_center_error_mm=error*1000))
        # Short trigger/index squeeze, released before the thumb begins cocking.
        squeeze=curve(t,[(0,0),(.018,1),(.09,1),(.16,0),(1,0)])
        tn='WPN_Trigger';tl=held[parents[tn]].inverted()@held[tn]
        p[tn]=p[parents[tn]]@tl@Matrix.Rotation(math.radians(-7)*squeeze,4,'X')
        trigger_contact=p[tn].translation+p['WPN_root'].to_quaternion()@(canonical_basis@Vector(trigger_recipe['offset_canonical']))
        finger_at(p,side,index_pad,trigger_contact,squeeze,'index',metacarpal=True)
        if approach>0 and cock_contract.get('index_release')!='follow_hand':
            held_index=delta@held['index_03_'+side]@index_pad
            held_index+=p['WPN_root'].to_quaternion()@(canonical_basis@Vector(cock_contract['grasp_target_translation_canonical']))*approach
            finger_at(p,side,index_pad,held_index,1-squeeze,'index')
        scene.frame_set(frame)
        for n in names:
            parent=r.data.bones[n].parent
            lm=p[parent.name].inverted()@p[n] if parent else p[n]
            basis=local_rest[n].inverted()@lm;pos,q,scale=basis.decompose()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();pb=r.pose.bones[n];pb.rotation_mode='QUATERNION';pb.location=pos;pb.rotation_quaternion=q;pb.scale=scale
            for prop in ('location','rotation_quaternion','scale'):pb.keyframe_insert(prop,frame=frame,group=n)
    for la in act.layers:
        for st in la.strips:
            for bag in st.channelbags:
                for fc in bag.fcurves:
                    for k in fc.keyframe_points:k.interpolation='LINEAR'
    name='A_RSH12_'+('' if FAMILY=='single' else FAMILY+'_')+kind
    scene.frame_set(0);bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
        add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,
        bake_anim_step=1,bake_anim_simplify_factor=0)
    receipt['clips'].append(dict(kind=kind,name=name,file=name+'.fbx',destination='/Game/Weapons/RSH12/SingleAction20261003/'+FAMILY))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(name+'_Editable.blend')))
    print('RSH12_SINGLE_ACTION_AUTHORED',FAMILY,kind,flush=True)
# Shared non-fire poses park the hammer cocked. Reload/equip source mechanics
# remain shared; the ready pose transitions the hammer over their authored tail.
new=copy.deepcopy(PROFILE)
for entry in new['clips']:
    if entry['kind'] in jobs:
        job=next(j for j in receipt['clips'] if j['kind']==entry['kind'])
        entry['base']=job['destination']+'/'+job['name'];entry['duration']=1.;entry['tracks']=[];continue
    tr=next((tr for tr in entry['tracks'] if tr['bone']=='WPN_Hammer'),None)
    if not tr:tr=dict(bone='WPN_Hammer',times=[0.],values=[0.,0.,0.,0.,0.,0.,1.,0.,0.,0.]);entry['tracks'].append(tr)
    for i,t in enumerate(tr['times']):
        amount=1 if not entry['kind'].startswith(('single_','equip')) else smooth((t-entry['duration']+.25)/.25)
        v=tr['values'][i*10:i*10+10];q=Quaternion((v[6],*v[3:6]))@Quaternion((1,0,0),-COCK*amount)
        tr['values'][i*10+3:i*10+7]=[q.x,q.y,q.z,q.w]
    if len(tr['times'])==1 and entry['kind'].startswith(('single_','equip')):
        value=tr['values'][:];tr['times']=[0,max(0,entry['duration']-.25),entry['duration']]
        q=Quaternion((1,0,0),-COCK)
        end=value[:];end[3:7]=[q.x,q.y,q.z,q.w];tr['values']=value+value+end
(OUT/'profile.json').write_text(json.dumps(new,separators=(',',':')),encoding='utf8')
(OUT/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
