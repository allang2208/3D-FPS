import bpy,numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent; R=O.parent/'M24StockJunctionR2_20261105'
bpy.ops.wm.open_mainfile(filepath=str(R/'M24_Meshy_JunctionR2.blend'),use_scripts=False)
col=bpy.data.collections['Native | fitted to M24']
def profile(ob,ys):
 m=ob.data;p=np.asarray([(ob.matrix_world@v.co)[:] for v in m.vertices])
 a=np.array([e.vertices[:] for e in m.edges]);s,e=p[a[:,0]],p[a[:,1]];print(ob.name)
 for y in ys:
    y*=.001;sel=((s[:,1]>y)!=(e[:,1]>y));k=s[sel];v=e[sel]-k
    if len(v):
        q=k+((y-k[:,1])/v[:,1])[:,None]*v
        print(round(y*1000),np.round(q.min(0)[[0,2]]*1000,1),np.round(q.max(0)[[0,2]]*1000,1))
for ob in col.objects: profile(ob,(-125,-110,-95,-85,-80,-76,-72,-68,-65,-32,-29,-25,-20,-16,-11,-5,0,5,15,25,38,52))
with bpy.data.libraries.load(str(O.parent/'M24StockContinuity20261031/M24_StockContinuity_Editable.blend')) as (x,y): y.objects=[s for s in x.objects if s=='M24_PistolGrip_Default']
for ob in y.objects:
 if ob:profile(ob,(-100,-90,-80,-70,-60,-50,-40,-30,-25,-20,-15,-10,0,10,20,30))
