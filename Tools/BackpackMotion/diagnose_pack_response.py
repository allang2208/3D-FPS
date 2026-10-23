"""Requested three-pack fit/mask audit at bounded motion extremes, no asset writes.

Checks authored reference-pose torso/garment cells; this is not animated collision
or rendered gameplay acceptance. Native pose-response output is recorded separately.
"""
import itertools
import json
import sys
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from response_profiles import PROFILES

P = Path('D:/FPS3D/FPSGAME')
R = P/'SourceAssets/BackpackMotion20261022'
sys.path.insert(0, str(P/'Tools/BackpackHarness'))
from author import envelope, read


def rear_exit(v, cells):
    result = np.zeros(len(v))
    for cell in cells:
        up = cell[:, 2] > .99999999
        down = cell[:, 2] < -.99999999
        low = float(cell[down, 3].max()) if down.any() else -np.inf
        high = float(-cell[up, 3].max()) if up.any() else np.inf
        candidates = np.flatnonzero((v[:, 2] >= low-1e-6) & (v[:, 2] <= high+1e-6))
        signed = v[candidates] @ cell[:, :3].T + cell[:, 3]
        local_ids = np.flatnonzero(signed.max(axis=1) < 0)
        ids = candidates[local_ids]
        if not len(ids):
            continue
        den = -cell[:, 1]
        # A nonempty closed hull always has at least one rear-facing plane.
        valid = den > 1e-7
        result[ids] = np.maximum(result[ids], (-signed[local_ids][:, valid]/den[valid]).min(axis=1))
    return result


def main():
    plan = read(R/'manifest.json')
    cfg = read(P/'Content/ColdSteelData/player_body.json')['outfits']
    inputs = P/'SourceAssets/ExpeditionBackpack20261022/BodyInputs'
    body = read(inputs/'body.json')
    rows = []
    for row in plan['variants']:
        if len(sys.argv)>1 and row['kind']+'/'+row['profile']!=sys.argv[1]:continue
        refit = row['kind']=='mountain' and row['profile']=='knit_sweater'
        data = read(R/'MountainSweaterR2/authored.json') if refit else read(Path(row['source']))
        maskdata = read(R/'MountainSweaterR2/mask.json') if refit else read(Path(row['mask']))
        v, t, mask = np.array(data['positions']), np.array(data['triangles']), np.array(maskdata['values'])
        rigid_ids = np.unique(t[data['harness_face_count']:])
        pinned, seams = [], []
        for part in data['parts']:
            if part.get('hardware') or part['name'].startswith('sternum'):
                faces = part.get('faces', part.get('side_faces', [])+part.get('cap_faces', []))
                pinned.extend(np.unique(t[faces]).tolist())
            elif part.get('rows'):
                seams.extend(part['rows'][0]+part['rows'][-1])
        item = cfg[row['item']]['backpack_motion']
        settings = dict(item, **PROFILES[row['item']])
        pivot = np.array(settings['pivot'])
        corners = np.array(list(itertools.product(*zip(settings['bounds_min'], settings['bounds_max']))))
        garment = read(inputs/(row['shirt']+'.json')) if row['shirt'] else None
        cells = envelope(body, garment)[0]['cells']
        # The WPO never moves any vertex forward in this scope. Only the rear
        # torso neighbourhood and active strap spans can meet these body cells.
        ids = np.flatnonzero((mask > 0) & (v[:, 1] > -22) & (v[:, 2] > 100) & (v[:, 2] < 156))
        rigid_count = len(rigid_ids)
        rigid_mask_min, pinned_mask_max, sewn_mask_min = float(mask[rigid_ids].min()), float(mask[pinned].max()), float(mask[seams].min())
        # A rigid affine field reaches its maximum norm on the convex hull.
        # Retain every harness/near-body vertex; skip only redundant rigid interior vertices.
        keep = np.unique(np.r_[np.arange(data['harness_vertex_count']), ids, rigid_ids[ConvexHull(v[rigid_ids]).vertices]])
        remap = np.full(len(v), -1); remap[keep] = np.arange(len(keep))
        ids = remap[ids]; v = v[keep]; mask = mask[keep]
        for part in data['parts']:
            if part.get('rows'):part['rows'] = remap[np.array(part['rows'])].tolist()
        points = v[ids]
        before = rear_exit(points, cells)
        max_wpo = max_forward = new_depth = 0.
        new_ids = set()
        max_length_ratio = 1.
        for signs in itertools.product([-1, 0, 1], repeat=3):
            rot = Rotation.from_euler('xyz', np.array(signs)*settings['max_angle_degrees']*[1, .8, .7], degrees=True)
            rear = max(0., (rot.apply(corners-pivot)-(corners-pivot))[:, 1].max())
            for x, z in itertools.product([-.3, .3], [-settings['max_bounce_cm'], settings['max_bounce_cm']]):
                shift = np.array([x, -rear, z])
                peak = np.linalg.norm(rot.apply(corners-pivot)-(corners-pivot)+shift, axis=1).max()
                limit = settings['max_displacement_cm']; soft = .7*limit
                ratio = (soft+.3*limit*np.tanh((peak-soft)/(.3*limit)))/peak if peak>soft else 1.
                limited = Rotation.from_rotvec(rot.as_rotvec()*ratio); shift *= ratio
                shift[1] = -max(0., (limited.apply(corners-pivot)-(corners-pivot))[:, 1].max())
                delta = (limited.apply(v-pivot)-(v-pivot)+shift)*mask[:, None]
                max_forward = max(max_forward, float(delta[:, 1].max()))
                moved = v+delta
                max_wpo = max(max_wpo, float(np.linalg.norm(moved-v, axis=1).max()))
                after = rear_exit(moved[ids], cells)
                increased = after > before+.01
                new_ids.update(ids[increased].tolist())
                new_depth = max(new_depth, float(np.maximum(after-before, 0).max(initial=0)))
                for part in data['parts']:
                    if not part.get('rows') or part['name'].startswith('sternum'):continue
                    rings = np.array(part['rows']); rest = v[rings].mean(axis=1); moved_path = moved[rings].mean(axis=1)
                    stretch = np.linalg.norm(np.diff(moved_path, axis=0), axis=1)/np.linalg.norm(np.diff(rest, axis=0), axis=1)
                    max_length_ratio = max(max_length_ratio, float(stretch.max()))
        result = dict(kind=row['kind'], profile=row['profile'], asset=row['asset'],
                      rigid_vertices=rigid_count, rigid_mask_min=rigid_mask_min,
                      fixed_hardware_chest_mask_max=pinned_mask_max,
                      sewn_end_mask_min=sewn_mask_min,
                      peak_wpo_cm=max_wpo, max_forward_advance_cm=max_forward,
                      baseline_reference_intruding_vertices=int((before>.01).sum()),
                      increased_reference_intruding_vertices=len(new_ids),
                      max_increased_reference_depth_cm=new_depth,
                      max_station_length_ratio=max_length_ratio)
        rows.append(result)
        print(json.dumps(result), flush=True)
    name='response_fit_audit_r2_final.json' if len(sys.argv)==1 else 'response_fit_audit_r2_selected.json'
    (R/name).write_text(json.dumps(dict(scope=__doc__, variants=rows), indent=2))


if __name__ == '__main__':
    main()
