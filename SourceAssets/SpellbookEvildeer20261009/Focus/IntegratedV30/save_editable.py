"""Save V30: staggered fingers, supported arm arc and closing contact.

Uses the same generated local-pose keys and timing settings as runtime.
Reading sway is a runtime layer in SpellbookComponent, not baked into grips.
"""
import bpy,json,math,bisect
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

OUT=Path(__file__).resolve().parent;P=OUT.parent
C=Matrix.Diagonal((1,-1,-1,1))
data=json.loads((OUT/'motion.json').read_text(encoding='utf-8'))
settings=data['settings']
PLAYBACK_RATE=settings['playback_rate']
AUTHORED_LENGTH=settings['authored_length']
LENGTH=AUTHORED_LENGTH/PLAYBACK_RATE
FPS=100 # Exact 112-frame action; the reference scene's original keys remain at 60 Hz.
S=Matrix.Diagonal((1,-1,1))

def convert(m):
    rotation=(S@m.to_3x3()@S).to_4x4()
    rotation.translation=S@m.translation*.01
    return rotation

def local_pose(source,returning):
    times=data['times'];a=max(0,min(len(times)-2,bisect.bisect_right(times,source)-1))
    weight=max(0.,min(1.,(source-times[a])/(times[a+1]-times[a])))
    result={}
    for name in data['arm_order']:
        first=Matrix(data['poses'][a][name]);second=Matrix(data['poses'][a+1][name])
        if returning:
            q0=data['return_rotations'][a][name];q1=data['return_rotations'][a+1][name]
            start=Quaternion((q0[3],q0[0],q0[1],q0[2]));end=Quaternion((q1[3],q1[0],q1[1],q1[2]))
        else:start=first.to_quaternion();end=second.to_quaternion()
        m=start.slerp(end,weight).to_matrix().to_4x4()
        m.translation=first.translation.lerp(second.translation,weight)
        result[name]=convert(m)
    return result

def source_time(age):
    age*=PLAYBACK_RATE
    if age<=0.:return 0.
    if age>=AUTHORED_LENGTH:return 1.95
    ages=settings['age_keys']
    sources=settings['source_keys']
    rates=settings['source_rates']
    a=next(i for i in range(8) if age<ages[i+1])
    span=ages[a+1]-ages[a];t=(age-ages[a])/span;t2=t*t;t3=t2*t
    return (2*t3-3*t2+1)*sources[a]+(t3-2*t2+t)*span*rates[a]+(-2*t3+3*t2)*sources[a+1]+(t3-t2)*span*rates[a+1]

for returning in (False,True):
    bpy.ops.wm.open_mainfile(filepath=str(P/'PalmUpOpeningV24/Spellbook_PalmUp_Preview.blend'))
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;scene.render.fps=FPS
    rig=bpy.data.objects['Spellbook_PhotoGripV3_V7_LeftArm']
    book=bpy.data.objects['SpellbookRig']
    samples=[];count=round((LENGTH if returning else LENGTH+.6)*FPS)+1
    for f in range(count):
        age=f/FPS;source=source_time(LENGTH-age if returning else age)
        frame=source*60;scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame))
        arms={b.name:b.matrix_basis.copy() for b in rig.pose.bones}
        for name,local in local_pose(min(source,1.62) if not returning else source,returning).items():
            bone=rig.pose.bones[name];ref=rig.data.bones[name]
            native=ref.parent.matrix_local.inverted()@ref.matrix_local if ref.parent else ref.matrix_local
            if name=='clavicle_l':local.translation+=bone.parent.matrix.to_3x3().inverted()@Vector((0,0,-.05))
            arms[name]=native.inverted()@local
        arms['book_spine_grip_l']=arms['book_spine_grip_l']@C
        bones={b.name:b.matrix_basis.copy() for b in book.pose.bones}
        bones['Book_Root']=C@bones['Book_Root']@C
        samples.append((arms,bones,book.matrix_world.copy()@C,source))
    for obj in (rig,book):
        obj.animation_data_clear();obj.animation_data_create()
        action=bpy.data.actions.new(('Recover' if returning else 'Opening')+'_V30_'+obj.name)
        obj.animation_data.action=action;action.use_fake_user=True
    previous={}
    for f,(arms,bones,frame,source) in enumerate(samples):
        scene.frame_set(f)
        for obj,poses in ((rig,arms),(book,bones)):
            for name,basis in poses.items():
                bone=obj.pose.bones[name];bone.rotation_mode='QUATERNION';bone.matrix_basis=basis
                key=(obj.name,name)
                if key in previous and bone.rotation_quaternion.dot(previous[key])<0:bone.rotation_quaternion.negate()
                previous[key]=bone.rotation_quaternion.copy()
                for prop in ('location','rotation_quaternion','scale'):bone.keyframe_insert(prop,frame=f)
        book.matrix_world=frame;book.rotation_mode='QUATERNION'
        if 'book' in previous and book.rotation_quaternion.dot(previous['book'])<0:book.rotation_quaternion.negate()
        previous['book']=book.rotation_quaternion.copy()
        for prop in ('location','rotation_quaternion','scale'):book.keyframe_insert(prop,frame=f)
        for constraint in book.constraints:
            constraint.influence=1. if source<.95 else 0.
            constraint.keyframe_insert('influence',frame=f)
    for obj in (rig,book):
        action=obj.animation_data.action
        if len(action.slots):obj.animation_data.action_slot=action.slots[0]
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:key.interpolation='CONSTANT' if 'influence' in curve.data_path else 'LINEAR'
    scene.frame_start=0;scene.frame_end=count-1;scene.timeline_markers.clear()
    if not returning:
        for label,age in [('Grip',0),('Soft grip settling',.84),('Finger unloading',1.04),('Opening preparation',1.40),('Sweep',1.57),('Settle',1.86),('Reading',AUTHORED_LENGTH)]:
            scene.timeline_markers.new(label,frame=round(age/PLAYBACK_RATE*FPS))
    else:
        for label,source in [('Fingers approach',1.24),('Contact and squeeze',1.07),('Grip fixed',.95)]:
            age=next(f/FPS for f in range(count) if source_time(LENGTH-f/FPS)<=source)
            scene.timeline_markers.new(label,frame=round(age*FPS))
    scene.frame_set(0)
    target=P/('Spellbook_Recover.blend' if returning else 'Spellbook_Focus.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(target))

(P/'editable-source.json').write_text(json.dumps({
    'revision':30,'opening':'Spellbook_Focus.blend','recover':'Spellbook_Recover.blend',
    'accepted_arm_source':'PalmUpOpeningV24/candidate.json',
    'book_direction':'local X half-turn at grip; conjugated book-root alignment',
    'arm_motion':'IntegratedV30/motion.json','arm_author':'IntegratedV30/author_motion.py',
    'settings':'IntegratedV30/motion-settings.json','editable_fps':FPS,
    'book_clips':'../PagesV1/author_pages.py','page_orientation':'../PagesV1/OrientationV2/rotate_uvs.py',
    'presentation_seconds':LENGTH,'soft_grip_settle_seconds':.20/PLAYBACK_RATE,'playback_rate':PLAYBACK_RATE,
    'source_seconds':1.95,'retiming':'shared monotone Hermite clock; distinct closing finger contact curve',
    'reading_sway':'existing runtime whole-arm layer preserved',
    'runtime_tested':False},indent=2),encoding='utf-8')
print('SPELLBOOK_V30_EDITABLE_SOURCES_SAVED')
