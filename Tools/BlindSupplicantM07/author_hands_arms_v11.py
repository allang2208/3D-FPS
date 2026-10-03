"""Repair original M07 hand surfaces and all arm poses in one reference frame.

Original Meshy geometry and UV remain the source. V09 membranes and V10 gait
are retained. The only reference-axis correction is upperarm Y along its real
shoulder/elbow segment. All twelve clips, display and cloth source are exported
with that same centimeter reference. No engine, renderer or game is launched.
"""
import copy
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'RecoveryHandsV11'
RIG_OUT = OUT/'rig_motion'
SOURCE = ROOT/'LocomotionV10/M07_Original_Locomotion_V10.blend'
sys.path.insert(0, str(Path(__file__).parent))
import author_original_surfaces_v08 as surfaces
import author_motion_v04 as motion


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def rows(matrix):
    return [[float(v) for v in row] for row in matrix]


def angle(q):
    return math.degrees(2*math.acos(min(1., abs(q.normalized().w))))


def mesh_arrays(obj):
    points = np.empty((len(obj.data.vertices), 3), np.float32)
    obj.data.vertices.foreach_get('co', points.ravel())
    faces = np.asarray([list(p.vertices) for p in obj.data.polygons], np.int32)
    return points, faces


def sparse_field(obj, names):
    lookup = {n:i for i,n in enumerate(names)}
    field = np.zeros((len(obj.data.vertices), len(names)), np.float32)
    groups = {g.index:lookup[g.name] for g in obj.vertex_groups if g.name in lookup}
    for vertex in obj.data.vertices:
        for group in vertex.groups:
            if group.group in groups:
                field[vertex.index, groups[group.group]] = group.weight
    return field


def strongest(field):
    ids = np.argpartition(field, -8, axis=1)[:, -8:]
    values = np.take_along_axis(field, ids, axis=1)
    order = np.argsort(-values, axis=1)
    ids, values = np.take_along_axis(ids, order, axis=1), np.take_along_axis(values, order, axis=1)
    values /= np.maximum(values.sum(axis=1, keepdims=True), 1.e-10)
    return ids, values


def normalize_upperarms(rig):
    before = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    bpy.context.view_layer.objects.active = rig
    rig.hide_set(False)
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    details = {}
    for side in ('l', 'r'):
        bone = rig.data.edit_bones['upperarm_'+side]
        elbow = rig.data.edit_bones['lowerarm_'+side].head.copy()
        a = bone.head.copy()
        direction = (elbow-a).normalized()
        z = before[bone.name].to_3x3() @ Vector((0,0,1))
        z -= direction*z.dot(direction)
        z.normalize()
        x = direction.cross(z).normalized()
        frame = Matrix((x, direction, z)).transposed().to_4x4()
        frame.translation = a
        old_axis = before[bone.name].to_3x3() @ Vector((0,1,0))
        details[side] = {'previous_axis_error_deg':math.degrees(old_axis.angle(direction)),
                         'head_cm':list(a), 'elbow_cm':list(elbow)}
        bone.matrix = frame
        bone.length = (elbow-a).length
        bone.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    return before, {b.name:b.matrix_local.copy() for b in rig.data.bones}, details


def cache_clips(rig):
    old = json.loads((ROOT/'RecoveryOriginalV08/rig_motion/motion_manifest.json').read_text(encoding='utf-8'))
    gait = json.loads((ROOT/'LocomotionV10/locomotion_manifest_v10.json').read_text(encoding='utf-8'))
    entries, cached = {}, {}
    for role, value in old['clips'].items():
        entry = copy.deepcopy(gait['clips'].get(role, value))
        action = bpy.data.actions[entry['action']]
        motion.activate(rig, action)
        frames = []
        for frame in range(1, entry['frames']+1):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            frames.append({p.name:p.matrix.copy() for p in rig.pose.bones})
        cached[role], entries[role] = frames, entry
    return entries, cached


def bounded_wrist(desired, neutral, axis, previous, max_swing=22., max_twist=15.):
    delta = neutral.inverted() @ desired
    if delta.w < 0: delta.negate()
    v = Vector((delta.x, delta.y, delta.z))
    projection = axis*v.dot(axis)
    twist = Quaternion((delta.w, *projection))
    if twist.magnitude < 1.e-8: twist = Quaternion()
    twist.normalize()
    if twist.w < 0: twist.negate()
    swing = delta @ twist.inverted()
    bounded=[]
    for q, limit in ((swing, max_swing), (twist, max_twist)):
        a, theta = q.to_axis_angle()
        if theta > math.radians(limit):
            q = Quaternion(a, math.radians(limit))
        bounded.append(q)
    result = bounded[0] @ bounded[1]
    if previous is not None:
        difference = angle(previous.inverted() @ result)
        if difference > 8.:
            result = previous.slerp(result, 8./difference)
    return result


def repair_arm_frame(rig, target, old_pose, old_rest, rest, side, state):
    """Reach-preserving two-bone IK with a transported, continuous elbow plane."""
    a = target['upperarm_'+side].translation.copy()
    desired_elbow = old_pose['lowerarm_'+side].translation
    goal = old_pose['hand_'+side].translation
    upper0 = rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation
    lower0 = rest['hand_'+side].translation-rest['lowerarm_'+side].translation
    l1, l2 = upper0.length, lower0.length
    vector = goal-a
    torso_q=target['spine_03'].to_quaternion() @ rest['spine_03'].to_quaternion().inverted()
    local_vector=torso_q.inverted() @ vector
    if 'goal_local' in state:
        old_local=state['goal_local']
        turn=old_local.normalized().rotation_difference(local_vector.normalized())
        turning_angle=angle(turn)
        if turning_angle>14.:
            axis,_=turn.to_axis_angle()
            unit=Quaternion(axis,math.radians(14.)) @ old_local.normalized()
        else: unit=local_vector.normalized()
        reach=max(old_local.length-10.,min(local_vector.length,old_local.length+10.))
        local_vector=unit*reach
    state['goal_local']=local_vector.copy()
    vector=torso_q @ local_vector
    direction = vector.normalized()
    distance = min(vector.length, math.sqrt(l1*l1+l2*l2+2*l1*l2*math.cos(math.radians(3.))))
    distance = max(distance, math.sqrt(l1*l1+l2*l2+2*l1*l2*math.cos(math.radians(145.))))
    bend = desired_elbow-a
    bend -= direction*bend.dot(direction)
    if 'bend' in state:
        body_transport=torso_q @ state['torso'].inverted()
        old_direction=body_transport @ state['direction']
        transport = old_direction.rotation_difference(direction)
        previous = transport @ body_transport @ state['bend']
        previous -= direction*previous.dot(direction)
        previous.normalize()
        if bend.length < .01:
            bend = previous
        else:
            bend.normalize()
            if bend.dot(previous) < 0:
                bend.negate()
            change = previous.angle(bend)
            if change > math.radians(12.):
                bend = Quaternion(direction, math.copysign(math.radians(12.), direction.dot(previous.cross(bend)))) @ previous
    elif bend.length < .01:
        bend = Vector((0,-1,0))
        bend -= direction*bend.dot(direction)
    bend.normalize()
    state['direction'], state['bend'] = direction.copy(), bend.copy()
    state['torso']=torso_q.copy()
    along = (l1*l1-l2*l2+distance*distance)/(2*distance)
    elbow = a+direction*along+bend*math.sqrt(max(0., l1*l1-along*along))
    end = a+direction*distance
    upper, lower = (elbow-a).normalized(), (end-elbow).normalized()
    hinge = upper.cross(lower).normalized()
    reference_hinge = upper0.normalized().cross(lower0.normalized())
    if reference_hinge.length < .02:
        reference_hinge = Vector((0,-1 if side=='l' else 1,0))
    reference_hinge.normalize()
    for name, position, unit, original in (
        ('upperarm_'+side, a, upper, upper0),
        ('lowerarm_'+side, elbow, lower, lower0)):
        rotation = motion.anatomical_frame(unit, hinge) @ motion.anatomical_frame(original, reference_hinge).transposed()
        q = rotation.to_quaternion() @ rest[name].to_quaternion()
        target[name] = Matrix.LocRotScale(position, q, Vector((1,1,1)))
    neutral = target['lowerarm_'+side].to_quaternion() @ rest['lowerarm_'+side].to_quaternion().inverted() @ rest['hand_'+side].to_quaternion()
    old_neutral = old_pose['lowerarm_'+side].to_quaternion() @ old_rest['lowerarm_'+side].to_quaternion().inverted() @ old_rest['hand_'+side].to_quaternion()
    # Keep small source wrist expression while removing old imposed >110deg roll.
    old_local = old_neutral.inverted() @ old_pose['hand_'+side].to_quaternion()
    wanted = neutral @ old_local
    axis = rest['hand_'+side].to_quaternion().inverted() @ lower0.normalized()
    local = bounded_wrist(wanted, neutral, axis, state.get('wrist'))
    state['wrist'] = local.copy()
    hand_q = neutral @ local
    target['hand_'+side] = Matrix.LocRotScale(end, hand_q, Vector((1,1,1)))
    # Fingers retain their existing correct CMC/MCP/IP and MCP/PIP/DIP bases.
    hand_delta = target['hand_'+side] @ old_pose['hand_'+side].inverted()
    for name in target:
        if name.endswith('_'+side) and name.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')):
            target[name] = hand_delta @ old_pose[name]
    return {'wrist_relative_deg':angle(local), 'endpoint_shift_cm':(end-goal).length,
            'elbow_cm':list(elbow), 'elbow_bend_plane':list(bend)}


def bake_clips(rig, entries, cached, old_rest, rest):
    ordered = sorted(rig.pose.bones, key=lambda p:len(p.bone.parent_recursive))
    inverse = {n:m.inverted() for n,m in old_rest.items()}
    actions, measurements = {}, {}
    for role, entry in entries.items():
        action = bpy.data.actions.new('A_M07_'+role+'_OriginalV11')
        action.use_fake_user = True
        motion.activate(rig, action)
        state = {'l':{}, 'r':{}}
        metrics = []
        previous = {}
        for frame, old_pose in enumerate(cached[role], 1):
            bpy.context.scene.frame_set(frame)
            target = {n:old_pose[n] @ inverse[n] @ rest[n] for n in rest}
            for side in ('l','r'):
                metrics.append({'frame':frame, 'side':side, **repair_arm_frame(rig, target, old_pose, old_rest, rest, side, state[side])})
            for p in ordered:
                n, parent = p.name, p.parent.name if p.parent else None
                if parent:
                    p.matrix_basis = p.bone.convert_local_to_pose(target[n], rest[n],
                        parent_matrix=target[parent], parent_matrix_local=rest[parent], invert=True)
                else:
                    p.matrix_basis = p.bone.convert_local_to_pose(target[n], rest[n], invert=True)
                p.rotation_mode = 'QUATERNION'
                q = p.rotation_quaternion.copy()
                if n in previous and q.dot(previous[n]) < 0: q.negate()
                p.rotation_quaternion = q
                previous[n] = q.copy()
                p.scale = Vector((1,1,1))
                if n != 'pelvis': p.location = Vector()
                for channel in ('location','rotation_quaternion','scale'):
                    p.keyframe_insert(data_path=channel, frame=frame)
            bpy.context.view_layer.update()
        for curve in motion_curves(action):
            for key in curve.keyframe_points: key.interpolation = 'LINEAR'
        actions[role] = action
        measurements[role] = {'max_wrist_relative_deg':max(m['wrist_relative_deg'] for m in metrics),
                              'max_endpoint_shift_cm':max(m['endpoint_shift_cm'] for m in metrics),
                              'frames':metrics}
        entry.update({'action':action.name, 'file':str(RIG_OUT/f'A_M07_{role}.fbx'),
                      'asset':'/Game/Monsters/BlindSupplicantM07/AnimationsOriginalV11/A_M07_'+role})
        print('M07_V11_ARM_CLIP_AUTHORED '+role, flush=True)
    return actions, measurements


def motion_curves(action):
    if not action.is_action_layered: return list(action.fcurves)
    return [c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves]


def fork_nodes(obj, sign, cut_cm):
    p, f = mesh_arrays(obj)
    quantized = np.rint(p/.0003).astype(np.int64)
    _, first, inverse = np.unique(quantized, axis=0, return_index=True, return_inverse=True)
    point = p[first]
    eligible = point[:,0]*sign > cut_cm
    edges = inverse[np.concatenate([f[:,[0,1]], f[:,[1,2]], f[:,[2,0]]])]
    edges = edges[eligible[edges].all(axis=1)]
    parent=np.arange(len(point))
    def root(index):
        while parent[index]!=index:
            parent[index]=parent[parent[index]]
            index=parent[index]
        return index
    for a,b in edges:
        ra,rb=root(a),root(b)
        if ra!=rb: parent[rb]=ra
    target = np.asarray([sign*.8565*206.08756, .104*206.08756, (.398+.7519199848)*206.08756])
    candidate = np.flatnonzero(eligible & (point[:,1]>18) & (point[:,1]<25) & (point[:,2]<239.0))
    if not len(candidate): return np.zeros(len(p), bool), None
    seed = candidate[np.argmin(np.linalg.norm(point[candidate]-target, axis=1))]
    seed_root=root(seed)
    comp=np.zeros(len(point),bool)
    for i in np.flatnonzero(eligible): comp[i]=root(i)==seed_root
    cloud = point[comp]
    # A valid secondary branch is distinct from the five real fingers.
    if len(cloud)<12 or len(cloud)>4000 or np.quantile(cloud[:,2], .95)>240.0:
        return np.zeros(len(p), bool), None
    return comp[inverse], {'welded_vertices':int(comp.sum()), 'bounds_cm':[cloud.min(0).tolist(),cloud.max(0).tolist()]}


def remove_secondary_forks(obj, cuts):
    removed = np.zeros(len(obj.data.vertices), bool)
    records = []
    for side, sign in (('l',1), ('r',-1)):
        mask, record = fork_nodes(obj, sign, cuts[side])
        if record is None: raise RuntimeError('Secondary fork cannot be separated from primary fingers: '+obj.name+' '+side)
        removed |= mask
        records.append({'side':side, 'cut_cm':cuts[side], **record})
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    delete = [bm.verts[i] for i in np.flatnonzero(removed)]
    surviving = set(v for v in bm.verts if not removed[v.index] and any(removed[e.other_vert(v).index] for e in v.link_edges))
    bmesh.ops.delete(bm, geom=delete, context='VERTS')
    surviving = [v for v in surviving if v.is_valid]
    # Original UVs are stored per loop and remain separate after welding.
    # Join coincident local hand seam copies so a cut contour is a closed
    # surface loop instead of several UV island boundary chains.
    local_hand=[v for v in bm.verts if abs(v.co.x)>155.]
    bmesh.ops.remove_doubles(bm, verts=local_hand, dist=.003)
    boundary = [e for e in bm.edges if e.is_boundary and
        all(abs(abs(v.co.x)-cuts['l' if v.co.x>0 else 'r'])<2.0 and
            17<v.co.y<27 and v.co.z<244.0 for v in e.verts)]
    cap = bmesh.ops.holes_fill(bm, edges=boundary, sides=0).get('faces',[]) if boundary else []
    if not cap:
        bm.free()
        raise RuntimeError('Original secondary-fork cut contour did not close: '+obj.name)
    uv = bm.loops.layers.uv.active
    if uv:
        for face in cap:
            for loop in face.loops:
                neighbors = [l[uv].uv.copy() for l in loop.vert.link_loops if l.face not in cap]
                if neighbors: loop[uv].uv = sum(neighbors, Vector((0,0)))/len(neighbors)
    bmesh.ops.triangulate(bm, faces=cap)
    bmesh.ops.recalc_face_normals(bm, faces=list({f for v in surviving if v.is_valid for f in v.link_faces}))
    bm.to_mesh(obj.data); bm.free(); obj.data.update()
    return {'object':obj.name, 'removed_vertices':int(removed.sum()), 'closed_cap_faces':len(cap), 'forks':records}


def reproject_body_display(display, high, names):
    hp,hf = mesh_arrays(high)
    tree = BVHTree.FromPolygons(hp.tolist(), hf.tolist(), all_triangles=True)
    high_field = sparse_field(high, names)
    field = sparse_field(display, names)
    p,_ = mesh_arrays(display)
    selected = (np.abs(p[:,0])>32.) & (p[:,2]>205.)
    ids = np.flatnonzero(selected)
    nearest_source = np.asarray([a.value for a in display.data.attributes['source_vertex_id'].data],np.int32)
    high_ids = np.asarray([a.value for a in high.data.attributes['source_vertex_id'].data],np.int32)
    source_faces = np.full(len(p), -1, np.int32)
    barycentric = np.zeros((len(p),3), np.float32)
    for i in ids:
        hit,normal,face,distance = tree.find_nearest(Vector(p[i]))
        if face is None: raise RuntimeError('Repaired body cannot supply arm weights.')
        a,b,c = hp[hf[face]]
        ab,ac,q = b-a,c-a,np.asarray(hit)-a
        aa,bb,cc = float(ab@ab),float(ab@ac),float(ac@ac)
        den = aa*cc-bb*bb
        if abs(den)<1.e-12: w=np.asarray([1.,0.,0.])
        else:
            v=(cc*float(q@ab)-bb*float(q@ac))/den
            z=(aa*float(q@ac)-bb*float(q@ab))/den
            w=np.maximum([1-v-z,v,z],0.); w/=max(w.sum(),1.e-10)
        field[i] = (high_field[hf[face]]*w[:,None]).sum(axis=0)
        nearest_source[i] = high_ids[hf[face][np.argmax(w)]]
        source_faces[i], barycentric[i] = face,w
    # Coincident seam points share a skin field even though UVs stay separate.
    quantized = np.rint(p/.0003).astype(np.int64)
    _,first,inverse = np.unique(quantized,axis=0,return_index=True,return_inverse=True)
    field[selected] = field[first[inverse[selected]]]
    top,values = strongest(field)
    surfaces.assign(display,names,top,values)
    display.data.attributes['source_vertex_id'].data.foreach_set('value',nearest_source)
    for name,type_,value in [('weight_source_high_triangle','INT',source_faces),
                             ('weight_source_barycentric','FLOAT_VECTOR',barycentric)]:
        if name in display.data.attributes: display.data.attributes.remove(display.data.attributes[name])
        attribute=display.data.attributes.new(name=name,type=type_,domain='POINT')
        attribute.data.foreach_set('value' if type_=='INT' else 'vector',value.ravel())
    display['source_vertex_id_policy']='Arm correspondence rebuilt from body-only BVH; exact skin correspondence is high triangle plus barycentric coordinates'
    return {'arm_vertices_reprojected':len(ids),'method':'Repaired same-part original high triangles, barycentric field interpolation, strongest eight, coincident seam equality'}


def author():
    OUT.mkdir(parents=True,exist_ok=True); RIG_OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    entries,cached=cache_clips(rig)
    print('M07_V11_TWELVE_INPUT_ACTIONS_CACHED',flush=True)
    rig.animation_data_clear(); rig.data.pose_position='REST'
    for p in rig.pose.bones: p.matrix_basis=Matrix.Identity(4)
    bpy.context.scene.frame_set(0)
    old_rest,rest,axis_details=normalize_upperarms(rig)
    skin=np.load(OUT/'weights/original_arm_hand_skin_weights_v11.npz')
    weight_manifest=json.loads((OUT/'weights/original_arm_hand_skin_weights_v11.json').read_text(encoding='utf-8'))
    names=weight_manifest['bone_names']
    body=bpy.data.objects['M07_OriginalBody_High']
    ids=np.asarray([a.value for a in body.data.attributes['source_vertex_id'].data],np.int32)
    surfaces.assign(body,names,skin['bone_indices'][ids],skin['bone_weights'][ids])
    display=bpy.data.objects['M07_OriginalBody_Display']
    scale=206.0875603390956
    cuts={}
    for side,sign in (('l',1),('r',-1)):
        # Lowest cut where the original extra offshoot separates from pinky.
        for cut in np.arange(.775,.834,.002):
            _,record=fork_nodes(body,sign,float(cut*scale))
            if record is not None:
                cuts[side]=float((cut+.001)*scale); break
        if side not in cuts: raise RuntimeError('Original secondary pinky fork was not isolated.')
    geometry=[remove_secondary_forks(body,cuts),remove_secondary_forks(display,cuts)]
    print('M07_V11_SECONDARY_FORKS_REMOVED '+json.dumps(geometry),flush=True)
    reprojection=reproject_body_display(display,body,names)
    print('M07_V11_BODY_DISPLAY_WEIGHTS_REPROJECTED '+json.dumps(reprojection),flush=True)
    rig.data.pose_position='POSE'
    actions,measurements=bake_clips(rig,entries,cached,old_rest,rest)
    scene=bpy.context.scene
    scene.render.fps=30;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
    rig.name='Armature';rig.data.name='M07_ReferenceOriginalV11'
    rig['reference_revision']='OriginalV11 normalized shoulder-elbow axes, retained joint positions and 83-bone names/parents'
    for role,entry in entries.items():
        motion.activate(rig,actions[role]);scene.frame_start=1;scene.frame_end=entry['frames'];scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
        bpy.ops.export_scene.fbx(filepath=entry['file'],use_selection=True,object_types={'ARMATURE'},
            add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',
            bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_all_actions=False,
            bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,
            bake_anim_step=1,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',
            apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')
    rig.animation_data_clear();rig.data.pose_position='REST'
    for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
    scene.frame_set(0)
    display_objects=[display]+[bpy.data.objects[f'M07_OriginalGill_{i:02d}_Display'] for i in range(1,7)]
    proxies=[bpy.data.objects[f'M07_OriginalGill_{i:02d}_Simulation'] for i in range(1,7)]
    surfaces.export(OUT/'SK_M07_Display_OriginalV11.fbx',rig,display_objects)
    surfaces.export(OUT/'SK_M07_ClothBuildSource_OriginalV11.fbx',rig,display_objects+proxies)
    cloth=json.loads((ROOT/'RecoveryOriginalV09/cloth_ue_manifest_original_v09.json').read_text(encoding='utf-8'))
    # Capsule frames must follow the same corrected upperarm reference.
    for capsule in cloth['collision_capsules']:
        name=capsule['bone']
        if name.startswith('upperarm_'):
            child='lowerarm_'+name[-1]
            local=rest[name].inverted()@rest[child].translation
            capsule['a_cm']=[0.,0.,0.];capsule['b_cm']=[local.x,-local.y,local.z]
    cloth['reference_revision']='OriginalV11';cloth['method']+='; V11 shoulder/elbow capsule axes matched to corrected reference'
    write_json(OUT/'cloth_ue_manifest_original_v11.json',cloth)
    rig.data.pose_position='POSE';motion.activate(rig,actions['Idle']);scene.frame_start=1;scene.frame_end=entries['Idle']['frames'];scene.frame_set(0)
    for obj in bpy.data.objects:
        if obj.type=='MESH' and (obj.name.endswith('_High') or obj.name.endswith('_Simulation')):
            obj.hide_set(True);obj.hide_render=True
    destination=OUT/'M07_Original_HandArm_Master_V11.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(destination),compress=True)
    manifest={'revision':'OriginalV11','fps':30,'source':str(destination),'clips':entries,
        'ue_skeleton':'/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11',
        'reference_bones':{n:rows(m) for n,m in rest.items()},'reference_units':'centimeter coordinates, scene scale .01, identity Armature object; frame0 reference excluded from clips',
        'tested':False,'runtime_tested':False,'rendered':False}
    write_json(RIG_OUT/'motion_manifest_v11.json',manifest)
    write_json(OUT/'requested_arm_pose_repair_v11.json',{'scope':'Requested arm/hand diagnosis and repair only','axis_correction':axis_details,'clips':measurements,'runtime_tested':False,'rendered':False})
    write_json(OUT/'hand_arm_delivery_v11.json',{'revision':'OriginalV11','source_master':str(SOURCE),'saved_source':str(destination),
        'scope':'Original connected finger-web skin, shoulder/elbow/wrist field, secondary pinky-fork cleanup, corrected upperarm reference and all twelve continuous arm actions',
        'original_mesh_source':str(ROOT/'Original/Meshy_AI_Veilwing_07_1001123357_texture.glb'),
        'original_geometry_reconstructed':False,'original_uv_retained':True,'joint_positions_retained':True,
        'reference_axis_corrections':axis_details,'bone_count':len(rig.data.bones),'geometry_local_cleanup':geometry,
        'weights_manifest':str(OUT/'weights/original_arm_hand_skin_weights_v11.json'),'body_display_reprojection':reprojection,
        'gill_geometry_and_weights_retained':'OriginalV09','gait_timing_stride_retained':'LocomotionV10',
        'motion_manifest':str(RIG_OUT/'motion_manifest_v11.json'),'ue_imported':False,'tested':False,'runtime_tested':False,'rendered':False})
    print('M07_V11_ORIGINAL_HAND_ARM_SOURCE_AND_ALL_EXPORTS_SAVED',flush=True)


if __name__=='__main__': author()
