"""Remove V12's near-180 degree leg rolls without shrinking the run.

The V12 planted/recovering feet, hip/knee/ankle positions, donor body timing,
360/160 cm/s speed, large contralateral arms and V11 reference remain intact.
Only the thigh/calf orientation transports are replaced with minimal swing
from the original anatomical segment. No rigid-bone hinge normal is forced
to flip against the original Meshy reference bend.
"""
from pathlib import Path
import copy
import json
import math
import sys

import bpy
from mathutils import Matrix, Vector

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT=ROOT/'RecoveryV13Legs'
RIG_OUT=OUT/'rig_motion'
sys.path.insert(0,str(Path(__file__).parent))
import author_running_v12 as running
import author_motion_v04 as motion
import repair_leg_skin_v13 as skin


def qangle(q):
    return math.degrees(2.*math.acos(min(1.,abs(q.normalized().w))))


def author():
    OUT.mkdir(parents=True,exist_ok=True);RIG_OUT.mkdir(parents=True,exist_ok=True)
    old=json.loads((ROOT/'RunningV12/motion_manifest_v12.json').read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'RunningV12/M07_Original_Running_V12.blend'))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    ordered=sorted(rig.pose.bones,key=lambda p:len(p.bone.parent_recursive))
    visibility={o.name:o.hide_viewport for o in bpy.data.objects if o.type=='MESH'}
    for o in bpy.data.objects:
        if o.type=='MESH':o.hide_viewport=True
    cache={}
    for role,entry in old['clips'].items():
        motion.activate(rig,bpy.data.actions[entry['action']]);frames=[]
        for frame in range(1,entry['frames']+1):
            bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
            frames.append({p.name:p.matrix.copy() for p in ordered})
        cache[role]=frames
    actions={};manifest=copy.deepcopy(old)
    manifest.update({'revision':'RunningV13MinimalLegRoll','source':str(OUT/'M07_Original_LegRepair_V13.blend'),
        'source_master':str(ROOT/'RunningV12/M07_Original_Running_V12.blend'),
        'reference_pose_modified':False,'geometry_modified':False,'weights_modified':True,
        'method':'V12 complete large walk/run choreography retained; both thigh and calf use minimal original-segment swing transported by the pelvis, removing forced anatomical-hinge axial flips; V13 continuous original leg weights and body-only barycentric reduced-mesh transfer',
        'source_saved':False,'animation_fbx_exported':False,'ue_imported':False,
        'runtime_tested':False,'rendered':False,'tested':False,'visual_accepted':False})
    metrics={}
    for role,entry in manifest['clips'].items():
        action=bpy.data.actions.new('A_M07_'+role+'_RunningV13');action.use_fake_user=True
        motion.activate(rig,action);actions[role]=action;previous={};max_twist=0.
        for index,old_pose in enumerate(cache[role]):
            frame=index+1;bpy.context.scene.frame_set(frame)
            target={n:m.copy() for n,m in old_pose.items()}
            pelvis=target['pelvis'].to_quaternion()@rest['pelvis'].to_quaternion().inverted()
            for side in ('l','r'):
                for n,child in (('thigh','calf'),('calf','foot')):
                    name,next_name=n+'_'+side,child+'_'+side
                    reference=(rest[next_name].translation-rest[name].translation).normalized()
                    direction=(target[next_name].translation-target[name].translation).normalized()
                    transport=pelvis@reference
                    swing=transport.rotation_difference(direction)
                    rotation=swing@pelvis@rest[name].to_quaternion()
                    target[name]=Matrix.LocRotScale(target[name].translation,rotation,Vector((1.,1.,1.)))
                    residual=reference.rotation_difference(direction).inverted()@(rotation@rest[name].to_quaternion().inverted())
                    max_twist=max(max_twist,qangle(residual))
            running.insert_frame(rig,target,rest,ordered,frame,previous)
        bpy.context.scene.frame_set(0)
        for p in ordered:
            p.matrix_basis=Matrix.Identity(4)
            for prop in ('location','rotation_quaternion','scale'):
                p.keyframe_insert(data_path=prop,frame=0,group=p.name)
        for curve in running.curves(action):
            for point in curve.keyframe_points:point.interpolation='LINEAR'
        entry.update({'action':action.name,'file':str(RIG_OUT/('A_M07_'+role+'.fbx')),
            'asset':'/Game/Monsters/BlindSupplicantM07/AnimationsOriginalV13/A_M07_'+role,
            'leg_orientation':'Pelvis-transported minimal rest-segment swing, no forced reverse hinge normal',
            'max_extra_axial_rotation_deg':max_twist,'V12_joint_positions_and_contacts_retained':True})
        metrics[role]={'max_extra_axial_rotation_deg':max_twist,'all_original_leg_lengths_retained':True,
            'all_old_hip_knee_ankle_targets_retained':True,'walk_run_speed_cm_s':entry['speed_cm_s']}
        print('M07_V13_MINIMAL_ROLL_LOCOTION_AUTHORED '+role+' '+json.dumps(metrics[role]),flush=True)
    projection=skin.apply_to_master(rig)
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True)
    bpy.context.view_layer.objects.active=rig;scene=bpy.context.scene
    scene.render.fps=30;scene.render.fps_base=1.;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
    for role,entry in manifest['clips'].items():
        motion.activate(rig,actions[role]);scene.frame_start,scene.frame_end=1,entry['frames'];scene.frame_set(0)
        bpy.ops.export_scene.fbx(filepath=entry['file'],use_selection=True,object_types={'ARMATURE'},
            add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',
            bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_all_actions=False,
            bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,
            bake_anim_simplify_factor=0.,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_UNITS')
        print('M07_V13_LEG_REPAIRED_CLIP_EXPORTED '+role,flush=True)
    for n,hidden in visibility.items():bpy.data.objects[n].hide_viewport=hidden
    motion.activate(rig,actions['Chase']);scene.frame_start=1;scene.frame_end=manifest['clips']['Chase']['frames'];scene.frame_set(0)
    rig['leg_revision']='V13 local continuous original leg skin; pelvis-transported minimal swing, unchanged V11 reference'
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'],compress=True)
    manifest.update({'source_saved':True,'animation_fbx_exported':True,'leg_weight_projection':projection,
        'ten_V11_nonlocomotion_actions_retained_for_root_composition':True})
    skin.write_json(OUT/'motion_manifest_v13.json',manifest)
    diagnosis=json.loads((OUT/'v12_leg_source_diagnosis.json').read_text(encoding='utf-8'))
    skin.write_json(OUT/'leg_repair_delivery_v13.json',{'revision':'OriginalV13Legs',
        'source':manifest['source'],'weights':str(OUT/'original_continuous_leg_weights_v13.npz'),
        'motion_manifest':str(OUT/'motion_manifest_v13.json'),'bone_reference_changed':False,
        'original_mesh_and_uv_preserved':True,'V12_speed_stride_arms_and_joint_targets_preserved':True,
        'old_max_axial_rotation_deg':{r:diagnosis['clips'][r]['max_extra_axial_rotation_deg'] for r in diagnosis['clips']},
        'authored_leg_orientation':metrics,'weight_projection':projection,'source_saved':True,
        'ue_imported':False,'runtime_tested':False,'rendered':False,'visual_accepted':False,
        'root_assembly':'Open the V11 or V13 attack-repair master with the exact V11 reference. Call repair_leg_skin_v13.apply_to_master(rig), append only the two A_M07_<role>_RunningV13 actions from this blend, and use motion_manifest_v13.json clips for those roles. Then performance LOD assembly/export/import in root. No joint/rest change is required.'})
    print('M07_V13_LEG_MASTER_TWO_CLIPS_AND_LOCAL_SKIN_SAVED '+manifest['source'],flush=True)


if __name__=='__main__':author()
