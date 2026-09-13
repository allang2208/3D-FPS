"""Fit accepted P9 hand poses to M1911 surfaces and correct the rear pivot.

Bounded whole-hand/finger authoring, followed by animation baking. No preview
render, gameplay launch or acceptance tests are part of this script.
"""
import bpy,json,math,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion,Euler
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent;A=O/'Animations';A.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
try:
    bpy.ops.wm.open_mainfile(filepath=str(S/'M1911Hero20260913/M1911_Hero_Editable.blend'))
except RuntimeError as error:
    # Blender completes this file load while reporting old unused library
    # override collections from the original M4 author file as operator errors.
    if 'Missing library override hierarchy root data' not in str(error) or 'SK_M1911_Manny' not in bpy.data.objects or 'M1911_LOW' not in bpy.data.collections:
        raise
s=bpy.context.scene;r=bpy.data.objects['SK_M1911_Manny'];hands=bpy.data.objects['SK_Manny_Arms_Export'];r.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in r.data.bones};names=list(rest)
parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
lr={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
fingers={side:[n for n in names if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))] for side in ['r','l']}
durations=json.loads((S/'M1911P9Retarget20260913/authoring.json').read_text())['durations']
source_actions={kind:bpy.data.actions['M1911_P9_'+kind] for kind in durations}
def pose(a,time):
    r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    f=time*60;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    return {b.name:b.matrix.copy() for b in r.pose.bones}
def basis(p,n):return lr[n].inverted()@(p[parent[n]].inverted()@p[n] if parent[n] else p[n])
def smooth(x):x=max(0.,min(1.,x));return x*x*(3-2*x)
idle=pose(source_actions['idle'],0);aim=pose(source_actions['aim'],0)
reference_poses=[idle,aim];W=idle['WPN_root'];Winv=W.inverted()
mesh_xf=r.matrix_world.inverted()@hands.matrix_world
coords=np.array([list(mesh_xf@v.co)+[1.] for v in hands.data.vertices]);normals=np.array([list(mesh_xf.to_3x3()@v.normal) for v in hands.data.vertices])
weights={n:[] for n in names};dominant=[]
for i,v in enumerate(hands.data.vertices):
    ws=[(hands.vertex_groups[g.group].name,g.weight) for g in v.groups]
    dominant.append(max(ws,key=lambda x:x[1])[0] if ws else '')
    for n,w in ws:
        if n in weights:weights[n].append((i,w))
weights={n:(np.array([i for i,w in vs]),np.array([w for i,w in vs])) for n,vs in weights.items() if vs}
rest_inv={n:rest[n].inverted() for n in names}
def skin(p):
    pts=np.zeros((len(coords),3));ns=np.zeros_like(pts)
    for n,(ids,ws) in weights.items():
        m=np.array(p[n]@rest_inv[n]);pts[ids]+=(coords[ids]@m.T)[:,:3]*ws[:,None];ns[ids]+=(normals[ids]@m[:3,:3].T)*ws[:,None]
    inv=np.array(p['WPN_root'].inverted());return (np.c_[pts,np.ones(len(pts))]@inv.T)[:,:3],ns@inv[:3,:3].T
def gun_surface(p):
    vertices=[];faces=[];grip_vertices=[];grip_faces=[]
    for ob in bpy.data.collections['M1911_LOW'].objects:
        bone=ob['bone'];m=p['WPN_root'].inverted()@p[bone]@rest_inv[bone]
        pts=[m@v.co for v in ob.data.vertices];offset=len(vertices);vertices.extend(pts);faces.extend([tuple(offset+i for i in f.vertices) for f in ob.data.polygons])
        if ob.name in ['M1911_Frame','M1911_LeftWoodPanel','M1911_RightWoodPanel','M1911_GripSafety','M1911_MainspringHousing']:
            offset=len(grip_vertices);grip_vertices.extend(pts);grip_faces.extend([tuple(offset+i for i in f.vertices) for f in ob.data.polygons])
    return BVHTree.FromPolygons(vertices,faces,all_triangles=True),BVHTree.FromPolygons(grip_vertices,grip_faces,all_triangles=True)
surfaces=[gun_surface(p) for p in reference_poses]
hand_ids={side:np.array([i for i,n in enumerate(dominant) if n=='hand_'+side or n in fingers[side]],dtype=int) for side in ['r','l']}
sample_ids={side:ids[np.linspace(0,len(ids)-1,min(420,len(ids))).astype(int)] for side,ids in hand_ids.items()}
contacts={}
idle_pts,idle_ns=skin(idle)
for side in ['r','l']:
    contacts[side]={}
    for digit in ['hand','thumb','index','middle','ring','pinky']:
        ids=[]
        for i in hand_ids[side]:
            if not dominant[i].startswith(digit):continue
            near,normal,face,d=surfaces[0][1].find_nearest(Vector(idle_pts[i]))
            if near is not None and np.dot(idle_ns[i],np.array(near)-idle_pts[i])>0:ids.append(i)
        ids=np.array(ids,dtype=int)
        if len(ids)>80:ids=ids[np.linspace(0,len(ids)-1,80).astype(int)]
        contacts[side][digit]=ids
def finger_pose(p,old,side,parameters,weight=1):
    for n in fingers[side]:
        local=basis(old,n);loc,q,scale=local.decompose()
        digit=n.split('_')[0]
        closure=parameters[6] if digit in ['middle','ring','pinky'] else parameters[7] if digit=='index' else parameters[8]
        # Preserve metacarpals and the thumb opposition base. Only the existing
        # flexion is eased as a group, rather than translating finger joints.
        if 'metacarpal' not in n and n!='thumb_01_'+side:
            if q.w<0:q.negate()
            axis,angle=q.to_axis_angle();q=Quaternion(axis,angle*(1+(closure-1)*weight))
        p[n]=p[parent[n]]@lr[n]@Matrix.LocRotScale(loc,q,scale)
def whole_hand(p,old,side,x,weight=1):
    H=old['WPN_root'].inverted()@old['hand_'+side]
    turn=Euler(tuple(float(v)*weight for v in x[3:6]),'XYZ').to_quaternion()
    H=Matrix.LocRotScale(H.translation+Vector(tuple(float(v)*weight for v in x[:3])),turn@H.to_quaternion(),H.to_scale())
    p['hand_'+side]=old['WPN_root']@H;finger_pose(p,old,side,x,weight)
    return p['hand_'+side]
def distances(tree,pts,ids):
    result=[]
    for i in ids:
        near,normal,face,d=tree.find_nearest(Vector(pts[i]))
        signed=d if np.dot(pts[i]-np.array(near),np.array(normal))>=0 else -d
        result.append(signed)
    return np.array(result)
fitted={};right_trees=[]
def make_right_tree(p):
    pts,_=skin(p);ids=set(hand_ids['r']);faces=[tuple(f.vertices) for f in hands.data.polygons if all(i in ids for i in f.vertices)]
    return BVHTree.FromPolygons([Vector(v) for v in pts],faces,all_triangles=False)
fit_records={}
if '--reuse-fit' in sys.argv:
    fit_records=json.loads((O/'contact_parameters.json').read_text())['hands']
    for side,record in fit_records.items():
        fitted[side]=np.array(record['translation_m']+record['rotation_rad']+[record['closure_middle_ring_pinky'],record['closure_index'],record['closure_thumb_distal']])
for side in ([] if fitted else ['r','l']):
    def objective(x):
        score=0.
        for frame,old in enumerate(reference_poses):
            p={n:m.copy() for n,m in old.items()};whole_hand(p,old,side,x);pts,_=skin(p)
            all_dist=distances(surfaces[frame][0],pts,sample_ids[side]);depth=np.maximum(.0007-all_dist,0)
            score+=70*np.mean(depth**2)+6*np.mean(np.sort(depth)[-30:]**2)
            for digit,ids in contacts[side].items():
                if len(ids)==0 or digit=='index' and side=='r':continue
                ds=distances(surfaces[frame][1],pts,ids);err=np.sort(np.abs(ds-.0009));count=max(4,len(err)//5)
                score+=(2 if digit=='hand' else .5)*np.mean(err[:count]**2)
            if side=='l':
                d=distances(right_trees[frame],pts,sample_ids[side]);penetration=np.maximum(.0008-d,0)
                score+=55*np.mean(penetration**2)+4*np.mean(np.sort(penetration)[-30:]**2)
        score+=.45*np.sum(x[:3]**2)+.0006*np.sum(x[3:6]**2)+.00005*np.sum((x[6:]-1)**2)
        return float(score)
    limits=np.array([.026,.026,.026,math.radians(10),math.radians(10),math.radians(10)])
    best=None
    for closure in [.96,.87]:
        x=np.array([0.,0.,0.,0.,0.,0.,closure,.99,.97]);value=objective(x)
        for ts,rs,cs in [(.006,math.radians(3),.04),(.002,math.radians(1),.015),(.0006,math.radians(.35),.006)]:
            for iteration in range(9):
                changed=False
                for axis,step in enumerate([ts]*3+[rs]*3+[cs]*3):
                    for sign in [-1,1]:
                        cand=x.copy();cand[axis]+=step*sign
                        if np.any(np.abs(cand[:6])>limits) or not(.78<=cand[6]<=1.04 and .91<=cand[7]<=1.035 and .90<=cand[8]<=1.035):continue
                        loss=objective(cand)
                        if loss<value:x,value,changed=cand,loss,True
                if not changed:break
        if best is None or value<best[0]:best=(value,x.copy())
    fitted[side]=best[1];fit_records[side]={'translation_m':list(map(float,best[1][:3])),'rotation_rad':list(map(float,best[1][3:6])),'closure_middle_ring_pinky':float(best[1][6]),'closure_index':float(best[1][7]),'closure_thumb_distal':float(best[1][8]),'author_objective':best[0]}
    if side=='r':
        for old in reference_poses:
            p={n:m.copy() for n,m in old.items()};whole_hand(p,old,'r',fitted['r']);right_trees.append(make_right_tree(p))
    print('M1911_HAND_FIT_AUTHORED',side,fit_records[side],flush=True)
    (O/'contact_parameters.json').write_text(json.dumps({'hands':fit_records,'status':'Surface fitting parameters, not an acceptance report'},indent=2),encoding='utf-8')

def solve_arm(p,old,side,H):
    un,fn,hn='upperarm_'+side,'lowerarm_'+side,'hand_'+side
    shoulder=old[un].translation.copy();elbow=old[fn].translation.copy();wrist=old[hn].translation.copy();target=H.translation
    # Shared small shoulder support keeps the original elbow plane and lengths.
    shift=(target-wrist)*.35;shoulder+=shift
    l1=(elbow-old[un].translation).length;l2=(wrist-elbow).length
    delta=target-shoulder;distance=delta.length;axis=delta.normalized()
    if distance>l1+l2-.002:shoulder+=axis*(distance-(l1+l2-.002));distance=(target-shoulder).length
    pole=elbow-old[un].translation;pole-=axis*pole.dot(axis)
    if pole.length<1e-6:pole=Vector((0,0,-1))-axis*axis.dot(Vector((0,0,-1)))
    pole.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    e=shoulder+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    p['clavicle_'+side].translation+=shoulder-old[un].translation
    for n,pos,direction,was in [(un,shoulder,e-shoulder,elbow-old[un].translation),(fn,e,target-e,wrist-elbow)]:
        p[n]=Matrix.LocRotScale(pos,was.rotation_difference(direction)@old[n].to_quaternion(),old[n].to_scale())
    for n in names:
        if n.endswith('_'+side) and n.startswith(('upperarm_twist','lowerarm_twist')):
            base=un if n.startswith('upperarm') else fn;p[n]=p[base]@old[base].inverted()@old[n]
    p[hn]=H
    if 'ik_hand_'+side in p:p['ik_hand_'+side]=H.copy()
ham_local=rest['WPN_root'].inverted()@rest['WPN_Hammer'];safe_local=rest['WPN_root'].inverted()@rest['WPN_Safety']
held_hands={side:[p['WPN_root'].inverted()@p['hand_'+side] for p in reference_poses] for side in ['r','l']}
records={}
for kind,duration in durations.items():
    samples=[];previous={};frames=[i*.5 for i in range(round(duration*120)+1)]
    for frame in frames:
        old=pose(source_actions[kind],frame/60);p={n:m.copy() for n,m in old.items()};G=p['WPN_root']
        # The donor delta rotates around its own pivot. Transfer the hinge
        # rotation only, re-anchored at M1911's existing pivot; never its orbit.
        D=G.inverted()@old['WPN_Hammer']@ham_local.inverted();q=D.to_quaternion()
        angle=2*math.atan2(q.x,q.w)
        if angle>math.pi:angle-=2*math.pi
        if angle<-math.pi:angle+=2*math.pi
        angle=max(-.62,min(.62,angle*.38))
        p['WPN_Hammer']=G@Matrix.LocRotScale(ham_local.translation,Quaternion((1,0,0),angle)@ham_local.to_quaternion(),ham_local.to_scale())
        p['WPN_Safety']=G@safe_local
        for side in ['r','l']:
            local=G.inverted()@old['hand_'+side];distance=min((local.translation-held.translation).length for held in held_hands[side])
            weight=1. if side=='r' else 1-smooth((distance-.018)/.070)
            if side=='l' and kind in ['reload','reload_empty']:
                # Source hand passes near the grip while seating the magazine.
                # Proximity alone must not apply the support-hand correction
                # to that contact; resume only on the actual return segment.
                t=frame/60;return_start=1.85 if kind=='reload_empty' else 1.25
                weight*=1-smooth((t-.04)/.10)+smooth((t-return_start)/.25)
            if weight>0:
                H=whole_hand(p,old,side,fitted[side],weight);solve_arm(p,old,side,H)
        row={}
        for n in names:
            loc,q,scale=basis(p,n).decompose()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();row[n]=(loc,q,scale)
        samples.append(row)
    action=bpy.data.actions.new('M1911_Contact_'+kind);action.use_fake_user=True;r.animation_data.action=action
    for n in names:
        b=r.pose.bones[n];b.rotation_mode='QUATERNION'
        for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0)
    curves={(c.data_path,c.array_index):c for c in action.layers[0].strips[0].channelbag(action.slots[0]).fcurves}
    for n in names:
        for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
            for axis in range(count):
                c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(frames))
                c.keyframe_points.foreach_set('co',[v for f,row in zip(frames,samples) for v in (f,row[n][field][axis])])
                for key in c.keyframe_points:key.interpolation='LINEAR'
                c.update()
    r.animation_data.action_slot=action.slots[0];s.frame_start=0;s.frame_end=math.ceil(duration*60);s.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(A/('A_M1911_'+kind+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
    records[kind]={'duration':duration,'sample_rate':120,'action':action.name};print('M1911_CONTACT_EXPORTED',kind,flush=True)
    (O/'animations.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
pose(bpy.data.actions['M1911_Contact_idle'],0);s.frame_end=180
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_Contact_Editable.blend'))
print('M1911_CONTACT_AUTHORING_COMPLETE',flush=True)
