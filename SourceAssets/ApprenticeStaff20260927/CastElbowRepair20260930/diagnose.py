"""Requested bounded staff-cast diagnosis; no UE/game or asset mutation.

Uses the V7 authored skin and saved chainmail render LODs. Axial roll and local
linear-blend contraction are deformation diagnostics, not anatomical angles or
measured physical volume. Not a collision or live visual acceptance test.
"""
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation, Slerp
from author_pose import P, PROJECT, SOURCE, roll


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def blend(a, b, u, spherical=False):
    q = Rotation.from_matrix(np.array([a[:3, :3], b[:3, :3]])).as_quat()
    if spherical:
        rotation = Slerp([0, 1], Rotation.from_quat(q))([u]).as_matrix()[0]
    else:
        if q[0] @ q[1] < 0:
            q[1] *= -1
        rotation = Rotation.from_quat(q[0]*(1-u)+q[1]*u).as_matrix()
    m = np.eye(4)
    m[:3, :3], m[:3, 3] = rotation, a[:3, 3]*(1-u)+b[:3, 3]*u
    return m


def ease(t):
    t = np.clip(t, 0., 1.)
    return float(t*t*t*(t*(t*6-15)+10))


def motion(source, variant, phase, t):
    contacts = [np.array(c['contact']) for c in source['poses'][variant]]
    for c in contacts:
        c[:3, 3] += [0, 4, 0]
    for i in (1, 2):
        contacts[i][:3, 3] += [10, 0, 0]
    shift = np.zeros(3)
    if phase in ('raise', 'ready'):
        a, b, u = 0, 1, ease(t/(.95 if phase == 'raise' else .2))
        shift += np.array([-3., 2., 1.]) * (16*u*u*(1-u)*(1-u))
    elif phase == 'release':
        if t < .035:
            a, b, u = 1, 2, ease(t/.035)
        elif t < .18:
            a, b, u = 2, 3, ease((t-.035)/.145)
        else:
            a, b, u = 3, 4, ease((t-.18)/.1)
        impact = t-.18
        if 0 < impact < .16:
            shift += np.array([-.9, 0, .25])*np.sin(impact*2*np.pi*9)*ease(impact/.012)*(1-ease(impact/.16))
    else:
        a, b, u = (1 if phase == 'charge_recover' else 4), 0, ease(t/.42)
        shift += np.array([0., 2., 2.]) * (16*u*u*(1-u)*(1-u))
    c = blend(contacts[a], contacts[b], u, spherical=True)
    c[:3, 3] += shift
    return a, b, u, c


def sample(data, variant, state):
    a, b, u, contact = state
    world = {n: np.array(m) for n, m in data['rest'].items()}
    clips = data['poses'][variant]
    for n in data['order']:
        local = blend(np.array(clips[a]['local'][n]), np.array(clips[b]['local'][n]), u)
        world[n] = world[data['parent'][n]] @ local
    goal = contact @ np.array(data['variants'][variant]['hand'])
    delta = goal @ np.linalg.inv(world['hand_r'])
    for n in data['order']:
        if n.endswith('_r'):
            world[n] = delta @ world[n]
    return world


class Surface:
    def __init__(self, mesh, rest):
        self.points = np.array(mesh['positions'])
        weights = mesh['weights']
        self.ids = np.array([i for i, w in enumerate(weights) if
            sum(v for n, v in w.items() if n.startswith('upperarm') and n.endswith('_r')) > .05 and
            sum(v for n, v in w.items() if n.startswith('lowerarm') and n.endswith('_r')) > .05])
        triangles = np.array(mesh['triangles'])
        mask = np.any(np.isin(triangles, self.ids), axis=1)
        triangles = triangles[mask]
        self.edges = np.unique(np.sort(np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1), axis=0)
        self.edge_rest = np.linalg.norm(self.points[self.edges[:, 0]]-self.points[self.edges[:, 1]], axis=1)
        used = np.unique(np.r_[self.ids, self.edges.flatten()])
        self.groups = {}
        for n in {n for i in used for n in weights[i]}:
            ids = np.array([i for i in used if n in weights[i]])
            self.groups[n] = (ids, np.array([weights[i][n] for i in ids]), np.linalg.inv(rest[n]))
        self.linear = {n: np.array([weights[i].get(n, 0) for i in self.ids]) for n in self.groups}

    def measure(self, world):
        points = np.zeros_like(self.points)
        jacobian = np.zeros((len(self.ids), 3, 3))
        for n, (ids, w, inverse) in self.groups.items():
            delta = world[n] @ inverse
            points[ids] += (self.points[ids] @ delta[:3, :3].T + delta[:3, 3])*w[:, None]
            jacobian += self.linear[n][:, None, None]*delta[:3, :3]
        values = np.linalg.svd(jacobian, compute_uv=False)[:, -1]
        lengths = np.linalg.norm(points[self.edges[:, 0]]-points[self.edges[:, 1]], axis=1)
        valid = self.edge_rest > .1
        return dict(mixed_elbow_vertices=len(self.ids), smallest_blend_scale_p10=float(np.percentile(values, 10)),
            smallest_blend_scale_min=float(values.min()), max_elbow_edge_stretch=float((lengths[valid]/self.edge_rest[valid]).max()))


def header_error(path, data):
    entries = re.findall(r'\{TEXT\("([^"]+)"\),FQuat\(([^)]+)\),FVector\(([^)]+)\)\}', path.read_text())
    expected = [(n, np.array(m)) for clips in data['poses'].values() for clip in clips for n, m in clip['local'].items()]
    if len(entries) != len(expected):
        raise RuntimeError('Header/source pose count mismatch: '+str(path))
    errors = []
    for (name, q, p), (n, m) in zip(entries, expected):
        if name != n:
            raise RuntimeError('Header/source bone order mismatch')
        errors.extend([np.abs(Rotation.from_quat([float(v) for v in q.split(',')]).as_matrix()-m[:3, :3]).max(),
            np.abs(np.array([float(v) for v in p.split(',')])-m[:3, 3]).max()])
    return float(max(errors))


def main():
    old, new = read(SOURCE), read(P/'full-pose.json')
    rest = {n: np.array(m) for n, m in old['rest'].items()}
    header_dir = PROJECT/'Source/FPSGAME/Weapons/Staff'
    headers = {name: header_error(header_dir/file, data) for name, file, data in [
        ('before', 'StaffAuthoredPoseV13.h', old), ('after', 'StaffAuthoredCastElbow20260930.h', new)]}
    surfaces = {'bare_v7_author': Surface(read(PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/M4.json'), rest)}
    for lod in range(3):
        mesh = read(PROJECT/f'SourceAssets/ChainmailCameraClearance20260929/M4/LOD{lod}.json')
        asset = PROJECT/'Content'/((mesh['source'].split('.')[0].removeprefix('/Game/'))+'.uasset')
        if hashlib.sha256(asset.read_bytes()).hexdigest() != mesh['asset_sha256']:
            raise RuntimeError('Chainmail asset changed since snapshot')
        surfaces[f'chainmail_lod{lod}'] = Surface(mesh, rest)
    rows = []
    for variant in old['poses']:
        for phase, duration in [('raise', .95), ('charge_recover', .42), ('ready', .2), ('release', .38), ('recover', .42)]:
            times = np.unique(np.r_[np.arange(0, duration, 1/120), duration,
                [.035, .18, .28] if phase == 'release' else []])
            row = dict(variant=variant, phase=phase, samples=len(times), before_max_abs_roll_deg=0., after_max_abs_roll_deg=0.,
                max_hand_matrix_error=0., max_finger_matrix_error=0., max_length_error_cm=0., surfaces={})
            for t in times:
                state = motion(old, variant, phase, t)
                worlds = [sample(d, variant, state) for d in (old, new)]
                for label, world in zip(('before', 'after'), worlds):
                    row[label+'_max_abs_roll_deg'] = max(row[label+'_max_abs_roll_deg'], abs(np.degrees(roll(world, rest))))
                    for name, surface in surfaces.items():
                        metrics = surface.measure(world)
                        summary = row['surfaces'].setdefault(name, {}).setdefault(label, metrics.copy())
                        for k, v in metrics.items():
                            summary[k] = max(summary[k], v) if k == 'max_elbow_edge_stretch' else min(summary[k], v)
                row['max_hand_matrix_error'] = max(row['max_hand_matrix_error'], float(np.abs(worlds[0]['hand_r']-worlds[1]['hand_r']).max()))
                fingers = [n for n in old['order'] if n.endswith('_r') and n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))]
                row['max_finger_matrix_error'] = max(row['max_finger_matrix_error'], max(float(np.abs(worlds[0][n]-worlds[1][n]).max()) for n in fingers))
                for a, b in [('upperarm_r', 'lowerarm_r'), ('lowerarm_r', 'hand_r')]:
                    length = np.linalg.norm(rest[b][:3, 3]-rest[a][:3, 3])
                    row['max_length_error_cm'] = max(row['max_length_error_cm'], abs(float(np.linalg.norm(worlds[1][b][:3, 3]-worlds[1][a][:3, 3])-length)))
            rows.append(row)
            print(variant, phase, 'roll', round(row['before_max_abs_roll_deg'], 2), '->', round(row['after_max_abs_roll_deg'], 2),
                'bare blend scale', round(row['surfaces']['bare_v7_author']['before']['smallest_blend_scale_p10'], 3),
                '->', round(row['surfaces']['bare_v7_author']['after']['smallest_blend_scale_p10'], 3), flush=True)
    result = dict(header_source_max_error=headers, rows=rows, samples=sum(r['samples'] for r in rows),
        scope='Four grips; default stationary raise, charge recovery, ready, release/hold and release recovery; 120 Hz with key times; bare V7 author surface and current saved chainmail LOD0/1/2',
        limitations='No live game, camera collision, full garment-skin intersection, locomotion/offhand blend or visual acceptance', runtime_visual='not_tested')
    (P/'diagnosis.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
