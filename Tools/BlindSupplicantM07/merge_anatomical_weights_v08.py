"""Merge independently authored palm/digit and hindleg fields onto the body."""
import json
from pathlib import Path
import numpy as np

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV08')


def merge():
    path = ROOT/'original_skin_weights_v08.npz'
    source = dict(np.load(path))
    record_path = ROOT/'original_skin_weights_v08.json'
    record = json.loads(record_path.read_text(encoding='utf-8'))
    names = record['bone_names']
    namespace = {n: i for i, n in enumerate(names)}
    indices, weights = source['bone_indices'], source['bone_weights']
    overlays = []
    for folder, filename in [('hands', 'hand_weights_v08.npz'), ('legs', 'leg_weights_v08.npz')]:
        overlay_path = ROOT/folder/filename if folder == 'legs' else ROOT.parent/'RecoveryOriginalV07/hands/hand_weights_v07.npz'
        overlay = np.load(overlay_path)
        ids = overlay['source_vertex_ids']
        other_names = overlay['bone_names'].tolist()
        other_indices = overlay['indices'] if folder == 'hands' else overlay['bone_indices']
        other_weights = overlay['weights']
        alpha = overlay['blend_alpha'] if folder == 'hands' else np.ones(len(ids))
        field = np.zeros((len(ids), len(names)), dtype=np.float32)
        rows = np.repeat(np.arange(len(ids)), indices.shape[1])
        np.add.at(field, (rows, indices[ids].ravel()), (weights[ids]*(1-alpha[:, None])).ravel())
        valid = other_indices >= 0
        mapping = np.asarray([namespace[n] for n in other_names])
        overlay_rows = np.broadcast_to(np.arange(len(ids))[:, None], other_indices.shape)
        np.add.at(field, (overlay_rows[valid], mapping[other_indices[valid]]),
                  (other_weights*alpha[:, None])[valid])
        strongest = np.argpartition(field, -8, axis=1)[:, -8:]
        values = np.take_along_axis(field, strongest, axis=1)
        order = np.argsort(-values, axis=1)
        strongest = np.take_along_axis(strongest, order, axis=1)
        values = np.take_along_axis(values, order, axis=1)
        values /= np.maximum(values.sum(axis=1, keepdims=True), 1.e-10)
        indices[ids] = strongest
        weights[ids] = values
        overlays.append({'source': str(overlay_path), 'source_vertices': len(ids),
                         'blend': 'Original wrist boundary transition' if folder == 'hands' else 'Anatomical pelvis-to-foot field'})
    source['bone_indices'], source['bone_weights'] = indices, weights
    np.savez_compressed(path, **source)
    record.update({'anatomical_overlays': overlays,
        'method': 'Original body family field plus surface-branch isolated human metacarpal/finger weights and original biped knee/ankle/toe support weights',
        'weight_budget': 8, 'tested': False})
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print('M07_V08_HAND_AND_HINDLEG_WEIGHTS_MERGED', flush=True)


if __name__ == '__main__':
    merge()
