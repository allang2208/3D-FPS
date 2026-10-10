"""Save the photo-based grip on the native V7 rig; no render or application UI."""
import bpy, bmesh, json, re
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[2]
data=json.loads((P/'grip.json').read_text(encoding='utf-8'))
tuning_source=ROOT/'Source/FPSGAME/Weapons/Spellbook/SpellbookCarryTuning.h'
tuning_text=tuning_source.read_text(encoding='utf-8')
tuning={name:float(re.search(r'\b'+name+r'\s*=\s*([0-9.]+)f',tuning_text).group(1))
        for name in ('WalkScale','RunScale','LowerCm')}

def carry_local(name,index):
    # Same normalized quaternion lerp and local translation blend as UE.
    # The source takes show the maximum envelope; gameplay adds its existing
    # speed blend and small time-dependent variation on top.
    idle=Matrix(data['poses'][0]['local'][name])
    sample=Matrix(data['poses'][index]['local'][name])
    weight=0. if index==0 else tuning['WalkScale'] if index<=32 else tuning['RunScale']
    a,b=idle.to_quaternion(),sample.to_quaternion()
    if a.dot(b)<0:b.negate()
    rotation=Quaternion(tuple(a[k]*(1-weight)+b[k]*weight for k in range(4)))
    rotation.normalize()
    result=rotation.to_matrix().to_4x4()
    result.translation=idle.translation.lerp(sample.translation,weight)
    return result
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/ApprenticeStaff20260927/LeftGaitV16/Staff_FreeLeftGait_V16.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['Staff_V7_FreeLeftGait_V16'];rig.name='Spellbook_PhotoGripV3_V7_LeftArm'
skins=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
for obj in list(bpy.data.objects):
    if obj!=rig and obj not in skins:bpy.data.objects.remove(obj,do_unlink=True)
rig.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
for obj in skins:
    # Deliver just this task's left arm; retain the native positions and weights.
    left={g.index for g in obj.vertex_groups if g.name.endswith('_l')}
    bm=bmesh.new();bm.from_mesh(obj.data);deform=bm.verts.layers.deform.active
    remove=[v for v in bm.verts if sum(w for g,w in v[deform].items() if g in left)<.5]
    bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(obj.data);bm.free()
    obj.name='V7_PhotoGrip_LeftSkin'

S=Matrix.Diagonal((1,-1,1))
def convert(m):
    m=Matrix(m);out=(S@m.to_3x3()@S).to_4x4();out.translation=S@m.translation*.01;return out
mount=Matrix(data['book_in_hand'])
bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bone=rig.data.edit_bones.new('book_spine_grip_l');bone.head=(0,0,0);bone.tail=(0,.025,0)
bone.matrix=rig.data.edit_bones['hand_l'].matrix@convert(mount);bone.length=.025
bone.parent=rig.data.edit_bones['hand_l']
bpy.ops.object.mode_set(mode='OBJECT')

source=P.parent/'Spellbook_Alchemy.blend'
with bpy.data.libraries.load(str(source),link=False) as (available,loaded):
    loaded.objects=[n for n in available.objects if n=='SM_Spellbook_Alchemy_Closed']
book=loaded.objects[0];bpy.context.collection.objects.link(book)
book.name='Alchemy_BluePurple_PhotoSpineGrip';book.hide_viewport=False;book.hide_render=False;book.hide_set(False)
book.parent=None;book.matrix_world=Matrix.Identity(4);book.scale=(.01,.01,.01)
for kind in ('COPY_LOCATION','COPY_ROTATION'):
    c=book.constraints.new(kind);c.target=rig;c.subtarget='book_spine_grip_l'
rig.animation_data_create();scene=bpy.context.scene;scene.render.fps=32
for label,indices in [('Idle',[0]),('Walk',list(range(1,33))+[1]),('Run',list(range(33,65))+[33])]:
    action=bpy.data.actions.new('A_Spellbook_PhotoGripV3_'+label);action.use_fake_user=True
    action['runtime_clock']='Existing offhand distance/footstep phase; the Blender loop is a normalized stride.'
    rig.animation_data.action=action;previous={}
    for frame,index in enumerate(indices):
        for n in data['poses'][index]['local']:
            bone=rig.pose.bones[n];ref=rig.data.bones[n]
            local=ref.parent.matrix_local.inverted()@ref.matrix_local if ref.parent else ref.matrix_local
            display=convert(carry_local(n,index))
            if n=='clavicle_l':
                lower=Vector((0,0,-tuning['LowerCm']*.01))
                display.translation+=bone.parent.matrix.to_3x3().inverted()@lower if bone.parent else lower
            bone.rotation_mode='QUATERNION';bone.matrix_basis=local.inverted()@display
            if n in previous and bone.rotation_quaternion.dot(previous[n])<0:bone.rotation_quaternion.negate()
            previous[n]=bone.rotation_quaternion.copy()
            for prop in ('location','rotation_quaternion','scale'):bone.keyframe_insert(prop,frame=frame)
rig.animation_data.action=bpy.data.actions['A_Spellbook_PhotoGripV3_Idle']
if len(rig.animation_data.action.slots):rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_start=0;scene.frame_end=32;scene.frame_set(0)
rig['reference']=data['reference'];rig['grip_intent']=data['intent'];rig['runtime_table']='SpellbookAuthoredGrip.h / Revision 3'
rig['carry_tuning']=json.dumps(tuning)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Spellbook_PhotoGripV3.blend'))
(P/'editable-source.json').write_text(json.dumps({'file':'Spellbook_PhotoGripV3.blend','revision':3,'takes':['Idle','Walk','Run'],
    'carry_tuning':tuning,'carry_tuning_source':str(tuning_source),
    'runtime':'native C++ pose table; no UE animation reimport required','rendered':False,'runtime_tested':False},indent=2),encoding='utf-8')
print('Saved editable photo grip, native left arm, book and normalized gait takes.',flush=True)
