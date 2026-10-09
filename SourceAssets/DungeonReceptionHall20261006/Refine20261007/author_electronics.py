"""Reuse accepted workshop equipment, soften cable bends and preserve its source anchor."""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2];PARENT=PROJECT/'SourceAssets/StationWorkshop20261003'
sys.path.insert(0,str(ROOT/'Scripts'));import office_geometry as g
BASE='/Game/Dungeons/ReceptionHall20261006/Refine20261007';g.BASE=BASE;g.OUT=ROOT/'Authored'
source=(PARENT/'Scripts/author_workshop.py').read_text('utf8')
for k in ('Keycaps','Legends','Display'):g.MATS[k]=bpy.data.materials.new('RS_'+k)
for k in g.MATS:g.MAP[k]=BASE+'/Materials/M_RH2_Office_'+k
exec(compile(source[source.index('REGIONS='):source.index('# Workshop fits')],'accepted_office_helpers','exec'))
stocktube=g.tube
def soft_tube(points,r=.007,mat='Steel'):
    if 2<len(points)<25:
        ps=[Vector(p) for p in points];out=[ps[0]]
        for i in range(1,len(ps)-1):
            p=ps[i];left=(p-ps[i-1]);right=ps[i+1]-p
            reach=min(left.length*.36,right.length*.36,.09 if r<.004 else .035)
            a=p-left.normalized()*reach;b=p+right.normalized()*reach
            for j in range(13):t=j/12;out.append((1-t)**2*a+2*t*(1-t)*p+t*t*b)
        out.append(ps[-1]);points=out
    return stocktube(points,r,mat)
g.tube=soft_tube
refined=(PARENT/'RefineV2/Scripts/author_refine.py').read_text('utf8')
exec(compile(refined[refined.index('# Preserve conduits'):refined.index('# Each bounded state')],'accepted_equipment_curved_leads','exec'))
for o in bpy.context.scene.objects:o.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/ReceptionElectronics.blend'))
records=[]
for item in g.records:
    item['mesh']=item.pop('asset');item['sha256']=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest();item['cast_shadow']=True;records.append(item)
(ROOT/'electronics.json').write_text(json.dumps(dict(meshes=records,keylabels=keylabels),ensure_ascii=False,indent=2),encoding='utf8')
print('RECEPTION_ELECTRONICS_EXPORTED',len(records),flush=True)
