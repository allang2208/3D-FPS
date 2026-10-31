"""Check rooftop prop roots against saved roof planes, without gameplay."""
from pathlib import Path
import sys,json,collections
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'pythonlib'))
import numpy as np,shapely
from scipy.spatial.transform import Rotation
S=json.loads((R/'saved_scene.json').read_text());M=json.loads((R.parent/'publish_manifest.json').read_text())
layers=collections.defaultdict(list)
for row in S['rows']:
    if not row['native'] or '/Meshes/RoofSurfaces' not in row['mesh']:continue
    mesh=S['meshes'][row['mesh']]
    for t in row['transforms']:
        mat=Rotation.from_quat(t['q']).as_matrix()*np.array(t['s'])[None,:]
        verts=(np.asarray(mesh['vertices'])@mat.T+np.array(t['p']))/100
        tris=verts[np.array(mesh['triangles'],dtype=int)]
        for tri in tris:
            if np.ptp(tri[:,2])>.02:continue
            layers[round(float(tri[:,2].mean()),2)].append(shapely.Polygon(tri[:,:2]))
layers={z:shapely.union_all(ps).buffer(.1) for z,ps in layers.items()}
count=0;unsupported=[];far_height=[]
for row in M['rows']:
    if row['actor']!='NBPCG_Production' or not any(s in row['mesh'].lower() for s in ['kit_roof_','kit_antenna']):continue
    for i,t in enumerate(row['transforms']):
        count+=1;p=np.array(t['p'])/100
        support=[z for z,g in layers.items() if z<p[2]+.3 and shapely.contains_xy(g,p[0],p[1])]
        if not support:unsupported.append(dict(mesh=row['mesh'],component=row['component'],index=i,p=t['p']))
        elif p[2]-max(support)>6:far_height.append(dict(mesh=row['mesh'],component=row['component'],index=i,p=t['p'],height_above_roof_m=p[2]-max(support)))
result=dict(method='root XY against actual horizontal roof triangle footprints, 10cm tolerance; no exhaustive prop-pair triangle sweep',checked=count,roof_elevations=len(layers),unsupported_roots=unsupported,roots_over_6m_above_support=far_height)
(R/'roof_support.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('ROOF_SUPPORT',count,'unsupported',len(unsupported),'height_outliers',len(far_height),'elevations',len(layers),flush=True)
