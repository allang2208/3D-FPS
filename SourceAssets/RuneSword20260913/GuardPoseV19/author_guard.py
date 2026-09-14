"""Author animation-only guard replacement from the accepted sword ready pose.

Both hands retain the exact ready grip. The guard uses a single shortest sword
rotation and explicit elbow poles; it never searches revolutions around a hilt.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

P=Path(__file__).parent;ROOT=P.parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
SOURCE=ROOT/'GuardParryV18/AzureRunesword_Manny_Editable.blend'
FPS=480;RAISE=.20;HIT=.22;BREAK=.40
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig']
ready_action=bpy.data.actions['A_RuneSword_Slash1']
r.animation_data.action=ready_action;r.animation_data.action_slot=ready_action.slots[0]
s.frame_set(0);bpy.context.view_layer.update()
BASE={b.name:b.matrix.copy() for b in r.pose.bones}
REST={b.name:b.matrix_local.copy() for b in r.data.bones}
LOCAL_REST={n:(REST[r.data.bones[n].parent.name].inverted()@m if r.data.bones[n].parent else m) for n,m in REST.items()}
SWORD=BASE['WPN_root'];IDENTITY=Quaternion((1,0,0,0))
blade_axis=(SWORD.to_3x3()@Vector((0,0,1))).normalized()
guard_axis=Vector((.935,.14,.325)).normalized()
GUARD_SWING=blade_axis.rotation_difference(guard_axis)
GUARD_HILT=Vector((-.10,.54,-.015))
GUARD_SWORD=Matrix.LocRotScale(GUARD_HILT,GUARD_SWING@SWORD.to_quaternion(),Vector((1,1,1)))

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3.-2.*t)

def blend(a,b,w):
    return Matrix.LocRotScale(a.translation.lerp(b.translation,w),a.to_quaternion().slerp(b.to_quaternion(),w),Vector((1,1,1)))

def plane_frame(axis,normal):
    y=axis.normalized();x=(normal-y*normal.dot(y)).normalized();z=x.cross(y)
    return Matrix((x,y,z)).transposed().to_quaternion()

def solve_pose(sword,weight):
    """Exact two-bone reach, outward/downward elbows, continuous supported wrists."""
    p={n:m.copy() for n,m in BASE.items()}
    delta=sword@SWORD.inverted();dq=delta.to_quaternion()
    for side in ('l','r'):
        un,fn,hn=['%s_%s'%(part,side) for part in ('upperarm','lowerarm','hand')]
        A0=BASE[un].translation;E0=BASE[fn].translation;T0=BASE[hn].translation
        upper0=E0-A0;fore0=T0-E0;l1=upper0.length;l2=fore0.length
        H=delta@BASE[hn];T=H.translation
        # Small shoulder advance supports the lift, with no shoulder spin.
        A=A0+Vector((0.,.025,.018))*weight
        axis=(T-A).normalized();distance=(T-A).length
        if distance>l1+l2-.012:
            A+=axis*(distance-(l1+l2-.012));distance=(T-A).length
        original_axis=(T0-A0).normalized()
        original_pole=(E0-A0)-original_axis*(E0-A0).dot(original_axis)
        carried=original_axis.rotation_difference(axis)@original_pole.normalized()
        # End elbow guide stays on its own side and below the supporting hands.
        guide=Vector((-.31 if side=='l' else .34,.24,-.30))
        wanted=guide-A;wanted-=axis*wanted.dot(axis);wanted.normalize()
        pole=carried.lerp(wanted,.72*weight)
        pole-=axis*pole.dot(axis);pole.normalize()
        along=(l1*l1-l2*l2+distance*distance)/(2.*distance)
        E=A+axis*along+pole*math.sqrt(max(0.,l1*l1-along*along))
        upper=(E-A).normalized();fore=(T-E).normalized()
        uq=plane_frame(upper,upper.cross(fore))@plane_frame(upper0,upper0.cross(fore0)).inverted()@BASE[un].to_quaternion()
        # Transport the accepted wrist/forearm roll with the held sword, then
        # bend the forearm by its shortest swing onto the solved elbow-to-wrist.
        carried_fore=dq@fore0.normalized()
        fq=carried_fore.rotation_difference(fore)@dq@BASE[fn].to_quaternion()
        p['clavicle_'+side].translation+=A-A0
        p[un]=Matrix.LocRotScale(A,uq,Vector((1,1,1)))
        p[fn]=Matrix.LocRotScale(E,fq,Vector((1,1,1)))
        p[hn]=H
        for prefix,parent in (('upperarm',un),('lowerarm',fn)):
            deformation=p[parent]@BASE[parent].inverted()
            for idx in ('01','02'):
                name=f'{prefix}_twist_{idx}_{side}'
                if name in BASE:p[name]=deformation@BASE[name]
        for name in BASE:
            if name.endswith('_'+side) and name.startswith(('index','middle','ring','pinky','thumb')):
                p[name]=delta@BASE[name]
    for name in ('WPN_root','Blade_Base','Blade_Tip'):p[name]=delta@BASE[name]
    return p

def raised_pose(t):
    u=max(0.,min(1.,t/RAISE));w=smooth(u)
    sword=blend(SWORD,GUARD_SWORD,w)
    # A shallow lift arc gives clearance while retaining the 0.20 s contract.
    sword.translation+=Vector((0.,.016,.025))*math.sin(math.pi*u)**2
    return BASE if t<=0. else solve_pose(sword,w)

raise_frames=[raised_pose(f/FPS) for f in range(round(RAISE*FPS)+1)]
guard=raise_frames[-1]
hit_frames=[]
for f in range(round(HIT*FPS)+1):
    t=f/FPS;force=smooth(t/.045) if t<.045 else 1.-smooth((t-.045)/(HIT-.045))
    recoil=Matrix.Translation(GUARD_HILT+Vector((0.,-.030,-.008))*force)@Matrix.Rotation(math.radians(3.)*force,4,'X')@Matrix.Translation(-GUARD_HILT)
    hit_frames.append(solve_pose(recoil@GUARD_SWORD,1.))
hit_frames[0]=guard;hit_frames[-1]=guard

drop=GUARD_SWORD.copy();drop.translation+=Vector((.035,-.045,-.14))
drop=Matrix.Translation(drop.translation)@Matrix.Rotation(math.radians(12.),4,'Y')@GUARD_SWORD.to_quaternion().to_matrix().to_4x4()
break_frames=[]
for f in range(round(BREAK*FPS)+1):
    t=f/FPS
    if t<=.12:sword=blend(GUARD_SWORD,drop,smooth(t/.12));weight=1.
    else:
        w=smooth((t-.12)/(BREAK-.12));sword=blend(drop,SWORD,w);weight=1.-w
    break_frames.append(solve_pose(sword,weight))
break_frames[0]=guard;break_frames[-1]=BASE

def export(name,frames):
    fullname='A_RuneSword_'+name
    old=bpy.data.actions.get(fullname)
    if old:old.name='REF_V18_'+fullname;old.use_fake_user=True
    action=bpy.data.actions.new(fullname);action.use_fake_user=True
    r.animation_data.action=action;s.frame_start=0;s.frame_end=len(frames)-1
    previous={}
    for f,pose in enumerate(frames):
        s.frame_set(f)
        for bone in r.pose.bones:
            local=pose[bone.parent.name].inverted()@pose[bone.name] if bone.parent else pose[bone.name]
            location,q,scale=(LOCAL_REST[bone.name].inverted()@local).decompose()
            if bone.name in previous and q.dot(previous[bone.name])<0:q.negate()
            bone.rotation_mode='QUATERNION';bone.location=location;bone.rotation_quaternion=q;bone.scale=scale
            previous[bone.name]=q.copy()
            for channel in ('location','rotation_quaternion','scale'):bone.keyframe_insert(channel,frame=f,group=bone.name)
    r.animation_data.action_slot=action.slots[0]
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(OUT/(fullname+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    print('GUARD_V19_EXPORTED '+fullname,flush=True)
    return action

s.render.fps=FPS;s.render.fps_base=1
guard_action=export('Guard',raise_frames)
export('GuardHit',hit_frames);export('GuardBreak',break_frames)
r.animation_data.action=guard_action;r.animation_data.action_slot=guard_action.slots[0]
s.frame_start=0;s.frame_end=round(RAISE*FPS);s.frame_set(s.frame_end)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({'revision':'GuardPoseV19','source':str(SOURCE),'pose_basis':'A_RuneSword_Slash1 frame 0 (accepted ready)','fps':FPS,'guard_raise_seconds':RAISE,'guard_hit_seconds':round(HIT*FPS)/FPS,'guard_break_seconds':BREAK,'guard_hilt_m':list(GUARD_HILT),'blade_direction':list(guard_axis),'grip':'exact fixed ready hand-to-sword transforms; no independent hilt-roll search','arms':'same-side elbow guides, shortest swing, retained finger and twist-helper relations','scope':'3 animation replacements only; no native, gameplay, camera, input, audio or attack changes','reference':'rico345100 firstperson.fbx.meta GuardStart / Guarding / GuardEnd; no external animation curves or meshes copied'},indent=2),encoding='utf-8')
print('RUNESWORD_V19_AUTHORED',flush=True)
