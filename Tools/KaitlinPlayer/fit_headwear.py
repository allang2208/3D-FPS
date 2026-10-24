"""Calibrate each existing headpiece to Kaitlin; retain its own tip rig."""
import copy
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
body = read(WORK / 'FitInputs/player_body.json')
captured = read(WORK / 'FitInputs/captured.json')
source = read(WORK / 'FitInputs' / captured[body['heads']['jason']['mesh']]['file'])
target = read(WORK / 'NativeGeometry/SKM_MHC_Kaitlin_FaceMesh.json')
source_body = read(WORK / 'FitInputs' / captured[body['body_mesh']]['file'])
target_body = read(WORK / 'NativeGeometry/MHC_Kaitlin_Body.json')
sb = next(b for b in source_body['bones'] if b['name'] == 'head')
tb = next(b for b in target_body['bones'] if b['name'] == 'head')
sp, tp = np.asarray(source['positions']), np.asarray(target['positions'])
sh, th = np.asarray(sb['position']), np.asarray(tb['position'])
height_ratio = (tp[:, 2].max() - th[2]) / (sp[:, 2].max() - sh[2])
recipes, dimensions = {}, {}
for item, recipe in body['head_equipment'].items():
    old = recipe['fits']['jason']
    world_mount = np.asarray(old['location']) @ sb['axes'] + sh
    target_z = th[2] + (world_mount[2] - sh[2]) * height_ratio
    source_band = sp[np.abs(sp[:, 2] - world_mount[2]) < 1.5]
    target_band = tp[np.abs(tp[:, 2] - target_z) < 1.5]
    if min(len(source_band), len(target_band)) < 8:
        raise RuntimeError('Headpiece needs a wider measured fit band: ' + item)
    # Retain the accepted clearance while matching this headpiece's opening.
    source_lo, source_hi = source_band[:, :2].min(0), source_band[:, :2].max(0)
    target_lo, target_hi = target_band[:, :2].min(0), target_band[:, :2].max(0)
    ratio = np.r_[(target_hi - target_lo + .6) / (source_hi - source_lo + .6), height_ratio]
    pitch, yaw, roll = old['rotation']
    old_rotation = Rotation.from_euler('xyz', [-roll, -pitch, yaw], degrees=True).as_matrix().T
    linear = np.diag(old['scale']) @ old_rotation @ np.asarray(sb['axes']) @ np.diag(ratio) @ np.linalg.inv(tb['axes'])
    scale = np.linalg.norm(linear, axis=1)
    frame = linear / scale[:, None]
    left, _, right = np.linalg.svd(frame)
    frame = left @ right
    r, p, y = Rotation.from_matrix(frame.T).as_euler('xyz', degrees=True)
    old_center = (source_hi + source_lo) * .5
    new_center = (target_hi + target_lo) * .5
    new_mount = np.r_[(world_mount[:2] - old_center) * ratio[:2] + new_center, target_z]
    local = (new_mount - th) @ np.linalg.inv(tb['axes'])
    result = copy.deepcopy(recipe)
    result['fits'] = {'kaitlin': {'location': local.tolist(), 'rotation': [-float(p), float(y), -float(r)], 'scale': scale.tolist()}}
    recipes[item] = result
    dimensions[item] = {'source_opening_z': float(world_mount[2]), 'target_opening_z': float(target_z),
                        'measured_head_ratio': ratio.tolist(), 'source_band_vertices': len(source_band),
                        'target_band_vertices': len(target_band), 'tip_rig_preserved': True}
output = WORK / 'Headwear'
output.mkdir(exist_ok=True)
(output / 'mounts.json').write_text(json.dumps(recipes, indent=2), encoding='utf-8')
(output / 'authoring_dimensions.json').write_text(json.dumps(dimensions, indent=2), encoding='utf-8')
print('KAITLIN_HEADWEAR_FITS_AUTHORED', len(recipes), flush=True)
