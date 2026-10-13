"""Offline per-emitter floor/range audit. No brightness or rendered-visibility claims."""
from pathlib import Path
import json,csv,math
import numpy as np

ROOT=Path(__file__).resolve().parent
report=json.loads((ROOT/'Receipts/floor-geometry.json').read_text('utf8'))

def surfaces(parts):
    batches=[];names=[]
    for p in parts:
        a=np.asarray(report['meshes'][p['mesh']],dtype=float).reshape((-1,3,3))
        if not len(a):continue
        a=(a*np.array(p['scale']))@np.array(p['axes'])+np.array(p['position'])
        batches.append(a);names.extend([p['mesh'].rsplit('/',1)[-1]]*len(a))
    return np.concatenate(batches) if batches else np.empty((0,3,3)),names

def below(point,triangles,names):
    if not len(triangles):return None
    p=np.array(point,dtype=float);a=triangles[:,0];b=triangles[:,1]-a;c=triangles[:,2]-a
    den=b[:,0]*c[:,1]-b[:,1]*c[:,0]
    valid=np.abs(den)>1e-6
    den=np.where(valid,den,1)
    dx=p[0]-a[:,0];dy=p[1]-a[:,1]
    s=(dx*c[:,1]-dy*c[:,0])/den;t=(b[:,0]*dy-b[:,1]*dx)/den
    z=a[:,2]+s*b[:,2]+t*c[:,2]
    mask=valid&(s>=-1e-5)&(t>=-1e-5)&(s+t<=1.00001)&(z<p[2]-5)
    ids=np.flatnonzero(mask)
    if not len(ids):return None
    i=ids[np.argmax(z[ids])]
    return dict(z=round(float(z[i]),3),mesh=names[i])

def audit(mid,lights,parts):
    tri,names=surfaces(parts);out=[]
    for i,l in enumerate(lights):
        p=l['position'];floor=below(p,tri,names)
        direction=l.get('forward',l.get('fixture_normal',[0,0,-1]))
        row=dict(module=mid,index=i,id=l.get('id',str(i)),type=l['type'],role=l.get('role',''),position=p,
            intensity=l['intensity'],radius=l['radius'],effective_radius=l.get('optimized_radius_cm',l['radius']),
            shadows=l.get('cast_shadows'),floor=floor,direction=direction)
        if floor:
            h=p[2]-floor['z'];r=row['effective_radius']
            row.update(height=round(h,3),range_height=round(r/h,3),axis_within_range=h<r,
                floor_disk_radius=round(math.sqrt(max(0,r*r-h*h)),2))
        out.append(row)
    return out

rows=[]
for m in report['catalog']['modules']:
    parts=report['modules'][m['id']]
    if m['id']=='FacilityTransit':
        parts=parts+[p for themes in report['portal_variants'].values() for p in next(iter(themes.values()))]
    rows+=audit(m['id'],m.get('lights',[]),parts)
rows+=audit('FixedStart',report['fixed']['lights'],report['fixed']['parts'])
(ROOT/'Receipts/range-audit.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
with (ROOT/'Receipts/range-audit.csv').open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.writer(f);writer.writerow(['module','index','id','type','role','intensity','height_cm','effective_radius_cm','range/height','shadows','floor_mesh'])
    for row in rows:writer.writerow([row['module'],row['index'],row['id'],row['type'],row['role'],row['intensity'],row.get('height'),row['effective_radius'],row.get('range_height'),row['shadows'],(row['floor'] or {}).get('mesh')])
for row in rows:
    if row['module']=='FacilityReceptionHall':continue
    print(row['module'],row['index'],row['id'],row['role'],row['type'],'h',row.get('height'),'range',row['effective_radius'],'ratio',row.get('range_height'),'shadows',row['shadows'],'int',row['intensity'])
