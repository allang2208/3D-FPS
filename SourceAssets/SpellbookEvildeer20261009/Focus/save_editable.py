"""Save an editable gather, float/open, round-trip page cycle and return. No render."""
import bpy,json,re,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
data=json.loads((P/'focus.json').read_text(encoding='utf-8'))
recovery=json.loads((P/'return.json').read_text(encoding='utf-8'))
tuning=(ROOT/'Source/FPSGAME/Weapons/Spellbook/SpellbookCarryTuning.h').read_text(encoding='utf-8')
lower=float(re.search(r'\bLowerCm\s*=\s*([0-9.]+)f',tuning).group(1))
motion=(ROOT/'Source/FPSGAME/Weapons/Spellbook/SpellbookFocusMotion.h').read_text(encoding='utf-8')
def number(name):return float(re.search(r'\b'+name+r'\s*=\s*([0-9.]+)f',motion).group(1))
detach,gather,open_start,open_duration,arrive,cycle,close,drop,grip,settle=[number(n) for n in ('Detach','Gather','OpenStart','OpenDuration','HoverArrive','PageCycle','Close','Drop','Grip','Settle')]
prepare=number('PalmPrepare');hold=number('ContactHold')
drop_start=close+prepare;contact=drop_start+drop;grip_start=contact+hold;grip_end=grip_start+grip
return_length=grip_end+settle
ready=open_start+open_duration;return_start=ready+cycle*1.25;end=return_start+return_length
def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
def ease(a,b,t):
    t=max(0,min(1,(t-a)/(b-a)));return t*t*t*(t*(6*t-15)+10)
def convert(m):
    m=Matrix(m);result=(S@m.to_3x3()@S).to_4x4();result.translation=S@m.translation*.01;return result
def blend(a,b,t):
    qa,qb=a.to_quaternion(),b.to_quaternion()
    if qa.dot(qb)<0:qb.negate()
    q=Quaternion(tuple(qa[i]*(1-t)+qb[i]*t for i in range(4)));q.normalize()
    result=q.to_matrix().to_4x4();result.translation=a.translation.lerp(b.translation,t);return result
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'GripPhotoV3/Spellbook_PhotoGripV3.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['Spellbook_PhotoGripV3_V7_LeftArm'];rig.animation_data_clear();rig.animation_data_create()
arm_action=bpy.data.actions.new('A_Spellbook_FocusGatherReturn');arm_action.use_fake_user=True;rig.animation_data.action=arm_action
bpy.data.objects['Alchemy_BluePurple_PhotoSpineGrip'].hide_render=True
bpy.data.objects['Alchemy_BluePurple_PhotoSpineGrip'].hide_set(True)
with bpy.data.libraries.load(str(P.parent/'Spellbook_Alchemy.blend'),link=False) as (available,loaded):
    loaded.objects=['SpellbookRig','SK_Spellbook_Alchemy']
for obj in loaded.objects:
    bpy.context.collection.objects.link(obj);obj.hide_set(False);obj.hide_viewport=False;obj.hide_render=False
book=next(o for o in loaded.objects if o.type=='ARMATURE');book.animation_data_clear();book.animation_data_create()
book_action=bpy.data.actions.new('A_Spellbook_FocusOpenReadClose');book_action.use_fake_user=True;book.animation_data.action=book_action
S=Matrix.Diagonal((1,-1,1));scene=bpy.context.scene;scene.render.fps=60
base={n:Matrix(data['poses'][0]['local'][n]) for n in data['arm_order']}
focus_end={n:Matrix(data['poses'][-1]['local'][n]) for n in data['arm_order']}
return_base={n:Matrix(recovery['poses'][0]['local'][n]) for n in data['arm_order']}
depart=None;return_frame=None;previous={};previous_book=None;frames=math.ceil(end*60)
for f in range(frames+1):
    age=min(f/60,end);scene.frame_set(f)
    returning=age>=return_start;close_age=max(0,age-return_start)
    back=max(0,min(1,close_age/return_length)) if returning else 0.
    arm_time=min(age,gather)
    samples=recovery if returning else data
    sample_time=back if returning else arm_time
    index=0
    while index<len(samples['times'])-2 and sample_time>=samples['times'][index+1]:index+=1
    alpha=max(0,min(1,(sample_time-samples['times'][index])/(samples['times'][index+1]-samples['times'][index])))
    for n in data['arm_order']:
        bone=rig.pose.bones[n];ref=rig.data.bones[n]
        native=ref.parent.matrix_local.inverted()@ref.matrix_local if ref.parent else ref.matrix_local
        sample=blend(Matrix(samples['poses'][index]['local'][n]),Matrix(samples['poses'][index+1]['local'][n]),alpha)
        if returning:
            # Runtime CaptureFocusReturn preserves the actual opening-end pose
            # while entering the unchanged recovery. Bake that same entry delta.
            entry=1-ease(0,drop_start,close_age)
            delta=focus_end[n].to_quaternion()@return_base[n].to_quaternion().inverted()
            rotation=Quaternion().slerp(delta,entry)@sample.to_quaternion()
            position=sample.translation+(focus_end[n].translation-return_base[n].translation)*entry
            sample=rotation.to_matrix().to_4x4();sample.translation=position
            sample=blend(sample,base[n],ease(return_length-.12,return_length,close_age))
        local=convert(sample)
        if n=='clavicle_l':
            offset=Vector((0,0,-lower*.01))
            local.translation+=bone.parent.matrix.to_3x3().inverted()@offset if bone.parent else offset
        bone.rotation_mode='QUATERNION';bone.matrix_basis=native.inverted()@local
        if n in previous and bone.rotation_quaternion.dot(previous[n])<0:bone.rotation_quaternion.negate()
        previous[n]=bone.rotation_quaternion.copy()
        for prop in ('location','rotation_quaternion','scale'):bone.keyframe_insert(prop,frame=f)
    bpy.context.view_layer.update()
    held=rig.matrix_world@rig.pose.bones['book_spine_grip_l'].matrix
    if returning:
        mount=blend(Matrix(recovery['return_mounts'][index]),Matrix(recovery['return_mounts'][index+1]),alpha)
        held=rig.matrix_world@rig.pose.bones['hand_l'].matrix@convert(mount)
    # Match OpenBook: restore the original reading frame and reach it once,
    # before opening the covers. The original gather has no added held flip.
    tilt=math.radians(25)
    u=Matrix(((0,math.cos(tilt),-math.sin(tilt)),(-1,0,0),(0,math.sin(tilt),math.cos(tilt)))).to_4x4()
    bob=smooth((age-ready)/.6)
    u.translation=Vector((44+.35*math.sin(age*1.1)*bob,-19,-14+.55*math.sin(age*1.5)*bob))
    hover=convert(u)
    if age<detach:frame=held
    else:
        if depart is None:depart=held.copy();depart_age=age
        rise=ease(depart_age,max(depart_age+.01,arrive),age)
        frame=blend(depart,hover,rise)
    if returning:
        if return_frame is None:return_frame=frame.copy()
        fall=max(0,min(1,(close_age-drop_start)/drop))
        # The back half rises as the front folds inward: both meet above the
        # stationary spine. The resulting spine-down orientation survives the fall.
        reading_tilt=math.radians(25)
        reading=Matrix(((0,math.cos(reading_tilt),-math.sin(reading_tilt)),(-1,0,0),(0,math.sin(reading_tilt),math.cos(reading_tilt)))).to_4x4()
        spine_down=convert(reading@Matrix.Rotation(-math.pi*.5,4,'Y'))
        spine_down.translation=return_frame.translation.copy()
        closed=blend(return_frame,spine_down,ease(0,close,close_age))
        frame=closed.copy()
        frame.translation=return_frame.translation.copy()
        frame.translation.z=return_frame.translation.z*(1-fall*fall)+held.translation.z*fall*fall
        if close_age<=drop_start:frame=closed.copy()
        frame=blend(frame,held,ease(grip_end-.08,grip_end,close_age))
    book.matrix_world=frame@Matrix.Diagonal((.01,.01,.01,1));book.rotation_mode='QUATERNION'
    if previous_book is not None and book.rotation_quaternion.dot(previous_book)<0:book.rotation_quaternion.negate()
    previous_book=book.rotation_quaternion.copy()
    for prop in ('location','rotation_quaternion','scale'):book.keyframe_insert(prop,frame=f)
    pose_age=min(age,return_start)
    opening=max(0,min(1,(pose_age-open_start)/open_duration))
    page=.5-.5*math.cos(2*math.pi*max(0,pose_age-ready)/cycle) if pose_age>=ready else 0.
    for bone in book.pose.bones:bone.rotation_mode='XYZ';bone.rotation_euler=(0,0,0);bone.location=(0,0,0);bone.scale=(1,1,1)
    book.pose.bones['Cover_Front'].rotation_euler.y=math.radians(-165)*smooth(opening)
    for p in range(3):
        t=smooth((page*120-p*30)/60);wave=math.sin(math.pi*t)
        leaf=book.pose.bones[f'Page_{p+1}_00'];leaf.rotation_euler.y=math.radians(-165)*t
        leaf.location.z=.05+.021*((2-p)*(1-t)+p*t)
        for s in range(1,8):book.pose.bones[f'Page_{p+1}_{s:02}'].rotation_euler.y=math.radians(7)*wave*math.sin(math.pi*s/8)
    for bone in book.pose.bones:
        if returning:
            closure=ease(0,close,close_age)
            bone.rotation_euler=blend(bone.rotation_euler.to_matrix().to_4x4(),Matrix.Identity(4),closure).to_euler('XYZ')
            bone.location*=1-closure
        bone.keyframe_insert('rotation_euler',frame=f);bone.keyframe_insert('location',frame=f)
for action in (arm_action,book_action):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
for obj,action in ((rig,arm_action),(book,book_action)):
    if len(action.slots):obj.animation_data.action_slot=action.slots[0]
scene.frame_start=0;scene.frame_end=frames;scene.frame_set(0)
for name,seconds in [('OriginalGather',0),('ReleaseAndRise',detach),('OriginalReadingFrame',arrive),('OpenCovers',open_start),('Read',ready),('PagesBack',ready+cycle/2),('CloseInPlace',return_start),('PalmReady',return_start+close),('VerticalDrop',return_start+drop_start),('PalmContact',return_start+contact),('GripStart',return_start+grip_start),('FingersClosed',return_start+grip_end),('ReturnToIdle',return_start+recovery['roll_mid_seconds']),('Settled',end)]:
    scene.timeline_markers.new(name,frame=round(seconds*60))
rig['focus']='Restored original V7 gather from pre-V14 backup; no added held-arm flip'
book['opening']='V17: restore original reading frame; one eased release-to-reading transition before local cover opening'
book['pages']='3 leaves x 8 bones; authored bending; no cloth/rigid-body simulation'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Spellbook_Focus.blend'))
(P/'editable-source.json').write_text(json.dumps({'file':'Spellbook_Focus.blend','opening_revision':'original-gather-pre-V14','book_motion_revision':17,'detach_seconds':detach,'float_arrive_seconds':arrive,'gather_seconds':gather,'open_seconds':open_duration,
    'page_cycle_seconds':cycle,'toggle':True,'runtime':'existing Open and FlipPages assets, manual active-only sampling',
    'reading_frame':{'position_cm':[44,-19,-14],'tilt_degrees':25,'page_orientation':'original reader-facing basis'},
    'opening_orientation':'one eased release-to-original-reading transition, complete before local cover/page opening','recovery':'V9 spine-first landing retained; V11 screen-clockwise book-led recovery with supported elbow/wrist and shared contact keys',
    'return_seconds':recovery['seconds'],'close_demonstration_page_alpha':.5,
    'gold_effect_source':'GoldOrbit/install_material.py; runtime SpellbookFocusGold.cpp',
    'rendered':False,'runtime_tested':False},indent=2),encoding='utf-8')
print('Saved V17 original gather and reading frame, eased entry, page cycle and existing return.')
