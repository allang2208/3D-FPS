"""Preserve the complete display and stowed worn body without another decimation."""
import json
from pathlib import Path
import numpy as np

R=Path('D:/FPS3D/FPSGAME/SourceAssets/FarreachBackpack20261024/SlimFitR2_20261024')
for kind,source in [('Display','static_source.npz'),('Worn','worn_body.npz')]:
    data=np.load(R/'Authored'/source);faces=data['triangles']
    # Index the existing corner attributes together, retaining normal/UV seams.
    corners=np.concatenate([data['positions'][faces],data['normals'],data['uv']],axis=2).reshape(-1,8)
    attributes,index=np.unique(corners,axis=0,return_inverse=True)
    folder=R/'Authored'/kind;folder.mkdir(exist_ok=True)
    for name,values in [('positions',attributes[:,:3]),('normals',attributes[:,3:6]),('uv',attributes[:,6:])]:
        values.astype('<f4').tofile(folder/(name+'.bin'))
    index.astype('<i4').tofile(folder/'triangles.bin')
    np.zeros(len(faces),dtype='<i4').tofile(folder/'materials.bin')
    (folder/'buffers.json').write_text(json.dumps(dict(vertices=len(attributes),triangles=len(faces),
        geometry_convention='cross_e1_e2',source=str(R/'Authored'/source),decimation_applied=False),indent=2))
    print('FARREACH_BUFFERS_READY',kind,len(attributes),len(faces),flush=True)
