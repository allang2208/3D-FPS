"""RSH-12 V7 grip first, then double-action motion from BV1vh4HejEUF 0-22 s.

Offline production only. No preview, game run or acceptance rendering.
Uses the preserved native 715 skeleton, original RSH surfaces and bore fit.
"""
import bpy, json, math, sys, copy, bisect
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
O = Path(__file__).parent
sys.path.insert(0, str(O))
import pose_math as M
B = O.parent / 'RSH12Integration20261003'
G = O.parent / 'RSH12Grip20261003'
FAMILY = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'single'
MODE = sys.argv[sys.argv.index('--') + 2] if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 2 else 'all'
SRC = B / ('Single' if FAMILY == 'single' else 'Dual/' + FAMILY)
OUT = O / FAMILY
OUT.mkdir(exist_ok=True)
D = json.loads((O / (FAMILY + '_sources.json')).read_text(encoding='utf8'))
PROFILE = json.loads((SRC / 'profile.json').read_text(encoding='utf8'))
META = json.loads((SRC / 'authoring.json').read_text(encoding='utf8'))
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SRC / ('RSH12_' + FAMILY + '_Editable.blend')))
r = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
r.animation_data_clear()
r.data.pose_position = 'POSE'
scene = bpy.context.scene
scene.render.fps = 120
names = list(r.data.bones.keys())
parents = D['parents']
rest = {b.name: b.matrix_local.copy() for b in r.data.bones}
local_rest = {n: rest[parents[n]].inverted() @ rest[n] if parents[n] in rest else rest[n] for n in names}
S = Matrix.Diagonal((1, -1, 1, 1))
cm = Matrix.Diagonal((.01, .01, .01, 1))
alignment = Matrix(META['alignment'])
for key in ('D', 'names', 'parents', 'r', 'rest', 'S', 'cm'):
    setattr(M, key, globals()[key])
side = 'l' if FAMILY == 'l' else 'r'
hands = ('r', 'l') if FAMILY == 'single' else (side,)
smooth, curve, mix = M.smooth, M.curve, M.mix

def source(kind, t=0):
    clip = D['clips'][kind]
    rows = clip['samples']
    times = [a['time'] for a in rows]
    i = max(0, min(len(rows)-1, bisect.bisect_right(times, t)-1))
    local = {n:M.matrix(v) for n,v in rows[i]['local'].items()}
    if i+1 < len(rows):
        w = max(0,min(1,(t-times[i])/(times[i+1]-times[i])))
        local = {n:mix(v,M.matrix(rows[i+1]['local'][n]),w) for n,v in local.items()}
    entry = next(e for e in PROFILE['clips'] if e['kind']==kind)
    return M.native_pose(M.apply_profile(local,entry,t))

def local_pose(p):
    return {n:p[parents[n]].inverted()@p[n] if parents[n] in p else p[n] for n in names}

base = source('idle')
canonical = base['WPN_root'] @ rest['WPN_root'].inverted() @ rest['WPN_root'] @ alignment
canonical_q = alignment.to_quaternion()

def point(c, p=base):
    return p['WPN_root'] @ alignment @ Vector(c)

def finger_rel(p, s):
    return {n:p[parents[n]].inverted()@p[n] for n in names if n.endswith('_'+s) and n.startswith(('thumb','index','middle','ring','pinky'))}

# Refine the trigger finger against mixed-weight skin. Other accepted grip
# joints remain intact, and ADS inherits this exact gun-relative grasp.
def fit_index(p):
    import numpy as np
    from mathutils.bvhtree import BVHTree
    raw=json.loads((B/'canonical_parts.json').read_text(encoding='utf8'))
    root=p['WPN_root']@alignment
    inv=root.inverted()
    solids=[]
    for part in raw:
        if part['name'] not in ('9_l','7_l','11_l','17_l'):continue
        verts=[Vector(v) for v in part['verts']]
        lo=Vector(tuple(min(v[a] for v in verts) for a in range(3)))
        hi=Vector(tuple(max(v[a] for v in verts) for a in range(3)))
        solids.append((part['name'],BVHTree.FromPolygons(verts,part['faces']),lo,hi))
    trigger=next(x[1] for x in solids if x[0]=='17_l')
    samples=[]
    for ob in bpy.data.objects:
        if ob.type!='MESH':continue
        groups={g.index:g.name for g in ob.vertex_groups}
        for v in ob.data.vertices:
            weights=[(groups[g.group],g.weight) for g in v.groups if groups[g.group] in rest and g.weight>.001]
            label=max(weights,key=lambda nw:nw[1])[0] if weights else ''
            if label.startswith('index_') and label.endswith('_'+side):
                samples.append((r.matrix_world.inverted()@ob.matrix_world@v.co,weights,label))
    used=list({n for _,ww,_ in samples for n,w in ww})
    coords=np.asarray([[*v,1.] for v,_,_ in samples])
    weights=np.asarray([[dict(ww).get(n,0.) for n in used] for _,ww,_ in samples])
    weights/=weights.sum(axis=1)[:,None]
    binds=np.asarray([rest[n].inverted() for n in used])
    distal=[i for i,(v,ww,label) in enumerate(samples) if label=='index_03_'+side]
    distal.sort(key=lambda i:(rest['index_03_'+side].inverted()@samples[i][0]).y)
    distal=distal[-max(1,len(distal)//3):]
    direction=Vector((.371,.691,.591)).normalized()
    pad=M.finger_pad(side,'index')
    def evaluate(target,ret=False):
        result={n:m.copy() for n,m in p.items()}
        M.finger_at(result,side,pad,root@Vector(target),1.,'index',metacarpal=True)
        mats=np.asarray([inv@result[n] for n in used])@binds
        pts=np.einsum('bij,pj,pb->pi',mats,coords,weights,optimize=True)[:,:3]
        depths=[]
        for pt in pts:
            v=Vector(pt);dep=0.
            for _,tree,lo,hi in solids:
                if any(v[a]<lo[a] or v[a]>hi[a] for a in range(3)):continue
                origin=v+direction*1e-7;count=0
                for _ in range(10):
                    hit,_,_,_=tree.ray_cast(origin,direction,.4)
                    if hit is None:break
                    count+=1;origin=hit+direction*1e-6
                if count%2:dep=max(dep,tree.find_nearest(v)[3]*1000)
            depths.append(dep)
        gap=min(trigger.find_nearest(Vector(pts[i]))[3]*1000 for i in distal)
        penalty=sum(max(0,d-.25)**2 for d in depths)/len(depths)*60+max(depths)**2*100+max(0,gap-.25)**2*80
        return (penalty,result,target) if ret else penalty
    recipe=json.loads((G/('trigger_contact_'+FAMILY+'_idle.json')).read_text(encoding='utf8'))
    x=list(inv@p['WPN_Trigger'].translation+Vector(recipe['offset_canonical']))
    cost=evaluate(x)
    for step in (.006,.003,.0015,.0007):
        for _ in range(2):
            for axis in range(3):
                best=x[:];bestcost=cost
                for sign in (-1,1):
                    q=x[:];q[axis]+=step*sign
                    if abs(q[0])>.04 or not .055<q[1]<.13 or not -.02<q[2]<.04:continue
                    score=evaluate(q)
                    if score<bestcost:best=q;bestcost=score
                x=best;cost=bestcost
    _,result,target=evaluate(x,True)
    return result,dict(target_canonical=target,pad_local=list(pad),method='full mixed-weight index skin constrained to trigger/guard; fixed-length CCD; other fingers preserved')

if MODE in ('all','grip'):
    base,index_recipe=fit_index(base)
    grip={s:dict(hand=M.pack(base['WPN_root'].inverted()@base['hand_'+s]),fingers={n:M.pack(m) for n,m in finger_rel(base,s).items()}) for s in hands}
    # Park the uncocked hammer using the geometry's transported bind frame.
    hammer_parent=parents['WPN_Hammer']
    base['WPN_Hammer']=base[hammer_parent] @ local_rest['WPN_Hammer']
    mech=Matrix(META['mechanical_bind_matrices']['WPN_Hammer'])
    base['WPN_Hammer']=base['WPN_root']@rest['WPN_root'].inverted()@mech
    (OUT/'grip.json').write_text(json.dumps(dict(revision='double-action-v1',family=FAMILY,hands=grip,index=index_recipe,base={n:M.pack(m) for n,m in base.items()},reference='BV1vh4HejEUF 0-22s',user_tested=False),indent=2),encoding='utf8')
    ue=lambda m:S@r.matrix_world@m@S
    markers={n:list((ue(base[n])).translation*100) for n in ('WPN_FrontSight','WPN_RearSight','WPN_Cylinder','hand_r') if n in base}
    (OUT/'framing_input.json').write_text(json.dumps(markers,indent=2))
    print('RSH12_GRIP_AUTHORED',FAMILY,flush=True)
else:
    held=json.loads((OUT/'grip.json').read_text(encoding='utf8'))
    base={n:M.matrix(v) for n,v in held['base'].items()}
    index_recipe=held['index'];grip=held['hands']

if MODE=='grip':
    sys.exit(0)

# A compact, five-lug speedloader is bound to the existing loader bone.
# Its cartridges are the actual five RSH case/round bones, never six donor rounds.
loader_material=bpy.data.materials.new('M_RSH12_LoaderPolymer')
loader_material.diffuse_color=(.045,.048,.052,1)
loader_parts=[]
def loader_cylinder(radius,depth,position,vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=position)
    ob=bpy.context.object
    ob.rotation_euler.x=math.pi/2
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    loader_parts.append(ob)
loader_cylinder(.026,.010,(0,0,0))
loader_cylinder(.010,.024,(0,.017,0),32)
loader_cylinder(.014,.006,(0,.030,0),40)
for i in range(5):
    a=i*math.tau/5
    loader_cylinder(.007,.008,(.020*math.cos(a),-.007,.020*math.sin(a)),24)
bpy.ops.object.select_all(action='DESELECT')
for ob in loader_parts:ob.select_set(True)
bpy.context.view_layer.objects.active=loader_parts[0]
bpy.ops.object.join()
loader=bpy.context.object;loader.name='RSH12_FiveRoundLoader'
# Local +Y is rearward along the bore; transform it into the native bind bone.
for v in loader.data.vertices:v.co=rest['WPN_Loader']@v.co
loader.data.materials.append(loader_material)
loader.vertex_groups.new(name='WPN_Loader').add(list(range(len(loader.data.vertices))),1.,'REPLACE')
loader.parent=r
loader.modifiers.new('NativeBinding','ARMATURE').object=r
mesh_name='SK_RSH12_Manny' if FAMILY=='single' else 'SK_Dual_RSH12_'+FAMILY
r.data.pose_position='REST'
bpy.ops.object.select_all(action='DESELECT')
meshes=[ob for ob in bpy.data.objects if ob.type=='MESH']
for ob in meshes:ob.select_set(True)
bpy.context.view_layer.objects.active=meshes[0]
bpy.ops.object.join()
r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(OUT/(mesh_name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE')
r.data.pose_position='POSE'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('RSH12_'+FAMILY+'_Editable.blend')))

def park_loader(p):
    p['WPN_Loader']=Matrix.LocRotScale(Vector((0,0,-3)),Quaternion(),Vector((.0001,)*3))

def held_pose(kind='idle',t=0):
    p=source(kind,t) if kind in D['clips'] else {n:m.copy() for n,m in base.items()}
    # Preserve donor movement, but retain the same physical grip in every state.
    for s in hands:
        rel=M.matrix(grip[s]['hand'])
        M.arm_at(p,p.copy(),s,p['WPN_root']@rel)
        for n,v in grip[s]['fingers'].items():p[n]=p[parents[n]]@M.matrix(v)
    hp=parents['WPN_Hammer']
    p['WPN_Hammer']=p[hp]@(base[hp].inverted()@base['WPN_Hammer'])
    park_loader(p)
    return p

idle=held_pose('idle')
aim=held_pose('aim') if FAMILY=='single' else idle
index_pad=Vector(index_recipe['pad_local'])
left_pads={digit:M.finger_pad('l',digit) for digit in ('thumb','index','middle','ring','pinky')} if FAMILY=='single' else {}
opened_source=source('single_0_5',.6)
press_source=source('single_0_5',1.0)

def carry(p,old,gun):
    delta=gun@old['WPN_root'].inverted()
    for n in names:
        if n.startswith('WPN_'):p[n]=delta@old[n]
    for s in hands:
        M.arm_at(p,old,s,gun@M.matrix(grip[s]['hand']))
    return p

def fire_pose(t,ads=False):
    start=aim if ads else idle
    p={n:m.copy() for n,m in start.items()}
    kick=curve(t,[(0,0),(.033,1),(.067,.96),(.14,.58),(.23,.14),(.30,-.025),(.40,0)])
    twist=curve(t,[(0,0),(.045,1),(.105,.7),(.24,0),(.4,0)])
    pivot=start['hand_'+side].translation
    axis=start['WPN_root'].to_quaternion()@(canonical_q@Vector((1,0,0)))
    turn=Quaternion(axis,math.radians(-26 if ads else -24)*kick)
    roll=Quaternion(start['WPN_root'].to_quaternion()@(canonical_q@Vector((0,1,0))),math.radians(-3.2 if side=='r' else 3.2)*twist)
    delta=Matrix.Translation(pivot)@(turn@roll).to_matrix().to_4x4()@Matrix.Translation(-pivot)
    delta.translation+=start['WPN_root'].to_quaternion()@(canonical_q@Vector((.002*twist,.022*kick,.004*kick)))
    carry(p,start,delta@start['WPN_root'])
    # Double action: the trigger drives hammer/cylinder, the thumb keeps its grip.
    squeeze=curve(t,[(0,0),(.008,1),(.085,1),(.16,.6),(.25,0),(.4,0)])
    hammer=curve(t,[(0,0),(.003,1),(.009,0),(.4,0)])
    for n,angle in (('WPN_Trigger',-10*squeeze),('WPN_Hammer',-27*hammer)):
        p[n]=p[parents[n]]@(start[parents[n]].inverted()@start[n])@Matrix.Rotation(math.radians(angle),4,'X')
    n='WPN_Cylinder'
    p[n]=p[parents[n]]@(start[parents[n]].inverted()@start[n])@Matrix.Rotation(math.radians(72)*smooth(t/.009),4,Vector(META['cylinder_bore_axis_local']))
    for n in names:
        if n.startswith(('WPN_Case_','WPN_Round_')):p[n]=p['WPN_Cylinder']@start['WPN_Cylinder'].inverted()@start[n]
    target=(p['WPN_root']@alignment)@Vector(index_recipe['target_canonical'])
    target+=p['WPN_root'].to_quaternion()@(canonical_q@Vector((0,.0025*squeeze,0)))
    M.finger_at(p,side,index_pad,target,1.,'index',metacarpal=True)
    park_loader(p)
    return p

RELOAD=4.333333333333
def reload_pose(t):
    p={n:m.copy() for n,m in idle.items()}
    # Measured phases: open .47, upright .93, eject 1.10, load 2.55,
    # release 2.90, withdraw 3.17, snap shut 3.70, held 4.33 seconds.
    pitch=curve(t,[(0,0),(.30,-8),(.60,-15),(1.02,-71),(1.40,-65),(1.85,-8),(2.15,0),(3.2,0),(3.45,5),(3.70,-10),(4.05,3),(RELOAD,0)])
    yaw=curve(t,[(0,0),(.4,-18),(.8,-10),(1.2,0),(1.7,-12),(2.25,0),(3.2,0),(3.55,38),(3.83,15),(RELOAD,0)])*(1 if side=='r' else -1)
    roll=curve(t,[(0,0),(.47,18),(.95,12),(1.4,10),(2.1,9),(3.25,9),(3.63,65),(3.92,10),(RELOAD,0)])*(1 if side=='r' else -1)
    shift=Vector((curve(t,[(0,0),(.6,.028),(1.1,.060),(1.8,.02),(2.6,-.01),(3.6,.08),(RELOAD,0)]),curve(t,[(0,0),(1.1,.01),(2.5,.03),(3.65,-.07),(RELOAD,0)]),curve(t,[(0,0),(1.1,.020),(2.4,-.014),(3.7,-.04),(RELOAD,0)])))
    C=idle['WPN_root']@alignment
    pivot=idle['hand_'+side].translation
    q=C.to_quaternion()
    rot=q@(Quaternion((1,0,0),math.radians(pitch))@Quaternion((0,0,1),math.radians(yaw))@Quaternion((0,1,0),math.radians(roll)))@q.inverted()
    delta=Matrix.Translation(pivot)@rot.to_matrix().to_4x4()@Matrix.Translation(-pivot)
    delta.translation+=q@shift
    carry(p,idle,delta@idle['WPN_root'])
    opening=curve(t,[(0,0),(.27,0),(.47,1),(3.50,1),(3.70,0),(RELOAD,0)])
    # Transport the source crane's native opening axis into the registered body.
    sample=opened_source
    crane='WPN_Crane'
    closed=idle[parents[crane]].inverted()@idle[crane]
    opened=sample[parents[crane]].inverted()@sample[crane]
    p[crane]=p[parents[crane]]@mix(closed,opened,opening)
    for n in ('WPN_Cylinder','WPN_Extractor'):
        p[n]=p[parents[n]]@(idle[parents[n]].inverted()@idle[n])
    for n in names:
        if n.startswith(('WPN_Case_','WPN_Round_')):p[n]=p['WPN_Cylinder']@idle['WPN_Cylinder'].inverted()@idle[n]
    axis=p['WPN_Cylinder'].to_quaternion()@Vector(META['cylinder_bore_axis_local'])
    extraction=curve(t,[(0,0),(.97,0),(1.10,.040),(1.24,.040),(1.45,0),(RELOAD,0)])
    p['WPN_Extractor'].translation+=axis*extraction
    # Empty cases leave on the extraction beat. The runtime hides spent cases
    # at 1.30 s and shows only the available new rounds at the loader reveal.
    for n in names:
        if not n.startswith(('WPN_Case_','WPN_Round_')):continue
        if t<1.30:p[n].translation+=axis*curve(t,[(0,0),(.98,0),(1.10,.035),(1.29,.19)])
        elif t<2.9:
            p[n].translation+=axis*curve(t,[(1.30,.30),(1.80,.24),(2.12,.16),(2.47,.055),(2.62,0),(2.9,0)])
    loader_pose=Matrix.LocRotScale(p['WPN_Cylinder'].translation+axis*(.057+curve(t,[(0,.4),(1.8,.30),(2.12,.16),(2.47,.055),(2.62,0),(2.9,0),(3.17,.16),(3.4,.32)])),
        (p['WPN_root']@alignment).to_quaternion(),Vector((1,1,1)))
    p['WPN_Loader']=loader_pose if 1.78<=t<=3.33 else Matrix.LocRotScale(Vector((0,0,-3)),Quaternion(),Vector((.0001,)*3))
    if FAMILY=='single':
        old={n:m.copy() for n,m in p.items()}
        neutral=p['hand_l'].copy()
        # Use the native open/press hand as shape donor, fitted to actual extractor.
        donor=press_source
        press=p['WPN_root']@donor['WPN_root'].inverted()@donor['hand_l']
        press.translation=p['WPN_Extractor'].translation+axis*.053+(p['WPN_root']@alignment).to_quaternion()@Vector((-.026,-.040,.028))
        pickup=neutral.copy();pickup.translation=loader_pose.translation+(p['WPN_root']@alignment).to_quaternion()@Vector((-.046,.022,-.023))
        down=neutral.copy();down.translation+=(p['WPN_root']@alignment).to_quaternion()@Vector((-.09,.045,-.19))
        keys=[(0,neutral),(.25,neutral),(.54,down),(.85,press),(1.12,press),(1.45,down),(1.90,down),(2.12,pickup),(3.10,pickup),(3.38,down),(3.82,down),(RELOAD,neutral)]
        target=keys[-1][1]
        for (a,x),(b,y) in zip(keys,keys[1:]):
            if t<=b:target=mix(x,y,smooth((t-a)/(b-a)));break
        M.arm_at(p,old,'l',target)
        # At the loader the fingers wrap its knob; at the press the native
        # open palm is retained. All interpolation is in native local joints.
        press_weight=smooth((t-.6)/.22)*smooth((1.43-t)/.23)
        load_weight=smooth((t-1.85)/.22)*smooth((3.35-t)/.23)
        for n in grip['l']['fingers']:
            a=M.matrix(grip['l']['fingers'][n])
            b=donor[parents[n]].inverted()@donor[n]
            p[n]=p[parents[n]]@mix(a,b,press_weight)
        if load_weight>0:
            C=p['WPN_root']@alignment
            for digit,offset in [('thumb',(.009,.025,.007)),('index',(-.009,.018,.021)),('middle',(-.018,.008,.006)),('ring',(-.019,.010,-.012)),('pinky',(-.014,.012,-.022))]:
                target=loader_pose.translation+C.to_quaternion()@Vector(offset)
                M.finger_at(p,'l',left_pads[digit],target,load_weight,digit)
    return p

receipt=dict(revision='double-action-v1',family=FAMILY,mesh=mesh_name+'.fbx',sample_hz=120,clips=[],reference='BV1vh4HejEUF 0-22s',user_tested=False)
new=copy.deepcopy(PROFILE)
def export(kind,duration,fn):
    r.animation_data_clear()
    act=bpy.data.actions.new('RSH12_DA_'+FAMILY+'_'+kind);act.use_fake_user=True
    r.animation_data_create();r.animation_data.action=act
    count=round(duration*120);scene.frame_start=0;scene.frame_end=count
    previous={}
    for frame in range(count+1):
        p=fn(frame/120)
        scene.frame_set(frame)
        for n in names:
            local=p[parents[n]].inverted()@p[n] if parents[n] in p else p[n]
            value=local_rest[n].inverted()@local
            pos,q,scale=value.decompose()
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
    bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
    dest='/Game/Weapons/RSH12/DoubleAction20261003/'+FAMILY
    receipt['clips'].append(dict(kind=kind,name=name,file=name+'.fbx',destination=dest,duration=duration))
    new['clips']=[e for e in new['clips'] if e['kind']!=kind]
    new['clips'].append(dict(kind=kind,base=dest+'/'+name,duration=duration,tracks=[]))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(name+'_Editable.blend')))
    print('RSH12_DOUBLE_ACTION_AUTHORED',FAMILY,kind,flush=True)

export('idle',1.,lambda t:held_pose('idle',t))
if FAMILY=='single':export('aim',1/30,lambda t:aim)
export('fire',.40,lambda t:fire_pose(t))
if FAMILY=='single':export('aim_fire',.40,lambda t:fire_pose(t,True))
if FAMILY=='single':
    export('reload_empty',RELOAD,reload_pose)
    export('reload',4.166666666667,lambda t:reload_pose(t*RELOAD/(500/120)))
# Dual reload remains the native one-handed insertion family; it cannot display
# a second support hand while the other gun is equipped. It shares new DA fire.
# Park loader on all shared channels; static mesh is never visible at rest.
for entry in new['clips']:
    if '/DoubleAction20261003/' in entry['base']:continue
    tr=next((tr for tr in entry['tracks'] if tr['bone']=='WPN_Loader'),None)
    if tr:entry['tracks'].remove(tr)
    entry['tracks'].append(dict(bone='WPN_Loader',times=[0.],values=[0,0,-300,0,0,0,1,-.9999,-.9999,-.9999]))
(OUT/'profile.json').write_text(json.dumps(new,separators=(',',':')),encoding='utf8')
(OUT/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('RSH12_DOUBLE_ACTION_FAMILY_SAVED',FAMILY,flush=True)
