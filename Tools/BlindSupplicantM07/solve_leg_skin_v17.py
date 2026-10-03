"""Local original-surface M07 V17 hip/knee/ankle skin production.

The saved V16 mother file is authoritative.  Geometry, UVs, materials, custom
normals, all 83 V11 reference bones, V16 arm weights and six gill objects stay
unchanged.  Only same-leg continuous body skin rows receive a new field.
Numerical welding is confined to a solver graph and never changes the mesh.
No UE, game, animation playback, render or acceptance test is launched.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys

import numpy as np

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
MASTER = ROOT/'ArmSweepV16/Skin/M07_Original_ArmSkin_V16.blend'
OUT = ROOT/'LegJointsV17/Skin'
PYTHON = Path('C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe')


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def smooth(x):
    x = np.clip(x, 0., 1.)
    return x*x*(3.-2.*x)


def unit(x):
    return x/max(float(np.linalg.norm(x)), 1.e-12)


def pack(field):
    ids = np.argpartition(field, -8, axis=1)[:, -8:]
    values = np.take_along_axis(field, ids, axis=1)
    order = np.argsort(-values, axis=1, kind='stable')
    ids = np.take_along_axis(ids, order, axis=1).astype(np.int16)
    values = np.take_along_axis(values, order, axis=1)
    values /= np.maximum(values.sum(axis=1, keepdims=True), 1.e-12)
    return ids, values.astype(np.float32)


def dump_source():
    import bpy
    from mathutils import Matrix
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    rig.animation_data_clear()
    rig.data.pose_position = 'REST'
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.scene.frame_set(0)
    body = bpy.data.objects['M07_OriginalBody_Display']
    names = [b.name for b in rig.data.bones]
    points = np.empty((len(body.data.vertices), 3), np.float32)
    body.data.vertices.foreach_get('co', points.ravel())
    edges = np.empty((len(body.data.edges), 2), np.int32)
    body.data.edges.foreach_get('vertices', edges.ravel())
    field = np.zeros((len(points), len(names)), np.float32)
    lookup = {n:i for i,n in enumerate(names)}
    groups = {g.index:lookup[g.name] for g in body.vertex_groups if g.name in lookup}
    for vertex in body.data.vertices:
        for group in vertex.groups:
            if group.group in groups:
                field[vertex.index, groups[group.group]] = group.weight
    np.savez_compressed(OUT/'leg_surface_input.npz', points=points, edges=edges,
                        weights=field, names=np.asarray(names))
    reference = {b.name:{'head_cm':list(b.head_local), 'tail_cm':list(b.tail_local),
                        'parent':b.parent.name if b.parent else None,
                        'matrix':[list(r) for r in b.matrix_local]}
                 for b in rig.data.bones}
    write(OUT/'reference_input.json', reference)
    print('M07_V17_ORIGINAL_LEG_SOURCE_READ '+json.dumps({
        'source':str(MASTER),'body_vertices':len(points),
        'body_triangles':len(body.data.polygons),'bone_count':len(names),
        'joint_heads_cm':{n:reference[n]['head_cm'] for n in names
                          if n.startswith(('thigh_', 'calf_', 'foot_', 'ball_'))}}), flush=True)
    return rig, body


def chain_chart(points, chain):
    delta = np.diff(chain, axis=0)
    lengths = np.linalg.norm(delta, axis=1)
    stations = np.r_[0., np.cumsum(lengths)]
    distance, station = [], []
    for head, axis, length, start in zip(chain, delta, lengths, stations):
        t = np.clip((points-head)@axis/max(float(axis@axis), 1.e-12), 0., 1.)
        distance.append(np.linalg.norm(points-head-t[:,None]*axis, axis=1))
        station.append(start+t*length)
    distance, station = np.stack(distance, axis=1), np.stack(station, axis=1)
    segment = np.argmin(distance, axis=1)
    row = np.arange(len(points))
    return distance[row,segment], station[row,segment], segment, stations


def joint_plane_station(points, chain, station, index, radius):
    """Continuous joint chart through the real incoming/outgoing directions."""
    axis = unit(unit(chain[index]-chain[index-1])+unit(chain[index+1]-chain[index]))
    relative = points-chain[index]
    local = station[index]+relative@axis
    mix = 1.-smooth(np.linalg.norm(relative, axis=1)/radius)
    return local, mix, axis


def locate_joint_skin(points, candidate, joint, axis, radial_limit):
    relative = points-joint
    axial = relative@axis
    radial = np.linalg.norm(relative-axial[:,None]*axis, axis=1)
    ring = candidate & (np.abs(axial) < 1.5) & (radial < radial_limit)
    if not ring.any():
        return {'ring_vertices':0,'reference_joint_cm':joint.tolist()}
    surface = points[ring]
    center = np.median(surface, axis=0)
    return {'reference_joint_cm':joint.tolist(),'section_normal':axis.tolist(),
        'ring_vertices':int(ring.sum()),'surface_ring_median_cm':center.tolist(),
        'surface_ring_bounds_cm':[surface.min(axis=0).tolist(),surface.max(axis=0).tolist()],
        'skin_ring_median_offset_from_reference_cm':float(np.linalg.norm(center-joint)),
        'ring_selection':'Actual same-leg body skin, real joint normal slab +/-1.5cm, anatomical radial corridor'}


def solve():
    from scipy.sparse import coo_matrix, diags
    from scipy.sparse.csgraph import connected_components, dijkstra
    from scipy.spatial import cKDTree

    data = np.load(OUT/'leg_surface_input.npz')
    reference = json.loads((OUT/'reference_input.json').read_text(encoding='utf-8'))
    positions, old, names = data['points'], data['weights'], data['names'].tolist()
    lookup = {n:i for i,n in enumerate(names)}
    _, first, welded = np.unique(np.round(positions/.001).astype(np.int32),
                                 axis=0, return_index=True, return_inverse=True)
    points = positions[first].astype(np.float64)
    base = np.zeros((len(first), len(names)), np.float64)
    counts = np.bincount(welded)
    np.add.at(base, welded, old)
    base /= counts[:,None]
    edges = welded[data['edges']]
    edges.sort(axis=1)
    edges = np.unique(edges[edges[:,0] != edges[:,1]], axis=0)
    lengths = np.linalg.norm(points[edges[:,0]]-points[edges[:,1]], axis=1)
    output = base.copy()
    changed = np.zeros(len(first), bool)
    details = []
    gill = base[:,[lookup[n] for n in names if n.startswith('gill_')]].sum(axis=1)
    arm_indices = [lookup[n] for n in names if n.startswith((
        'clavicle_', 'upperarm_', 'lowerarm_', 'hand_', 'thumb_', 'index_',
        'middle_', 'ring_', 'pinky_'))]
    arm = base[:,arm_indices].sum(axis=1)
    pelvis = np.asarray(reference['pelvis']['head_cm'], np.float64)
    for side in ('l', 'r'):
        opposite = 'r' if side == 'l' else 'l'
        bones = [n+'_'+side for n in ('thigh','calf','foot','ball')]
        opposite_bones = [n+'_'+opposite for n in ('thigh','calf','foot','ball')]
        chain = np.asarray([pelvis]+[reference[n]['head_cm'] for n in bones])
        other = np.asarray([pelvis]+[reference[n]['head_cm'] for n in opposite_bones])
        radius, chart, segment, stations = chain_chart(points, chain)
        other_radius, _, _, _ = chain_chart(points, other)
        current = base[:,[lookup[n] for n in bones]].sum(axis=1)
        other_weight = base[:,[lookup[n] for n in opposite_bones]].sum(axis=1)
        corridor = np.asarray([22.,18.,13.,20.])[segment]
        distal = (points[:,2] < 15.) & (current > .02)
        owner = (radius <= other_radius) | (current > other_weight+.1)
        candidate = owner & ((radius < corridor) | distal)
        candidate &= (current > .015) & (points[:,2] < 146.)
        # Detached shoulder-root tissue and long hanging original fragments
        # must not enter a thigh field through height or side coordinates.
        candidate &= (gill < 1.e-6) & (arm < 1.e-6)
        candidate &= (np.abs(points[:,0]) < 64.) & (np.abs(points[:,1]) < 47.)
        ids = np.flatnonzero(candidate)
        if not len(ids):
            raise RuntimeError('No original same-leg skin corridor: '+side)
        remap = np.full(len(points), -1, np.int32)
        remap[ids] = np.arange(len(ids))
        selected_edges = candidate[edges].all(axis=1)
        ee, el = remap[edges[selected_edges]], lengths[selected_edges]
        graph = coo_matrix((np.r_[el,el],(np.r_[ee[:,0],ee[:,1]],
                            np.r_[ee[:,1],ee[:,0]])),shape=(len(ids),len(ids))).tocsr()
        component_count, components = connected_components(graph, directed=False)
        main = int(np.bincount(components).argmax())
        main_ids = components == main
        s = chart[ids].copy()
        start = np.flatnonzero(main_ids & (s > stations[1]+8.) & (s < stations[1]+12.))
        end = np.flatnonzero(main_ids & (s > stations[3]-3.) & (s < stations[3]+1.))
        if not len(start) or not len(end):
            raise RuntimeError('Original proximal thigh/ankle skin rings missing: '+side)
        d0 = dijkstra(graph,directed=False,indices=start,min_only=True)
        d1 = dijkstra(graph,directed=False,indices=end,min_only=True)
        route = float(np.median(d0[end]))
        s0, s1 = float(np.median(s[start])), float(np.median(s[end]))
        routed = np.isfinite(d0) & np.isfinite(d1)
        path_s = s0+(d0[routed]-d1[routed]+route)*.5*(s1-s0)/max(route,1.e-12)
        s[routed] = .75*s[routed]+.25*path_s
        joint_axes = {}
        for joint, index, influence_radius in (('hip',1,22.),('knee',2,25.),('ankle',3,18.)):
            local, mix, axis = joint_plane_station(points[ids],chain,stations,index,influence_radius)
            s = s*(1.-mix)+local*mix
            joint_axes[joint] = axis

        # The convex knee cap follows the proximal segment slightly more;
        # the inside fold has a broader transition.  The rest bend itself is
        # retained, including its asymmetric original shape.
        hip, knee, ankle, ball = chain[1:]
        leg_axis = unit(ankle-hip)
        knee_pole = unit(knee-hip-leg_axis*float((knee-hip)@leg_axis))
        relative = points[ids]-knee
        cap = np.clip((relative@knee_pole)/8.,-1.,1.)
        knee_s = s-1.5*np.maximum(cap,0.)*(1.-smooth(np.linalg.norm(relative,axis=1)/20.))
        knee_width = 24.+6.*np.maximum(-cap,0.)
        hip_mix = smooth((s-(stations[1]-12.))/26.)
        knee_mix = smooth((knee_s-stations[2]+knee_width*.5)/knee_width)
        ankle_mix = smooth((s-(stations[3]-8.))/16.)
        # Low plantar/claw fan cannot retain shin ownership after the ankle
        # blend. The existing foot-versus-ball identity is kept; no new toe
        # bones or arbitrary finger-like toe partition is invented.
        plantar = smooth((13.-points[ids,2])/5.)
        ankle_mix = 1.-(1.-ankle_mix)*(1.-plantar)
        original_foot = base[ids,lookup['foot_'+side]]
        original_ball = base[ids,lookup['ball_'+side]]
        toe_ratio = original_ball/np.maximum(original_foot+original_ball,1.e-12)
        toe_ratio[(original_foot+original_ball) < 1.e-8] = 0.
        toe_gate = smooth((s-(stations[3]+3.))/14.)
        toe_ratio *= np.maximum(toe_gate, plantar)
        anatomical = np.zeros((len(ids),len(names)),np.float64)
        anatomical[:,lookup['pelvis']] = 1.-hip_mix
        anatomical[:,lookup['thigh_'+side]] = hip_mix*(1.-knee_mix)
        anatomical[:,lookup['calf_'+side]] = hip_mix*knee_mix*(1.-ankle_mix)
        foot_total = hip_mix*knee_mix*ankle_mix
        anatomical[:,lookup['foot_'+side]] = foot_total*(1.-toe_ratio)
        anatomical[:,lookup['ball_'+side]] = foot_total*toe_ratio
        if (~routed).any():
            source = np.flatnonzero(routed)
            nearest = source[cKDTree(points[ids[source]]).query(points[ids[~routed]])[1]]
            anatomical[~routed] = anatomical[nearest]

        alpha = smooth((s-(stations[1]-8.))/12.)
        radial = smooth((corridor[ids]-radius[ids])/4.)
        radial[distal[ids]] = 1.
        alpha *= radial
        boundary = np.zeros(len(ids),bool)
        crossing = candidate[edges].sum(axis=1) == 1
        endpoint = edges[crossing][candidate[edges[crossing]]]
        boundary[remap[endpoint]] = True
        if boundary.any():
            border_distance = dijkstra(graph,directed=False,indices=np.flatnonzero(boundary),min_only=True)
            alpha *= smooth(border_distance/5.)
        anchor = base[ids]*(1.-alpha[:,None])+anatomical*alpha[:,None]
        conductance = 1./(el*el+.16)
        adjacency = coo_matrix((np.r_[conductance,conductance],
                               (np.r_[ee[:,0],ee[:,1]],np.r_[ee[:,1],ee[:,0]])),
                               shape=(len(ids),len(ids))).tocsr()
        degree = np.asarray(adjacency.sum(axis=1)).ravel()
        average = diags(1./np.maximum(degree,1.e-12))@adjacency
        # Preserve terminal toe support ownership.  Only joint folds are
        # diffused; the shafts and low claw tips keep deterministic weights.
        toe_tips = (points[ids,2] < 8.) & ((original_foot > .99) | (original_ball > .99))
        fixed = boundary | (alpha < .001) | toe_tips
        diffused = anchor.copy()
        for _ in range(28):
            diffused = .32*anchor+.68*(average@diffused)
            diffused[fixed] = anchor[fixed]
            diffused[degree == 0.] = anchor[degree == 0.]
        joint_strength = np.maximum.reduce([1.-smooth(np.abs(s-stations[j])/r)
                                          for j,r in ((1,23.),(2,23.),(3,17.))])
        blend = .8*joint_strength*alpha*(1.-plantar)
        repaired = anchor*(1.-blend[:,None])+diffused*blend[:,None]
        repaired[boundary] = base[ids[boundary]]
        repaired /= np.maximum(repaired.sum(axis=1,keepdims=True),1.e-12)
        packed, values = pack(repaired)
        repaired[:] = 0.
        np.add.at(repaired,(np.broadcast_to(np.arange(len(ids))[:,None],packed.shape),packed),values)
        actual = np.max(np.abs(repaired-base[ids]),axis=1) > 2.e-6
        output[ids[actual]] = repaired[actual]
        changed[ids[actual]] = True
        joints = {joint:locate_joint_skin(points,candidate,chain[index],joint_axes[joint],limit)
                  for joint,index,limit in (('hip',1,20.),('knee',2,12.),('ankle',3,12.))}
        reference_axis_angles = {}
        for bone,next_joint in zip(bones[:3],chain[2:]):
            axis = np.asarray(reference[bone]['matrix'],np.float64)[:3,1]
            link = next_joint-np.asarray(reference[bone]['head_cm'])
            reference_axis_angles[bone] = float(np.degrees(np.arccos(np.clip(unit(axis)@unit(link),-1.,1.))))
        details.append({'side':side,'joints':joints,
            'bone_heads_cm':{name:reference[name]['head_cm'] for name in bones},
            'reference_y_axis_vs_child_head_direction_degrees':reference_axis_angles,
            'reference_y_axis_note':'V11 visual bone tails point upward and are not the anatomical head-to-child shaft; reference is retained. Movement authoring must use actual head-to-child directions.',
            'candidate_welded_skin_vertices':int(len(ids)),
            'changed_welded_skin_vertices':int(actual.sum()),
            'connected_skin_components':int(component_count),
            'small_disconnected_skin_rows_transferred':int((~routed).sum()),
            'fixed_boundary_skin_vertices':int(boundary.sum()),
            'preserved_terminal_support_rows':int(toe_tips.sum()),
            'joint_blend_widths_cm':{'hip':26.,'knee_convex':24.,'knee_inside_fold':30.,'ankle':16.},
            'skin_route_length_cm':route,'bone_path_station_cm':stations.tolist(),
            'bone_vs_skin_route_mix':[.75,.25],'surface_diffusion_iterations':28,
            'same_leg_anatomical_segment_corridor_radii_cm':[22.,18.,13.,20.],
            'original_opposite_leg_weight_maximum_in_corridor':float(other_weight[ids].max(initial=0.)),
            'foot_policy':'Old original foot/ball ratio remains on the plantar claw fan; shin mass is removed below the ankle fold; extreme original foot/ball tip ownership is fixed.',
            'knee_pole_direction_original_reference':knee_pole.tolist()})
        print('M07_V17_LOCAL_JOINT_FIELD_SOLVED '+json.dumps(details[-1]),flush=True)

    original_rows = np.flatnonzero(changed[welded])
    indices, weights = pack(output[welded[original_rows]])
    np.savez_compressed(OUT/'leg_skin_solution.npz',vertex_ids=original_rows,
                        bone_indices=indices,bone_weights=weights,names=np.asarray(names))
    write(OUT/'leg_skin_solution_record.json',{
        'method':'Actual anatomical bone-head shaft chart, joint-normal plane blending and same-leg skin geodesic correction with fixed-boundary screened surface diffusion',
        'source_field_limitation':'V13 leg field used global-Z hip/knee/ankle bands; this does not follow bent three-dimensional shafts or front/back joint folds. V11 bone display tails/local Y are not the true anatomical head-to-child segments.',
        'changed_display_body_vertices':int(len(original_rows)),
        'changed_welded_body_vertices':int(changed.sum()),'maximum_influences':8,
        'normalized':True,'sides':details,
        'preserved':['All original V13 display positions/triangles/UV/custom normals/material slots',
            'OriginalV11 83 bone names/hierarchy/reference matrices/joint lengths',
            'V16 shoulder/elbow/forearm/wrist and all phalanx skin weights',
            'All non-leg body rows, including existing gill-owned body attachment tissue',
            'All six OriginalV13 display gills and cloth simulation proxies',
            'Existing V13 cloth mobility and body collision recipe'],
        'runtime_tested':False,'rendered':False,'tested':False,'visual_accepted':False})


def author():
    import bpy
    sys.path.insert(0,str(Path(__file__).parent))
    import author_original_surfaces_v08 as surfaces
    from solve_arm_skin_v16 import apply_local
    rig, body = dump_source()
    subprocess.run([str(PYTHON),str(Path(__file__).resolve()),'--stage','solve'],check=True)
    solution = np.load(OUT/'leg_skin_solution.npz')
    apply_local(body,solution)
    body['leg_skin_revision'] = 'OriginalV17 actual hip/knee/ankle surface paths and anatomical joint planes'
    display = [body]+[bpy.data.objects[f'M07_OriginalGill_{i:02d}_Display'] for i in range(1,7)]
    export_path = OUT/'SK_M07_Display_LegJointsV17.fbx'
    source_path = OUT/'M07_Original_LegJoints_V17.blend'
    surfaces.export(export_path,rig,display)
    bpy.ops.wm.save_as_mainfile(filepath=str(source_path),compress=True)
    record = json.loads((OUT/'leg_skin_solution_record.json').read_text(encoding='utf-8'))
    record.update({'revision':'LegJointsV17','source':str(source_path),
        'display_fbx':str(export_path),'original_master':str(MASTER),
        'reference_skeleton':'/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11',
        'bone_count':len(rig.data.bones),'reference_revision':'OriginalV11',
        'reference_pose_modified':False,'geometry_modified':False,'uv_modified':False,
        'display_triangles':sum(len(o.data.polygons) for o in display),
        'display_vertices':sum(len(o.data.vertices) for o in display),
        'body_triangles':len(body.data.polygons),'body_vertices':len(body.data.vertices),
        'display_objects':[{'name':o.name,'vertices':len(o.data.vertices),
                           'triangles':len(o.data.polygons),'materials':[m.name for m in o.data.materials]}
                          for o in display],
        'cloth_source':'Reuse RecoveryOriginalV13/SK_M07_ClothBuildSource_OriginalV13.fbx; existing six gill display objects unchanged',
        'lod_operation':'No source reduction; same original V13 three-LOD production recipe',
        'source_saved':True,'fbx_exported':True,'ue_imported':False,'ue_saved':False,
        'runtime_tested':False,'rendered':False,'tested':False,'user_review_pending':True})
    write(OUT/'leg_skin_manifest_v17.json',record)
    print('M07_V17_ORIGINAL_LEG_SOURCE_AND_FBX_SAVED '+str(OUT/'leg_skin_manifest_v17.json'),flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage',choices=('dump','solve','author'),default='author')
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else (
        [] if 'bpy' in sys.modules else sys.argv[1:])
    args = parser.parse_args(argv)
    if args.stage == 'dump':
        dump_source()
    elif args.stage == 'solve':
        solve()
    else:
        author()


if __name__ == '__main__':
    main()
