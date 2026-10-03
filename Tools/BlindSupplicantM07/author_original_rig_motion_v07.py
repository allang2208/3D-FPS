"""Fresh M07 ORIGINAL-geometry rig and clean-source motion authoring.

Only original-source joint guides and point positions inform the target rig.
Epic mannequin FBXs provide reference bone axes and animation, never geometry.
The saved target source is centimeter-native and uses the dummy Armature name.
No preview, render, simulation, playback, runtime test or acceptance is performed.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT / 'RecoveryOriginalV07/rig_motion'
TOOLS = ROOT.parents[1] / 'Tools/BlindSupplicantM07'
FOUNDATION = ROOT.parent / 'WitchFoundation20260920'
FINGERS = ('thumb', 'index', 'middle', 'ring', 'pinky')
FPS = 30


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def original_points():
    source = np.load(ROOT / 'Authoring/source_mesh.npz')
    guides = json.loads((ROOT / 'Authoring/region_authoring.json').read_text(encoding='utf-8'))
    original_sections = ROOT/'RecoveryOriginalV07/regions/joint_guides_source.json'
    if original_sections.is_file():
        measured = json.loads(original_sections.read_text(encoding='utf-8'))
        guides['joint_guides_source'] = measured['joint_guides_source']
        guides['anatomical_section_source'] = str(original_sections)
    raw = source['positions'].astype(np.float64)
    scale = float(guides['scale_to_meters'])
    ground = float(guides['ground_source_y'])
    points = np.c_[raw[:, 0], -raw[:, 2], raw[:, 1] - ground] * scale
    joints = {n: Vector((p[0]*scale, -p[2]*scale, (p[1]-ground)*scale))
              for n, p in guides['joint_guides_source'].items()}
    return raw, points, joints, guides


def make_reference():
    OUT.mkdir(parents=True, exist_ok=True)
    raw, points, joints, input_guides = original_points()
    source_profiles = {}
    for side, sign in (('l',1),('r',-1)):
        rows=[]
        for x in np.arange(.18,.97,.04):
            use=(np.abs(raw[:,0]*sign-x)<.008)&(raw[:,1]>.29)
            cloud=raw[use]
            if len(cloud):
                rows.append({'x':float(x),'n':len(cloud),'yz_min':cloud[:,1:].min(axis=0).tolist(),
                    'yz_max':cloud[:,1:].max(axis=0).tolist(),'yz_median':np.median(cloud[:,1:],axis=0).tolist()})
        source_profiles[side]=rows
    write_json(OUT/'original_arm_surface_profiles.json',source_profiles)
    # The former wrist guide was behind and below the actual original hand,
    # and also inside the fingers. Refit true shoulder/elbow/wrist sections.
    fitted_joint_source = dict(input_guides['joint_guides_source'])
    for side, sign in (('l',1),('r',-1)):
        for name, x in (('upperarm',.190),('lowerarm',.460),('hand',.655)):
            use=(np.abs(raw[:,0]*sign-x)<.012)&(raw[:,1]>.390)&(raw[:,1]<.510)&(raw[:,2]>-.103)
            cloud=raw[use]
            if len(cloud)<8:
                raise RuntimeError('Original arm section is unavailable: '+name+'_'+side)
            # The midpoint of section extrema centers the bone inside the
            # surface rather than letting dense cuff topology bias it.
            yz=(np.quantile(cloud[:,1:],.03,axis=0)+np.quantile(cloud[:,1:],.97,axis=0))*.5
            value=[sign*x,float(yz[0]),float(yz[1])]
            fitted_joint_source[name+'_'+side]=value
            scale=input_guides['scale_to_meters'];ground=input_guides['ground_source_y']
            joints[name+'_'+side]=Vector((value[0]*scale,-value[2]*scale,(value[1]-ground)*scale))
    # Import the Epic source once to retain a mature parent topology and bone
    # roll convention. No source mesh is copied or fitted to this monster.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FOUNDATION / 'Sources/Quinn.fbx'), use_anim=False)
    donor = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    old = {b.name: donor.matrix_world @ b.matrix_local for b in donor.data.bones}
    parents = {b.name: b.parent.name if b.parent else None for b in donor.data.bones}
    old_tails = {b.name: donor.matrix_world @ b.tail_local for b in donor.data.bones}
    wanted = set(joints)
    wanted.update(n for n in old if n.startswith(tuple(f+'_' for f in FINGERS))
                  and n.split('_')[-2] in ('01', '02', '03', 'metacarpal'))
    next_bone = {'pelvis': 'spine_01', 'spine_01': 'spine_02', 'spine_02': 'spine_03',
                 'spine_03': 'spine_04', 'spine_04': 'spine_05', 'spine_05': 'neck_01',
                 'neck_01': 'neck_02', 'neck_02': 'head'}
    for side in ('l', 'r'):
        for a, b in (('clavicle','upperarm'), ('upperarm','lowerarm'), ('lowerarm','hand'),
                     ('thigh','calf'), ('calf','foot'), ('foot','ball')):
            next_bone[a+'_'+side] = b+'_'+side
    target = {}
    actual_finger_guides = {}
    finger_tips = {}
    hand_characterization = {}
    for n, position in joints.items():
        ref = old[n]
        following = next_bone.get(n)
        if following:
            source_axis = old[following].translation-ref.translation
            target_axis = joints[following]-position
        elif n == 'head':
            source_axis = old_tails[n]-ref.translation
            target_axis = Vector((0, -.015, .105))
        elif n.startswith('hand_'):
            side = n[-1]
            source_axis = old['middle_01_'+side].translation-ref.translation
            # The source is an outward arm reference, with the long five
            # fingers continuing along the forearm before the hanging pose.
            target_axis = (joints[n]-joints['lowerarm_'+side]).normalized()
        else:
            source_axis = old_tails[n]-ref.translation
            target_axis = Vector((0, -.10, .0))
        swing = source_axis.normalized().rotation_difference(target_axis.normalized())
        frame = (swing @ ref.to_quaternion()).to_matrix().to_4x4()
        frame.translation = position
        target[n] = frame
    for side, sign in (('l', 1), ('r', -1)):
        wrist = joints['hand_'+side]
        # The hand starts at its actual palm transition, not the former guide
        # inside the fingers. Five semantic lanes follow original hand depth.
        hand_ids=np.flatnonzero((raw[:,0]*sign>.65)&(raw[:,1]>.375)&(raw[:,1]<.49))
        hand_raw=raw[hand_ids];hand=points[hand_ids]
        section=hand_raw[np.abs(hand_raw[:,0]*sign-.78)<.012]
        z_lanes=np.quantile(section[:,2],[.96,.75,.50,.25,.04])
        hand_characterization[side]={'source_vertex_count':len(hand_ids),
            'bounds_m':[hand.min(axis=0).tolist(),hand.max(axis=0).tolist()],
            'wrist_m':list(wrist),'finger_lane_source_z':z_lanes.tolist()}
        chains={}
        for finger, lane in zip(FINGERS,z_lanes):
            lane_mask=np.abs(hand_raw[:,2]-lane)<.012
            lane_cloud=hand_raw[lane_mask]
            tip_x=float(np.quantile(lane_cloud[:,0]*sign,.99))
            base_x=.680 if finger=='thumb' else .735
            # Center phalanges on the original digit's local cross-section.
            chain=[]
            for amount in (0.,.38,.73,1.):
                x=base_x+(tip_x-base_x)*amount
                cloud=lane_cloud[np.abs(lane_cloud[:,0]*sign-x)<.011]
                if len(cloud)<6:
                    distances=(lane_cloud[:,0]*sign-x)**2+((lane_cloud[:,2]-lane)*.5)**2
                    cloud=lane_cloud[np.argsort(distances)[:min(32,len(lane_cloud))]]
                yz=(np.quantile(cloud[:,1:],.06,axis=0)+np.quantile(cloud[:,1:],.94,axis=0))*.5
                scale=input_guides['scale_to_meters'];ground=input_guides['ground_source_y']
                chain.append(Vector((sign*x*scale,-float(yz[1])*scale,(float(yz[0])-ground)*scale)))
            chains[finger]=chain
            actual_finger_guides[finger+'_'+side]=[list(v) for v in chain[:3]]
            finger_tips[finger+'_'+side]=list(chain[3])
        def frame_axes(along,across):
            along=along.normalized();across=(across-along*across.dot(along)).normalized()
            normal=along.cross(across).normalized()
            return Matrix((along,across,normal)).transposed()
        donor_hand_frame=frame_axes(old['middle_01_'+side].translation-old['hand_'+side].translation,
            old['index_01_'+side].translation-old['pinky_01_'+side].translation)
        original_hand_frame=frame_axes(chains['middle'][0]-wrist,chains['index'][0]-chains['pinky'][0])
        hand_swing=(original_hand_frame@donor_hand_frame.transposed()).to_quaternion()
        frame=(hand_swing@old['hand_'+side].to_quaternion()).to_matrix().to_4x4();frame.translation=wrist
        target['hand_'+side]=frame
        for finger in FINGERS:
            chain=chains[finger]
            for segment in (1,2,3):
                n=f'{finger}_{segment:02d}_{side}'
                source_axis=old_tails[n]-old[n].translation
                posed_source_axis=hand_swing@source_axis
                direction=chain[segment]-chain[segment-1]
                digit_swing=posed_source_axis.normalized().rotation_difference(direction.normalized())
                frame=(digit_swing@hand_swing@old[n].to_quaternion()).to_matrix().to_4x4()
                frame.translation=chain[segment-1];target[n]=frame
            meta=finger+'_metacarpal_'+side
            if meta in wanted:
                frame=(hand_swing@old[meta].to_quaternion()).to_matrix().to_4x4()
                frame.translation=wrist.lerp(chain[0],.25);target[meta]=frame
    # Remove every imported source object and animation. The target file
    # contains only its own original-fitted armature.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    data = bpy.data.armatures.new('M07_OriginalReferenceV07')
    rig = bpy.data.objects.new('Armature', data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for n in sorted(wanted):
        b = data.edit_bones.new(n)
        b.matrix = target[n]
        following = next_bone.get(n)
        if following:
            b.length = max(.012, (joints[following]-joints[n]).length)
        elif n.startswith(tuple(f+'_' for f in FINGERS)):
            finger, segment, side = n.split('_')
            if segment=='metacarpal':
                b.length=max(.012,(target[finger+'_01_'+side].translation-target[n].translation).length)
            else:
                following = f'{finger}_{int(segment)+1:02d}_{side}' if int(segment)<3 else None
                b.length = max(.012, (target[following].translation-target[n].translation).length) if following else (Vector(finger_tips[finger+'_'+side])-target[n].translation).length
        else:
            b.length = .075 if n=='head' else .055
    for n in sorted(wanted):
        parent = parents.get(n)
        while parent and parent not in wanted:
            parent = parents.get(parent)
        if parent:
            data.edit_bones[n].parent = data.edit_bones[parent]
    # Six chain bases are derived from the original shoulder/back attachment,
    # and remain independent of any membrane reconstruction or old partition.
    gill_guides = {}
    scale = input_guides['scale_to_meters']; ground = input_guides['ground_source_y']
    attachment_path = ROOT/'RecoveryOriginalV07/gill_reference_guides_source.json'
    original_attachments = json.loads(attachment_path.read_text(encoding='utf-8')) if attachment_path.is_file() else {}
    for panel in range(1, 7):
        side = 'l' if panel <=3 else 'r'; sign = 1 if side=='l' else -1
        layer = (panel-1)%3
        depth = (-.185, -.125, -.060)[layer]
        root_raw = np.array((sign*.16, .455, depth))
        tip_raw = np.array((sign*(.27+layer*.015), -.48-layer*.06, depth-.025))
        if str(panel) in original_attachments:
            root_raw = np.asarray(original_attachments[str(panel)]['root_source'])
            tip_raw = np.asarray(original_attachments[str(panel)]['tip_source'])
        def convert(p): return Vector((p[0]*scale, -p[2]*scale, (p[1]-ground)*scale))
        a, c = convert(root_raw), convert(tip_raw)
        chain=[]
        for segment in range(3):
            n=f'gill_{panel:02d}_{segment:02d}'; b=data.edit_bones.new(n)
            b.head=a.lerp(c, segment/3); b.tail=a.lerp(c,(segment+1)/3)
            attachment_parent = original_attachments.get(str(panel), {}).get('parent_bone', 'spine_05')
            b.parent=data.edit_bones[chain[-1]] if chain else data.edit_bones[attachment_parent]
            chain.append(n)
        gill_guides[f'{panel:02d}']={'side':side,'root_m':list(a),'tip_m':list(c),
            'chain':chain,'base_source_xyz':root_raw.tolist(),'tip_source_xyz':tip_raw.tolist(),
            'method':'Original shoulder/back attachment guide; hidden simulation surface may use this chain'}
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.animation_data_clear()
    for p in rig.pose.bones:
        p.rotation_mode='QUATERNION'; p.matrix_basis=Matrix.Identity(4)
    scene=bpy.context.scene
    scene.render.fps=FPS; scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    scene.frame_set(0)
    rig['visible_geometry_source']='Original Meshy GLB only; no donor mesh present'
    rig['reference_revision']='OriginalV07'
    path=OUT/'M07_OriginalReference_Meter_V07.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    record={'revision':'OriginalV07','source_glb':str(ROOT/'Original/Meshy_AI_Veilwing_07_1001123357_texture.glb'),
        'joint_guides_source':fitted_joint_source,
        'old_guide_correction':'Former wrist guide was behind/below actual hand and placed inside fingers; shoulder, elbow and wrist refitted to original arm sections',
        'joint_guides_m':{n:list(v) for n,v in joints.items()},
        'finger_guides_m':actual_finger_guides,'finger_tip_guides_m':finger_tips,
        'finger_fit_method':'Five original-source depth lanes, original digit extent and local surface section centers; Epic bone roll convention only',
        'hands_source_characterization':hand_characterization,
        'gill_guides':gill_guides,'bone_count':len(data.bones),
        'bone_names':list(data.bones.keys()),'parents':{b.name:b.parent.name if b.parent else None for b in data.bones},
        'meter_reference_source':str(path),'source_mesh_used':False,'donor_geometry_used':False,
        'reference_pose':'Original Meshy reference arms; animation can move limbs without modifying the rest geometry',
        'tested':False,'rendered':False,'user_accepted':False}
    write_json(OUT/'original_rig_guides.json',record)
    print('M07_ORIGINAL_V07_REFERENCE '+json.dumps({'path':str(path),'bones':len(data.bones),'hands':hand_characterization}),flush=True)
    return path


def author_motion():
    # Reuse the clean mathematical implementation, not its old M07 skeleton,
    # anatomy meshes, rig master or baked motion. Its raw donor import is fresh.
    spec=importlib.util.spec_from_file_location('m07_clean_motion_math',TOOLS/'author_motion_v04.py')
    motion=importlib.util.module_from_spec(spec);spec.loader.exec_module(motion)
    motion.MASTER=OUT/'M07_OriginalReference_Meter_V07.blend'
    motion.OUT=OUT/'motion_meter'
    motion.author()
    manifest=json.loads((motion.OUT/'motion_manifest.json').read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(motion.OUT/'M07_Motion_V04.blend'))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    sys.path.insert(0, str(TOOLS))
    import author_hindlegs_v07
    import author_hand_actions_v07
    for role, entry in manifest['clips'].items():
        action = bpy.data.actions.get(entry['action'])
        author_hindlegs_v07.apply_motion(rig, action, 'A_M07_'+role, fps=FPS, unit_scale=1)
        author_hand_actions_v07.apply_motion(rig, action, role, entry['frames'], FPS, motion.activate)
    manifest['method'] = 'Original-source anatomy; canine hindleg control curves adapted to biped phase and dimensions; human palm and finger articulation; explicit parent-local reference conversion'
    rig.name='Armature'; rig.data.name='M07_OriginalReferenceV07'
    rig.data.transform(Matrix.Scale(100,4))
    rig.matrix_world=Matrix.Identity(4)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
    for action in bpy.data.actions:
        curves=action.fcurves if not action.is_action_layered else [c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves]
        for c in curves:
            if c.data_path.endswith('.location'):
                for k in c.keyframe_points:
                    k.co.y*=100;k.handle_left.y*=100;k.handle_right.y*=100
        action.use_fake_user=True
    rig.animation_data_create()
    for role, entry in manifest['clips'].items():
        action=bpy.data.actions.get(entry['action']);motion.activate(rig,action)
        scene.frame_start=1;scene.frame_end=entry['frames'];scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
        path=OUT/f'A_M07_{role}.fbx'
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},
            add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',
            bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_all_actions=False,
            bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,
            bake_anim_step=1,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',
            apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
        entry.update({'file':str(path),'asset':'/Game/Monsters/BlindSupplicantM07/AnimationsOriginalV07/A_M07_'+role})
        print('M07_ORIGINAL_V07_CLIP '+role,flush=True)
    motion.activate(rig,bpy.data.actions.get(manifest['clips']['Idle']['action']))
    scene.frame_start=1;scene.frame_end=121;scene.frame_set(0)
    centimeter_source=OUT/'M07_OriginalRigAndMotion_V07.blend'
    rig['motion_revision']='OriginalV07 fresh clean-donor adaptation to original source reference'
    bpy.ops.wm.save_as_mainfile(filepath=str(centimeter_source))
    manifest.update({'schema':6,'revision':'OriginalV07','source':str(centimeter_source),
        'master_reference':str(OUT/'M07_OriginalReference_Meter_V07.blend'),
        'reference_units':'Native centimeter coordinates; scene scale_length 0.01; armature object scale 1',
        'reference_object_matrix_world':[list(row) for row in rig.matrix_world],
        'reference_bones':{b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones},
        'ue_skeleton':'/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV07',
        'fresh_reference_from_original_glb':True,'donor_body_geometry_used':False,
        'source_saved':True,'animation_fbx_exported':True,'tested':False,'rendered':False,
        'user_visual_acceptance':False,
        'original_guide_manifest':str(OUT/'original_rig_guides.json')})
    manifest['import']['ue_skeleton']=manifest['ue_skeleton']
    manifest.pop('repair_cause',None)
    manifest['method']='Fresh original Meshy body joint reference; accepted canine hindleg control curves adapted to biped M07 and explicit hock chains; human metacarpal and finger actions; clean-source remaining choreography; no donor surface geometry; reference frame0 excluded from all clips.'
    manifest['limitations']=['All animations are newly fitted candidates and remain untested by request.',
        'Hindleg controls are reauthored for this biped anatomy; four-legged gallop phase is not copied.',
        'Original hands have a short fork beside each pinky; these source surfaces remain grouped to their pinky chain.',
        'Six gill chains use shoulder/back guide anchors; root may align hidden proxy control to actual original membrane attachments.']
    write_json(OUT/'motion_manifest.json',manifest)
    # A separate clean rest rig is the exact interface for mesh weighting.
    rig.animation_data_clear()
    for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
    scene.frame_set(0)
    reference=OUT/'M07_OriginalReference_Centimeter_V07.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(reference))
    record=json.loads((OUT/'original_rig_guides.json').read_text(encoding='utf-8'))
    record.update({'centimeter_reference_source':str(reference),'motion_source':str(centimeter_source),
        'bone_heads_cm':{b.name:list(b.head_local) for b in rig.data.bones},
        'bone_tails_cm':{b.name:list(b.tail_local) for b in rig.data.bones},
        'bone_reference_matrices_cm':{b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones},
        'motion_manifest':str(OUT/'motion_manifest.json')})
    write_json(OUT/'original_rig_guides.json',record)
    print('M07_ORIGINAL_V07_RIG_AND_MOTION_SAVED '+str(reference),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=('reference','motion','all'),default='all')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.stage in ('reference','all'):
        sys.path.insert(0, str(TOOLS))
        from assemble_reference_v07 import make_reference as assemble_reference
        assemble_reference()
    if args.stage in ('motion','all'):author_motion()
