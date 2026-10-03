"""Change only three thumb rotation tracks; keep the preceding four-finger wrap."""
import bpy,json,sys
from pathlib import Path
from mathutils import Quaternion
O=Path(__file__).parent;BASE=O.parent
prior=json.loads((BASE/'authoring.json').read_text())
fits=json.loads((O/'selected_grasp.json').read_text())
receipt=json.loads((O/'authoring.json').read_text()) if (O/'authoring.json').exists() else {}
bpy.context.preferences.filepaths.save_version=0
thumb=['thumb_01_l','thumb_02_l','thumb_03_l']
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def curves(action):
    return {fc.data_path+'#'+str(fc.array_index):fc for la in action.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves}
for key,info in prior.items():
    if key in receipt:continue
    bpy.ops.wm.open_mainfile(filepath=info['blend']);s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
    old=r.animation_data.action
    # Read the original entry/return thumb action without appending its meshes
    # or changing the already authored wrist, forearm or four-finger tracks.
    with bpy.data.libraries.load(info['original_blend'],link=False) as (src,dst):
        dst.objects=['SK_M4_Infima']
    original_rig=dst.objects[0];original_action=original_rig.animation_data.action
    original=curves(original_action)
    action=old.copy();action.name=Path(info['fbx']).stem+'_RearThumbV2';action.use_fake_user=True
    r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    current=curves(action);fit=fits[info['gun']]
    finish=272 if info['clip']=='reload_empty' else 284
    for n in thumb:
        tracks=[current[f'pose.bones["{n}"].rotation_quaternion#{i}'] for i in range(4)]
        baseline=[original[f'pose.bones["{n}"].rotation_quaternion#{i}'] for i in range(4)]
        hold=Quaternion(fit['finger_basis'][n]);opened=Quaternion(fit['open_thumb_basis'][n]);previous=None
        for index,keyframe in enumerate(tracks[0].keyframe_points):
            f=float(keyframe.co.x)
            if 14<=f<=finish:
                original_q=Quaternion([curve.evaluate(f) for curve in baseline]);original_q.normalize()
                # Reach the rear side while the hand approaches. Close from
                # that side only after the thumb has cleared the shell edge.
                q=original_q.slerp(opened,smooth((f-14)/18))
                q=q.slerp(hold,smooth((f-30)/18))
                q=q.slerp(opened,smooth((f-237)/13))
                q=q.slerp(original_q,smooth((f-248)/(finish-248)))
            else:q=Quaternion([curve.keyframe_points[index].co.y for curve in tracks])
            if previous is not None and previous.dot(q)<0:q.negate()
            previous=q.copy()
            for axis,curve in enumerate(tracks):curve.keyframe_points[index].co.y=q[axis];curve.keyframe_points[index].interpolation='LINEAR'
        for curve in tracks:curve.update()
    bpy.data.objects.remove(original_rig,do_unlink=True)
    dest=O/info['gun']/info['magazine']/info['family'];dest.mkdir(parents=True,exist_ok=True)
    filename=Path(info['fbx']).stem;s.frame_set(148)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/(filename+'.blend')))
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.fbx(filepath=str(dest/(filename+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=info['fps']/info['rate'],bake_anim_simplify_factor=0)
    receipt[key]={**info,'previous_blend':info['blend'],'blend':str(dest/(filename+'.blend')),'fbx':str(dest/(filename+'.fbx')),
                  'revision':'ThumbOppositionV2','changed_bones':thumb,'edit_frames':[14,finish],
                  'thumb_open_rear_frames':[14,32],'thumb_close_frames':[30,48],'thumb_release_frames':[237,250]}
    (O/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('REAR_THUMB_ANIMATION_AUTHORED',key,flush=True)
