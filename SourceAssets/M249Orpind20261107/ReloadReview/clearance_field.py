"""Surface volumes used by the game hand-pose authoring solve, in native mesh cm."""
import numpy as np
import trimesh
from scipy.ndimage import binary_fill_holes,distance_transform_edt

class ClearanceField:
    def __init__(self, points, faces, pitch=.32):
        mesh=trimesh.Trimesh(points,faces,process=False)
        vox=mesh.voxelized(pitch)
        occupied=np.pad(binary_fill_holes(vox.matrix),3)
        self.origin=vox.transform[:3,3]-3*pitch
        self.pitch=pitch
        self.dist=((distance_transform_edt(~occupied)-distance_transform_edt(occupied))*pitch).astype(np.float32)

    def costs(self, points):
        ix=np.rint((points-self.origin)/self.pitch).astype(int)
        inside=np.all((ix>=0)&(ix<self.dist.shape),axis=1)
        if not inside.any():return 0.
        distance=self.dist[tuple(ix[inside].T)]
        overlap=np.maximum(.36-distance,0)
        return float(np.sum(overlap**2)/len(points)+.04*np.max(overlap)**2)
