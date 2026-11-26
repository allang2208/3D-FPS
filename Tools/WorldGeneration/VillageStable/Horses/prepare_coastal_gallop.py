"""Transfer the approved CoastalGallop cycle to the stable controller's nominal speed."""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from prepare_horse import Horse


def prepare(study, output):
    fit = json.loads((study / 'fit.json').read_text(encoding='utf-8'))
    horse = Horse((study / 'Warhorse_CoastalGallop.glb').read_bytes())
    clip = horse.clips['CoastalGallop']
    indices = horse.doc['skins'][0]['joints']
    # Keep every original key on the resident package's native 30 Hz compression grid.
    # RateScale restores the actual gait cadence without baking a second interpolation.
    frame_rate = 30
    authored_frames = frames = horse.doc['accessors'][clip['samplers'][0]['input']]['count'] - 1
    marks = np.arange(authored_frames) / authored_frames
    _, tracks = horse.sample(clip, marks)
    for i in range(len(horse.nodes)):
        tracks.setdefault((i, 'translation'), horse.local(i, 'translation', {}, authored_frames).copy())
    seat = horse.world_pos(horse.index['saddle_socket'], tracks, authored_frames)
    # The riding component already settles on the low saddle at 1/4 cycle.
    offset = (marks[np.argmin(seat[:, 1])] - .25) % 1.
    phase = (np.arange(frames + 1) / frames + offset) % 1.
    phase[-1] = phase[0]
    _, tracks = horse.sample(clip, phase)
    # Source +Z is forward and +Y is up. The imported UE horse faces +Y and uses +Z for up.
    axes = np.eye(3)[[0, 2, 1]]
    def world_delta(i):
        posed = horse.world_rot(i, tracks, len(phase))
        bind = horse.world_rot(i, {}, 1)
        return Rotation.from_matrix(axes @ (posed * bind.inv()).as_matrix() @ axes)
    deltas = {i: world_delta(i) for i in indices}
    bones = {}
    for i in indices:
        name = horse.nodes[i]['name']
        parent = horse.parent.get(i)
        parent_delta = deltas.get(parent, Rotation.identity())
        turn = (parent_delta.inv() * deltas[i]).as_quat()
        for k in range(1, len(turn)):
            if turn[k] @ turn[k-1] < 0:
                turn[k] *= -1
        row = dict(parent=horse.nodes[parent]['name'] if parent in deltas else None,
                   rotation=turn.round(9).tolist())
        if (i, 'translation') in tracks:
            shift = tracks[i,'translation'] - horse.local(i, 'translation', {}, 1)
            if np.max(np.abs(shift)) > 1e-6:
                shift = horse.world_rot(parent, {}, 1).apply(shift) @ axes.T * 100
                row['translation_cm'] = shift.round(7).tolist()
        bones[name] = row
    contacts = {name: ((v['video_plant_s'] - fit['video_start_s']) / fit['video_cycle_s'] - offset) % 1.
                for name,v in fit['limb_landmarks'].items()}
    content = dict(source='CoastalGallopR14', frames=frames, rate=frame_rate, contacts=contacts,
                   phase_offset=offset, stride_m=fit['estimated_stride_m'],
                   rate_scale=(frames/frame_rate)*6.6/fit['estimated_stride_m'], bones=bones)
    with gzip.open(output, 'wt', encoding='utf-8') as stream:
        json.dump(content, stream, separators=(',', ':'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('study', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    prepare(args.study, args.output)

