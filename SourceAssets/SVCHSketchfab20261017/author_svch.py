"""Author the SVCh viewmodel on the accepted shared Manny rig.

Read-only inputs
  Donor/vm.json.gz              accepted SVD viewmodel: arms geometry, skin weights, 101 bones
  Skeleton/rest.json            the identical Manny rest skeleton (metres)
  download/svch.glb             Sketchfab "Low-Poly SVCh 308" by TastyTony, CC BY 4.0
  Authoring/svd_root_space.json the accepted SVD's contacts in WPN_root space at idle

Outputs
  Exports/SK_SVCH_Manny.fbx     skeletal viewmodel: V9 arms + SVCh parts
  Authoring/authoring.json      seat, markers, part map, material map
  Authoring/SVCH_Viewmodel.blend

Bone map (same convention as SVD):
    receiver / barrel / handguard / stock / grip / sights   -> WPN_root
    magazine                                                -> WPN_SOCKET_Magazine
    trigger                                                 -> WPN_Trigger
    bolt carrier + charging handle                          -> WPN_ChargingHandle
    safety + magazine release (rigid)                       -> WPN_root

Both the arms and the weapon live in WPN_root space, metres, -Y muzzle, +Z up.
The weapon sits on the rig's +X side, exactly like the accepted SVD.
"""
import gzip
import json
import struct
from pathlib import Path

import bmesh
import bpy
import math
import numpy as np
from mathutils import Matrix, Vector

O = Path(__file__).parent
GLB = O / 'download' / 'svch.glb'
X = O / 'Exports'
A = O / 'Authoring'
X.mkdir(exist_ok=True)
A.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0

CT = {5120: ('i1', 1), 5121: ('u1', 1), 5122: ('i2', 2), 5123: ('u2', 2),
      5125: ('u4', 4), 5126: ('f4', 4)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def load_glb(path):
    src = open(path, 'rb').read()
    _, _, length = struct.unpack_from('<III', src, 0)
    off, chunks = 12, []
    while off < length:
        clen, ctype = struct.unpack_from('<II', src, off)
        chunks.append((ctype, off + 8, clen))
        off += 8 + clen
    j = json.loads(src[chunks[0][1]:chunks[0][1] + chunks[0][2]].decode('utf-8'))
    blob = src[chunks[1][1]:chunks[1][1] + chunks[1][2]]

    def acc(i):
        a = j['accessors'][i]
        bv = j['bufferViews'][a['bufferView']]
        dt, sz = CT[a['componentType']]
        n = NC[a['type']]
        st = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = bv.get('byteStride') or sz * n
        cnt = a['count']
        if stride == sz * n:
            return np.frombuffer(blob, dtype=np.dtype(dt), count=cnt * n, offset=st).reshape(cnt, n)
        return np.array([np.frombuffer(blob, dtype=np.dtype(dt), count=n,
                                       offset=st + i * stride) for i in range(cnt)])

    mats = [m['name'] for m in j['materials']]
    joints = j['skins'][0]['joints']
    jname = {k: j['nodes'][joints[k]].get('name') for k in range(len(joints))}
    # The source splits the rifle into one mesh per material (ten of them).
    allpos, alljt, allwt, alltri, allmat = [], [], [], [], []
    base = 0
    for mesh in j['meshes']:
        prim = mesh['primitives'][0]
        pos = acc(prim['attributes']['POSITION']).astype('float64')
        jt = acc(prim['attributes']['JOINTS_0']).astype('int64')
        wt = acc(prim['attributes']['WEIGHTS_0']).astype('float64')
        idx = acc(prim['indices']).ravel().astype('int64').reshape(-1, 3)
        allpos.append(pos)
        alljt.append(jt)
        allwt.append(wt)
        alltri.append(idx + base)
        allmat.extend([mats[prim['material']]] * len(idx))
        base += len(pos)
    pos = np.vstack(allpos)
    jt = np.vstack(alljt)
    wt = np.vstack(allwt)
    idx = np.vstack(alltri)
    return dict(pos=pos, tri=idx, dom=jt[range(len(jt)), wt.argmax(axis=1)],
                joint_names=jname, material=allmat,
                materials={m['name']: m for m in j['materials']})


# Measured hold registration (fit_hold_frame.py). Module level because both the
# vertex conversion and the landmark conversion must use the same transform.
_HOLD = json.loads((Path(__file__).parent / 'Authoring' / 'hold_frame.json')
                   .read_text(encoding='utf-8'))
HOLD_R = np.array(_HOLD['R'], dtype='float64')
HOLD_T = np.array(_HOLD['t_cm'], dtype='float64')


def to_author_rows(pos, R=None, T=None):
    """glTF (Y up, +X muzzle, +Z right) -> author bind space, in METRES.

    The placement is the measured SVD hold registration (Authoring/hold_frame.json):
    a proper rotation mapping this gun's bore frame onto the accepted SVD's, plus
    the translation that puts both pistol grips at the same point. That is what
    makes the hands close on the grip instead of hovering beside it.

    Units: the shared rest skeleton is in metres and UE's FBX import multiplies by
    100 exactly once, so the author file must be metres too. The glTF stores
    centimetres, hence the single /100.
    """
    R = R if R is not None else HOLD_R
    T = T if T is not None else HOLD_T
    return (pos @ R.T + T) / 100.0


# --------------------------------------------------------------------------
# Surface finishing (skills/ue5-weapon-workflow: geometry before material)
#
# The source is a flat-shaded low-poly mesh with no UVs: every facet reads as a
# separate plate and the WS1 grain has nothing to tile on. Each part gets
#   * smooth shading with sharp edges above SHARP_ANGLE, so barrels shade as
#     cylinders while rails, ports and machined steps stay crisp;
#   * a small chamfer on those hard edges, which gives a low-poly model a
#     highlight to catch instead of a razor-thin silhouette;
#   * a real UV layout so the shared surface master's grain and scratches work.
# --------------------------------------------------------------------------
SHARP_ANGLE = math.radians(35.0)
BEVEL_ANGLE = math.radians(40.0)
BEVEL_WIDTH_M = 0.0006      # 0.6 mm chamfer
UV_CUBE_M = 0.25            # one UV tile per 25 cm, matching GrainTileCm scale


def finish_surface(ob, bevel=0.0, uv_angle=66.0):
    """Smooth-by-angle, optional chamfer, and a UV layout."""
    me = ob.data
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))

    bm = bmesh.new()
    bm.from_mesh(me)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            e.smooth = e.calc_face_angle(math.pi) < SHARP_ANGLE
        else:
            e.smooth = False
    bm.to_mesh(me)
    bm.free()
    me.update()

    bpy.context.view_layer.objects.active = ob
    for other in list(bpy.context.selected_objects):
        other.select_set(False)
    ob.select_set(True)

    if bevel > 0.0:
        # bmesh rather than a Bevel modifier: modifier_apply silently cancels in
        # background mode, which is how the first attempt shipped with no chamfer.
        bm = bmesh.new()
        bm.from_mesh(me)
        hard = [e for e in bm.edges
                if len(e.link_faces) == 2 and e.calc_face_angle(math.pi) > BEVEL_ANGLE]
        if hard:
            try:
                bmesh.ops.bevel(bm, geom=hard, offset=bevel, offset_type='OFFSET',
                                segments=1, profile=0.5, affect=
'EDGES',
                                clamp_overlap=True, loop_slide=True)
            except TypeError:
                bmesh.ops.bevel(bm, geom=hard, offset=bevel, segments=1)
        bm.to_mesh(me)
        bm.free()
        me.update()

    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # World-scale box projection, not smart project: WS1 tiles its grain and
    # mottle in physical centimetres (GrainTileCm), so a normalised 0..1 layout
    # gives every island an arbitrary texel density and the surface reads as
    # camouflage blotches instead of steel.
    bpy.ops.uv.cube_project(cube_size=UV_CUBE_M, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')


ARTICULATED = {
    'mag_02':        ('Magazine', 'WPN_SOCKET_Magazine'),
    'bolt_01':       ('BoltCarrier', 'WPN_ChargingHandle'),
    'magrelease_05': ('MagRelease', 'WPN_root'),
    'selector_06':   ('Selector', 'WPN_root'),
}
CARTRIDGE_JOINTS = {'bullet_03', 'bullets_04'}
# The audit's frame is (X along the barrel, Y lateral, Z up with Z=0 at the bore).
# The audit reports centimetres in the FBX node frame. The mesh vertices are the
# raw glTF POSITION values, which are the same picture translated along the bore
# and up: solve_frame_offset.py measures dx = 18.7444, dz = 1.5268, dy = 0 and
# cross-checks them against the sight top and the butt. Fill them in before
# mapping to author space, or every landmark lands ~19 cm off along the barrel.
AUDIT_TO_GLTF = {'dx': 18.7444, 'dy': 0.0, 'dz': 1.5268}


def gltf_of_audit(a):
    """Audit centimetres -> glTF accessor centimetres."""
    return np.array([float(a[0]) - AUDIT_TO_GLTF['dx'],
                     float(a[2]) - AUDIT_TO_GLTF['dz'],
                     float(a[1]) - AUDIT_TO_GLTF['dy']])


def author_of_gltf(p):
    """glTF centimetres -> author space, metres."""
    return (HOLD_R @ np.asarray(p, dtype='float64') + HOLD_T) / 100.0


def audit(a):
    """Audit centimetres -> author metres, through the hold registration."""
    return Vector(author_of_gltf(gltf_of_audit(a)))


# --------------------------------------------------------------------------
# Export frame
#
# Measured, not assumed (measure_roundtrip.py + Receipts/orientation.json): the
# FBX round trip maps Blender (x, y, z) to UE (100x, -100y, 100z). Author space
# is UE component space in metres, so a point must be written to Blender as
# (x, -y, z). Writing author coordinates straight in mirrors the weapon front to
# back, which is exactly the "reversed direction" this fixes.
#
# Negating one axis flips handedness, so triangle winding is reversed to keep
# the outward normal on the outside.
# --------------------------------------------------------------------------
def export_pos(p):
    return (float(p[0]), -float(p[1]), float(p[2]))


def export_tri(tri, remap=None):
    a, b, c = (int(tri[0]), int(tri[1]), int(tri[2]))
    if remap is not None:
        a, b, c = remap[a], remap[b], remap[c]
    return (a, c, b)


def main():
    contact = json.loads((A / 'svd_bind_space.json').read_text(encoding='utf-8'))
    rest = json.loads((O / 'Skeleton' / 'rest.json').read_text(encoding='utf-8'))
    lm = json.loads((O / 'audit' / 'work' / 'final_landmarks.json').read_text(encoding='utf-8'))
    g = load_glb(GLB)
    P = to_author_rows(g['pos'])
    names = g['joint_names']
    dom = g['dom']

    # ---------- face -> part ----------
    face_part = {}
    for fi, tri in enumerate(g['tri']):
        counts = {}
        for vi in tri:
            b = names[int(dom[vi])]
            counts[b] = counts.get(b, 0) + 1
        bone = max(counts, key=counts.get)
        if bone in ARTICULATED:
            face_part[fi] = ARTICULATED[bone][0]
        elif bone in CARTRIDGE_JOINTS:
            face_part[fi] = 'Cartridge'
        else:
            face_part[fi] = 'Body'

    # ---------- hold registration ----------
    # The accepted SVD's own hold is the reference: fit_hold_frame.py measures a
    # bore frame on the SVD and on this gun (muzzle-cap fit + sight line) and
    # solves the rigid transform that puts the SVCh's pistol grip exactly where
    # the SVD's is held. A translation alone left the barrel pitch and roll free,
    # which is why the hands did not close on the grip.


    sights = json.loads((O / 'audit' / 'measurements.json')
                        .read_text(encoding='utf-8'))['landmarks']
    # Same landmark source the hold frame was fitted from, so the check compares like with like.
    svch_grip = Vector(audit(sights['pistol_grip']['centre']))
    svch_trigger = Vector(audit(sights['trigger']['blade_centre']))
    svch_muzzle = Vector(audit(sights['muzzle_tip']['point']))
    svch_butt = Vector(audit(sights['stock_butt_plate']['centre']))
    # The SVD reference is stored in the dump's centimetres; author space is metres.
    svd_grip = Vector(contact['grip']['centre']) / 100.0
    svd_trigger = Vector(contact['parts']['Trigger']['centre']) / 100.0
    seat = Vector((0.0, 0.0, 0.0))

    report = {
        'frame': 'WPN_root bind space, metres, -Y muzzle, +Z up, weapon on +X',
        'conversion': 'glTF centimetres -> SVD hold registration (rigid) -> metres; measured by fit_hold_frame.py',
        'source': 'https://sketchfab.com/3d-models/low-poly-svch-308-739390f40fef4b22ac9a71b72f7a95b8',
        'source_author': 'TastyTony', 'license': 'CC BY 4.0',
        'hold_translation_m': [round(float(v), 6) for v in (HOLD_T / 100.0)],
        'hold_det': round(float(np.linalg.det(HOLD_R)), 8),
        'landmarks_source_m': {'grip': [round(v, 5) for v in svch_grip],
                               'trigger': [round(v, 5) for v in svch_trigger],
                               'muzzle': [round(v, 5) for v in svch_muzzle],
                               'butt': [round(v, 5) for v in svch_butt]},
        'landmarks_reference_m': {'grip': [round(v, 5) for v in svd_grip],
                                  'trigger': [round(v, 5) for v in svd_trigger]},
        'residual_trigger_cm': round((svd_trigger - svch_trigger).length * 100.0, 3),
        'parts': {}, 'arms': {},
    }

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene

    # ---------- rig ----------
    arm_data = bpy.data.armatures.new('SK_M4_Infima')
    rig = bpy.data.objects.new('SK_M4_Infima', arm_data)
    sc.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    ebs = {}
    for b in rest['bones']:
        eb = arm_data.edit_bones.new(b['name'])
        eb.head = Vector(b['head'])
        eb.tail = Vector(b['tail'])
        # The bone's own roll is part of the bind: reconstruct it from the full
        # rest matrix instead of forcing roll = 0, which would twist every bone
        # and shear the skin.
        m = Matrix([row[:] for row in b['matrix']])
        eb.matrix = m
        ebs[b['name']] = eb
    for b in rest['bones']:
        if b['parent'] and b['parent'] in ebs:
            ebs[b['name']].parent = ebs[b['parent']]
            ebs[b['name']].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    report['rig'] = {'bones': len(rig.data.bones)}

    # ---------- arms, taken verbatim from the accepted viewmodel ----------
    vm = json.load(gzip.open(O / 'Donor' / 'vm.json.gz', 'rt', encoding='utf-8'))
    slots = vm['slots']
    bn = vm['bone_names']
    # The dump stores flat index/material arrays parallel to the triangle list.
    tris = np.array(vm['triangles'], dtype='int64').reshape(-1, 3)
    is_manny = [slots[m] in ('MI_Manny_01', 'MI_Manny_02') for m in vm['material']]
    arms_faces = [i for i in range(len(tris)) if is_manny[i]]
    used = sorted({vi for i in arms_faces for vi in tris[i]})
    remap = {old: new for new, old in enumerate(used)}
    # The dump is component-space centimetres. Author space (what the markers and
    # the seat are expressed in) is metres; export_frame() below converts to the
    # Blender coordinates that land on that same space in UE.
    arms_pos = np.array(vm['positions'], dtype='float64').reshape(-1, 3) / 100.0
    me = bpy.data.meshes.new('SVCH_BareArmsV9')
    me.from_pydata([export_pos(arms_pos[v]) for v in used], [],
                   [export_tri(tris[i], remap) for i in arms_faces])
    me.update()
    mat_slot = {'MI_Manny_01': 0, 'MI_Manny_02': 1}
    for nm in ('MI_Manny_01', 'MI_Manny_02'):
        m = bpy.data.materials.new(nm)
        m.use_nodes = True
        me.materials.append(m)
    me.polygons.foreach_set('material_index',
                            [mat_slot[slots[vm['material'][arms_faces[i]]]]
                             for i in range(len(arms_faces))])
    me.update()
    arms = bpy.data.objects.new('SVCH_BareArmsV9', me)
    sc.collection.objects.link(arms)
    groups = {}
    for nm in bn:
        if rig.data.bones.get(nm) and nm not in groups:
            groups[nm] = arms.vertex_groups.new(name=nm)
    rows = vm['weights']
    for new_i, old_i in enumerate(used):
        for bidx, w in rows[old_i]:
            nm = bn[bidx]
            if nm in groups and w > 0.0:
                groups[nm].add([new_i], w, 'REPLACE')
    finish_surface(arms, bevel=0.0, uv_angle=75.0)
    arms.parent = rig
    arms.modifiers.new('Armature', 'ARMATURE').object = rig
    report['arms'] = {'source': vm['source'], 'faces': len(arms_faces),
                      'verts': len(used), 'skin_groups': len(groups)}

    # ---------- SVCh parts ----------
    part_faces = {}
    cartridge_mats = {'Material.001', 'Material.002', 'Material.003'}
    for fi, p in face_part.items():
        if g['material'][fi] in cartridge_mats:
            p = 'Cartridge'
        part_faces.setdefault(p, []).append(fi)
    part_bones = {'Body': 'WPN_root', 'Magazine': 'WPN_SOCKET_Magazine',
                  'BoltCarrier': 'WPN_ChargingHandle', 'MagRelease': 'WPN_root',
                  'Selector': 'WPN_root', 'Cartridge': 'WPN_root'}
    part_mats = {'Body': 'Material.007', 'Magazine': 'Material.007',
                 'BoltCarrier': 'Material.006', 'MagRelease': 'Material.005',
                 'Selector': 'Material.005', 'Cartridge': 'Material.001'}
    objs = []
    for part, faces in sorted(part_faces.items()):
        vids = sorted({vi for i in faces for vi in g['tri'][i]})
        vmap = {old: new for new, old in enumerate(vids)}
        pm = bpy.data.meshes.new('SM_SVCH_' + part)
        # Component-wise on purpose: numpy row plus mathutils.Vector does not
        # reliably add element-wise here, and a silently dropped Y offset shifts
        # the whole weapon along the barrel.
        pm.from_pydata([export_pos(P[v]) for v in vids], [],
                       [export_tri(g['tri'][i], vmap) for i in faces])
        pm.update()
        # One semantic material slot per part: the runtime import binds a WS1
        # instance per slot, and unnamed slots collapse into a single "Material".
        m = bpy.data.materials.new('SM_SVCH_' + part)
        m.use_nodes = True
        pm.materials.append(m)
        ob = bpy.data.objects.new('SM_SVCH_' + part, pm)
        sc.collection.objects.link(ob)
        ob.parent = rig
        ob.vertex_groups.new(name=part_bones[part]).add(
            list(range(len(vids))), 1.0, 'REPLACE')
        finish_surface(ob, bevel=BEVEL_WIDTH_M)
        ob.modifiers.new('SVCh rigid', 'ARMATURE').object = rig
        objs.append(ob)
        report['parts'][part] = {'faces': len(faces), 'verts': len(vids),
                                 'bone': part_bones[part],
                                 'material': part_mats.get(part)}

    # ---------- markers: the SVCh's own measured points ----------
    # Author space is metres, so every landmark is converted once here.
    # Sight points come from the audit's raycast landmarks: the rear aperture
    # centre and the front post tip, both on the bore centreline, so the sight
    # axis agrees with the barrel to within the measured 0.1 mm.
    measurements = json.loads((O / 'audit' / 'measurements.json').read_text(encoding='utf-8'))
    sights = measurements['landmarks']
    rear = sights['rear_sight']['aperture_centre']
    front = sights['front_sight']['post_tip']
    muzzle = sights['muzzle_tip']['point']

    # Self-check in author space: the weapon must span muzzle..butt exactly.
    author = [(float(P[v][0]), float(P[v][1]), float(P[v][2])) for v in range(len(P))]
    ay = [a[1] for a in author]
    report['author_bounds_m'] = {
        'y_min': round(min(ay), 4), 'y_max': round(max(ay), 4),
        'x_min': round(min(a[0] for a in author), 4), 'x_max': round(max(a[0] for a in author), 4),
        'z_min': round(min(a[2] for a in author), 4), 'z_max': round(max(a[2] for a in author), 4)}
    # Self-check: the registration must put the pistol grip exactly on the SVD's,
    # and the model must keep its measured overall length.
    grip_err = (Vector(svd_grip) - Vector(audit(lm['grip']['centre']))).length
    length_m = max(ay) - min(ay)
    if grip_err > 0.001:
        raise RuntimeError('hold registration missed the grip by %.4f m' % grip_err)
    if abs(length_m - 1.07307) > 0.02:
        raise RuntimeError('author length %.4f m does not match the measured 1.07307 m' % length_m)
    report['orientation_check'] = {'grip_error_m': round(grip_err, 6),
                                   'length_m': round(length_m, 4),
                                   'status': 'ok'}
    # Landmark -> author space, with the audit frame offset applied once.
    def bind(p):
        return audit(p) + seat

    markers = {
        'WPN_SOCKET_Muzzle': bind(muzzle),
        'WPN_SOCKET_Eject': bind(sights['ejection_port']['centre']),
        'WPN_RearSight': bind(rear),
        'WPN_FrontSight': bind(front),
        'WPN_ChargingHandle': bind(sights['charging_handle']['centre']),
        'WPN_SOCKET_Magazine': bind(sights['magazine_interface']['centre']),
        'WPN_Trigger': bind(sights['trigger']['blade_centre']),
    }
    report['markers_m'] = {k: [round(v, 6) for v in val] for k, val in markers.items()}
    report['sight_line_above_bore_m'] = round(float(sights['sight_line']['height_above_bore_mm']) / 1000.0, 5)

    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs + [arms, rig]:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.wm.save_as_mainfile(filepath=str(A / 'SVCH_Viewmodel.blend'))
    bpy.ops.export_scene.fbx(filepath=str(X / 'SK_SVCH_Manny.fbx'), use_selection=True,
                             object_types={'MESH', 'ARMATURE'}, axis_forward='-Y',
                             axis_up='Z', add_leaf_bones=False, bake_anim=False,
                             mesh_smooth_type='OFF', use_tspace=False)
    (A / 'authoring.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
    print('SVCH_AUTHORED', json.dumps(report['parts']), flush=True)
    print('SVCH_SEAT', json.dumps(report['hold_translation_m']),
          'residual_cm', report['residual_trigger_cm'], flush=True)


main()
