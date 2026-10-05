"""One continuous death deformation field, with local metal reinforcement."""
from pathlib import Path
import itertools, json
import numpy as np
from scipy.spatial import cKDTree

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004')
OUT=ROOT/'ProductionV19'
for directory in ('Exports','Records','Authoring'):
    (OUT/directory).mkdir(parents=True,exist_ok=True)

cage=json.loads((ROOT/'ProductionV17/Exports/cage.json').read_text())
count=cage['soft_node_count']
cage['nodes']=cage['nodes'][:count]
cage['hardware']=[]
points=np.array(cage['nodes'])
source=np.load(ROOT/'ProductionV11/Records/hardware_source.npz')
# Use actual metal faces. The old feathered owner region includes long strips
# of adjoining flesh and must not define a rigid object's extent.
metal_ids=np.unique(source['f'][source['metal']])
tree=cKDTree(source['p'][metal_ids])
edges=np.unique(np.sort(np.array([pair for tet in cage['tetrahedra']
    for pair in itertools.combinations(tet,2)]),axis=1),axis=0)
samples=points[edges[:,0],None,:]*(1-np.array([.25,.5,.75])[None,:,None])+points[edges[:,1],None,:]*np.array([.25,.5,.75])[None,:,None]
distance,_=tree.query(samples.reshape(-1,3))
reinforced=edges[np.min(distance.reshape(-1,3),axis=1)<.045]
cage['reinforced_edges']=reinforced.tolist()
cage['embedding']='one positive tetrahedral field for all surface vertices; local metal strain resistance'
cage['source']='ProductionV15; V17 cage topology retained, independent hardware frames removed'
(OUT/'Exports/cage.json').write_text(json.dumps(cage,separators=(',',':'))+'\n',encoding='utf8')

with (ROOT/'ProductionV17/Exports/embedding.bin').open('rb') as stream:
    header=np.fromfile(stream,dtype='<i4',count=2)
    binding=np.fromfile(stream,dtype='<f4').reshape(tuple(header))
# All UV/material-cut duplicates already share the same tetrahedron/weights.
# Do not mix these with an independently moving rigid transform at the seam.
binding[:,11]=-1
binding[:,12]=0
with (OUT/'Exports/embedding.bin').open('wb') as stream:
    header.tofile(stream);binding.tofile(stream)

with (OUT/'Authoring/M14_ContinuousProxy_v19.obj').open('w',encoding='utf8') as stream:
    for x,y,z in points: stream.write(f'v {x:.7f} {y:.7f} {z:.7f}\n')
    for a,b in reinforced: stream.write(f'l {a+1} {b+1}\n')

report=dict(soft_nodes=count,tetrahedra=len(cage['tetrahedra']),
    edges=len(edges),reinforced_edges=len(reinforced),independent_hardware_nodes=0,
    source_vertices=len(source['p']),source_triangles=len(source['f']),
    geometry_removed=0,surface_rows=len(binding),tested=False,rendered=False,
    prior_faults=['rigid proxy corner starts 18.9cm below ground',
                  'hardware-to-tissue tethers up to 139.9cm',
                  'rigid and soft skin at shared attachment follow different fields'])
(OUT/'Records/authoring.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('M14_V19_CONTINUOUS_CORPSE_AUTHORED',json.dumps(report))
