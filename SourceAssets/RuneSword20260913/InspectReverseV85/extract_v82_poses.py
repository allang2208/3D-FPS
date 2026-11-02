"""Bake the V82 author Inspect into rig-space bone matrices for the R6 hybrid (one file per grip variant).

blender -b --factory-startup --python extract_v82_poses.py -- [--long-grip]
Writes Work/v82_poses_<variant>.npz: names, parents, rest (bone matrix_local), pose[frame, bone, 4, 4] at 120 Hz.
"""
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).parent
LONG = '--long-grip' in sys.argv
VARIANT = 'LongGrip' if LONG else 'Standard'
SRC = HERE.parent / 'InspectFollowThroughV82' / ('AzureRunesword_InspectFollowThroughV82' + ('_LongGrip' if LONG else '') + '.blend')
bpy.ops.wm.open_mainfile(filepath=str(SRC))
s = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
act = rig.animation_data.action
first, last = int(act.frame_range[0]), int(act.frame_range[1])
names = [b.name for b in rig.data.bones]
rest = np.array([[list(r) for r in b.matrix_local] for b in rig.data.bones])
pose = np.zeros((last - first + 1, len(names), 4, 4))
for f in range(first, last + 1):
    s.frame_set(f)
    for i, n in enumerate(names):
        pose[f - first, i] = np.array([list(r) for r in rig.pose.bones[n].matrix])
parents = [b.parent.name if b.parent else '' for b in rig.data.bones]
out = HERE / 'Work' / ('v82_poses_%s.npz' % VARIANT)
np.savez_compressed(out, names=np.array(names), parents=np.array(parents), rest=rest, pose=pose,
                    fps=s.render.fps / s.render.fps_base, world=np.array([list(r) for r in rig.matrix_world]))
print('V82_POSES', VARIANT, pose.shape, out)
