"""Continuous dorsal/cuff/thumb surface, with deliberately deformable joins.

The visual shell takes priority over mechanically rigid overlapping plates.
Distances are UE centimetres. Other finger plates keep their existing fit.
"""
import math
import bpy
import numpy as np
from mathutils import Vector
import build_metal_gauntlet_sample as s
import steel_gauntlet_finish as finish
import steel_gauntlet_coverage as coverage
import steel_gauntlet_motion_fit as motion_fit


def smooth(t):
    t = float(np.clip(t, 0., 1.))
    return t*t*t*(10. + t*(-15. + 6.*t))


def mix_weights(a, b, t):
    out = {key: a.get(key, 0.)*(1.-t) + b.get(key, 0.)*t for key in a.keys() | b.keys()}
    out = {key: value for key, value in out.items() if value > 1.e-7}
    total = sum(out.values())
    return {key: value/total for key, value in out.items()}


def hermite(a, b, da, db, t):
    return (2*t**3-3*t*t+1)*a + (t**3-2*t*t+t)*da + (-2*t**3+3*t*t)*b + (t**3-t*t)*db


def wrist_weights(point, wrist, forward, side):
    # Four centimetres of soft transition; no seam between hand and forearm.
    t = smooth((float((point-wrist)@forward)+2.8)/3.8)
    return mix_weights({'lowerarm_twist_01_'+side: 1.}, {'hand_'+side: 1.}, t)


def cuff_grid(palm, tree, wrist, x, f, z):
    cols = palm.shape[1]
    def row(y):
        result = []
        for a in np.linspace(-1.27, 1.27, cols):
            radial = z*math.cos(a)+x*math.sin(a)
            result.append(s.ray_surface(tree, wrist+f*y, radial, 7.)+radial*.34)
        return np.asarray(result)
    cuff = [row(y) for y in np.linspace(-4.2, -2.4, 9)]
    # Native fitted cuff and wide hand roof share a tangent-continuous loft.
    start, end = cuff[-1], palm[0]
    span = 2.5
    da = (cuff[-1]-cuff[-2])/(1.8/8)*span
    dy = np.maximum((palm[1]-palm[0])@f, .10)
    db = (palm[1]-palm[0])/dy[:, None]*span
    transition = [hermite(start, end, da, db, t) for t in np.linspace(0., 1., 13)[1:-1]]
    return np.asarray(cuff+transition+list(palm)), len(cuff)+len(transition)


def thumb_rows(d, a, side, columns, root_direction):
    sections = [next(q for q in a['digits'] if q['bone']==f'thumb_{j:02d}_{side}') for j in (1, 2, 3)]
    lengths = np.array([q['length'] for q in sections])
    joints = np.r_[0., np.cumsum(lengths)]
    # Positive across follows the welded root edge, in both mirrored hands.
    cross_sign = 1. if np.asarray(sections[0]['across'])@root_direction > 0 else -1.
    fits = []
    for j, section in enumerate(sections):
        head = np.asarray(d['bones'][section['bone']]['position'])
        # The root guard wraps the outside of the thumb; the distal guard
        # gradually returns to its dorsal surface without separate plate ends.
        outer = np.asarray(d['bones']['thumb_01_'+side]['position']) - np.asarray(d['bones']['hand_'+side]['position'])
        orientation = 1. if np.asarray(section['across'])@outer > 0 else -1.
        centre = orientation*math.radians((30., 10., 0.)[j])
        angles = centre+cross_sign*np.linspace(-math.radians(62), math.radians(62), columns)
        fit = coverage.radial_fit(section, head, motion_fit.section_trees(d, section['bone']), angles)
        fits.append((head, fit))

    def section_row(j, distance):
        head, (angles, radii, (axis, dorsal, across)) = fits[j]
        local = distance-joints[j]
        radius = radii(local)+.055
        return np.asarray([head+axis*local+(dorsal*math.cos(angle)+across*math.sin(angle))*r
                           for angle, r in zip(angles, radius)])

    rows, weights = [], []
    # Enough longitudinal rings for smooth flexion at both thumb joints.
    for distance in np.linspace(lengths[0]*.64, joints[-1]-lengths[-1]*.10, 31):
        j = min(2, int(np.searchsorted(joints[1:], distance)))
        points = section_row(j, distance)
        ws = {sections[j]['bone']: 1.}
        for joint in (1, 2):
            half = min(lengths[joint-1], lengths[joint])*.29
            if abs(distance-joints[joint]) < half:
                t = smooth((distance-joints[joint]+half)/(half*2))
                points = section_row(joint-1, distance)*(1.-t)+section_row(joint, distance)*t
                ws = mix_weights({sections[joint-1]['bone']: 1.}, {sections[joint]['bone']: 1.}, t)
                break
        rows.append(points)
        weights.append(ws)
    return np.asarray(rows), weights


def build(d, a, side, rig, mat, palm, tree, wrist, x, f, z):
    # Preserve the broad dorsal silhouette, soften corners with one shared
    # subdivision surface, then solidify the entire branched surface once.
    palm = np.asarray([[finish.sample(palm, u, v) for u in np.linspace(0, 1, 29)]
                       for v in np.linspace(0, 1, 33)])
    for iy, row in enumerate(palm):
        for ix, point in enumerate(row):
            u, v = ix/28., iy/32.
            palm[iy, ix] = point+z*(.07*math.exp(-((u-.5)/.09)**2)*math.sin(math.pi*v)**2)
    grid, palm_start = cuff_grid(palm, tree, wrist, x, f, z)
    nr, nc = grid.shape[:2]
    points = list(grid.reshape((-1, 3)))
    weights = [wrist_weights(p, wrist, f, side) for p in points]
    faces = [[y*nc+i, y*nc+i+1, (y+1)*nc+i+1, (y+1)*nc+i]
             for y in range(nr-1) for i in range(nc-1)]

    # This row is literally the hand shell's outer edge: shared indices, not
    # overlapping geometry or a floating thumb-root patch.
    root_ids = [(palm_start+j)*nc+nc-1 for j in range(3, 18)]
    root = np.asarray([points[i] for i in root_ids])
    thumb, thumb_weights = thumb_rows(d, a, side, len(root_ids), root[-1]-root[0])
    end = thumb[0]
    reach = np.linalg.norm(end-root, axis=1)
    across = np.asarray([s.unit(points[i]-points[i-1]) for i in root_ids])
    da = across*reach[:, None]*.60
    db = np.asarray([s.unit(v) for v in thumb[1]-thumb[0]])*reach[:, None]*.62
    branch = []
    branch_weights = []
    for t in np.linspace(0., 1., 15)[1:-1]:
        branch.append(hermite(root, end, da, db, t))
        # Coincident boundaries have identical weights; spread thumb movement
        # over the whole web instead of a single hard hinge at its upper edge.
        branch_weights.append([mix_weights(weights[i], thumb_weights[0], smooth(t)) for i in root_ids])
    branch.extend(thumb)
    branch_weights.extend([[ws.copy() for _ in root_ids] for ws in thumb_weights])
    previous = root_ids
    for row, ws in zip(branch, branch_weights):
        current = list(range(len(points), len(points)+len(row)))
        points.extend(row); weights.extend(ws)
        for i in range(len(row)-1):
            # Opposite winding to the neighbouring main-shell boundary.
            faces.append([previous[i], current[i], current[i+1], previous[i+1]])
        previous = current

    obj = s.mesh_object('Plate_ContinuousBackWristThumb_'+side, points, faces, mat)
    s.activate(obj)
    panel = obj.data.uv_layers.new(name='SteelPanelUV')
    for face in obj.data.polygons:
        for li in face.loop_indices:
            point = np.asarray(points[obj.data.loops[li].vertex_index])-wrist
            panel.data[li].uv = ((float(point@x)+6.)/14., (float(point@f)+4.5)/16.)
    for name in {name for ws in weights for name in ws}:
        group = obj.vertex_groups.new(name=name)
        for i, ws in enumerate(weights):
            if name in ws: group.add([i], ws[name], 'REPLACE')
    # UE-to-Blender reverses handedness. Pick outward orientation from the
    # known dorsal roof, then let connected winding propagate through thumb.
    roof_face = obj.data.polygons[(palm_start+22)*(nc-1)+nc//2]
    if roof_face.normal.dot(s.to_blender(z)) < 0.:
        for face in obj.data.polygons: face.flip()
    obj.data.update()
    sub = obj.modifiers.new('ContinuousRoundedSurface', 'SUBSURF')
    sub.levels = 1; sub.render_levels = 1
    bpy.ops.object.modifier_apply(modifier=sub.name)
    shell = obj.modifiers.new('ContinuousSteelWall', 'SOLIDIFY')
    shell.thickness = .00065; shell.offset = -1.; shell.use_even_offset = True
    bpy.ops.object.modifier_apply(modifier=shell.name)
    bevel = obj.modifiers.new('RoundedOuterEdge', 'BEVEL')
    bevel.width = .00022; bevel.segments = 2; bevel.limit_method = 'ANGLE'; bevel.angle_limit = .65
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for face in obj.data.polygons: face.use_smooth = True
    exported_weights = []
    for vertex in obj.data.vertices:
        ws = {obj.vertex_groups[g.group].name: g.weight for g in vertex.groups if g.weight > 1.e-7}
        total = sum(ws.values())
        exported_weights.append({name: value/total for name, value in ws.items()})
    atlas = obj.data.uv_layers.new(name='SteelSampleUV'); obj.data.uv_layers.active = atlas
    for layer in obj.data.uv_layers: layer.active_render = layer.name=='SteelSampleUV'
    obj.color = (.14, .16, .55, 1.)
    obj.parent = rig
    modifier = obj.modifiers.new('NativeSmoothBinding', 'ARMATURE'); modifier.object = rig
    obj['Construction'] = 'One connected hand-back / wrist / thumb shell; no internal plate seams'
    obj['WeightRule'] = 'Smooth native wrist and thumb gradients; visual continuity takes priority'
    s.PARTS.append(dict(name=obj.name, bone='hand_'+side, kind='continuous_steel_shell', object=obj,
                        thickness_cm=.065, vertices=len(obj.data.vertices), weights=exported_weights))
    # Fewer small details: retain just four rivets on the stable hand roof.
    for i, (u, v) in enumerate(((.18, .37), (.78, .37), (.20, .80), (.76, .80))):
        finish.rivet(f'Rivet_HandBack_{side}_{i}', palm, u, v, z, 'hand_'+side, rig, mat, radius=.13)
    print('STEEL_CONTINUOUS_SHELL_AUTHORED', side, len(obj.data.vertices), flush=True)
