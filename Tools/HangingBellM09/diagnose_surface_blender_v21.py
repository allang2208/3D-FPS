"""Read-only authored mesh/UV/material diagnosis for the user's missing-surface report."""
import bpy,json,numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'SurfaceDiagnosisV21/Records'
report={}
for label,rel in [('before','CrownClawV15/Authoring/M09_Rigged_ClawV15.blend'),('current','ArmContinuityV16/Authoring/M09_Claw_Continuous_V16.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/rel))
    objects=[]
    for ob in sorted(bpy.context.scene.objects,key=lambda x:x.name):
        if ob.type!='MESH' or not ob.name.startswith('M09_'):continue
        me=ob.data;mi=np.empty(len(me.polygons),np.int32);me.polygons.foreach_get('material_index',mi)
        mats=[]
        for i,mat in enumerate(me.materials):
            images=[]
            if mat and mat.use_nodes:
                images=[{'image':n.image.name,'path':n.image.filepath,'packed':bool(n.image.packed_file),'size':list(n.image.size)} for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
            mats.append({'index':i,'name':mat.name if mat else None,'polygons':int((mi==i).sum()),'images':images})
        uv=[]
        for layer in me.uv_layers:
            a=np.empty((len(me.loops),2),np.float32);layer.data.foreach_get('uv',a.ravel())
            uv.append({'name':layer.name,'min':a.min(axis=0).tolist(),'max':a.max(axis=0).tolist(),'finite':bool(np.isfinite(a).all()),'unique_rounded_corners':int(len(np.unique(np.round(a,5),axis=0)))})
        objects.append({'name':ob.name,'vertices':len(me.vertices),'polygons':len(me.polygons),'materials':mats,'uv':uv})
    report[label]={'source':rel,'objects':objects}
(OUT/'blender_surface.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M09_SURFACE_SOURCE_DIAGNOSED')
