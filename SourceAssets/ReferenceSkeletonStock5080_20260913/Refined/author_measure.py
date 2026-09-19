"""Read source surface coordinates required for local repairs and mount authoring."""
import json
from pathlib import Path
import numpy as np, trimesh
root=Path(__file__).resolve().parents[1]
m=trimesh.load(root/'seed_91379/textured_master_00001_.glb',force='mesh',process=False)
v=m.vertices[:,[0,2,1]].copy();v[:,1]*=-1
r={}
for name,limits in {'rim':[-.502,-.480,.09,.34],'front_side':[-.445,-.365,.17,.26],'lower_joint':[.075,.170,-.29,-.17],'rear_seam':[.425,.465,-.20,.32],'diagonal':[-.18,.04,-.09,.02]}.items():
    x0,x1,z0,z1=limits;pts=v[(v[:,0]>=x0)&(v[:,0]<=x1)&(v[:,2]>=z0)&(v[:,2]<=z1)]
    r[name]={'bounds':[pts.min(0).tolist(),pts.max(0).tolist()],'y_percentiles':np.percentile(pts[:,1],[0,10,25,50,75,90,100]).tolist()}
print(json.dumps(r,indent=2))
(Path(__file__).parent/'source_measurements.json').write_text(json.dumps(r,indent=2))
