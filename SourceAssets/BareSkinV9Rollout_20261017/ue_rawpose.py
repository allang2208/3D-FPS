"""Reliable pose reads inside UE: the sequence's own data model (AnimationLibrary.get_bone_poses_for_frame).

AnimPose evaluation is not usable for authoring: RAW evaluation samples these sequencer data models at the
wrong rate, and the first COMPRESSED evaluations after a load can return the reference pose while
compression is still being built (that produced false "first-frame pops"). The data model is what every
write goes to and what compression is built from.
"""
import json
from pathlib import Path
import unreal as u

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017')
HIER = json.loads((R / 'Work/mesh_hierarchy.json').read_text())


def frame_count(seq):
    dmi = seq.get_editor_property('data_model_interface'); return dmi.get_number_of_keys(), dmi.get_frame_rate()


def local_poses(seq, mesh_path, frame, mesh=None):
    names = HIER[mesh_path]['names']
    poses = u.AnimationLibrary.get_bone_poses_for_frame(seq, names, frame, False, mesh)
    return dict(zip(names, poses))


def component(seq, mesh_path, frame, mesh=None, want=None):
    """Component-space transforms (unreal.Transform) for the bones in `want` (all if None)."""
    h = HIER[mesh_path]; loc = local_poses(seq, mesh_path, frame, mesh); comp = {}
    for n, p in zip(h['names'], h['parents']):
        comp[n] = loc[n] if p is None else loc[n].multiply(comp[p])
    return comp if want is None else {n: comp[n] for n in want}
