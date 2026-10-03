"""Correct three index rotation tracks and extract the requested contact diagnostics."""
import bpy,json,shutil
from pathlib import Path
from mathutils import Quaternion
O=Path(__file__).parent;BASE=O.parent;PREVIOUS=BASE/'FingerContactV3'
prior=json.loads((PREVIOUS/'authoring.json').read_text())
old_fits=json.loads((PREVIOUS/'selected_grasp.json').read_text())
fits=json.loads((O/'selected_grasp.json').read_text())
transitions=json.loads((O/'transitions.json').read_text())
live={x['asset']:x for x in json.loads((O/'sources.json').read_text())['animations']}
receipt=json.loads((O/'authoring.json').read_text()) if (O/'authoring.json').exists() else {}
samples=json.loads((O/'source_pose_samples.json').read_text()) if (O/'source_pose_samples.json').exists() else {}
if (O/'source_pose_samples.json').exists() and not (O/'transition_input_poses.json').exists():
    shutil.copy2(O/'source_pose_samples.json',O/'transition_input_poses.json')
data=json.loads((BASE/'fit_input.json').read_text())
bpy.context.preferences.filepaths.save_version=0
bones=['index_01_l','index_02_l','index_03_l']
sample_frames=[f/2 for f in range(56,101)]+[148.]+[f/2 for f in range(472,509)]
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def curves(action):
    return {fc.data_path+'#'+str(fc.array_index):fc for la in action.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves}
for key,info in prior.items():
    if key in receipt and receipt[key].get('recipe')=='staged-index-path-v3':continue
    if Path(live[info['asset']]['source'][0]).resolve()!=Path(info['fbx']).resolve():
        raise RuntimeError('Installed source changed since V3: '+info['asset'])
    bpy.ops.wm.open_mainfile(filepath=info['blend']);s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
    old=r.animation_data.action;action=old.copy();action.name=Path(info['fbx']).stem+'_IndexClearanceV4';action.use_fake_user=True
    r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    current=curves(action);fit=fits[info['gun']];transition=transitions[info['gun']]
    for n in bones:
        tracks=[current[f'pose.bones["{n}"].rotation_quaternion#{i}'] for i in range(4)]
        hold=Quaternion(fit['finger_basis'][n]);opened=Quaternion(transition['open_basis'][n])
        previous=None
        for index,keyframe in enumerate(tracks[0].keyframe_points):
            f=float(keyframe.co.x);q=Quaternion([curve.keyframe_points[index].co.y for curve in tracks])
            if 20<=f<=254:
                original_q=q.copy()
                q=q.slerp(opened,smooth((f-20)/12))
                q=q.slerp(hold,smooth((f-38)/8))
                q=q.slerp(opened,smooth((f-237)/8))
                q=q.slerp(original_q,smooth((f-244)/10));q.normalize()
            if previous is not None and previous.dot(q)<0:q.negate()
            previous=q.copy()
            for axis,curve in enumerate(tracks):curve.keyframe_points[index].co.y=q[axis];curve.keyframe_points[index].interpolation='LINEAR'
        for curve in tracks:curve.update()
    rows={}
    for f in sample_frames:
        s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();mag_inverse=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted()
        rows[str(f)]={n:[list(row) for row in mag_inverse@r.pose.bones[n].matrix] for n in data['names']}
    samples[key]=rows
    (O/'source_pose_samples.json').write_text(json.dumps(samples),encoding='utf-8')
    dest=O/info['gun']/info['magazine']/info['family'];dest.mkdir(parents=True,exist_ok=True)
    filename=Path(info['fbx']).stem;s.frame_set(148)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/(filename+'.blend')))
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(dest/(filename+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=info['fps']/info['rate'],bake_anim_simplify_factor=0)
    receipt[key]={**info,'previous_blend':info['blend'],'blend':str(dest/(filename+'.blend')),'fbx':str(dest/(filename+'.fbx')),
                  'revision':'IndexClearanceV4','recipe':'staged-index-path-v3','changed_bones':bones,'edit_frames':[20,254],
                  'index_prepare_frames':[20,32],'index_close_frames':[38,46],'index_open_frames':[237,245],'index_return_frames':[244,254],
                  'other_fingers_and_palm_preserved':True,'game_tested':False}
    (O/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('INDEX_ANIMATION_AUTHORED',key,flush=True)
