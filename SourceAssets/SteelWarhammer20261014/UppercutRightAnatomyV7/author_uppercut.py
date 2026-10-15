"""Repair the uppercut's right anatomical hinge while keeping its weapon path.

The existing gather, left hand and hammer are sampled unchanged. The right
palm rolls as one closed grasp around the shaft during release; the elbow cap
starts from the native hinge, with pronation distributed towards the wrist.
"""
import ast,copy,json,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=240;DURATION=2.05
SOURCE=P.parent/'UppercutTiltClearanceV6/Warhammer_Uppercut_TiltClearance_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
source=[]
for i in range(round(DURATION*FPS)+1):
    scene.frame_set(i);source.append({b.name:b.matrix.copy() for b in rig.pose.bones})
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']['r']
U,L,H='upperarm_r','lowerarm_r','hand_r';C='clavicle_r'
u0=rest[L].translation-rest[U].translation;f0=rest[H].translation-rest[L].translation
A,B=u0.length,f0.length;native_plane=u0.cross(f0).normalized()
idle=source[0];idle_axis=(idle[H].translation-idle[U].translation).normalized()
idle_pole=idle[L].translation-idle[U].translation;idle_pole=(idle_pole-idle_axis*idle_pole.dot(idle_axis)).normalized()
hand_children=[b.name for b in rig.data.bones if any(a.name==H for a in b.parent_recursive)]
surface=json.loads((P.parent/'UppercutTiltClearanceV6/authoring_surface.json').read_text())
ring=next(x for x in surface['rings'] if x['mesh']=='Warhammer_BareArmsV7' and x['weights'][0][0].endswith('_r'))
ring_groups={};ring_points=np.array([[*p,1.] for p in ring['points']])
for n in {n for skin in ring['skin'] for n in skin}:
    ring_groups[n]=(ring_points@np.asarray(rest[n].inverted()).T,np.array([skin.get(n,0.) for skin in ring['skin']]))

def frame(axis,normal):
    x=axis.normalized();z=(normal-x*normal.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed().to_quaternion()
def rigid(p,q,scale=Vector((1,1,1))):return Matrix.LocRotScale(p,q,scale)
def wrap(a):return (a+math.pi)%(2*math.pi)-math.pi
def axial(q,axis):return wrap(2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w))
def near(a,old):return old+wrap(a-old)
def weight(t):return ease((t-1.0)/.09)*(1-ease((t-1.57)/.48))
def palm_roll_weight(t):return ease((t-1.0)/.105)*(1-ease((t-1.52)/.53))
def grasp(src,degrees,slide=0.):
    w=src['WPN_root'];turn=w@Quaternion((0,0,1),math.radians(degrees)).to_matrix().to_4x4()@Matrix.Translation((0,0,slide))@w.inverted()
    return turn@src[H],turn
def boundary(pose):
    p=sum((local@np.asarray(pose[n]).T)[:,:3]*w[:,None] for n,(local,w) in ring_groups.items())
    x,y,z=p.T;vertical=math.tan(math.radians(41));horizontal=vertical*16/9
    return max(float(np.min(x-horizontal*y)),float(np.min(-z-vertical*y)),float(np.min(-y)))

def build_arm(src,hand,bend_degrees,influence=1.,cone_degrees=0.,phi_reference=None):
    # Build from the palm's anatomical forearm axis. The former fixed-shoulder
    # circle forced the elbow behind an almost horizontal palm approach.
    dh=hand.to_quaternion()@rest[H].to_quaternion().inverted()
    neutral=(dh@f0).normalized()
    source_fore=(src[H].translation-src[L].translation).normalized()
    turn=neutral.rotation_difference(source_fore)
    bend=min(math.radians(bend_degrees),turn.angle)
    fore_direction=Quaternion().slerp(turn,bend/max(turn.angle,1e-8))@neutral
    fore_direction=Quaternion(neutral,math.radians(cone_degrees))@fore_direction
    fore_direction=Quaternion().slerp(source_fore.rotation_difference(fore_direction),influence)@source_fore
    elbow=hand.translation-fore_direction*B
    # The closest shoulder on the native upper-arm sphere provides a small,
    # continuous shoulder-girdle contribution, not a stretched forearm.
    upper_direction=(elbow-src[U].translation).normalized()
    shoulder=elbow-upper_direction*A
    upper=elbow-shoulder;fore=hand.translation-elbow
    plane=upper.cross(fore).normalized()
    du=frame(upper,plane)@frame(u0,native_plane).inverted()
    df=(du@f0).rotation_difference(fore)@du
    aligned=(dh@f0).rotation_difference(fore)@dh
    phi=axial(aligned@df.inverted(),fore.normalized())
    if phi_reference is not None:phi=near(phi,phi_reference)
    out={U:rigid(shoulder,du@rest[U].to_quaternion(),src[U].to_scale()),
         L:rigid(elbow,df@rest[L].to_quaternion(),src[L].to_scale()),H:hand,C:src[C].copy()}
    out[C].translation+=shoulder-src[U].translation
    for num in ('01','02'):
        n='upperarm_twist_'+num+'_r'
        out[n]=rigid(shoulder+du@(rest[n].translation-rest[U].translation),du@rest[n].to_quaternion(),src[n].to_scale())
        n='lowerarm_twist_'+num+'_r'
        out[n]=rigid(elbow+df@(rest[n].translation-rest[L].translation),Quaternion(fore.normalized(),phi*STATIONS[n])@df@rest[n].to_quaternion(),src[n].to_scale())
    bend=math.degrees(fore.angle(dh@f0));clearance=boundary(out)
    cost=(max(0.,bend-22.)/10.)**2+(max(0.,abs(math.degrees(phi))-95.)/20.)**2
    cost+=.025*(bend/25.)**2+.02*(math.degrees(phi)/90.)**2
    # The current held grasp enters this interval on its positive pronation
    # branch. Do not select an equally oriented but fully wound negative pose.
    cost+=10.*(max(0.,-math.degrees(phi))/45.)**2
    cost+=50.*(max(0.,.012-clearance)/.015)**2
    cost+=2.*(max(0.,elbow.z-hand.translation.z+.02)/.10)**2
    cost+=2.*(max(0.,-.02-elbow.x)/.10)**2
    shift=(shoulder-src[U].translation).length
    cost+=.3*(shift/.06)**2+20.*(max(0.,shift-.085)/.04)**2
    return cost,out,{'wrist_axis_bend_degrees':bend,'forearm_pronation_degrees':math.degrees(phi),
                    'shoulder_boundary_margin_m':clearance,'shoulder_assistance_m':shift}

# Author a single comfortable closed grasp for the raised pose. The elbow
# pole and palm rotation are fitted together, not by adding roll to the wrist.
hold=source[round(1.125*FPS)];best=None
for slide in (0.,-.02,-.04,-.06):
    for roll in range(-90,91,5):
        hand,_=grasp(hold,roll,slide)
        for bend in (15.,25.,35.):
            for cone in range(-180,181,30):
                cost,_,info=build_arm(hold,hand,bend,cone_degrees=cone,phi_reference=math.radians(140.))
                cost+=.05*(roll/90.)**2+.4*(slide/.08)**2+.01*(cone/120.)**2
                if best is None or cost<best[0]:best=(cost,roll,bend,info,slide,cone)
PALM_ROLL=float(best[1]);PALM_SLIDE=float(best[4]);WRIST_APPROACH=float(best[2]);WRIST_CONE=float(best[5])
print('RAISED_GRASP_FIT '+json.dumps({'palm_roll_degrees':PALM_ROLL,'palm_slide_m':PALM_SLIDE,'wrist_cone_degrees':WRIST_CONE,**best[3]}),flush=True)

poses=[];records=[];previous_phi=math.radians(180.)
for i,src in enumerate(source):
    t=i/FPS;w=weight(t);pose=copy.deepcopy(src)
    if w>1e-8:
        hand,grasp_turn=grasp(src,PALM_ROLL*palm_roll_weight(t),PALM_SLIDE*palm_roll_weight(t))
        # Transport full segment directions continuously; no pole search can
        # switch elbows to the opposite side halfway through the fast strike.
        _,fitted,info=build_arm(src,hand,WRIST_APPROACH,w,WRIST_CONE,previous_phi)
        previous_phi=math.radians(info['forearm_pronation_degrees'])
        shoulder=fitted[U].translation;elbow=fitted[L].translation
        for n in (U,'upperarm_twist_01_r','upperarm_twist_02_r'):
            old_axis=src[L].translation-src[U].translation;new_axis=elbow-shoulder
            swing=old_axis.rotation_difference(new_axis)
            q=(swing@src[n].to_quaternion()).slerp(fitted[n].to_quaternion(),w)
            offset=(swing@(src[n].translation-src[U].translation)).lerp(fitted[n].translation-shoulder,w)
            pose[n]=rigid(shoulder+offset,q,src[n].to_scale())
        for n in (L,'lowerarm_twist_02_r','lowerarm_twist_01_r'):
            old_axis=src[H].translation-src[L].translation;new_axis=hand.translation-elbow
            swing=old_axis.rotation_difference(new_axis)
            q=(swing@src[n].to_quaternion()).slerp(fitted[n].to_quaternion(),w)
            offset=(swing@(src[n].translation-src[L].translation)).lerp(fitted[n].translation-elbow,w)
            pose[n]=rigid(elbow+offset,q,src[n].to_scale())
        pose[C]=fitted[C];pose[H]=hand
        for n in hand_children:pose[n]=grasp_turn@src[n]
        n='ik_hand_r'
        if n in pose:pose[n]=grasp_turn@src[n]
        records.append({'source_seconds':t,'support_weight':w,**info})
    poses.append(pose)
name='A_Warhammer_Uppercut';bake(name,poses,FPS)
scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Uppercut_RightAnatomy_Editable.blend'))
receipt={'clips':[name],'fps':FPS,'seconds':DURATION,'revision':'RightAnatomyV7_20261015','source':str(SOURCE),
         'scope':'Right arm and whole-palm circumferential grip during release/recovery only',
         'palm_roll_degrees':PALM_ROLL,'palm_slide_m':PALM_SLIDE,'wrist_approach_degrees':WRIST_APPROACH,'wrist_cone_degrees':WRIST_CONE,'raised_grasp_fit':best[3],
         'native_hinge':'Native rest upper/forearm bending frame; zero added elbow-cap pronation, twist distributed by actual skin stations',
         'support_source_seconds':[1.0,1.09,1.57,2.05],'weapon_and_left_hand':'Preserved from V6',
         'damage_timing_and_arc':'Unchanged; no C++ edits or DLL build required','runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
(P/'authoring_fit.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('WARHAMMER_UPPERCUT_RIGHT_ANATOMY_AUTHORED '+json.dumps(receipt))
