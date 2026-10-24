"""Native bind-frame and local surface displacement used for garment authoring.

Positions remain in UE centimetres. The input mesh's vertex order, topology and
UVs stay intact; the returned data is consumed by the separate UE save stage.
Backpack shells and rigid headwear use their own attachment fitting.
"""
import numpy as np
from scipy.spatial import cKDTree


def regions(data):
    bones = data['bones']
    groups = []
    limbs = {part + '_' + side for part in ('hand', 'lowerarm', 'upperarm', 'thigh', 'calf', 'foot', 'ball')
             for side in ('l', 'r')}
    for bone in bones:
        index = bone['index']
        region = 'torso'
        while index >= 0:
            name = bones[index]['name']
            if name.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')):
                region = name.split('_')[0] + '_' + name[-1]
                break
            if name in limbs:
                region = name
                break
            if name in ('head', 'neck_01', 'neck_02'):
                region = 'neck'
                break
            index = bones[index]['parent']
        groups.append(region)
    result = []
    for weights in data['weights']:
        totals = {}
        for bone, weight in weights:
            group = groups[bone]
            totals[group] = totals.get(group, 0.) + weight
        result.append(max(totals, key=totals.get))
    return np.asarray(result)


def common_bind_map(data, target):
    source_bones = data['bones']
    target_bones = {bone['name']: bone for bone in target['bones']}
    mapped = []
    for bone in source_bones:
        ancestor = bone
        while ancestor['name'] not in target_bones and ancestor['parent'] >= 0:
            ancestor = source_bones[ancestor['parent']]
        if ancestor['name'] not in target_bones:
            raise RuntimeError('No common bind ancestor for ' + bone['name'])
        mapped.append((ancestor, target_bones[ancestor['name']]))
    return mapped


def bind_warp(data, target):
    points = np.asarray(data['positions'], float)
    result = np.zeros_like(points)
    mapped = common_bind_map(data, target)
    influences = [[] for _ in data['bones']]
    for vertex, weights in enumerate(data['weights']):
        for bone, weight in weights:
            influences[bone].append((vertex, weight))
    for bone, rows in enumerate(influences):
        if not rows:
            continue
        source, destination = mapped[bone]
        ids = np.asarray([row[0] for row in rows], int)
        weight = np.asarray([row[1] for row in rows])
        local = (points[ids] - source['position']) @ np.linalg.inv(np.asarray(source['axes']))
        moved = local @ np.asarray(destination['axes']) + destination['position']
        result[ids] += moved * weight[:, None]
    return result


def neighbors(query, query_regions, points, point_regions, count=8):
    ids = np.empty((len(query), count), int)
    weights = np.empty((len(query), count), float)
    for region in np.unique(query_regions):
        queries = np.flatnonzero(query_regions == region)
        candidates = np.flatnonzero(point_regions == region)
        if not len(candidates) and region == 'neck':
            # The full body stops at the head seam; its uppermost skin is
            # weighted to spine_05. Neck-bound collars share that torso field.
            candidates = np.flatnonzero(point_regions == 'torso')
        if not len(candidates):
            raise RuntimeError('Missing anatomical region: ' + region)
        distance, near = cKDTree(points[candidates]).query(query[queries], k=min(count, len(candidates)))
        if distance.ndim == 1:
            distance, near = distance[:, None], near[:, None]
        if distance.shape[1] < count:
            pad = count - distance.shape[1]
            distance = np.pad(distance, ((0, 0), (0, pad)), mode='edge')
            near = np.pad(near, ((0, 0), (0, pad)), mode='edge')
        ids[queries] = candidates[near]
        influence = 1. / np.maximum(distance, .05) ** 2
        weights[queries] = influence / influence.sum(axis=1)[:, None]
    return ids, weights


class BodySurfaceFit:
    def __init__(self, source_body, target_body, target_to_source=None):
        self.target = target_body
        self.points = bind_warp(source_body, target_body)
        self.regions = regions(source_body)
        target_points = np.asarray(target_body['positions'], float)
        target_regions = regions(target_body)
        if target_to_source is not None:
            paired_target = np.empty_like(self.points)
            paired_target[np.asarray(target_to_source, int)] = target_points
            residual = paired_target - self.points
        else:
            near, weights = neighbors(self.points, self.regions, target_points, target_regions, 4)
            residual = (target_points[near] * weights[:, :, None]).sum(axis=1) - self.points
        smooth, weights = neighbors(self.points, self.regions, self.points, self.regions, 12)
        self.residual = (residual[smooth] * weights[:, :, None]).sum(axis=1)

    def garment(self, source):
        moved = bind_warp(source, self.target)
        near, weights = neighbors(moved, regions(source), self.points, self.regions)
        moved += (self.residual[near] * weights[:, :, None]).sum(axis=1)
        mapped = common_bind_map(source, self.target)
        skin_weights = []
        for source_weights in source['weights']:
            totals = {}
            for bone, weight in source_weights:
                destination = mapped[bone][1]['index']
                totals[destination] = totals.get(destination, 0.) + weight
            total = sum(totals.values())
            skin_weights.append([[bone, weight / total] for bone, weight in totals.items()])
        return {'source': source['source'], 'positions': moved.tolist(), 'weights': skin_weights,
                'materials': source['materials'], 'target_skeleton': self.target['skeleton'],
                'method': 'native_bind_frames_and_region_surface_displacement'}
