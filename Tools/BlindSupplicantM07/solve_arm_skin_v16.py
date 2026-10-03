"""Re-solve the original M07 shoulder/arm skin on connected surface paths.

The V13 geometry, UVs, six gills, leg repair and 83-bone V11 reference stay
immutable.  The numerical stage runs in the installed scientific Python;
Blender only reads the mother file, writes local weight groups and exports.
No game, render, import, playback or acceptance test is performed.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys

import numpy as np

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
MASTER = ROOT/'RecoveryOriginalV13/M07_Original_Recovery_V13.blend'
OUT = ROOT/'ArmSweepV16/Skin'
PYTHON = Path('C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe')


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


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
    obj = bpy.data.objects['M07_OriginalBody_Display']
    names = [b.name for b in rig.data.bones]
    points = np.empty((len(obj.data.vertices), 3), np.float32)
    obj.data.vertices.foreach_get('co', points.ravel())
    edges = np.empty((len(obj.data.edges), 2), np.int32)
    obj.data.edges.foreach_get('vertices', edges.ravel())
    field = np.zeros((len(points), len(names)), np.float32)
    lookup = {n:i for i,n in enumerate(names)}
    groups = {g.index:lookup[g.name] for g in obj.vertex_groups if g.name in lookup}
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group in groups:
                field[v.index, groups[g.group]] = g.weight
    # UV is read only to recognize existing metallic wrist-cuff texels.  No
    # geometry is welded, no source UV is edited, and no texture is baked.
    uv = np.zeros((len(points), 2), np.float32)
    layer = obj.data.uv_layers.active
    if layer:
        for loop in obj.data.loops:
            uv[loop.vertex_index] = layer.data[loop.index].uv
    np.savez_compressed(OUT/'body_surface_input.npz', points=points, edges=edges,
                        weights=field, names=np.asarray(names), uv=uv)
    reference = {b.name:{'head_cm':list(b.head_local), 'tail_cm':list(b.tail_local),
                        'parent':b.parent.name if b.parent else None,
                        'matrix':[list(r) for r in b.matrix_local]}
                 for b in rig.data.bones}
    write(OUT/'reference_input.json', reference)
    print('M07_V16_SKIN_SOURCE '+json.dumps({'body_vertices':len(points),
          'body_triangles':len(obj.data.polygons), 'bone_count':len(names),
          'materials':[m.name for m in obj.data.materials],
          'arms':{n:reference[n]['head_cm'] for n in names
                  if n.startswith(('clavicle_', 'upperarm_', 'lowerarm_', 'hand_'))}}), flush=True)
    return rig, obj


def smooth(x):
    x = np.clip(x, 0., 1.)
    return x*x*(3.-2.*x)


def pack(field):
    ids = np.argpartition(field, -8, axis=1)[:, -8:]
    values = np.take_along_axis(field, ids, axis=1)
    order = np.argsort(-values, axis=1, kind='stable')
    ids = np.take_along_axis(ids, order, axis=1).astype(np.int16)
    values = np.take_along_axis(values, order, axis=1)
    values /= np.maximum(values.sum(axis=1, keepdims=True), 1.e-12)
    return ids, values.astype(np.float32)


def chain_chart(points, chain):
    """Nearest actual bone segment and its continuous arc-length chart."""
    delta = np.diff(chain, axis=0)
    lengths = np.linalg.norm(delta, axis=1)
    stations = np.r_[0., np.cumsum(lengths)]
    distance, chart = [], []
    for a, ab, length, offset in zip(chain, delta, lengths, stations):
        t = np.clip((points-a)@ab/max(float(ab@ab), 1.e-12), 0., 1.)
        distance.append(np.linalg.norm(points-a-t[:,None]*ab, axis=1))
        chart.append(offset+t*length)
    distance, chart = np.stack(distance, axis=1), np.stack(chart, axis=1)
    segment = np.argmin(distance, axis=1)
    rows = np.arange(len(points))
    return distance[rows, segment], chart[rows, segment], segment, stations


def solve():
    from PIL import Image
    from scipy.sparse import coo_matrix, diags
    from scipy.sparse.csgraph import connected_components, dijkstra
    from scipy.spatial import cKDTree

    data = np.load(OUT/'body_surface_input.npz')
    reference = json.loads((OUT/'reference_input.json').read_text(encoding='utf-8'))
    positions, old, names = data['points'], data['weights'], data['names'].tolist()
    lookup = {n:i for i,n in enumerate(names)}
    # Weld coincident UV duplicates in a numerical graph only.  Mesh vertices,
    # triangles, loops, seams, normals and UV arrays remain the original data.
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
    length = np.linalg.norm(points[edges[:,0]]-points[edges[:,1]], axis=1)
    metallic = np.asarray(Image.open(ROOT/'Textures/M07_metallic.png').convert('L'))/255.
    uv = data['uv'][first]
    tx = np.clip((uv[:,0]*metallic.shape[1]).astype(int), 0, metallic.shape[1]-1)
    ty = np.clip(((1.-uv[:,1])*metallic.shape[0]).astype(int), 0, metallic.shape[0]-1)
    metal = metallic[ty,tx]
    output = base.copy()
    changed = np.zeros(len(first), bool)
    details = []
    for side in ('l', 'r'):
        bone_chain = ['clavicle_'+side, 'upperarm_'+side, 'lowerarm_'+side, 'hand_'+side]
        chain = [reference[n]['head_cm'] for n in bone_chain]
        palm = np.mean([reference[f'{f}_metacarpal_{side}']['head_cm']
                        for f in ('index', 'middle', 'ring', 'pinky')], axis=0)
        chain = np.asarray([*chain, palm], np.float64)
        radius, chart, segment, stations = chain_chart(points, chain)
        opposite = 'r' if side == 'l' else 'l'
        opposite_distance, _, _, _ = chain_chart(points, np.asarray([
            reference[n[:-1]+opposite]['head_cm'] for n in bone_chain]+[
            np.mean([reference[f'{f}_metacarpal_{opposite}']['head_cm']
                     for f in ('index', 'middle', 'ring', 'pinky')], axis=0)]))
        tube = np.asarray([17., 18., 12., 12.])[segment]
        current = base[:, [lookup[n] for n in bone_chain]].sum(axis=1)
        # Side ownership follows real segment distance.  Chest, opposite arm,
        # hanging non-arm source fragments and separate six-leaf objects have
        # no entry to this connected arm corridor.
        candidate = ((radius < tube) & (radius <= opposite_distance) &
                     (chart > 7.) & (chart < stations[3]+10.) &
                     ((current > .025) | (chart > stations[1]-4.)))
        gill_indices = [lookup[n] for n in names if n.startswith('gill_')]
        # Original shoulder-root tissue can share a body object with membrane
        # attachment islands.  Its established gill ownership stays fixed.
        candidate &= base[:,gill_indices].sum(axis=1) < 1.e-6
        finger_names = [n for n in names if n.endswith('_'+side) and
                        n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_'))]
        phalanx = [lookup[n] for n in finger_names if '_metacarpal_' not in n]
        # Distal finger identities are authoritative; this solve only reaches
        # the proximal wrist/palm blend, never across empty digit gaps.
        candidate &= base[:, phalanx].sum(axis=1) < 1.e-6
        ids = np.flatnonzero(candidate)
        remap = np.full(len(points), -1, np.int32)
        remap[ids] = np.arange(len(ids))
        selected_edges = candidate[edges].all(axis=1)
        ee, el = remap[edges[selected_edges]], length[selected_edges]
        graph = coo_matrix((np.r_[el, el],
                           (np.r_[ee[:,0], ee[:,1]], np.r_[ee[:,1], ee[:,0]])),
                           shape=(len(ids), len(ids))).tocsr()
        count, components = connected_components(graph, directed=False)
        sizes = np.bincount(components)
        main = int(sizes.argmax())
        main_ids = components == main
        s = chart[ids].copy()
        # Surface distances correct the analytic bone chart on actual skin.
        # Seed rings are on the same connected body, not nearest opposing or
        # back-membrane vertices.  Small disconnected source fittings borrow
        # a coherent field from the nearest connected same-arm surface.
        start = np.flatnonzero(main_ids & (s > 13.) & (s < 16.))
        end = np.flatnonzero(main_ids & (np.abs(s-(stations[3]+4.)) < 1.5))
        if not len(start) or not len(end):
            raise RuntimeError('Actual proximal/distal arm rings could not be located: '+side)
        d0 = dijkstra(graph, directed=False, indices=start, min_only=True)
        d1 = dijkstra(graph, directed=False, indices=end, min_only=True)
        route = float(np.median(d0[end]))
        s0 = float(np.median(s[start])); s1 = float(np.median(s[end]))
        routed = np.isfinite(d0) & np.isfinite(d1)
        path_s = s0+(d0[routed]-d1[routed]+route)*.5*(s1-s0)/max(route, 1.e-12)
        s[routed] = .65*s[routed]+.35*path_s
        upper = smooth((s-(stations[1]-12.))/24.)
        lower = smooth((s-(stations[2]-10.))/20.)
        hand = smooth((s-(stations[3]-6.))/12.)
        anatomical = np.zeros((len(ids), len(names)), np.float64)
        anatomical[:, lookup[bone_chain[0]]] = 1.-upper
        anatomical[:, lookup[bone_chain[1]]] = upper*(1.-lower)
        anatomical[:, lookup[bone_chain[2]]] = upper*lower*(1.-hand)
        anatomical[:, lookup[bone_chain[3]]] = upper*lower*hand
        # Preserve all five proximal metacarpal identities at the wrist edge.
        finger_indices = [lookup[n] for n in finger_names]
        fraction = base[ids][:,finger_indices].sum(axis=1)
        anatomical *= (1.-fraction[:,None])
        anatomical[:,finger_indices] += base[ids][:,finger_indices]
        if (~routed).any():
            source = np.flatnonzero(routed)
            nearest = source[cKDTree(points[ids[source]]).query(points[ids[~routed]])[1]]
            anatomical[~routed] = anatomical[nearest]

        # The metallic cuff remains a rigid lowerarm-owned fitting.  A short
        # geodesic skin band approaches that fitting continuously; cuffs do
        # not pick up palm/finger rotation just because they touch the wrist.
        cuff = ((metal[ids] > .24) & (s > stations[2]+12.) &
                (s < stations[3]+2.) & (radius[ids] < 12.))
        cuff_seed = np.flatnonzero(cuff)
        cuff_blend = np.zeros(len(ids))
        if len(cuff_seed):
            cuff_distance = dijkstra(graph, directed=False, indices=cuff_seed, min_only=True)
            cuff_blend = 1.-smooth(np.maximum(cuff_distance-1.25, 0.)/3.75)
            rigid = np.zeros_like(anatomical)
            rigid[:,lookup['lowerarm_'+side]] = 1.
            anatomical = anatomical*(1.-cuff_blend[:,None])+rigid*cuff_blend[:,None]
        proximal = smooth((s-(stations[1]-19.))/21.)
        distal = 1.-smooth((s-(stations[3]+3.))/6.)
        radial = smooth((tube[ids]-radius[ids])/3.)
        alpha = proximal*distal*radial
        boundary = np.zeros(len(ids), bool)
        crossing = candidate[edges].sum(axis=1) == 1
        endpoint = edges[crossing][candidate[edges[crossing]]]
        boundary[remap[endpoint]] = True
        if boundary.any():
            border_distance = dijkstra(graph, directed=False, indices=np.flatnonzero(boundary), min_only=True)
            alpha *= smooth(border_distance/5.)
        alpha[cuff] = 1.
        anchor = base[ids]*(1.-alpha[:,None])+anatomical*alpha[:,None]

        # Screened surface diffusion keeps the real segment/joint solution
        # anchored, removes UV-seam discontinuities, and respects all graph
        # edges into unchanged skin as fixed boundary data.
        conductance = 1./(el*el+.16)
        adjacency = coo_matrix((np.r_[conductance, conductance],
                               (np.r_[ee[:,0],ee[:,1]], np.r_[ee[:,1],ee[:,0]])),
                               shape=(len(ids),len(ids))).tocsr()
        degree = np.asarray(adjacency.sum(axis=1)).ravel()
        average = diags(1./np.maximum(degree,1.e-12))@adjacency
        # Dirichlet borders retain the existing skin field exactly.
        fixed = boundary | (alpha < .001) | cuff
        diffused = anchor.copy()
        for _ in range(24):
            diffused = .30*anchor+.70*(average@diffused)
            diffused[fixed] = anchor[fixed]
            diffused[degree == 0.] = anchor[degree == 0.]
        # Broad joint/shoulder bands use diffusion; unaffected limb shafts
        # keep deterministic bone ownership rather than unnecessary blur.
        joint = np.maximum.reduce([1.-smooth(np.abs(s-stations[j])/w)
                                   for j,w in ((1,22.),(2,17.),(3,13.))])
        blend = .8*joint*alpha
        repaired = anchor*(1.-blend[:,None])+diffused*blend[:,None]
        repaired[boundary] = base[ids[boundary]]
        repaired[cuff] = 0.; repaired[cuff,lookup['lowerarm_'+side]] = 1.
        repaired /= np.maximum(repaired.sum(axis=1,keepdims=True),1.e-12)
        packed, values = pack(repaired)
        repaired[:] = 0.
        np.add.at(repaired,(np.broadcast_to(np.arange(len(ids))[:,None],packed.shape),packed),values)
        actual = np.max(np.abs(repaired-base[ids]),axis=1) > 2.e-6
        output[ids[actual]] = repaired[actual]
        changed[ids[actual]] = True
        details.append({'side':side,'candidate_surface_vertices':int(len(ids)),
            'changed_welded_surface_vertices':int(actual.sum()),
            'connected_surface_components':int(count),
            'disconnected_fitting_vertices_transferred':int((~routed).sum()),
            'rigid_lowerarm_metal_cuff_vertices':int(cuff.sum()),
            'same_side_skin_corridor_radii_cm':[17.,18.,12.,12.],
            'geodesic_vs_real_segment_chart_mix':[.35,.65],
            'joint_blend_widths_cm':{'shoulder':24.,'elbow':20.,'wrist':12.},
            'surface_diffusion_iterations':24,'fixed_boundary_vertices':int(boundary.sum()),
            'bone_heads_cm':chain.tolist(),'bone_path_length_cm':stations.tolist(),
            'surface_route_length_cm':route,
            'original_gill_owned_body_rows_locked':True,
            'independent_phalanx_field_changed':False})
        print('M07_V16_SOLVED_ARM '+json.dumps(details[-1]),flush=True)
    original_rows = np.flatnonzero(changed[welded])
    indices, weights = pack(output[welded[original_rows]])
    np.savez_compressed(OUT/'arm_skin_solution.npz', vertex_ids=original_rows,
                        bone_indices=indices,bone_weights=weights,names=np.asarray(names))
    write(OUT/'skin_solution_record.json', {'method':'Actual bone segment arc length with same-arm connected-skin geodesic correction and screened surface diffusion; no source-X partition',
        'changed_display_body_vertices':int(len(original_rows)),
        'changed_welded_body_vertices':int(changed.sum()),
        'maximum_influences':8,'normalized':True,'sides':details,
        'preserved':['OriginalV13 body positions/faces/UV/normals/material slots',
            'OriginalV11 83-bone names/hierarchy/reference matrices/joint lengths',
            'OriginalV13 knee/leg field and non-arm skin',
            'Five distal phalanx anatomical chains and identities',
            'All six OriginalV13 display gills and simulation proxies',
            'Original cloth mobility map and 24 collision definitions'],
        'runtime_tested':False,'rendered':False})


def apply_local(obj, solution):
    """Only touched vertex rows are replaced; other groups are never cleared."""
    names = solution['names'].tolist()
    groups = {g.name:g for g in obj.vertex_groups}
    selected = solution['vertex_ids'].tolist()
    for name in names:
        if name in groups:
            groups[name].remove(selected)
    values = np.rint(solution['bone_weights']*255).astype(np.int16)
    values[:,0] += 255-values.sum(axis=1)
    vertices = np.repeat(solution['vertex_ids'],8)
    indices, amount = solution['bone_indices'].ravel(), values.ravel()
    positive = amount > 0
    keys = indices[positive].astype(np.int64)*256+amount[positive]
    vertices = vertices[positive]
    order = np.argsort(keys)
    keys,vertices = keys[order],vertices[order]
    splits = np.r_[0,np.flatnonzero(np.diff(keys))+1,len(keys)]
    for a,b in zip(splits[:-1],splits[1:]):
        key = int(keys[a]); name = names[key//256]
        groups[name].add(vertices[a:b].tolist(),(key%256)/255.,'REPLACE')


def author():
    import bpy
    sys.path.insert(0,str(Path(__file__).parent))
    import author_original_surfaces_v08 as surfaces
    rig,body = dump_source()
    subprocess.run([str(PYTHON),str(Path(__file__).resolve()),'--stage','solve'],check=True)
    solution = np.load(OUT/'arm_skin_solution.npz')
    apply_local(body,solution)
    body['arm_skin_revision'] = 'OriginalV16 surface-path anatomical solve'
    display = [body]+[bpy.data.objects[f'M07_OriginalGill_{i:02d}_Display'] for i in range(1,7)]
    export_path = OUT/'SK_M07_Display_ArmSweepV16.fbx'
    source_path = OUT/'M07_Original_ArmSkin_V16.blend'
    surfaces.export(export_path,rig,display)
    bpy.ops.wm.save_as_mainfile(filepath=str(source_path),compress=True)
    record = json.loads((OUT/'skin_solution_record.json').read_text(encoding='utf-8'))
    record.update({'revision':'ArmSweepV16','source':str(source_path),
        'display_fbx':str(export_path),'original_master':str(MASTER),
        'reference_skeleton':'/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11',
        'bone_count':len(rig.data.bones),'reference_revision':'OriginalV11',
        'reference_pose_modified':False,
        'display_triangles':sum(len(o.data.polygons) for o in display),
        'display_vertices':sum(len(o.data.vertices) for o in display),
        'body_triangles':len(body.data.polygons),'body_vertices':len(body.data.vertices),
        'display_objects':[{'name':o.name,'vertices':len(o.data.vertices),
                           'triangles':len(o.data.polygons),'materials':[m.name for m in o.data.materials]}
                           for o in display],
        'cloth_source':'Reuse RecoveryOriginalV13/SK_M07_ClothBuildSource_OriginalV13.fbx; only matching existing six gills supply cloth mapping',
        'lod_operation':'No source reduction; importer should retain three existing V13 display LOD budgets',
        'source_saved':True,'fbx_exported':True,'ue_imported':False,'ue_saved':False,
        'runtime_tested':False,'rendered':False})
    write(OUT/'skin_manifest_v16.json',record)
    print('M07_V16_ORIGINAL_ARM_SKIN_SOURCE_AND_FBX_SAVED '+str(OUT/'skin_manifest_v16.json'),flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('dump', 'solve', 'author'), default='author')
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
