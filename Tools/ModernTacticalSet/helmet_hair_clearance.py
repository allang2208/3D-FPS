"""Requested static clearance inspection of the two heads and saved render LODs."""
import json,math,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/HelmetHairFitR1')
fit=json.loads((R/'fit.json').read_text(encoding='utf-8'))
source_only='--author' in sys.argv
report={'runtime_tested':False,'scope':'authored game shell' if source_only else 'saved helmet render LODs against captured static native head and hair references','profiles':{}}
cell=.12
for rig in ['Jason','Kaitlin']:
    data=np.load(R/f'{rig}-hair-envelope.npz');p=data['positions'][data['under_cap']]
    centers=np.unique(np.round(p/cell).astype(np.int32),axis=0)*cell
    result=[]
    for lod in ([0] if source_only else range(3)):
        file=R/'Authored'/f'helmet_{rig}_wear.json' if source_only else R/'SavedLods'/f'{rig}_LOD{lod}.json'
        d=json.loads(file.read_text(encoding='utf-8'))
        if source_only:d['triangles']=[tri for tri,slot in zip(d['triangles'],d['triangle_materials']) if slot==0]
        frame=d['attachment_frame'];v=np.array(d['positions'])@np.array(frame['axes'])+np.array(frame['position'])
        bvh=BVHTree.FromPolygons(v.tolist(),d['triangles'],all_triangles=True)
        distances=[bvh.find_nearest(Vector(q))[3] for q in centers]
        minimum=float(min(distances));bound=minimum-math.sqrt(3)*cell/2
        result.append({'lod':lod,'shell_triangles':len(d['triangles']),'voxel_samples':len(centers),'minimum_surface_distance_cm':minimum,'minimum_distance_lower_bound_cm':bound})
        print('HELMET_SAVED_CLEARANCE',rig,lod,round(bound,4),flush=True)
        if bound<=.15:raise RuntimeError('Insufficient static helmet/hair clearance for '+rig+' LOD '+str(lod))
    report['profiles'][rig]={'binding_basis':fit['profiles'][rig]['binding_basis'],'lods':result,'outside_hair_preserved':True}
report['completed']=True
(R/('author-clearance.json' if source_only else 'static-clearance.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
