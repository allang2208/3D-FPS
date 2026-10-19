"""Update the editable capri construction to match the authored waist fit."""
from pathlib import Path
import sys
import bpy
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerSet20261018'
sys.path.insert(0,str(P/'Tools/SmokeGreyCapri'));from waist_fit import deform
source=R/'Before/SourceAssets/SmokeGreyCapri20261004/Capri_Construction.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
for ob in bpy.data.objects:
    if ob.type!='MESH':continue
    points=np.array([(v.co.x*100,-v.co.y*100,v.co.z*100) for v in ob.data.vertices]);points=deform(points)
    for v,p in zip(ob.data.vertices,points):v.co=(p[0]*.01,-p[1]*.01,p[2]*.01)
    ob.data.update()
bpy.context.scene['WaistFit']='NativeWaistFit20261018'
bpy.ops.wm.save_as_mainfile(filepath=str(P/'SourceAssets/SmokeGreyCapri20261004/Capri_Construction.blend'))
print('CAPRI_CONSTRUCTION_WAIST_UPDATED',flush=True)
