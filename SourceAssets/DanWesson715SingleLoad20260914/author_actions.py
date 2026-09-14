"""Bake 21 contact-authored single-round reloads on the upgraded 715 rig.

Existing loaded chambers remain in place. Each loop removes one spent case,
fetches one cartridge and seats it. GitHub donor curves shape the hand arcs;
model-space pivots and the source skeleton remain unchanged. No test/render.
"""
import bpy, math, json
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion, Euler

OUT = Path(__file__).parent
SOURCE = OUT.parent / 'DanWesson715Upgrade20260914'
# Reuse the previous authoring library and its actual source action samples.
# Its export loop starts after events; do not execute or overwrite that work.
library = (SOURCE / 'author_actions.py').read_text(encoding='utf-8').split("events={'open':", 1)[0]
library = library.replace('DanWesson715_Hero_Editable.blend', 'DanWesson715_Upgrade_Editable.blend')
previous_file = __file__
__file__ = str(SOURCE / 'author_actions.py')
exec(compile(library, __file__, 'exec'), globals())
__file__ = previous_file
O = OUT
(O / 'Animations').mkdir(exist_ok=True)

OPEN = .48
BEGIN = .55
STEP = 1.15
REMOVE = .23
VISIBLE = .56
SEAT = .91
CLOSE_TAIL = .70
thumb_tip = idle['thumb_03_l'] @ Vector((0, rig.data.bones['thumb_03_l'].length, 0))
index_tip = idle['index_03_l'] @ Vector((0, rig.data.bones['index_03_l'].length, 0))
pinch_offset = idle['hand_l'].inverted() @ ((thumb_tip+index_tip)*.5)

def pinch_goal(point):
    H = hand_goal(point, (1, 0, 0), (0, -1, .15))
    H.translation = Vector(point) - H.to_quaternion() @ pinch_offset
    return H

def solve_finger(p, family, target):
    chain = [f'{family}_{i:02}_l' for i in range(1, 4)]
    matrices = [p[n].copy() for n in chain]
    points = [m.translation.copy() for m in matrices]
    points.append(matrices[-1] @ Vector((0, rig.data.bones[chain[-1]].length, 0)))
    lengths = [(b-a).length for a, b in zip(points, points[1:])]
    anchor = points[0].copy()
    reach = sum(lengths) * .985
    delta = target-anchor
    if delta.length > reach:
        target = anchor + delta.normalized()*reach
    for _ in range(12):
        points[-1] = target.copy()
        for i in range(2, -1, -1):
            points[i] = points[i+1] + (points[i]-points[i+1]).normalized()*lengths[i]
        points[0] = anchor.copy()
        for i in range(3):
            points[i+1] = points[i] + (points[i+1]-points[i]).normalized()*lengths[i]
    for i, n in enumerate(chain):
        direction = matrices[i].to_quaternion() @ Vector((0, 1, 0))
        rotation = direction.rotation_difference((points[i+1]-points[i]).normalized()) @ matrices[i].to_quaternion()
        p[n] = Matrix.LocRotScale(points[i], rotation, Vector((1, 1, 1)))

def pose_single(start, count, t):
    old = {n: m.copy() for n, m in idle.items()}
    p = {n: old.get(n, rest[n]).copy() for n in names}
    tail = BEGIN + STEP * count
    duration = tail + CLOSE_TAIL
    weight = smooth(t/.48)*(1-smooth((t-tail)/CLOSE_TAIL))
    G = old['WPN_root'] @ Matrix.LocRotScale(Vector((.030, .050, .025))*weight, Euler((math.radians(18)*weight, 0, math.radians(-14)*weight), 'XYZ').to_quaternion(), Vector((1, 1, 1)))
    hand_at(p, old, 'r', G @ rightlocal)
    p['WPN_root'] = G
    for n, L in gunlocal.items():
        if n != 'WPN_root': p[n] = G @ L
    hidden = Matrix.Diagonal((.0001, .0001, .0001, 1))
    p['WPN_Loader'] = G @ gunlocal['WPN_Loader'] @ hidden
    opening = smooth((t-.22)/.26)*(1-smooth((t-tail-.12)/.25))
    D = mech('WPN_Crane', 'Y', math.radians(-78)*opening)
    for n in ['WPN_Crane', 'WPN_Cylinder', 'WPN_Extractor', 'WPN_SOCKET_Magazine', 'WPN_SOCKET_Eject']+[f'WPN_Case_{i}' for i in range(6)]+[f'WPN_Round_{i}' for i in range(6)]:
        p[n] = G @ D @ gunlocal[n]
    center = (D @ gunlocal['WPN_Cylinder']).translation
    latch = hand_goal((-.033, -.022, .026), (1, 0, 0), (0, -.35, 1))
    hold = hand_goal(center+Vector((-.027, .004, -.005)), (1, 0, 0), (0, -.4, 1))
    pinch = None
    if t < .22:
        H = curved_hand(leftlocal, latch, t/.22, 'ReloadInit'); fk, fw = 'ReloadInit', t/.48
    elif t < BEGIN:
        H = curved_hand(latch, hold, (t-.22)/(BEGIN-.22), 'ReloadInit'); fk, fw = 'ReloadInit', t/BEGIN
    elif t < tail:
        cycle = min(count-1, int((t-BEGIN)/STEP))
        phase = t-BEGIN-cycle*STEP
        index = start+cycle
        bn = f'WPN_Case_{index}'
        # Rear face is shared by all chambers; retain the source radial centers.
        chamber = gunlocal[bn].translation.copy()
        rear = Vector((chamber.x, -.0055, chamber.z))
        pull = smooth((phase-.07)/.16)
        case_offset = Vector((0, .057*pull, 0))
        mouth = D @ rear
        extracting = D @ (rear+case_offset)
        pouch = D @ (rear+Vector((-.080, .18, -.17)))
        # Round emerges along the same -Y chamber axis; hand follows its base.
        incoming = Vector((
            key_sample([(.56, -.080), (.72, -.022), (.82, 0)], phase),
            key_sample([(.56, .18), (.72, .072), (.91, 0)], phase),
            key_sample([(.56, -.17), (.74, -.032), (.82, 0)], phase)))
        cartridge_point = D @ (rear+incoming)
        if phase < .07:
            H = curved_hand(hold, pinch_goal(mouth), phase/.07, 'ReloadLoop')
        elif phase < .23:
            H = pinch_goal(extracting); pinch = extracting
        elif phase < .56:
            H = curved_hand(pinch_goal(D@(rear+Vector((0, .057, 0)))), pinch_goal(pouch), (phase-.23)/.33, 'SearchAmmo')
        elif phase < .95:
            H = pinch_goal(cartridge_point); pinch = cartridge_point
        else:
            H = curved_hand(pinch_goal(mouth), hold, (phase-.95)/.20, 'ReloadLoop')
        fk, fw = 'ReloadLoop', phase/STEP
        Cpose = G @ D @ gunlocal[bn]
        if phase < .23:
            Cpose = G @ D @ Matrix.Translation(case_offset) @ gunlocal[bn]
        elif phase < .40:
            fall = phase-.23
            Cpose = G @ D @ Matrix.Translation((0, .057+.20*fall, 0)) @ gunlocal[bn]
            Cpose.translation += Vector((0, 0, -3.5*fall*fall))
        elif phase < VISIBLE:
            Cpose = Cpose @ hidden
        elif phase < SEAT:
            Cpose = G @ D @ Matrix.Translation(incoming) @ gunlocal[bn]
        p[bn] = Cpose
        p[f'WPN_Round_{index}'] = Cpose @ gunlocal[bn].inverted() @ gunlocal[f'WPN_Round_{index}']
    elif t < tail+.37:
        H = hold; fk, fw = 'ReloadEnd', (t-tail)/CLOSE_TAIL
    else:
        H = curved_hand(hold, leftlocal, (t-tail-.37)/.33, 'ReloadEnd'); fk, fw = 'ReloadEnd', (t-tail)/CLOSE_TAIL
    hand_at(p, old, 'l', G @ H)
    fingers(p, fk, fw, .45*weight)
    if pinch is not None:
        # Two fingertips grip opposite sides of the cartridge rear, not a
        # generic closed fist. The arm remains solved from the same contact.
        solve_finger(p, 'thumb', G @ (pinch+Vector((.0045, .0015, -.002))))
        solve_finger(p, 'index', G @ (pinch+Vector((-.0045, -.0015, .002))))
    return p

actions = {}
manifest = {'open': OPEN, 'begin': BEGIN, 'step': STEP, 'remove': REMOVE, 'visible': VISIBLE, 'seat': SEAT, 'close_tail': CLOSE_TAIL, 'sample_rate': 120, 'clips': {}}
for start in range(6):
    for count in range(1, 7-start):
        kind = f'single_{start}_{count}'
        duration = BEGIN+STEP*count+CLOSE_TAIL
        frames = [i*.5 for i in range(round(duration*120)+1)]
        rows = []; previous = {}
        for f in frames:
            p = pose_single(start, count, f/60); row = {}
            for n in names:
                basis = lr[n].inverted() @ (p[parent[n]].inverted_safe() @ p[n] if parent[n] else p[n])
                loc, q, scale = basis.decompose()
                if n in previous and previous[n].dot(q) < 0: q.negate()
                previous[n] = q.copy(); row[n] = (loc, q, scale)
            rows.append(row)
        a = bpy.data.actions.new('DW715_Single_'+str(start)+'_'+str(count)); a.use_fake_user = True
        rig.animation_data_create(); rig.animation_data.action = a
        for n in names:
            rig.pose.bones[n].rotation_mode = 'QUATERNION'
            for prop in ('location', 'rotation_quaternion', 'scale'): rig.pose.bones[n].keyframe_insert(prop, frame=0)
        curves = {(c.data_path,c.array_index):c for c in a.layers[0].strips[0].channelbag(a.slots[0]).fcurves}
        for n in names:
            for prop, field, size in [('location',0,3), ('rotation_quaternion',1,4), ('scale',2,3)]:
                for axis in range(size):
                    c = curves[(f'pose.bones["{n}"].{prop}', axis)]
                    c.keyframe_points.clear(); c.keyframe_points.add(len(frames))
                    c.keyframe_points.foreach_set('co', [v for f,row in zip(frames,rows) for v in (f,row[n][field][axis])])
                    for k in c.keyframe_points: k.interpolation = 'LINEAR'
                    c.update()
        rig.animation_data.action_slot = a.slots[0]
        s.frame_start = 0; s.frame_end = round(duration*60); s.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT'); rig.hide_set(False); rig.select_set(True); bpy.context.view_layer.objects.active = rig
        bpy.ops.export_scene.fbx(filepath=str(O/'Animations'/f'A_DW715_{kind}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
        actions[kind] = a
        manifest['clips'][kind] = {'start_live':start,'load':count,'duration':duration,'seats':[BEGIN+i*STEP+SEAT for i in range(count)],'close':BEGIN+count*STEP+.37}
        print('DW715_SINGLE_EXPORTED', kind, flush=True)
rig.animation_data.action = actions['single_0_6']; rig.animation_data.action_slot = actions['single_0_6'].slots[0]
s.frame_start = 0; s.frame_end = round((BEGIN+STEP*6+CLOSE_TAIL)*60); s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_SingleLoad_Editable.blend'))
(O/'animation.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('DW715_SINGLE_AUTHORING_COMPLETE', flush=True)
