"""Apply four-finger contact refinement over the accepted rear-thumb clips."""
import bpy,json
from pathlib import Path
from mathutils import Quaternion

O=Path(__file__).parent; BASE=O.parent; PREVIOUS=BASE/'ThumbOppositionV2'
prior=json.loads((PREVIOUS/'authoring.json').read_text())
old_fits=json.loads((PREVIOUS/'selected_grasp.json').read_text())
fits=json.loads((O/'selected_grasp.json').read_text())
receipt=json.loads((O/'authoring.json').read_text()) if (O/'authoring.json').exists() else {}
bpy.context.preferences.filepaths.save_version=0
fingers=[digit+f'_{j:02d}_l' for digit in ('index','middle','ring','pinky') for j in (1,2,3)]

def smooth(t):
    t=max(0,min(1,t)); return t*t*(3-2*t)

def curves(action):
    return {fc.data_path+'#'+str(fc.array_index):fc for la in action.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves}

for key,info in prior.items():
    if key in receipt: continue
    bpy.ops.wm.open_mainfile(filepath=info['blend'])
    s=bpy.context.scene; r=bpy.data.objects['SK_M4_Infima']
    old=r.animation_data.action
    action=old.copy(); action.name=Path(info['fbx']).stem+'_FingerContactV3'; action.use_fake_user=True
    r.animation_data.action=action; r.animation_data.action_slot=action.slots[0]
    current=curves(action); fit=fits[info['gun']]; old_fit=old_fits[info['gun']]
    for n in fingers:
        tracks=[current[f'pose.bones["{n}"].rotation_quaternion#{i}'] for i in range(4)]
        delta=Quaternion(old_fit['finger_basis'][n]).inverted() @ Quaternion(fit['finger_basis'][n])
        if delta.w<0: delta.negate()
        delay={'index':1.5,'middle':2.5,'ring':3.5,'pinky':4.5}[n.split('_')[0]]
        previous=None
        for index,keyframe in enumerate(tracks[0].keyframe_points):
            f=float(keyframe.co.x)
            q=Quaternion([curve.keyframe_points[index].co.y for curve in tracks])
            # Add the contact refinement as the fingers close. Remove it by
            # the existing open pose, keeping the return and bolt work intact.
            weight=smooth((f-20-delay)/24)*(1-smooth((f-237)/13))
            if weight>0:
                q=q @ Quaternion().slerp(delta,weight); q.normalize()
            if previous is not None and previous.dot(q)<0: q.negate()
            previous=q.copy()
            for axis,curve in enumerate(tracks):
                curve.keyframe_points[index].co.y=q[axis]
                curve.keyframe_points[index].interpolation='LINEAR'
        for curve in tracks: curve.update()
    dest=O/info['gun']/info['magazine']/info['family']; dest.mkdir(parents=True,exist_ok=True)
    filename=Path(info['fbx']).stem; s.frame_set(148)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/(filename+'.blend')))
    bpy.ops.object.select_all(action='DESELECT'); r.hide_set(False); r.select_set(True)
    bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(dest/(filename+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=info['fps']/info['rate'],bake_anim_simplify_factor=0)
    receipt[key]={**info,'previous_blend':info['blend'],'blend':str(dest/(filename+'.blend')),
                  'fbx':str(dest/(filename+'.fbx')),'revision':'FingerContactV3','changed_bones':fingers,
                  'edit_frames':[21.5,250],'tighten_close_delays':{'index':1.5,'middle':2.5,'ring':3.5,'pinky':4.5},
                  'tighten_release_frames':[237,250],'palm_and_thumb_preserved':True,'game_tested':False}
    (O/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('FOUR_FINGER_ANIMATION_AUTHORED',key,flush=True)
