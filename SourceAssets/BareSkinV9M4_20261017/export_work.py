"""System Python: pack the V9 rest mesh for Blender (no scipy there). Writes Work/mesh.npz.

Blender space = UE with Y mirrored; triangle order is reversed when needed so Blender faces point
outward. 'perm' maps Blender loop order back to snapshot corner order.
"""
import numpy as np
from m4data import M4, R

m = M4(); g = np.load(R / 'Work/geometry.npz'); X = g['welded'][m.weld]
B = X * np.array([1, -1, 1]); Nb = m.N.mean(axis=1) * np.array([1, -1, 1])
fn = np.cross(B[m.T[:, 1]] - B[m.T[:, 0]], B[m.T[:, 2]] - B[m.T[:, 0]])
inward = np.einsum('ij,ij->i', fn, Nb) < 0
perm = np.array([0, 2, 1]) if inward.mean() > .5 else np.array([0, 1, 2])
masks = m.old_masks()
np.savez(R / 'Work/mesh.npz', X=B, T=m.T[:, perm], UV=m.UV[:, perm], region=m.region, section=m.section, perm=perm,
         weld=m.weld, nail=masks[:, 0], palm=masks[:, 3], crease=masks[:, 2])
print('EXPORT', 'reversed' if perm[1] == 2 else 'kept', 'inward share %.3f' % inward.mean())
