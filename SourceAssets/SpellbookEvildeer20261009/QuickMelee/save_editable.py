"""Save the authored shove on the accepted V7 book rig, without rendering."""
import bpy,json,re
from pathlib import Path
from mathutils import Matrix,Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[2]
data=json.loads((P/'strike.json').read_text(encoding='utf-8'))
tuning=(ROOT/'Source/FPSGAME/Weapons/Spellbook/SpellbookCarryTuning.h').read_text(encoding='utf-8')
lower=float(re.search(r'\bLowerCm\s*=\s*([0-9.]+)f',tuning).group(1))
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'GripPhotoV3/Spellbook_PhotoGripV3.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['Spellbook_PhotoGripV3_V7_LeftArm']
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
action=bpy.data.actions.new('A_Spellbook_F_ForwardShove');action.use_fake_user=True
rig.animation_data.action=action
S=Matrix.Diagonal((1,-1,1));previous={}
for time,pose in zip(data['times'],data['poses']):
    for name in data['arm_order']:
        bone=rig.pose.bones[name];ref=rig.data.bones[name]
        rest=ref.parent.matrix_local.inverted()@ref.matrix_local if ref.parent else ref.matrix_local
        src=Matrix(pose['local'][name]);display=(S@src.to_3x3()@S).to_4x4()
        display.translation=S@src.translation*.01
        if name=='clavicle_l':
            offset=Vector((0,0,-lower*.01))
            display.translation+=bone.parent.matrix.to_3x3().inverted()@offset if bone.parent else offset
        bone.rotation_mode='QUATERNION';bone.matrix_basis=rest.inverted()@display
        if name in previous and bone.rotation_quaternion.dot(previous[name])<0:bone.rotation_quaternion.negate()
        previous[name]=bone.rotation_quaternion.copy()
        for prop in ('location','rotation_quaternion','scale'):bone.keyframe_insert(prop,frame=time*120)
# Dense authored frames use linear interpolation just like the runtime pose table.
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:key.interpolation='LINEAR'
if len(action.slots):rig.animation_data.action_slot=action.slots[0]
scene=bpy.context.scene;scene.render.fps=120;scene.frame_start=0;scene.frame_end=52;scene.frame_set(0)
for label,time in zip(('Entry','Release','Drive','Contact','Follow','Recover','End'),data['landmarks']):
    scene.timeline_markers.new(label,frame=round(time*120))
rig['quick_melee_intent']=data['intent'];rig['runtime_table']='SpellbookAuthoredStrike.h'
action['seconds']=.43;action['contact_seconds']=.14
action['grip']='Fixed photo spine grip and book mount'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Spellbook_QuickMelee.blend'))
(P/'editable-source.json').write_text(json.dumps({'file':'Spellbook_QuickMelee.blend',
    'action':action.name,'length_seconds':.43,'contact_seconds':.14,'lower_cm':lower,
    'runtime':'C++ native pose table, same F action clock; no AnimationSequence reimport',
    'runtime_tested':False,'rendered':False},indent=2),encoding='utf-8')
print('Saved editable fixed-grip spellbook forward shove.')
