import bpy,json,copy,hashlib
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent
source=S/'Super90LoaderR21_20261010/Super90_Speedloader_R21.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));rig=bpy.data.objects['SK_Super90'];scene=bpy.context.scene;scene.render.fps=60
surface=json.loads((O/'bind_surface.json').read_text());skin=bpy.data.objects['Super90_V7_M4_BareArmsV6']
for edit in surface['edits']:skin.data.vertices[edit['index']].co=edit['after']
skin.data.update()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones};I=Matrix.Identity(4)
lr={n:rest.get(parents[n],I).inverted()@rest[n] for n in rest}
changed=['hand_l',*[n for n in rest if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]]
poses=json.loads((O/'contact_poses.json').read_text());manifest=json.loads((S/'Super90LoaderR21_20261010/authoring.json').read_text())
X=O/'Exports';X.mkdir(exist_ok=True);report=dict(revision='LoaderR23-20261010',source=str(source),modified_bones=changed,
    support_owner='Super90SupportArmNode after runtime channel/grip blending; preview in repaired_poses.json',
    left_elbow_surface='bind_surface.json',runtime_tested=False,clips=[])
for clip in manifest['clips']:
    name=clip['name']
    if '_normal_' in name:continue
    branch='cycle' if name.endswith('_cycle') else 'empty';ps=[{n:Matrix(m) for n,m in p.items()} for p in poses[branch]]
    action=bpy.data.actions[name];bag=action.layers[0].strips[0].channelbag(action.slots[0]);curves={(c.data_path,c.array_index):c for c in bag.fcurves}
    for n in changed:
        values=[]
        for p in ps:
            v=list((lr[n].inverted()@p.get(parents[n],I).inverted()@p[n]).decompose())
            if values and values[-1][1].dot(v[1])<0:v[1].negate()
            values.append(v)
        for prop,field,size in (('location',0,3),('rotation_quaternion',1,4),('scale',2,3)):
            for axis in range(size):
                curve=curves[(f'pose.bones["{n}"].{prop}',axis)]
                for key in curve.keyframe_points:
                    f=round(key.co.x)
                    if 0<=f<len(values):key.co.y=values[f][field][axis]
                curve.update()
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];scene.frame_start=0;scene.frame_end=len(ps)-1;scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    file=X/(name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    record=copy.deepcopy(clip);record.update(file=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest());report['clips'].append(record)
    print('R23_AUTHORED',name,flush=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_Speedloader_R23.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2));print('SUPER90_R23_AUTHORED',len(report['clips']),flush=True)
